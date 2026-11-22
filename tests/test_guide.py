from remgtd import guide, rules, state

from conftest import NOW, World


def test_shipped_guide_has_five_complete_cards():
    cards = guide.cards()
    assert [c["id"] for c in cards] == ["capture", "clarify", "organize", "reflect", "engage"]
    for card in cards:
        assert card["purpose"] and card["start"] and card["end"] and card["status"]
        assert card["questions"] and card["advice"]


def test_nested_bullets_and_notes():
    md = """## 1. Clarify
**Purpose:** Decide.
**Key questions**, in order:
- Is it actionable?
  - **No:** trash it
1. Numbered
**Advice**
- One at a time
"""
    (card,) = guide.parse(md)
    assert card["questionsNote"] == "in order"
    assert [(q["text"], q["depth"]) for q in card["questions"]] == [
        ("Is it actionable?", 0),
        ("**No:** trash it", 1),
        ("Numbered", 0),
    ]
    assert card["advice"] == [{"text": "One at a time", "depth": 0}]


def steps(world: World) -> dict:
    m = world.model()
    return state.build(m, rules.check(m, NOW), NOW)["steps"]


def test_step_status_counts(world):
    world.add("old", "inbox", age_days=9)
    world.add("new", "inbox", age_days=1)
    world.add("Parcel", "waiting_for")  # R11 violation
    loop = world.add("Passport renewed", "open_loops", section="Work")
    world.add("Book appointment", "open_loops", parent=loop, tags=("computer", "work"), flagged=True)
    s = steps(world)
    assert s["inbox"] == 2 and s["oldestInboxDays"] == 9
    assert s["violations"] == 1 and s["topViolation"]["rule"] == "R11"
    assert s["leadActions"] == [{"id": loop + 1, "work": True}]


def test_checklist_uses_newest_copy(world):
    # an old completed copy and today's copy of the same Checklist (outside the GTD group)
    world.add("Paper", "inbox", list_name="Clarify In-boxes", age_days=3, completed=True)
    world.add("Paper", "inbox", list_name="Clarify In-boxes", age_days=0.1, completed=True)
    world.add("Email", "inbox", list_name="Clarify In-boxes", age_days=0.1)
    assert steps(world)["checklist"] == {"name": "Clarify In-boxes", "done": 1, "total": 2}


def test_no_checklist(world):
    assert steps(world)["checklist"] is None
