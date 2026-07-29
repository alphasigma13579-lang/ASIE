from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from pathlib import Path
from typing import Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.contracts import DB_PATH
from backend.repository import Repository

PASSWORD_ENVIRONMENT_VARIABLE = "ASIE_INITIAL_ADMIN_PASSWORD"


def create_initial_platform_admin(
    *,
    repository: Repository,
    email: str,
    display_name: str,
    password: str,
    organization_name: str,
) -> dict[str, object]:
    if repository.user_count() != 0:
        raise RuntimeError("initial_admin_already_exists")
    if not organization_name.strip():
        raise ValueError("organization_name_required")

    user = repository.create_user(
        email=email,
        display_name=display_name,
        password=password,
        platform_role="platform_admin",
    )
    organization = repository.create_organization(
        name=organization_name,
        owner_user_id=str(user["user_id"]),
    )
    repository.audit(
        actor_user_id=str(user["user_id"]),
        organization_id=str(organization["organization_id"]),
        action="initial_platform_admin.create",
        target_type="organization",
        target_id=str(organization["organization_id"]),
        result="allowed",
        reason="local_cli_only",
    )
    return {
        "created": True,
        "user": user,
        "organization": organization,
        "session_created": False,
        "login_required": True,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Create the first ASIE platform administrator from the local host without exposing an HTTP bootstrap route."
    )
    parser.add_argument("--database", type=Path, default=DB_PATH)
    parser.add_argument("--email", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--organization-name", required=True)
    parser.add_argument(
        "--confirm-empty-database",
        action="store_true",
        help="Required acknowledgement that this command is only for a database containing zero users.",
    )
    args = parser.parse_args(argv)

    if not args.confirm_empty_database:
        parser.error("--confirm-empty-database is required")

    password = os.environ.get(PASSWORD_ENVIRONMENT_VARIABLE)
    if password is None:
        password = getpass.getpass("Initial platform administrator password: ")

    repository = Repository(args.database)
    result = create_initial_platform_admin(
        repository=repository,
        email=args.email,
        display_name=args.display_name,
        password=password,
        organization_name=args.organization_name,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
