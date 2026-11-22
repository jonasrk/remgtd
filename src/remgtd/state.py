"""Model + findings → the JSON document the View renders. Open items only."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from . import rules
from .model import Item, Model


def _days(now: datetime, then: datetime | None) -> int | None:
    return None if then is None else (now - then).days


def _item(m: Model, item: Item, now: datetime, finding_idx: dict[int, list[int]]) -> dict[str, Any]:
    parent = m.parent(item)
    return {
        "id": item.id,
        "title": item.title,
        "role": item.role,
        "parentId": item.parent_id,
        "children": [c.id for c in item.open_children()],
        "flagged": item.flagged,
        "isLead": bool(item.flagged and parent is not None and parent.role == "open_loops"),
        "contexts": m.context_tags(item),
        "tags": list(item.tags),
        "work": m.is_work(item),
        "section": (item.section if item.is_top_level else (parent.section if parent else None)),
        "ageDays": _days(now, item.created),
        "due": item.due.date().isoformat() if item.due else None,
        "hasNotes": bool(item.notes.strip()),
        "findings": finding_idx.get(item.id, []),
    }


def _checklist(m: Model, name: str) -> dict[str, Any] | None:
    """Progress of the newest copy of a Checklist (lists made from a template share a name)."""
    rows = [i for i in m.items.values() if i.list.casefold() == name.casefold() and i.is_top_level]
    dated = [i.created for i in rows if i.created]
    if not rows or not dated:
        return None
    day = max(dated).date()
    batch = [i for i in rows if i.created and i.created.date() == day]
    return {"name": name, "done": sum(i.completed for i in batch), "total": len(batch)}


def _steps(m: Model, findings: list[rules.Finding], now: datetime) -> dict[str, Any]:
    inbox = m.top_level("inbox")
    ages = [d for d in (_days(now, i.created) for i in inbox) if d is not None]
    violations = [f for f in findings if f.severity == rules.VIOLATION]
    by_rule: dict[str, int] = {}
    for f in violations:
        by_rule[f.rule] = by_rule.get(f.rule, 0) + 1
    top = max(by_rule, key=lambda r: (by_rule[r], -int(r[1:])), default=None)
    leads = [lead for loop in m.open_loops() for lead in m.lead_actions(loop)]
    return {
        "inbox": len(inbox),
        "oldestInboxDays": max(ages, default=None),
        "checklist": _checklist(m, m.cfg.view.inbox_sweep_checklist),
        "violations": len(violations),
        "topViolation": {"rule": top, "title": rules.RULES[top].title, "count": by_rule[top]} if top else None,
        "stalled": sum(f.rule == "R6" for f in findings),
        "oldWaiting": sum(f.rule == "R12" for f in findings),
        "leadActions": [{"id": lead.id, "work": m.is_work(lead)} for lead in leads],
    }


def build(m: Model, findings: list[rules.Finding], now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now()
    finding_idx: dict[int, list[int]] = {}
    for n, f in enumerate(findings):
        for i in f.item_ids:
            finding_idx.setdefault(i, []).append(n)

    visible = [i for i in m.items.values() if i.is_open and i.role is not None]
    items = {str(i.id): _item(m, i, now, finding_idx) for i in visible}

    def ids(role: str) -> list[int]:
        rows = sorted(m.top_level(role), key=lambda i: (i.created or now))
        return [i.id for i in rows]

    kinds: list[str] = []
    for ctx in m.contexts.values():
        if ctx.kind not in kinds:
            kinds.append(ctx.kind)
    order = {k.casefold(): n for n, k in enumerate(m.cfg.contexts.groups)}
    kinds.sort(key=lambda k: order.get(k.casefold(), len(order)))

    v = sum(f.severity == rules.VIOLATION for f in findings)
    return {
        "ok": True,
        "error": None,
        "generatedAt": now.isoformat(timespec="seconds"),
        "config": {
            "group": m.cfg.group,
            "agendaKind": m.cfg.contexts.agenda_group,
            "sphereTag": m.cfg.sphere.tag,
            "sphereSection": m.cfg.sphere.section,
            "weeklyReviewUrl": m.cfg.view.weekly_review_url,
            "inboxSweepChecklist": m.cfg.view.inbox_sweep_checklist,
            "thresholds": {
                "inboxDays": m.cfg.thresholds.inbox_days,
                "waitingDays": m.cfg.thresholds.waiting_days,
                "stalledDays": m.cfg.thresholds.stalled_days,
            },
        },
        "groupFound": m.group_found,
        "missingLists": m.missing_lists,
        "counts": {"violations": v, "hints": len(findings) - v},
        "steps": _steps(m, findings, now),
        "items": items,
        "lists": {
            "inbox": ids("inbox"),
            "openLoops": ids("open_loops"),
            "nextActions": ids("next_actions"),
            "waitingFor": ids("waiting_for"),
            "someday": ids("someday"),
            "autopilot": ids("autopilot"),
        },
        "contextKinds": kinds,
        "contexts": [{"tag": c.tag, "kind": c.kind, "smartList": c.smart_list} for c in m.contexts.values()],
        "findings": [
            {
                "rule": f.rule,
                "severity": f.severity,
                "title": rules.RULES[f.rule].title,
                "message": f.message,
                "itemIds": list(f.item_ids),
            }
            for f in findings
        ],
    }


def error(message: str, last: dict[str, Any] | None = None) -> dict[str, Any]:
    """An error state; keeps the last good data so the View can still show it, marked stale."""
    base = dict(last) if last else {"items": {}, "lists": {}, "findings": [], "counts": {"violations": 0, "hints": 0}}
    base.update({"ok": False, "error": message, "generatedAt": datetime.now().isoformat(timespec="seconds")})
    return base
