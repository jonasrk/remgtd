"""A tiny builder for synthetic Reminders data. Tests never use real data."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import pytest

from remgtd import model, rules
from remgtd.config import Config
from remgtd.snapshot import Snapshot

NOW = datetime(2026, 1, 31, 12, 0)

# Context Kind group → tags with a smart list in it.
DEFAULT_CONTEXTS = {
    "Agenda": ["alex", "sam"],
    "Place/Tool": ["home", "computer"],
    "Condition": ["quick"],
}


class World:
    def __init__(self, cfg: Config | None = None, contexts: dict[str, list[str]] | None = None) -> None:
        self.cfg = cfg or Config()
        self.contexts = DEFAULT_CONTEXTS if contexts is None else contexts
        self.reminders: list[dict[str, Any]] = []
        self.sections: dict[int, str] = {}
        self.extra_lists: list[str] = []
        self.smart_lists: list[dict[str, Any]] = []
        self._next = 1

    def add(
        self,
        title: str,
        role: str,
        *,
        tags: tuple[str, ...] = (),
        flagged: bool = False,
        parent: int | None = None,
        age_days: float = 1,
        completed: bool = False,
        completed_days_ago: float | None = None,
        due: datetime | None = None,
        section: str | None = None,
        list_name: str | None = None,
    ) -> int:
        rid = self._next
        self._next += 1
        self.reminders.append(
            {
                "id": rid,
                "title": title,
                "list": list_name or getattr(self.cfg.lists, role),
                "completed": completed,
                "flagged": flagged,
                "tags": list(tags) or None,
                "parentID": parent,
                "isSubtask": parent is not None,
                "createdDate": (NOW - timedelta(days=age_days)).isoformat(),
                "completionDate": (NOW - timedelta(days=completed_days_ago)).isoformat()
                if completed_days_ago is not None
                else None,
                "dueDate": due.isoformat() if due else None,
                "deepLink": f"x-apple-reminderkit://REMCDReminder/{rid}",
            }
        )
        if section:
            self.sections[rid] = section
        return rid

    def snapshot(self) -> Snapshot:
        children = [
            {"id": 10 + i, "title": getattr(self.cfg.lists, role), "isGroup": False, "children": []}
            for i, role in enumerate(model.ROLES)
        ] + [{"id": 50 + i, "title": t, "isGroup": False, "children": []} for i, t in enumerate(self.extra_lists)]
        lists: list[dict[str, Any]] = [{"id": 1, "title": self.cfg.group, "isGroup": True, "children": children}]
        smart: list[dict[str, Any]] = list(self.smart_lists)
        for gi, (group, tags) in enumerate(self.contexts.items()):
            gid = 100 + gi
            lists.append({"id": gid, "title": group, "isGroup": True, "children": []})
            for ti, tag in enumerate(tags):
                smart.append(
                    {
                        "id": gid * 10 + ti,
                        "name": f"#{tag}",
                        "kind": "custom",
                        "smartListType": "com.apple.reminders.smartlist.custom",
                        "parentListId": gid,
                        "filterJSON": {"hashtags": {"hashtags": {"operation": "or", "include": [tag], "exclude": []}}},
                    }
                )
        return Snapshot(reminders=self.reminders, lists=lists, smart_lists=smart, sections=self.sections, taken_at=NOW)

    def model(self) -> model.Model:
        return model.build(self.snapshot(), self.cfg)

    def findings(self, rule_id: str | None = None) -> list[rules.Finding]:
        found = rules.check(self.model(), NOW)
        return [f for f in found if rule_id is None or f.rule == rule_id]


@pytest.fixture
def world() -> World:
    return World()
