from __future__ import annotations

from pathlib import Path

TARGET = Path(__file__).resolve().parents[1] / "backend/asie_local_api.py"

IMPORT_ANCHOR = "from backend.acceptance import build_acceptance_pack\n"
IMPORT_REPLACEMENT = (
    "from backend.acceptance import build_acceptance_pack\n"
    "from backend.bootstrap_security import authorize_local_bootstrap, legacy_local_operator_allowed\n"
)

PRINCIPAL_OLD = '''        if principal is None and REPO.user_count() == 0 and organization_id in {None, LEGACY_ORGANIZATION_ID}:
            return Principal(
                user_id="local_legacy_operator",
                session_id="local_legacy_session",
                organization_id=LEGACY_ORGANIZATION_ID,
                role="organization_owner",
            )
'''

PRINCIPAL_NEW = '''        if (
            principal is None
            and REPO.user_count() == 0
            and organization_id in {None, LEGACY_ORGANIZATION_ID}
            and legacy_local_operator_allowed(self.client_address[0] if self.client_address else None)
        ):
            return Principal(
                user_id="local_legacy_operator",
                session_id="local_legacy_session",
                organization_id=LEGACY_ORGANIZATION_ID,
                role="organization_owner",
            )
'''

BOOTSTRAP_OLD = '''            if path == "/api/auth/local-bootstrap":
                if REPO.user_count() != 0:
                    write_error(self, "local_bootstrap_already_completed", 409)
                    return
                user = REPO.create_user(email=str(payload.get("email") or ""), display_name=str(payload.get("display_name") or ""), password=str(payload.get("password") or ""), platform_role="platform_admin")
                organization = REPO.create_organization(name=str(payload.get("organization_name") or "مساحة ASIE المحلية"), owner_user_id=user["user_id"])
                token, _authenticated_user = REPO.create_session(email=user["email"], password=str(payload.get("password") or ""))
                REPO.audit(actor_user_id=user["user_id"], organization_id=organization["organization_id"], action="local_bootstrap", target_type="organization", target_id=organization["organization_id"], result="allowed")
                write_json(self, {"access_token": token, "token_type": "Bearer", "user": user, "organization": organization, "external_access_enabled": False}, 201)
                return
'''

BOOTSTRAP_NEW = '''            if path == "/api/auth/local-bootstrap":
                bootstrap_authorization = authorize_local_bootstrap(
                    client_host=self.client_address[0] if self.client_address else None,
                    provided_secret=self.headers.get("X-ASIE-Bootstrap-Secret"),
                )
                if not bootstrap_authorization.allowed:
                    REPO.audit(
                        actor_user_id=None,
                        organization_id=None,
                        action="local_bootstrap",
                        target_type="platform",
                        target_id="initial_platform_admin",
                        result="denied",
                        reason=bootstrap_authorization.code,
                        correlation_id=self.request_id,
                    )
                    write_error(self, bootstrap_authorization.code, bootstrap_authorization.status)
                    return
                if REPO.user_count() != 0:
                    write_error(self, "local_bootstrap_already_completed", 409)
                    return
                user = REPO.create_user(email=str(payload.get("email") or ""), display_name=str(payload.get("display_name") or ""), password=str(payload.get("password") or ""), platform_role="platform_admin")
                organization = REPO.create_organization(name=str(payload.get("organization_name") or "مساحة ASIE المحلية"), owner_user_id=user["user_id"])
                token, _authenticated_user = REPO.create_session(email=user["email"], password=str(payload.get("password") or ""))
                REPO.audit(actor_user_id=user["user_id"], organization_id=organization["organization_id"], action="local_bootstrap", target_type="organization", target_id=organization["organization_id"], result="allowed", reason="explicit_loopback_development_bootstrap", correlation_id=self.request_id)
                write_json(self, {"access_token": token, "token_type": "Bearer", "user": user, "organization": organization, "external_access_enabled": False}, 201)
                return
'''


def replace_exactly_once(source: str, old: str, new: str, label: str) -> str:
    occurrences = source.count(old)
    if occurrences != 1:
        raise RuntimeError(f"{label}_anchor_count={occurrences}")
    return source.replace(old, new, 1)


def main() -> int:
    source = TARGET.read_text(encoding="utf-8")
    source = replace_exactly_once(source, IMPORT_ANCHOR, IMPORT_REPLACEMENT, "bootstrap_security_import")
    source = replace_exactly_once(source, PRINCIPAL_OLD, PRINCIPAL_NEW, "legacy_principal")
    source = replace_exactly_once(source, BOOTSTRAP_OLD, BOOTSTRAP_NEW, "local_bootstrap_route")
    TARGET.write_text(source, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
