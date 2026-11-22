"""Build remgtd.alfredworkflow: keyword `gtd` → `remgtd open`.

Run with:  uv run integrations/alfred/build.py
"""

from __future__ import annotations

import plistlib
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
KEYWORD_UID = "6F1C1D2E-6E2B-4C1A-9B1E-52E0D1A7C001"
SCRIPT_UID = "6F1C1D2E-6E2B-4C1A-9B1E-52E0D1A7C002"

SCRIPT = """\
# uv installs tools into ~/.local/bin; Alfred doesn't load your shell profile.
export PATH="$HOME/.local/bin:$HOME/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
remgtd open
"""

INFO = {
    "bundleid": "io.github.remgtd",
    "category": "Productivity",
    "connections": {
        KEYWORD_UID: [
            {"destinationuid": SCRIPT_UID, "modifiers": 0, "modifiersubtext": "", "vitoclose": False}
        ]
    },
    "createdby": "remgtd",
    "description": "Open Reminders and the remgtd View side by side",
    "disabled": False,
    "name": "remgtd",
    "objects": [
        {
            "config": {
                "argumenttype": 2,
                "keyword": "gtd",
                "subtext": "Reminders on the left, the remgtd View on the right",
                "text": "Open remgtd",
                "withspace": False,
            },
            "type": "alfred.workflow.input.keyword",
            "uid": KEYWORD_UID,
            "version": 1,
        },
        {
            "config": {
                "concurrently": False,
                "escaping": 0,
                "script": SCRIPT,
                "scriptargtype": 1,
                "scriptfile": "",
                "type": 0,
            },
            "type": "alfred.workflow.action.script",
            "uid": SCRIPT_UID,
            "version": 2,
        },
    ],
    "readme": "Type `gtd` in Alfred. Requires remgtd on PATH (`uv tool install git+https://github.com/jonasrk/remgtd`).",
    "uidata": {KEYWORD_UID: {"xpos": 50, "ypos": 50}, SCRIPT_UID: {"xpos": 250, "ypos": 50}},
    "version": "0.1.0",
    "webaddress": "https://github.com/jonasrk/remgtd",
}


def main() -> None:
    plist = plistlib.dumps(INFO, sort_keys=True)
    (HERE / "info.plist").write_bytes(plist)
    out = HERE / "remgtd.alfredworkflow"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        info = zipfile.ZipInfo("info.plist", date_time=(2026, 1, 1, 0, 0, 0))
        zf.writestr(info, plist)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
