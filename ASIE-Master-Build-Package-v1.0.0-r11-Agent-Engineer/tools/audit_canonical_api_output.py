from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "registry" / "asie-canonical-api-output.v1.json"
API_TS_PATH = ROOT / "src" / "api.ts"
BACKEND_API_PATH = ROOT / "backend" / "asie_local_api.py"
TYPE_AUGMENTATION_PATH = ROOT / "src" / "contracts.canonical.d.ts"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.snapshot_assembly import REQUIRED_MODULE_OUTPUTS  # noqa: E402

EXPORT_ASYNC_FUNCTION = re.compile(r"export\s+async\s+function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")
INTERFACE_BLOCK = re.compile(r"interface\s+([A-Za-z_][A-Za-z0-9_]*)\s*\{(.*?)\n\s*\}", re.DOTALL)
VALID_METHODS = {"GET", "POST", "PATCH", "PUT", "DELETE"}


class AuditFailure(AssertionError):
    pass


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise AuditFailure(f"{path.name} root must be an object")
    return value


def _assert_unique(values: list[Any], label: str) -> None:
    duplicates = sorted({str(value) for value in values if values.count(value) > 1})
    if duplicates:
        raise AuditFailure(f"duplicate {label}: {', '.join(duplicates)}")


def _frontend_function_bodies(source: str) -> dict[str, str]:
    matches = list(EXPORT_ASYNC_FUNCTION.finditer(source))
    bodies: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(source)
        bodies[match.group(1)] = source[match.start():end]
    return bodies


def _backend_method_sections(source: str) -> dict[str, str]:
    markers = {
        "GET": source.index("    def _dispatch_get(self) -> None:"),
        "POST": source.index("    def do_POST(self) -> None:"),
        "PATCH": source.index("    def do_PATCH(self) -> None:"),
        "PUT": source.index("    def do_PUT(self) -> None:"),
        "DELETE": source.index("    def do_DELETE(self) -> None:"),
    }
    ordered = ["GET", "POST", "PATCH", "PUT", "DELETE"]
    sections: dict[str, str] = {}
    for index, method in enumerate(ordered):
        start = markers[method]
        end = markers[ordered[index + 1]] if index + 1 < len(ordered) else len(source)
        sections[method] = source[start:end]
    return sections


def _path_fragments(path_template: str) -> list[str]:
    return [fragment for fragment in re.split(r"\{[^}]+\}", path_template) if len(fragment) > 1]


def _assert_frontend_binding(route: dict[str, Any], bodies: dict[str, str]) -> None:
    method = route["method"]
    path_template = route["path"]
    for function_name in route.get("frontend_functions", []):
        body = bodies.get(function_name)
        if body is None:
            raise AuditFailure(f"registered frontend function is missing: {function_name}")
        missing_fragments = [fragment for fragment in _path_fragments(path_template) if fragment not in body]
        if missing_fragments:
            raise AuditFailure(
                f"frontend function {function_name} does not contain path fragments {missing_fragments} for {path_template}"
            )
        if method != "GET" and f'method: "{method}"' not in body:
            raise AuditFailure(f"frontend function {function_name} does not declare HTTP method {method}")
        if method == "GET" and re.search(r'method:\s*"(?:POST|PATCH|PUT|DELETE)"', body):
            raise AuditFailure(f"frontend GET function {function_name} declares a mutating method")


def _assert_backend_binding(route: dict[str, Any], method_sections: dict[str, str]) -> None:
    method = route["method"]
    if method not in method_sections:
        raise AuditFailure(f"unsupported method in registry: {method}")
    section = method_sections[method]
    for evidence in route.get("backend_evidence", []):
        if evidence not in section:
            raise AuditFailure(
                f"backend evidence missing for {method} {route['path']}: {evidence}"
            )


def _assert_type_requirements(register: dict[str, Any]) -> None:
    source = TYPE_AUGMENTATION_PATH.read_text(encoding="utf-8")
    blocks = {name: body for name, body in INTERFACE_BLOCK.findall(source)}
    for interface_name, fields in register.get("public_type_requirements", {}).items():
        body = blocks.get(interface_name)
        if body is None:
            raise AuditFailure(f"canonical TypeScript augmentation missing interface {interface_name}")
        for field in fields:
            if not re.search(rf"\b{re.escape(field)}\s*:", body):
                raise AuditFailure(f"{interface_name} missing canonical field {field}")


def _assert_surface_labels(register: dict[str, Any]) -> None:
    scan = register.get("surface_scan", {})
    violations: list[str] = []
    for relative_path in scan.get("files", []):
        path = ROOT / relative_path
        if not path.exists():
            raise AuditFailure(f"surface scan file missing: {relative_path}")
        lines = path.read_text(encoding="utf-8").splitlines()
        for line_number, line in enumerate(lines, start=1):
            for alias in scan.get("prohibited_aliases", []):
                if alias in line:
                    violations.append(f"{relative_path}:{line_number}:{alias}")
    if violations:
        raise AuditFailure("prohibited aliases found on active surfaces: " + ", ".join(violations))


def run_audit() -> dict[str, int]:
    register = _load_json(REGISTRY_PATH)
    api_source = API_TS_PATH.read_text(encoding="utf-8")
    backend_source = BACKEND_API_PATH.read_text(encoding="utf-8")
    frontend_bodies = _frontend_function_bodies(api_source)
    method_sections = _backend_method_sections(backend_source)

    frontend_routes = list(register.get("frontend_routes", []))
    backend_only_routes = list(register.get("backend_only_routes", []))
    all_routes = frontend_routes + backend_only_routes

    route_ids = [route["route_id"] for route in all_routes]
    route_keys = [(route["method"], route["path"]) for route in all_routes]
    _assert_unique(route_ids, "route ids")
    _assert_unique(route_keys, "method/path identities")

    for route in all_routes:
        if route.get("method") not in VALID_METHODS:
            raise AuditFailure(f"invalid method for {route.get('route_id')}: {route.get('method')}")
        if not str(route.get("path", "")).startswith("/api/"):
            raise AuditFailure(f"non-canonical API path: {route.get('path')}")
        _assert_backend_binding(route, method_sections)

    for route in frontend_routes:
        _assert_frontend_binding(route, frontend_bodies)

    discovered_frontend_functions = set(frontend_bodies)
    declared_frontend_functions = {
        function_name
        for route in frontend_routes
        for function_name in route.get("frontend_functions", [])
    }
    if discovered_frontend_functions != declared_frontend_functions:
        missing = sorted(discovered_frontend_functions - declared_frontend_functions)
        stale = sorted(declared_frontend_functions - discovered_frontend_functions)
        raise AuditFailure(f"frontend API function inventory mismatch; missing={missing}; stale={stale}")

    output_mappings = list(register.get("sealed_output_mappings", []))
    declared_output_keys = {item["sealed_output_key"] for item in output_mappings}
    if declared_output_keys != set(REQUIRED_MODULE_OUTPUTS):
        missing = sorted(set(REQUIRED_MODULE_OUTPUTS) - declared_output_keys)
        stale = sorted(declared_output_keys - set(REQUIRED_MODULE_OUTPUTS))
        raise AuditFailure(f"sealed output mapping mismatch; missing={missing}; stale={stale}")

    for mapping in output_mappings:
        output_key = mapping["sealed_output_key"]
        expected_module, expected_contract = REQUIRED_MODULE_OUTPUTS[output_key]
        if mapping.get("module_id") != expected_module:
            raise AuditFailure(f"{output_key} module mismatch")
        if mapping.get("result_contract") != expected_contract:
            raise AuditFailure(f"{output_key} contract mismatch")
        for payload_key in mapping.get("module_payload_keys", []):
            if f'"{payload_key}"' not in backend_source:
                raise AuditFailure(f"{output_key} payload key is not present in backend source: {payload_key}")
        for projection_key in mapping.get("public_projection_keys", []):
            if f'"{projection_key}"' not in backend_source:
                raise AuditFailure(f"{output_key} projection key is not present in backend source: {projection_key}")

    _assert_type_requirements(register)
    _assert_surface_labels(register)

    return {
        "frontend_routes": len(frontend_routes),
        "backend_only_routes": len(backend_only_routes),
        "frontend_functions": len(discovered_frontend_functions),
        "sealed_output_mappings": len(output_mappings),
        "public_type_interfaces": len(register.get("public_type_requirements", {})),
        "surface_files": len(register.get("surface_scan", {}).get("files", [])),
    }


def main() -> int:
    try:
        counts = run_audit()
    except (AuditFailure, KeyError, TypeError, ValueError, OSError, json.JSONDecodeError) as exc:
        print(f"CANONICAL API/OUTPUT AUDIT: FAIL\n{exc}", file=sys.stderr)
        return 1

    print("CANONICAL API/OUTPUT AUDIT: PASS")
    for key, value in counts.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
