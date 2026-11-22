import asyncio
import json

import pytest
from starlette.testclient import TestClient

from remgtd import model, rules, state
from remgtd.server import Poller, create_app

from conftest import NOW, World


class FakeRemctl:
    """Serves a World's snapshot through the same methods as Remctl."""

    def __init__(self, world: World) -> None:
        self.world = world
        self.calls: list[str] = []

    def _snap(self):
        return self.world.snapshot()

    def export(self):
        self.calls.append("export")
        return self._snap().reminders

    def lists(self):
        self.calls.append("lists")
        return self._snap().lists

    def smart_lists(self):
        self.calls.append("smart-lists")
        return self._snap().smart_lists

    def show(self, title):
        self.calls.append(f"show {title}")
        list_items = [r for r in self._snap().reminders if r["list"] == title]
        return [{**r, "section": self.world.sections.get(r["id"])} for r in list_items if r["parentID"] is None]


@pytest.fixture
def setup(world):
    loop = world.add("Quarterly report shipped", "open_loops", section="Work")
    lead = world.add("Draft outline", "open_loops", parent=loop, tags=("computer", "work"), flagged=True)
    world.add("Parcel", "waiting_for")  # R11
    rc = FakeRemctl(world)
    opened: list[str] = []
    poller = Poller(world.cfg, rc, clock=lambda: NOW)
    app = create_app(world.cfg, rc, opener=opened.append, start_polling=False, poller=poller)
    asyncio.run(poller.tick())
    client = TestClient(app, base_url="http://127.0.0.1")
    return client, poller, rc, opened, loop, lead


def test_health(setup):
    client, *_ = setup
    assert client.get("/health").json()["ok"] is True


def test_state_reflects_model(setup):
    client, _, _, _, loop, lead = setup
    data = client.get("/state.json").json()
    assert data["ok"] is True
    assert data["lists"]["openLoops"] == [loop]
    assert data["items"][str(lead)]["isLead"] is True
    assert data["items"][str(lead)]["work"] is True
    assert data["items"][str(loop)]["work"] is True
    assert data["counts"] == {"violations": 1, "hints": 0}


def test_first_tick_reads_every_sectioned_list(setup):
    _, _, rc, *_ = setup
    shows = {c for c in rc.calls if c.startswith("show ")}
    assert shows == {"show Open Loops", "show Waiting For", "show Someday/Maybe", "show Autopilot"}


def test_unchanged_data_does_not_publish_again(setup):
    _, poller, *_ = setup
    version = poller.version
    asyncio.run(poller.tick())
    asyncio.run(poller.tick())
    assert poller.version == version


def test_changed_data_publishes(setup, world):
    _, poller, *_ = setup
    version = poller.version
    world.add("New capture", "inbox")
    asyncio.run(poller.tick())
    assert poller.version == version + 1


def test_foreign_host_is_rejected(setup):
    client, *_ = setup
    assert client.get("/health", headers={"host": "evil.example"}).status_code == 400


def test_open_requires_header(setup):
    client, _, _, opened, loop, _ = setup
    assert client.post(f"/open/{loop}").status_code == 403
    assert opened == []


def test_open_uses_deep_link(setup):
    client, _, _, opened, loop, _ = setup
    assert client.post(f"/open/{loop}", headers={"X-Remgtd": "1"}).json() == {"ok": True}
    assert opened == [f"x-apple-reminderkit://REMCDReminder/{loop}"]


def test_open_unknown_item(setup):
    client, *_ = setup
    assert client.post("/open/99999", headers={"X-Remgtd": "1"}).status_code == 404


def test_index_and_static_are_served(setup):
    client, *_ = setup
    assert "remgtd" in client.get("/").text
    js = client.get("/static/app.js")
    assert js.status_code == 200
    assert js.headers["cache-control"] == "no-cache"


def test_error_state_keeps_last_data(world):
    world.add("Call the dentist", "next_actions", tags=("quick",))
    m = world.model()
    good = state.build(m, rules.check(m, NOW), NOW)
    bad = state.error("remctl failed", good)
    assert bad["ok"] is False and bad["error"] == "remctl failed"
    assert bad["items"] == good["items"]
    json.dumps(bad)  # serializable
