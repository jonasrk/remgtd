from datetime import datetime

from remgtd import rules

from conftest import World


def ids(world: World, rule_id: str) -> list[tuple[int, ...]]:
    return [f.item_ids for f in world.findings(rule_id)]


def healthy_loop(world: World, **kw) -> tuple[int, int]:
    loop = world.add("Passport renewed", "open_loops", **kw)
    lead = world.add("Book appointment at the citizen office", "open_loops", parent=loop, tags=("computer",), flagged=True)
    return loop, lead


def test_every_rule_is_registered_with_doc_ids():
    assert list(rules.RULES) == [f"R{n}" for n in range(1, 20)]
    violations = {r.id for r in rules.RULES.values() if r.severity == rules.VIOLATION}
    assert violations == {"R2", "R3", "R5", "R11", "R14", "R15"}


def test_clean_system_has_no_findings(world):
    healthy_loop(world)
    world.add("Call the dentist", "next_actions", tags=("quick",))
    world.add("Signed contract", "waiting_for", tags=("alex",))
    world.add("Learn Italian", "someday")
    world.add("Weekly sport", "autopilot")
    world.add("fresh capture", "inbox")
    assert world.findings() == []


# --- In-box -------------------------------------------------------------------


def test_r1_old_inbox_item(world):
    old = world.add("old", "inbox", age_days=8)
    world.add("new", "inbox", age_days=7)
    world.add("done", "inbox", age_days=30, completed=True)
    assert ids(world, "R1") == [(old,)]


# --- Open Loops ---------------------------------------------------------------


def test_r2_loop_without_next_action(world):
    loop = world.add("Kitchen renovated", "open_loops")
    world.add("someday think about colours", "open_loops", parent=loop)  # no Context
    assert ids(world, "R2") == [(loop,)]


def test_r2_completed_next_action_does_not_count(world):
    loop = world.add("Kitchen renovated", "open_loops")
    world.add("Get quotes", "open_loops", parent=loop, tags=("computer",), completed=True)
    assert ids(world, "R2") == [(loop,)]


def test_r3_next_actions_but_no_lead(world):
    loop = world.add("Kitchen renovated", "open_loops")
    world.add("Get quotes", "open_loops", parent=loop, tags=("computer",))
    assert ids(world, "R3") == [(loop,)]
    assert ids(world, "R2") == []


def test_r4_two_leads(world):
    loop, lead = healthy_loop(world)
    second = world.add("Find old passport", "open_loops", parent=loop, tags=("home",), flagged=True)
    assert ids(world, "R4") == [(loop, lead, second)]


def test_r5_lead_without_context(world):
    loop = world.add("Kitchen renovated", "open_loops")
    world.add("Get quotes", "open_loops", parent=loop, tags=("computer",))
    lead = world.add("Decide budget", "open_loops", parent=loop, flagged=True)
    assert ids(world, "R5") == [(lead,)]
    assert ids(world, "R7") == []  # not double-reported


def test_r6_stalled_loop(world):
    loop = world.add("Garden tidy", "open_loops", age_days=60)
    world.add("Buy gloves", "open_loops", parent=loop, tags=("quick",), flagged=True, age_days=45)
    assert ids(world, "R6") == [(loop,)]


def test_r6_recent_completion_keeps_loop_alive(world):
    loop = world.add("Garden tidy", "open_loops", age_days=60)
    world.add("Buy gloves", "open_loops", parent=loop, tags=("quick",), flagged=True, age_days=45)
    world.add("Mow lawn", "open_loops", parent=loop, age_days=50, completed=True, completed_days_ago=2)
    assert ids(world, "R6") == []


# --- Next Actions -------------------------------------------------------------


def test_r7_action_without_context(world):
    loop, _ = healthy_loop(world)
    sub = world.add("Scan old passport", "open_loops", parent=loop)
    standalone = world.add("Water plants", "next_actions")
    assert sorted(ids(world, "R7")) == sorted([(sub,), (standalone,)])


def test_r8_next_action_with_subtasks(world):
    item = world.add("Plan party", "next_actions", tags=("home",))
    world.add("Invite people", "next_actions", parent=item, tags=("computer",))
    assert ids(world, "R8") == [(item,)]


def test_r9_flag_on_standalone(world):
    item = world.add("Call the dentist", "next_actions", tags=("quick",), flagged=True)
    assert ids(world, "R9") == [(item,)]


def test_r10_due_date_on_action(world):
    item = world.add("Pay invoice", "next_actions", tags=("computer",), due=datetime(2026, 2, 3))
    assert ids(world, "R10") == [(item,)]


# --- Waiting For --------------------------------------------------------------


def test_r11_waiting_for_without_person(world):
    item = world.add("Parcel", "waiting_for")
    not_agenda = world.add("Quote", "waiting_for", tags=("computer",))
    world.add("Contract", "waiting_for", tags=("sam",))
    assert sorted(ids(world, "R11")) == sorted([(item,), (not_agenda,)])


def test_r12_old_waiting_for(world):
    old = world.add("Contract", "waiting_for", tags=("alex",), age_days=15)
    world.add("Report", "waiting_for", tags=("alex",), age_days=14)
    assert ids(world, "R12") == [(old,)]


def test_r13_waiting_for_looks_doable(world):
    flagged = world.add("Contract", "waiting_for", tags=("alex",), flagged=True)
    ctx = world.add("Report", "waiting_for", tags=("alex", "quick"))
    assert sorted(ids(world, "R13")) == sorted([(flagged,), (ctx,)])


# --- Someday/Maybe and Autopilot ----------------------------------------------


def test_r14_someday_with_context_or_flag_including_subtasks(world):
    parked = world.add("Boat trip", "someday")
    sub = world.add("Compare charters", "someday", parent=parked, tags=("computer",))
    flagged = world.add("Learn piano", "someday", flagged=True)
    assert sorted(ids(world, "R14")) == sorted([(sub,), (flagged,)])


def test_r15_autopilot_with_context(world):
    item = world.add("Weekly sport", "autopilot", tags=("quick",))
    assert ids(world, "R15") == [(item,)]


# --- Contexts and Sphere ------------------------------------------------------


def test_r16_unknown_tag_but_not_in_inbox_or_sphere_tag(world):
    item = world.add("Call the dentist", "next_actions", tags=("quick", "stray"))
    world.add("captured", "inbox", tags=("whatever",))
    world.add("Work thing", "next_actions", tags=("computer", "work"))
    assert ids(world, "R16") == [(item,)]


def test_r17_sphere_tag_on_non_action(world):
    loop, _ = healthy_loop(world)
    tagged_loop = world.add("Quarterly report shipped", "open_loops", tags=("work",))
    world.add("Draft outline", "open_loops", parent=tagged_loop, tags=("computer", "work"), flagged=True)
    someday = world.add("Conference talk", "someday", tags=("work",))
    assert sorted(ids(world, "R17")) == sorted([(tagged_loop,), (someday,)])


def test_r18_sphere_disagreement_both_directions(world):
    work_loop = world.add("Quarterly report shipped", "open_loops", section="Work")
    untagged = world.add("Draft outline", "open_loops", parent=work_loop, tags=("computer",), flagged=True)
    personal_loop = world.add("Passport renewed", "open_loops")
    tagged = world.add("Book appointment", "open_loops", parent=personal_loop, tags=("computer", "work"), flagged=True)
    assert sorted(ids(world, "R18")) == sorted([(untagged,), (tagged,)])


def test_r18_agreement_is_fine(world):
    work_loop = world.add("Quarterly report shipped", "open_loops", section="Work")
    world.add("Draft outline", "open_loops", parent=work_loop, tags=("computer", "work"), flagged=True)
    assert ids(world, "R18") == []


# --- Structure ----------------------------------------------------------------


def test_r19_unknown_list_in_group(world):
    world.extra_lists.append("Shopping")
    found = world.findings("R19")
    assert len(found) == 1 and "Shopping" in found[0].message


def test_items_outside_the_group_are_ignored(world):
    world.add("Milk", "inbox", list_name="Groceries", tags=("stray",), age_days=99)
    assert world.findings() == []


def test_violations_sort_before_hints(world):
    world.add("old", "inbox", age_days=30)  # R1 hint
    world.add("Parcel", "waiting_for")  # R11 violation
    severities = [f.severity for f in world.findings()]
    assert severities == [rules.VIOLATION, rules.HINT]
