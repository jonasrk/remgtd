"""A synthetic GTD system for `remgtd serve --demo`: try the View without Reminders.

DemoRemctl offers the same read methods as Remctl and returns RemCTL-shaped JSON.
The data deliberately breaks a few Rules so every kind of badge shows up.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

GROUP = "GTD"
LISTS = ["In-box", "Open Loops", "Next Actions", "Waiting For", "Someday/Maybe", "Autopilot"]
CONTEXTS = {
    "Agenda": ["alex", "sam"],
    "Place/Tool": ["home", "computer", "errands"],
    "Condition": ["quick_wins", "low_energy"],
}


class DemoRemctl:
    path = "demo"

    def __init__(self, now: datetime | None = None) -> None:
        self.now = now or datetime.now()
        self._rows: list[dict[str, Any]] = []
        self._sections: dict[int, str] = {}
        self._next = 1
        self._build()

    # --- data ----------------------------------------------------------------

    def _add(self, title: str, list_name: str, *, tags: tuple[str, ...] = (), flagged: bool = False,
             parent: int | None = None, age: float = 2, done: bool = False, section: str | None = None) -> int:
        rid = self._next
        self._next += 1
        created = self.now - timedelta(days=age)
        self._rows.append({
            "id": rid,
            "title": title,
            "list": list_name,
            "completed": done,
            "flagged": flagged,
            "urgent": False,
            "priority": "none",
            "subtaskCount": 0,
            "isSubtask": parent is not None,
            "allDay": False,
            "createdDate": created.isoformat(),
            "completionDate": (created + timedelta(hours=1)).isoformat() if done else None,
            "tags": list(tags) or None,
            "parentID": parent,
            "deepLink": f"x-apple-reminderkit://REMCDReminder/demo-{rid}",
        })
        if section:
            self._sections[rid] = section
        return rid

    def _build(self) -> None:
        a = self._add
        a("Call mom back about the weekend", "In-box", age=1)
        a("Receipt for the tax return", "In-box", age=10)  # R1: older than 7 days

        passport = a("Passport renewed", "Open Loops", age=12)
        a("Book an appointment at the citizen office", "Open Loops", parent=passport, tags=("computer",), flagged=True, age=3)
        a("Find the birth certificate", "Open Loops", parent=passport, tags=("home",), age=3)

        report = a("Q3 report shipped", "Open Loops", age=8, section="Work")
        a("Draft the outline for the Q3 report", "Open Loops", parent=report, tags=("computer", "work"), flagged=True, age=2)
        a("Ask Sam for the final sales numbers", "Open Loops", parent=report, tags=("sam", "work"), age=2)

        kitchen = a("Kitchen renovated", "Open Loops", age=20)
        a("Get three quotes for the countertop", "Open Loops", parent=kitchen, tags=("computer",), age=5)  # R3: no Lead

        a("Website relaunched", "Open Loops", age=40, section="Work")  # R2 + R6

        a("Call the dentist to move the check-up", "Next Actions", tags=("quick_wins",))
        a("Buy light bulbs for the hallway", "Next Actions", tags=("errands",))
        a("Water the plants", "Next Actions")  # R7: no Context
        a("Review the onboarding doc", "Next Actions", tags=("computer", "low_energy", "work"))

        a("Signed contract from the landlord", "Waiting For", tags=("alex",), age=20)  # R12
        a("Parcel from the online shop", "Waiting For", age=4)  # R11: no person

        a("Learn Italian", "Someday/Maybe", section="Learning")
        a("Weekend in Lisbon", "Someday/Maybe", section="Travel")
        a("Build a bookshelf", "Someday/Maybe")
        a("Give a conference talk", "Someday/Maybe", section="Work")

        a("Weekly run with the club", "Autopilot")
        a("Language exchange on Thursdays", "Autopilot")

        for title, done in (("Paper tray", True), ("Email", True), ("Downloads folder", False)):
            a(title, "Clarify In-boxes", age=0.1, done=done)

        counts: dict[int, int] = {}
        for row in self._rows:
            if row["parentID"] and not row["completed"]:
                counts[row["parentID"]] = counts.get(row["parentID"], 0) + 1
        for row in self._rows:
            row["subtaskCount"] = counts.get(row["id"], 0)

    # --- the Remctl interface ----------------------------------------------------

    def export(self) -> list[dict[str, Any]]:
        return [dict(r) for r in self._rows]

    def lists(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = [{
            "id": 1, "title": GROUP, "listType": "group", "isGroup": True,
            "children": [{"id": 10 + i, "title": t, "listType": "standard", "isGroup": False, "children": []}
                         for i, t in enumerate(LISTS)],
        }]
        for gi, group in enumerate(CONTEXTS):
            out.append({"id": 100 + gi, "title": group, "listType": "group", "isGroup": True, "children": []})
        out.append({"id": 200, "title": "Clarify In-boxes", "listType": "standard", "isGroup": False, "children": []})
        return out

    def smart_lists(self) -> list[dict[str, Any]]:
        out = []
        for gi, (group, tags) in enumerate(CONTEXTS.items()):
            for ti, tag in enumerate(tags):
                out.append({
                    "id": 1000 + gi * 10 + ti, "name": f"#{tag}", "kind": "custom",
                    "smartListType": "com.apple.reminders.smartlist.custom", "parentListId": 100 + gi,
                    "filterJSON": {"hashtags": {"hashtags": {"operation": "or", "include": [tag], "exclude": []}}},
                })
        return out

    def show(self, list_name: str) -> list[dict[str, Any]]:
        return [
            {**r, "section": self._sections.get(r["id"])}
            for r in self._rows
            if r["list"] == list_name and r["parentID"] is None
        ]
