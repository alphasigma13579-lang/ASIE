from __future__ import annotations

import csv
import base64
import zipfile
from io import BytesIO, StringIO
from statistics import mean
from typing import Any
from xml.etree import ElementTree

from backend.contracts import json_dumps, new_id, now_iso

DATASET_STATES = {"draft", "review_required", "approved_for_use", "rejected", "archived"}
IMPORT_METHODS = {"manual_csv", "manual_json", "manual_table"}
APPROVED_DATASET_REQUIRED_FIELDS = [
    "dataset_id",
    "source_id",
    "title",
    "publisher",
    "license_snapshot_ref",
    "terms_hash",
    "classification",
    "pdpl_check",
    "attribution",
    "human_review_decision",
]


def normalize_dataset_payload(payload: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    if any(payload.get(key) for key in ["fetch_url", "crawler_url", "api_url", "external_fetch_url"]):
        raise PermissionError("datasets support manual local import only; external fetch is blocked")
    import_method = str(payload.get("import_method") or (existing or {}).get("import_method") or "manual_table")
    if import_method not in IMPORT_METHODS:
        raise PermissionError("import_method must be manual_csv, manual_json, or manual_table")
    review_status = str(payload.get("review_status") or (existing or {}).get("review_status") or "draft")
    if review_status not in DATASET_STATES:
        raise ValueError("review_status must be draft, review_required, approved_for_use, rejected, or archived")

    rows = _extract_rows(payload, import_method)
    if not rows and existing:
        columns = list(existing.get("columns", []))
        preview = list(existing.get("preview", []))
        row_count = int(existing.get("row_count") or 0)
        profile = dict(existing.get("notes", {}).get("profile", {}))
        quality_review = dict(existing.get("notes", {}).get("quality_review", {}))
    else:
        columns = _columns_for_rows(rows, payload.get("columns"))
        preview = [{key: row.get(key, "") for key in columns} for row in rows[:5]]
        row_count = len(rows)
        profile = _profile_rows(rows, columns)
        quality_review = build_dataset_quality_review(rows, columns, profile)

    now = now_iso()
    dataset = {
        "dataset_id": str(payload.get("dataset_id") or (existing or {}).get("dataset_id") or new_id("dataset")),
        "source_id": str(payload.get("source_id") or (existing or {}).get("source_id") or ""),
        "title": str(payload.get("title") or (existing or {}).get("title") or "Untitled local dataset"),
        "publisher": str(payload.get("publisher") or (existing or {}).get("publisher") or "Unknown publisher"),
        "import_method": import_method,
        "review_status": review_status,
        "human_review_decision": str(
            payload.get("human_review_decision") or (existing or {}).get("human_review_decision") or ""
        ),
        "license_snapshot_ref": str(
            payload.get("license_snapshot_ref") or (existing or {}).get("license_snapshot_ref") or ""
        ),
        "terms_hash": str(payload.get("terms_hash") or (existing or {}).get("terms_hash") or ""),
        "classification": str(payload.get("classification") or (existing or {}).get("classification") or ""),
        "pdpl_check": str(payload.get("pdpl_check") or (existing or {}).get("pdpl_check") or ""),
        "attribution": str(payload.get("attribution") or (existing or {}).get("attribution") or ""),
        "row_count": row_count,
        "columns_json": json_dumps(columns),
        "preview_json": json_dumps(preview),
        "notes_json": json_dumps(
            {
                "notes": payload.get("notes") or (existing or {}).get("notes", {}).get("notes", ""),
                "profile": profile,
                "quality_review": quality_review,
                "external_fetch_allowed": False,
            }
        ),
        "created_at": str((existing or {}).get("created_at") or now),
        "updated_at": now,
    }
    if review_status == "approved_for_use":
        missing = [field for field in APPROVED_DATASET_REQUIRED_FIELDS if not dataset.get(field)]
        if missing:
            raise PermissionError(f"approved datasets require complete review metadata. Missing: {', '.join(missing)}")
        if dataset["human_review_decision"] != "approved":
            raise PermissionError("approved datasets require human_review_decision=approved")
    return dataset


def dataset_quality_gate(dataset: dict[str, Any], source: dict[str, Any] | None) -> dict[str, Any]:
    reasons: list[str] = []
    quality_review = dataset_quality_review(dataset)
    if source is None:
        reasons.append("source_not_found")
    elif source.get("state") != "enabled" or source.get("reviewer_decision") != "approved":
        reasons.append("source_not_enabled_by_human_review")
    for field in APPROVED_DATASET_REQUIRED_FIELDS:
        if not dataset.get(field):
            reasons.append(f"missing_{field}")
    if dataset.get("review_status") != "approved_for_use":
        reasons.append("dataset_not_approved_for_use")
    if dataset.get("human_review_decision") != "approved":
        reasons.append("dataset_missing_human_approval")
    quality_reasons: list[str] = []
    if quality_review["status"] == "rejected":
        quality_reasons.extend(quality_review["reasons"])
    status = "passed"
    can_use = True
    if reasons:
        status = "failed"
        can_use = False
    elif quality_review["status"] == "rejected":
        status = "rejected"
        can_use = False
    elif quality_review["status"] == "warning":
        status = "warning"
    return {
        "dataset_id": dataset.get("dataset_id", ""),
        "source_id": dataset.get("source_id", ""),
        "status": status,
        "can_use_for_assumptions": can_use,
        "reasons": reasons + quality_reasons,
        "quality_review": quality_review,
        "checks": {
            "source_reviewed": bool(source and source.get("state") == "enabled" and source.get("reviewer_decision") == "approved"),
            "license_snapshot": bool(dataset.get("license_snapshot_ref")),
            "terms_hash": bool(dataset.get("terms_hash")),
            "classification": bool(dataset.get("classification")),
            "pdpl_check": bool(dataset.get("pdpl_check")),
            "attribution": bool(dataset.get("attribution")),
            "human_review": dataset.get("human_review_decision") == "approved",
            "data_quality_review": quality_review["status"] in {"passed", "warning"},
            "external_fetch_enabled": False,
        },
    }


def dataset_quality_review(dataset: dict[str, Any]) -> dict[str, Any]:
    notes = dataset.get("notes") or {}
    quality_review = notes.get("quality_review") or {}
    if quality_review:
        return quality_review
    profile = notes.get("profile") or {}
    row_count = int(dataset.get("row_count") or 0)
    columns = list(dataset.get("columns") or profile.keys())
    return build_dataset_quality_review([], columns, profile, row_count=row_count)


def build_dataset_quality_review(
    rows: list[dict[str, Any]],
    columns: list[str],
    profile: dict[str, Any],
    row_count: int | None = None,
) -> dict[str, Any]:
    row_count = len(rows) if row_count is None else row_count
    duplicate_count = _duplicate_row_count(rows, columns) if rows else 0
    duplicate_ratio = (duplicate_count / row_count) if row_count else 0
    max_missing_ratio = 0.0
    columns_with_missing: list[str] = []
    numeric_columns: list[str] = []
    text_columns: list[str] = []
    mixed_type_columns: list[str] = []
    outlier_counts: dict[str, int] = {}
    for column in columns:
        column_profile = profile.get(column) or {}
        missing_count = int(column_profile.get("missing_count") or 0)
        missing_ratio = (missing_count / row_count) if row_count else 0
        if missing_count:
            columns_with_missing.append(column)
        max_missing_ratio = max(max_missing_ratio, missing_ratio)
        inferred_type = str(column_profile.get("inferred_type") or "text")
        if inferred_type == "number":
            numeric_columns.append(column)
        elif inferred_type == "mixed":
            mixed_type_columns.append(column)
        else:
            text_columns.append(column)
        if int(column_profile.get("outlier_count") or 0):
            outlier_counts[column] = int(column_profile.get("outlier_count") or 0)

    reasons: list[str] = []
    warning_reasons: list[str] = []
    if row_count == 0:
        reasons.append("empty_dataset")
    if max_missing_ratio >= 0.8:
        reasons.append("missing_values_above_80_percent")
    elif max_missing_ratio > 0.2:
        warning_reasons.append("missing_values_above_20_percent")
    if duplicate_ratio >= 0.5 and row_count >= 2:
        reasons.append("duplicate_rows_above_50_percent")
    elif duplicate_count:
        warning_reasons.append("duplicate_rows_detected")
    if mixed_type_columns:
        warning_reasons.append("mixed_column_types_detected")
    if outlier_counts:
        warning_reasons.append("numeric_outliers_detected")

    status = "rejected" if reasons else "warning" if warning_reasons else "passed"
    return {
        "status": status,
        "row_count": row_count,
        "column_count": len(columns),
        "duplicate_row_count": duplicate_count,
        "duplicate_ratio": round(duplicate_ratio, 4),
        "max_missing_ratio": round(max_missing_ratio, 4),
        "columns_with_missing": columns_with_missing,
        "numeric_columns": numeric_columns,
        "text_columns": text_columns,
        "mixed_type_columns": mixed_type_columns,
        "outlier_counts": outlier_counts,
        "reasons": reasons + warning_reasons,
    }


def normalize_evidence_link(project_id: str, payload: dict[str, Any], existing: dict[str, Any] | None = None) -> dict[str, Any]:
    now = now_iso()
    decision = str(payload.get("human_review_decision") or (existing or {}).get("human_review_decision") or "")
    if decision != "approved":
        raise PermissionError("evidence links require human_review_decision=approved")
    target_type = str(payload.get("target_type") or (existing or {}).get("target_type") or "assumption")
    if target_type not in {"assumption", "sector_criterion"}:
        raise ValueError("target_type must be assumption or sector_criterion")
    target_id = str(
        payload.get("target_id")
        or payload.get("assumption_id")
        or (existing or {}).get("target_id")
        or (existing or {}).get("assumption_id")
        or ""
    )
    if not target_id:
        raise ValueError("evidence links require target_id or assumption_id")
    return {
        "evidence_link_id": str(
            payload.get("evidence_link_id") or (existing or {}).get("evidence_link_id") or new_id("evidence")
        ),
        "project_id": project_id,
        "target_type": target_type,
        "target_id": target_id,
        "assumption_id": target_id if target_type == "assumption" else target_id,
        "dataset_id": str(payload.get("dataset_id") or (existing or {}).get("dataset_id") or ""),
        "transformation_id": str(payload.get("transformation_id") or (existing or {}).get("transformation_id") or ""),
        "evidence_ref": str(payload.get("evidence_ref") or (existing or {}).get("evidence_ref") or ""),
        "transformation_note": str(
            payload.get("transformation_note") or (existing or {}).get("transformation_note") or "manual_review_only"
        ),
        "human_review_decision": decision,
        "created_at": str((existing or {}).get("created_at") or now),
        "updated_at": now,
    }


def normalize_file_import_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if any(payload.get(key) for key in ["fetch_url", "crawler_url", "api_url", "external_fetch_url"]):
        raise PermissionError("file import supports local files only; external fetch is blocked")
    file_name = str(payload.get("file_name") or "local-data.csv")
    extension = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if extension == "csv" or payload.get("csv_text"):
        csv_text = str(payload.get("csv_text") or "")
        return {
            **payload,
            "title": payload.get("title") or file_name,
            "import_method": "manual_csv",
            "csv_text": csv_text,
            "notes": _merge_import_notes(payload, file_name, "csv"),
        }
    if extension == "xlsx" or str(payload.get("file_type") or "").endswith("spreadsheetml.sheet"):
        rows = rows_from_xlsx_base64(str(payload.get("file_base64") or ""))
        return {
            **payload,
            "title": payload.get("title") or file_name,
            "import_method": "manual_table",
            "rows": rows,
            "notes": _merge_import_notes(payload, file_name, "xlsx"),
        }
    raise ValueError("unsupported_local_file_type")


def rows_from_xlsx_base64(file_base64: str) -> list[dict[str, Any]]:
    if not file_base64:
        raise ValueError("xlsx_file_base64_required")
    raw = base64.b64decode(file_base64)
    with zipfile.ZipFile(BytesIO(raw)) as archive:
        shared_strings = _xlsx_shared_strings(archive)
        sheet_path = _xlsx_first_sheet_path(archive)
        with archive.open(sheet_path) as sheet_file:
            root = ElementTree.parse(sheet_file).getroot()
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    matrix: list[list[str]] = []
    for row in root.findall(".//x:sheetData/x:row", namespace):
        values: list[str] = []
        for cell in row.findall("x:c", namespace):
            value = _xlsx_cell_value(cell, shared_strings, namespace)
            values.append(value)
        matrix.append(values)
    if not matrix:
        return []
    headers = [str(value or f"column_{index + 1}") for index, value in enumerate(matrix[0])]
    rows: list[dict[str, Any]] = []
    for values in matrix[1:]:
        rows.append({headers[index]: values[index] if index < len(values) else "" for index in range(len(headers))})
    return rows


def _extract_rows(payload: dict[str, Any], import_method: str) -> list[dict[str, Any]]:
    if import_method == "manual_csv" and payload.get("csv_text"):
        reader = csv.DictReader(StringIO(str(payload["csv_text"])))
        return [dict(row) for row in reader]
    raw_rows = payload.get("rows") or payload.get("json_rows") or []
    if isinstance(raw_rows, list):
        return [dict(row) for row in raw_rows if isinstance(row, dict)]
    return []


def _merge_import_notes(payload: dict[str, Any], file_name: str, file_type: str) -> str:
    notes = str(payload.get("notes") or "")
    return f"{notes}\nlocal_file_import:{file_type}:{file_name}".strip()


def _xlsx_shared_strings(archive: zipfile.ZipFile) -> list[str]:
    try:
        with archive.open("xl/sharedStrings.xml") as shared_file:
            root = ElementTree.parse(shared_file).getroot()
    except KeyError:
        return []
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    values = []
    for item in root.findall("x:si", namespace):
        text_parts = [node.text or "" for node in item.findall(".//x:t", namespace)]
        values.append("".join(text_parts))
    return values


def _xlsx_first_sheet_path(archive: zipfile.ZipFile) -> str:
    candidates = sorted(name for name in archive.namelist() if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"))
    if not candidates:
        raise ValueError("xlsx_sheet_not_found")
    return candidates[0]


def _xlsx_cell_value(cell: ElementTree.Element, shared_strings: list[str], namespace: dict[str, str]) -> str:
    value_node = cell.find("x:v", namespace)
    inline_node = cell.find("x:is/x:t", namespace)
    if inline_node is not None:
        return inline_node.text or ""
    if value_node is None:
        return ""
    raw_value = value_node.text or ""
    if cell.attrib.get("t") == "s":
        try:
            return shared_strings[int(raw_value)]
        except (IndexError, ValueError):
            return ""
    return raw_value


def _columns_for_rows(rows: list[dict[str, Any]], provided: Any) -> list[str]:
    if isinstance(provided, list) and provided:
        return [str(item) for item in provided]
    columns: list[str] = []
    for row in rows:
        for key in row:
            if key not in columns:
                columns.append(str(key))
    return columns


def _profile_rows(rows: list[dict[str, Any]], columns: list[str]) -> dict[str, Any]:
    numeric: dict[str, list[float]] = {column: [] for column in columns}
    missing: dict[str, int] = {column: 0 for column in columns}
    non_null: dict[str, int] = {column: 0 for column in columns}
    for row in rows:
        for column in columns:
            value = row.get(column)
            if value in {None, ""}:
                missing[column] += 1
                continue
            non_null[column] += 1
            try:
                numeric[column].append(float(value))
            except (TypeError, ValueError):
                pass
    return {
        column: {
            "row_count": len(rows),
            "non_null_count": non_null[column],
            "numeric_count": len(values),
            "missing_count": missing[column],
            "min": min(values) if values else None,
            "max": max(values) if values else None,
            "mean": mean(values) if values else None,
            "outlier_count": _outlier_count(values),
            "inferred_type": _inferred_type(non_null[column], len(values)),
        }
        for column, values in numeric.items()
    }


def _inferred_type(non_null_count: int, numeric_count: int) -> str:
    if non_null_count and numeric_count == non_null_count:
        return "number"
    if numeric_count:
        return "mixed"
    return "text"


def _outlier_count(values: list[float]) -> int:
    if len(values) < 4:
        return 0
    ordered = sorted(values)
    q1 = ordered[len(ordered) // 4]
    q3 = ordered[(len(ordered) * 3) // 4]
    iqr = q3 - q1
    if iqr == 0:
        return 0
    low = q1 - (1.5 * iqr)
    high = q3 + (1.5 * iqr)
    return sum(1 for value in values if value < low or value > high)


def _duplicate_row_count(rows: list[dict[str, Any]], columns: list[str]) -> int:
    seen: set[tuple[str, ...]] = set()
    duplicates = 0
    for row in rows:
        signature = tuple(str(row.get(column, "")) for column in columns)
        if signature in seen:
            duplicates += 1
        else:
            seen.add(signature)
    return duplicates
