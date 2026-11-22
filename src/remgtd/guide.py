"""Parse the Step Guide markdown (content/step_guide.md) into cards for the View."""

from __future__ import annotations

import re
from importlib import resources
from typing import Any

_STEP = re.compile(r"^## (\d+)\. (.+?)\s*$")
_SCALAR = re.compile(r"^\*\*(Purpose|Start point|End point|Live status):\*\*\s*(.*)$")
_LIST = re.compile(r"^\*\*(Key questions|Advice)\*\*\s*(.*)$")
_BULLET = re.compile(r"^(\s*)(?:[-*]|\d+\.)\s+(.*)$")

_SCALAR_KEYS = {"Purpose": "purpose", "Start point": "start", "End point": "end", "Live status": "status"}
_LIST_KEYS = {"Key questions": "questions", "Advice": "advice"}


def load_text() -> str:
    return (resources.files("remgtd") / "content" / "step_guide.md").read_text(encoding="utf-8")


def parse(markdown: str) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    card: dict[str, Any] | None = None
    current: str | None = None
    for line in markdown.splitlines():
        if m := _STEP.match(line):
            card = {
                "n": int(m[1]),
                "name": m[2],
                "id": m[2].strip().lower(),
                "purpose": "",
                "start": "",
                "end": "",
                "status": "",
                "questions": [],
                "questionsNote": "",
                "advice": [],
                "adviceNote": "",
            }
            cards.append(card)
            current = None
            continue
        if card is None:
            continue
        if m := _SCALAR.match(line):
            card[_SCALAR_KEYS[m[1]]] = m[2].strip()
            current = None
        elif m := _LIST.match(line):
            current = _LIST_KEYS[m[1]]
            card[f"{current}Note"] = m[2].strip(" ,:").strip()
        elif current and (m := _BULLET.match(line)):
            card[current].append({"text": m[2].strip(), "depth": len(m[1].expandtabs(2)) // 2})
        elif line.startswith("---"):
            current = None
    return cards


def cards() -> list[dict[str, Any]]:
    return parse(load_text())
