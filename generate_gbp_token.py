"""Authorize Google Business Profile and securely store its refresh token."""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = ["https://www.googleapis.com/auth/business.manage"]
REFRESH_TOKEN_NAME = "GBP_REFRESH_TOKEN"
REFRESH_TOKEN_PATTERN = re.compile(r"^\s*GBP_REFRESH_TOKEN\s*=")


def _verify_env_is_ignored(repository_root: Path) -> None:
    result = subprocess.run(
        ["git", "check-ignore", "--quiet", "--", ".env"],
        cwd=repository_root,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Repository root .env is not git-ignored; refusing to store GBP credentials."
        )


def _line_ending(line: str) -> str:
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith("\n"):
        return "\n"
    if line.endswith("\r"):
        return "\r"
    return ""


def _preferred_line_ending(lines: list[str]) -> str:
    return next((ending for line in lines if (ending := _line_ending(line))), os.linesep)


def _store_refresh_token(env_path: Path, refresh_token: str) -> None:
    original = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    lines = original.splitlines(keepends=True)
    replacement = f"{REFRESH_TOKEN_NAME}={refresh_token}"
    found = False
    updated_lines: list[str] = []

    for line in lines:
        content = line.removesuffix(_line_ending(line))
        if REFRESH_TOKEN_PATTERN.match(content):
            updated_lines.append(replacement + _line_ending(line))
            found = True
        else:
            updated_lines.append(line)

    updated = "".join(updated_lines)
    if not found:
        if updated and not updated.endswith(("\n", "\r")):
            updated += _preferred_line_ending(lines)
        updated += replacement

    with env_path.open("w", encoding="utf-8", newline="") as env_file:
        env_file.write(updated)


def _refresh_token_is_present(env_path: Path) -> bool:
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if REFRESH_TOKEN_PATTERN.match(line):
            return bool(line.split("=", 1)[1].strip())
    return False


def main() -> None:
    repository_root = Path(__file__).resolve().parent
    env_path = repository_root / ".env"

    flow = InstalledAppFlow.from_client_secrets_file(
        repository_root / "client_secret_gbp.json",
        scopes=SCOPES,
    )
    credentials = flow.run_local_server(
        host="localhost",
        port=0,
        open_browser=True,
        access_type="offline",
        prompt="consent",
        success_message="GBP authorization successful. You can close this window.",
    )

    refresh_token = credentials.refresh_token
    if not refresh_token:
        raise RuntimeError(
            "No GBP refresh token was returned. Re-authorization may be required."
        )

    _verify_env_is_ignored(repository_root)
    _store_refresh_token(env_path, refresh_token)
    if not _refresh_token_is_present(env_path):
        raise RuntimeError("GBP_REFRESH_TOKEN presence verification failed.")

    print("Google Business Profile authorization succeeded.")
    print("GBP_REFRESH_TOKEN was securely stored in the ignored .env file.")
    print("GBP_REFRESH_TOKEN presence verification: PASSED")


if __name__ == "__main__":
    main()
