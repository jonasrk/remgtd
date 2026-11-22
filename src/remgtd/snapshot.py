"""One read of everything remgtd needs from Reminders."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .config import Config
from .remctl import Remctl

# Roles whose lists use sections to mark the Work Sphere.
SECTIONED_ROLES = ("open_loops", "waiting_for", "someday", "autopilot")


@dataclass(frozen=True)
class Snapshot:
    reminders: list[dict[str, Any]]
    lists: list[dict[str, Any]]
    smart_lists: list[dict[str, Any]]
    # Section name per reminder id, for top-level reminders in sectioned lists.
    sections: dict[int, str] = field(default_factory=dict)
    taken_at: datetime = field(default_factory=datetime.now)


def sectioned_list_titles(cfg: Config, lists: list[dict[str, Any]]) -> list[str]:
    """Actual titles of the sectioned GTD lists that exist inside the GTD group."""
    wanted = {getattr(cfg.lists, role).casefold() for role in SECTIONED_ROLES}
    group = find_group(lists, cfg.group)
    children = group.get("children", []) if group else []
    return [c["title"] for c in children if c["title"].casefold() in wanted]


def find_group(lists: list[dict[str, Any]], title: str) -> dict[str, Any] | None:
    for entry in lists:
        if entry.get("isGroup") and entry.get("title", "").casefold() == title.casefold():
            return entry
    return None


def sections_from_show(rows: list[dict[str, Any]]) -> dict[int, str]:
    return {row["id"]: row["section"] for row in rows if row.get("section")}


def read(rc: Remctl, cfg: Config) -> Snapshot:
    """Read a complete snapshot (export, lists, smart lists, and every sectioned list)."""
    lists = rc.lists()
    reminders = rc.export()
    smart = rc.smart_lists()
    sections: dict[int, str] = {}
    for title in sectioned_list_titles(cfg, lists):
        sections.update(sections_from_show(rc.show(title)))
    return Snapshot(reminders=reminders, lists=lists, smart_lists=smart, sections=sections)
