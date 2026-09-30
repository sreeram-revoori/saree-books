"""Write .streamlit/secrets.toml from the Google key file, and check it works.

Usage (in this folder):
    .venv/bin/python make_secrets.py ~/Downloads/saree-books-xxxxxxxx.json

It asks for the Google Sheet link and an app password, writes
.streamlit/secrets.toml (never uploaded to GitHub), tries to open the sheet,
and can copy the settings to the clipboard for Streamlit's Secrets box.
"""
from __future__ import annotations

import getpass
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
TARGET = HERE / ".streamlit" / "secrets.toml"
KEY_FIELDS = [
    "type", "project_id", "private_key_id", "private_key", "client_email", "client_id",
    "auth_uri", "token_uri", "auth_provider_x509_cert_url", "client_x509_cert_url",
    "universe_domain",
]


def toml_str(value: str) -> str:
    # A JSON string is also a valid TOML basic string (same escapes for \n, \", \\).
    return json.dumps(str(value), ensure_ascii=False)


def is_ignored_by_git(path: Path) -> bool:
    r = subprocess.run(["git", "check-ignore", "-q", str(path)], cwd=HERE, capture_output=True)
    return r.returncode == 0


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    key_file = Path(sys.argv[1]).expanduser()
    try:
        key = json.loads(key_file.read_text())
    except (OSError, ValueError) as exc:
        sys.exit(f"Couldn't read the key file: {exc}")
    if key.get("type") != "service_account" or "private_key" not in key:
        sys.exit("That doesn't look like a Google service account key (.json) file.")

    if not is_ignored_by_git(TARGET):
        sys.exit("Safety stop: .streamlit/secrets.toml isn't excluded from GitHub (.gitignore). Not writing it.")

    sheet = input("Google Sheet link: ").strip()
    if "docs.google.com/spreadsheets/d/" not in sheet:
        sys.exit("That doesn't look like a Google Sheet link.")
    password = getpass.getpass("App password (typing is hidden; leave empty for none): ")
    if password and getpass.getpass("Type it again: ") != password:
        sys.exit("The two passwords didn't match — nothing was written.")

    lines = [
        "# Real secrets — this file stays on this computer and is never uploaded to GitHub.",
        f"spreadsheet = {toml_str(sheet)}",
    ]
    if password:
        lines.append(f"app_password = {toml_str(password)}")
    lines += ["", "[gcp_service_account]"]
    lines += [f"{k} = {toml_str(key[k])}" for k in KEY_FIELDS if k in key]
    text = "\n".join(lines) + "\n"

    TARGET.parent.mkdir(exist_ok=True)
    TARGET.write_text(text)
    TARGET.chmod(0o600)
    print(f"\n✓ Wrote {TARGET.relative_to(HERE)}")

    print("Checking that the app can open the Google Sheet…")
    try:
        import gspread

        book = gspread.service_account_from_dict(key).open_by_url(sheet)
        print(f"✓ Connected to “{book.title}”. The app on this computer will now use it.")
    except Exception as exc:
        print(f"✗ Couldn't open the sheet: {exc}")
        print(f"  Check the sheet is shared with {key.get('client_email')} as Editor,")
        print("  and that the Google Sheets and Google Drive APIs are enabled (DEPLOY.md, Step 2).")

    if sys.platform == "darwin" and input("\nCopy these settings for Streamlit's Secrets box? [y/N] ").lower().startswith("y"):
        subprocess.run(["pbcopy"], input=text.encode(), check=True)
        print("✓ Copied — paste into Streamlit Cloud → your app → Settings → Secrets, then Save.")
    print("\nYou can now delete the downloaded .json key file (the settings file has everything).")


if __name__ == "__main__":
    main()
