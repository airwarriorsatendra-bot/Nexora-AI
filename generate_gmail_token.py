"""Authorize Gmail and securely store its refresh token in the local .env."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]
REFRESH_TOKEN_KEY = b"GMAIL_REFRESH_TOKEN="


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
            "Repository root .env is not git-ignored; refusing to store Gmail credentials."
        )


def _split_line_ending(line: bytes) -> tuple[bytes, bytes]:
    if line.endswith(b"\r\n"):
        return line[:-2], b"\r\n"
    if line.endswith((b"\n", b"\r")):
        return line[:-1], line[-1:]
    return line, b""


def _preferred_line_ending(lines: list[bytes]) -> bytes:
    for line in lines:
        _, ending = _split_line_ending(line)
        if ending:
            return ending
    return os.linesep.encode("ascii")


def _store_refresh_token(env_path: Path, refresh_token: str) -> None:
    original = env_path.read_bytes() if env_path.exists() else b""
    lines = original.splitlines(keepends=True)
    replacement = REFRESH_TOKEN_KEY + refresh_token.encode("utf-8")
    found = False
    updated_lines: list[bytes] = []

    for line in lines:
        content, ending = _split_line_ending(line)
        if content.startswith(REFRESH_TOKEN_KEY):
            updated_lines.append(replacement + ending)
            found = True
        else:
            updated_lines.append(line)

    updated = b"".join(updated_lines)
    if not found:
        if updated and not updated.endswith((b"\n", b"\r")):
            updated += _preferred_line_ending(lines)
        updated += replacement

    env_path.write_bytes(updated)


def main() -> None:
    repository_root = Path(__file__).resolve().parent
    env_path = repository_root / ".env"

    flow = InstalledAppFlow.from_client_secrets_file(
        repository_root / "client_secret_gmail.json",
        scopes=SCOPES,
    )
    credentials = flow.run_local_server(
        host="localhost",
        port=0,
        open_browser=True,
        access_type="offline",
        prompt="consent",
        authorization_prompt_message="Opening Gmail authorization...",
        success_message="Gmail authorization successful. You can close this window.",
    )

    if not credentials.refresh_token:
        raise RuntimeError(
            "No Gmail refresh token was returned. Re-authorization may be required."
        )

    _verify_env_is_ignored(repository_root)
    _store_refresh_token(env_path, credentials.refresh_token)

    print("Gmail authorization succeeded.")
    print("GMAIL_REFRESH_TOKEN was securely stored in the ignored .env file.")


if __name__ == "__main__":
    main()
