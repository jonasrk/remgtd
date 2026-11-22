"""Pure translation of a Snapshot into GTD terms (see GLOSSARY.md)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterator

from .config import Config
from .snapshot import Snapshot, find_group

ROLES = ("inbox", "open_loops", "next_actions", "waiting_for", "someday", "autopilot")


@dataclass
class Item:
    id: int
    title: str
    list: str
    role: str | None  # one of ROLES, or None when outside the GTD group
    completed: bool
    flagged: bool
    tags: tuple[str, ...]
    parent_id: int | None
    created: datetime | None
    completed_at: datetime | None
    due: datetime | None
    notes: str
    deep_link: str
    section: str | None = None
    children: list["Item"] = field(default_factory=list)

    @property
    def is_open(self) -> bool:
        return not self.completed

    @property
    def is_top_level(self) -> bool:
        return self.parent_id is None

    def open_children(self) -> list["Item"]:
        return [c for c in self.children if c.is_open]


@dataclass(frozen=True)
class Context:
    tag: str
    kind: str  # the Context Kind group's title
    smart_list: str


@dataclass
class Model:
    cfg: Config
    items: dict[int, Item]
    contexts: dict[str, Context]  # keyed by casefolded tag
    group_found: bool
    unknown_group_lists: list[str]
    missing_lists: list[str]  # configured GTD lists not found in the group

    # --- lookups -----------------------------------------------------------

    def parent(self, item: Item) -> Item | None:
        return self.items.get(item.parent_id) if item.parent_id is not None else None

    def top_level(self, role: str) -> list[Item]:
        """Open top-level items in the list with this role."""
        return [i for i in self.items.values() if i.role == role and i.is_open and i.is_top_level]

    def open_items(self, role: str) -> list[Item]:
        """All open items (top-level and subtasks) in the list with this role."""
        return [i for i in self.items.values() if i.role == role and i.is_open]

    def open_loops(self) -> list[Item]:
        return self.top_level("open_loops")

    def actions(self) -> Iterator[Item]:
        """Open actions: subtasks of open Open Loops, and items (and their subtasks) in Next Actions."""
        for loop in self.open_loops():
            yield from loop.open_children()
        for item in self.top_level("next_actions"):
            yield item
            yield from item.open_children()

    # --- Contexts ------------------------------------------------------------

    def context_tags(self, item: Item) -> list[str]:
        return [t for t in item.tags if t.casefold() in self.contexts]

    def has_context(self, item: Item) -> bool:
        return bool(self.context_tags(item))

    def is_agenda(self, tag: str) -> bool:
        ctx = self.contexts.get(tag.casefold())
        return ctx is not None and ctx.kind.casefold() == self.cfg.contexts.agenda_group.casefold()

    def is_next_action(self, item: Item) -> bool:
        return self.has_context(item)

    def lead_actions(self, loop: Item) -> list[Item]:
        return [c for c in loop.open_children() if c.flagged]

    # --- Sphere --------------------------------------------------------------

    def has_sphere_tag(self, item: Item) -> bool:
        tag = self.cfg.sphere.tag.casefold()
        return any(t.casefold() == tag for t in item.tags)

    def in_sphere_section(self, item: Item) -> bool:
        """Whether the item (or, for a subtask, its top-level parent) sits in the Work section."""
        top = item if item.is_top_level else (self.parent(item) or item)
        return top.section is not None and top.section.casefold() == self.cfg.sphere.section.casefold()

    def is_work(self, item: Item) -> bool:
        """Work if a Next Action-ish item carries the Sphere tag, or its list position is in the Work section."""
        return self.has_sphere_tag(item) or self.in_sphere_section(item)

    # --- display -------------------------------------------------------------

    def label(self, item: Item) -> str:
        parent = self.parent(item)
        return f"{parent.title} › {item.title}" if parent else item.title


def _date(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed


def smart_list_tag(smart_list: dict[str, Any]) -> str | None:
    """The single tag a Context smart list selects, from its filter or its '#tag' name."""
    filt = smart_list.get("filterJSON") or {}
    outer = filt.get("hashtags") if isinstance(filt, dict) else None
    selected = outer.get("hashtags") if isinstance(outer, dict) else None
    if isinstance(selected, list) and len(selected) == 1 and isinstance(selected[0], str):
        return selected[0]
    if isinstance(selected, dict):
        include = selected.get("include") or []
        exclude = selected.get("exclude") or []
        if len(include) == 1 and not exclude:
            return include[0]
    name = (smart_list.get("name") or "").strip()
    if name.startswith("#") and len(name) > 1 and " " not in name:
        return name[1:]
    return None


def _is_custom(smart_list: dict[str, Any]) -> bool:
    kind = smart_list.get("kind") or ""
    stype = smart_list.get("smartListType") or ""
    return kind == "custom" or stype.endswith(".custom")


def build(snap: Snapshot, cfg: Config) -> Model:
    role_by_name = {getattr(cfg.lists, role).casefold(): role for role in ROLES}

    group = find_group(snap.lists, cfg.group)
    children = [c.get("title", "") for c in (group.get("children", []) if group else [])]
    role_by_list = {t.casefold(): role_by_name[t.casefold()] for t in children if t.casefold() in role_by_name}
    unknown = [t for t in children if t.casefold() not in role_by_name]
    present = set(role_by_list.values())
    missing = [getattr(cfg.lists, r) for r in ROLES if r not in present] if group else []

    # Contexts: custom smart lists inside a Context Kind group.
    kind_groups = {g.casefold() for g in cfg.contexts.groups}
    group_titles = {
        entry["id"]: entry["title"]
        for entry in snap.lists
        if entry.get("isGroup") and entry.get("title", "").casefold() in kind_groups
    }
    contexts: dict[str, Context] = {}
    for sl in snap.smart_lists:
        if not _is_custom(sl) or sl.get("parentListId") not in group_titles:
            continue
        tag = smart_list_tag(sl)
        if tag:
            contexts[tag.casefold()] = Context(tag=tag, kind=group_titles[sl["parentListId"]], smart_list=sl.get("name", ""))

    items: dict[int, Item] = {}
    for r in snap.reminders:
        items[r["id"]] = Item(
            id=r["id"],
            title=(r.get("title") or "").strip(),
            list=r.get("list", ""),
            role=role_by_list.get((r.get("list") or "").casefold()),
            completed=bool(r.get("completed")),
            flagged=bool(r.get("flagged")),
            tags=tuple(r.get("tags") or ()),
            parent_id=r.get("parentID"),
            created=_date(r.get("createdDate")),
            completed_at=_date(r.get("completionDate")),
            due=_date(r.get("dueDate")),
            notes=r.get("notes") or "",
            deep_link=r.get("deepLink") or "",
            section=snap.sections.get(r["id"]),
        )
    for item in items.values():
        parent = items.get(item.parent_id) if item.parent_id is not None else None
        if parent is not None:
            parent.children.append(item)

    return Model(
        cfg=cfg,
        items=items,
        contexts=contexts,
        group_found=group is not None,
        unknown_group_lists=unknown,
        missing_lists=missing,
    )
