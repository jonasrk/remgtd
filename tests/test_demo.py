from datetime import datetime

from remgtd import model, rules, snapshot
from remgtd.config import Config
from remgtd.demo import DemoRemctl


def test_demo_shows_every_kind_of_problem():
    now = datetime(2026, 1, 31, 12)
    rc = DemoRemctl(now=now)
    m = model.build(snapshot.read(rc, Config()), Config())
    found = {f.rule for f in rules.check(m, now)}
    assert {"R1", "R2", "R3", "R6", "R7", "R11", "R12"} <= found
    assert m.group_found and not m.missing_lists and len(m.contexts) == 7


def test_demo_work_sphere():
    rc = DemoRemctl()
    m = model.build(snapshot.read(rc, Config()), Config())
    work_loops = [l.title for l in m.open_loops() if m.is_work(l)]
    assert sorted(work_loops) == ["Q3 report shipped", "Website relaunched"]
