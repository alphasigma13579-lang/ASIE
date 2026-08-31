from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from backend.repository import Repository


def create_invite(
    *,
    repository: Repository,
    email: str,
    organization_name: str,
    expires_in_hours: int,
) -> dict[str, object]:
    return repository.create_beta_registration_invite(
        email=email,
        organization_name=organization_name,
        expires_in_hours=expires_in_hours,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Create one email-bound ASIE closed-beta registration invite.")
    parser.add_argument("--database", required=True, help="Path to the ASIE SQLite database on the host.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--organization-name", required=True)
    parser.add_argument("--expires-in-hours", type=int, default=168)
    parser.add_argument("--confirm-invite", action="store_true", help="Required acknowledgement before issuing a bearer invite token.")
    args = parser.parse_args()
    if not args.confirm_invite:
        parser.error("confirm_invite_required")
    invite = create_invite(
        repository=Repository(Path(args.database)),
        email=args.email,
        organization_name=args.organization_name,
        expires_in_hours=args.expires_in_hours,
    )
    print(json.dumps(invite, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
