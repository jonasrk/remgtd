"""The Rules from docs/rules.md, one pure function each. Rule ids match the doc."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Iterable, Iterator

from .model import Item, Model

VIOLATION = "violation"
HINT = "hint"


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    item_ids: tuple[int, ...]
    message: str


@dataclass(frozen=True)
class Rule:
    id: str
    severity: str
    title: str
    check: Callable[[Model, datetime], Iterable[Finding]]


RULES: dict[str, Rule] = {}


def rule(rule_id: str, severity: str, title: str):
    def register(fn: Callable[[Model, datetime], Iterable[tuple[tuple[int, ...], str]]]):
        def check(model: Model, now: datetime) -> Iterator[Finding]:
            for item_ids, message in fn(model, now):
                yield Finding(rule_id, severity, item_ids, message)

        RULES[rule_id] = Rule(rule_id, severity, title, check)
        return fn

    return register


def _days(now: datetime, then: datetime | None) -> int | None:
    return None if then is None else (now - then).days


def _ids(*items: Item) -> tuple[int, ...]:
    return tuple(i.id for i in items)


# --- In-box -----------------------------------------------------------------


@rule("R1", HINT, "In-box item not clarified in time")
def r1(m: Model, now: datetime):
    limit = m.cfg.thresholds.inbox_days
    for item in m.top_level("inbox"):
        age = _days(now, item.created)
        if age is not None and age > limit:
            yield _ids(item), f"In the In-box for {age} days (limit {limit})."


# --- Open Loops -------------------------------------------------------------


@rule("R2", VIOLATION, "Open Loop has no Next Action")
def r2(m: Model, now: datetime):
    for loop in m.open_loops():
        if not any(m.is_next_action(c) for c in loop.open_children()):
            yield _ids(loop), "No subtask with a Context, so nothing moves it forward."


@rule("R3", VIOLATION, "Open Loop has no Lead Action")
def r3(m: Model, now: datetime):
    for loop in m.open_loops():
        has_next = any(m.is_next_action(c) for c in loop.open_children())
        if has_next and not m.lead_actions(loop):
            yield _ids(loop), "Has Next Actions, but none is flagged as the Lead Action."


@rule("R4", HINT, "Open Loop has more than one Lead Action")
def r4(m: Model, now: datetime):
    for loop in m.open_loops():
        leads = m.lead_actions(loop)
        if len(leads) > 1:
            yield _ids(loop, *leads), f"{len(leads)} flagged actions; the Lead Action should be one."


@rule("R5", VIOLATION, "Lead Action has no Context")
def r5(m: Model, now: datetime):
    for loop in m.open_loops():
        for lead in m.lead_actions(loop):
            if not m.has_context(lead):
                yield _ids(lead), "Flagged as Lead Action but has no Context, so it never comes up."


@rule("R6", HINT, "Open Loop has stalled")
def r6(m: Model, now: datetime):
    limit = m.cfg.thresholds.stalled_days
    for loop in m.open_loops():
        moments = [loop.created] + [c.created for c in loop.children] + [c.completed_at for c in loop.children]
        latest = max((d for d in moments if d is not None), default=None)
        age = _days(now, latest)
        if age is not None and age > limit:
            yield _ids(loop), f"Nothing created or completed for {age} days (limit {limit})."


# --- Next Actions -----------------------------------------------------------


@rule("R7", HINT, "Action has no Context")
def r7(m: Model, now: datetime):
    for action in m.actions():
        parent = m.parent(action)
        is_lead = action.flagged and parent is not None and parent.role == "open_loops"
        if not m.has_context(action) and not is_lead:  # a Lead Action without Context is R5
            yield _ids(action), "Without a Context it never shows up when you could do it."


@rule("R8", HINT, "Next Actions item has subtasks")
def r8(m: Model, now: datetime):
    for item in m.top_level("next_actions"):
        if item.open_children():
            yield _ids(item), "More than one step makes it an Open Loop."


@rule("R9", HINT, "Standalone Next Action is flagged")
def r9(m: Model, now: datetime):
    for item in m.open_items("next_actions"):
        if item.flagged:
            yield _ids(item), "The flag only means Lead Action inside an Open Loop."


@rule("R10", HINT, "Next Action has a due date")
def r10(m: Model, now: datetime):
    for action in m.actions():
        if action.due is not None:
            yield _ids(action), "Dates are for real deadlines; appointments belong in the Calendar."


# --- Waiting For ------------------------------------------------------------


@rule("R11", VIOLATION, "Waiting For names no person")
def r11(m: Model, now: datetime):
    for item in m.top_level("waiting_for"):
        if not any(m.is_agenda(t) for t in item.tags):
            yield _ids(item), "Add the person you're waiting on as an Agenda Context."


@rule("R12", HINT, "Waiting For is getting old")
def r12(m: Model, now: datetime):
    limit = m.cfg.thresholds.waiting_days
    for item in m.top_level("waiting_for"):
        age = _days(now, item.created)
        if age is not None and age > limit:
            yield _ids(item), f"Waiting for {age} days (limit {limit}); time to follow up?"


@rule("R13", HINT, "Waiting For looks doable")
def r13(m: Model, now: datetime):
    for item in m.open_items("waiting_for"):
        other = [t for t in m.context_tags(item) if not m.is_agenda(t)]
        if item.flagged or other:
            yield _ids(item), "It isn't yours to do: remove the flag and non-Agenda Contexts."


# --- Someday/Maybe and Autopilot --------------------------------------------


def _no_engage_markers(m: Model, role: str, what: str):
    for item in m.open_items(role):
        markers = m.context_tags(item)
        if item.flagged or markers:
            found = ", ".join(["flag"] * item.flagged + [f"#{t}" for t in markers])
            yield _ids(item), f"{what} must not show up in Engage lists (found {found})."


@rule("R14", VIOLATION, "Someday/Maybe item has a Context or flag")
def r14(m: Model, now: datetime):
    yield from _no_engage_markers(m, "someday", "Someday/Maybe items")


@rule("R15", VIOLATION, "Autopilot item has a Context or flag")
def r15(m: Model, now: datetime):
    yield from _no_engage_markers(m, "autopilot", "Autopilot items")


# --- Contexts and Sphere ----------------------------------------------------


@rule("R16", HINT, "Unknown tag")
def r16(m: Model, now: datetime):
    sphere = m.cfg.sphere.tag.casefold()
    for item in m.items.values():
        if not item.is_open or item.role in (None, "inbox"):
            continue
        unknown = [t for t in item.tags if t.casefold() not in m.contexts and t.casefold() != sphere]
        if unknown:
            yield _ids(item), "Not a Context or the Sphere tag: " + ", ".join(f"#{t}" for t in unknown)


@rule("R17", HINT, "Sphere tag on something that isn't a Next Action")
def r17(m: Model, now: datetime):
    action_ids = {a.id for a in m.actions()}
    for item in m.items.values():
        if not item.is_open or item.role in (None, "inbox") or item.id in action_ids:
            continue
        if m.has_sphere_tag(item):
            yield _ids(item), f"Use the \"{m.cfg.sphere.section}\" section here instead of #{m.cfg.sphere.tag}."


@rule("R18", HINT, "Next Action's Sphere disagrees with its Open Loop")
def r18(m: Model, now: datetime):
    for loop in m.open_loops():
        loop_work = m.in_sphere_section(loop)
        for action in loop.open_children():
            if m.is_next_action(action) and m.has_sphere_tag(action) != loop_work:
                if loop_work:
                    msg = f"The Open Loop is Work; add #{m.cfg.sphere.tag} so Work lists show this action."
                else:
                    msg = f"Tagged #{m.cfg.sphere.tag}, but its Open Loop isn't in the \"{m.cfg.sphere.section}\" section."
                yield _ids(action), msg


# --- Structure --------------------------------------------------------------


@rule("R19", HINT, "Unknown list in the GTD group")
def r19(m: Model, now: datetime):
    for title in m.unknown_group_lists:
        yield (), f"\"{title}\" isn't one of the GTD lists, so remgtd ignores it."


# --- running ----------------------------------------------------------------


def _order(finding: Finding) -> tuple[int, int]:
    return (0 if finding.severity == VIOLATION else 1, int(finding.rule[1:]))


def check(model: Model, now: datetime | None = None) -> list[Finding]:
    now = now or datetime.now()
    findings = [f for r in RULES.values() for f in r.check(model, now)]
    return sorted(findings, key=_order)
