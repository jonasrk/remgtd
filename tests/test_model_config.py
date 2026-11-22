import pytest

from remgtd import config
from remgtd.config import Config, ConfigError
from remgtd.model import smart_list_tag

from conftest import World


# --- smart list → Context tag -------------------------------------------------


def test_tag_from_legacy_filter():
    assert smart_list_tag({"name": "x", "filterJSON": {"hashtags": {"hashtags": ["car"]}}}) == "car"


def test_tag_from_current_filter():
    sl = {"name": "x", "filterJSON": {"hashtags": {"hashtags": {"operation": "or", "include": ["car"], "exclude": []}}}}
    assert smart_list_tag(sl) == "car"


def test_tag_falls_back_to_name():
    assert smart_list_tag({"name": "#car", "filterJSON": None}) == "car"


def test_exclusion_filters_are_not_contexts():
    sl = {"name": "Personal", "filterJSON": {"hashtags": {"hashtags": {"include": [], "exclude": ["work"]}}}}
    assert smart_list_tag(sl) is None


# --- model --------------------------------------------------------------------


def test_contexts_get_their_kind_from_the_group(world):
    m = world.model()
    assert m.contexts["alex"].kind == "Agenda"
    assert m.is_agenda("Alex")  # case-insensitive
    assert not m.is_agenda("home")


def test_list_names_match_case_insensitively():
    cfg = config.parse({"lists": {"waiting_for": "waiting for"}})
    w = World(cfg=cfg)
    w.reminders.clear()
    rid = w.add("Contract", "waiting_for", list_name="Waiting for")
    snap = w.snapshot()
    for child in snap.lists[0]["children"]:
        if child["title"].casefold() == "waiting for":
            child["title"] = "Waiting for"
    from remgtd import model

    assert model.build(snap, cfg).items[rid].role == "waiting_for"


def test_missing_group_is_reported():
    w = World(cfg=Config(group="Nope"))
    snap = w.snapshot()
    snap.lists[0]["title"] = "Something else"
    from remgtd import model

    assert model.build(snap, w.cfg).group_found is False


def test_subtask_inherits_work_section(world):
    loop = world.add("Quarterly report shipped", "open_loops", section="Work")
    sub = world.add("Draft outline", "open_loops", parent=loop, tags=("computer",))
    m = world.model()
    assert m.is_work(m.items[sub])


# --- config -------------------------------------------------------------------


def test_defaults_without_file(tmp_path):
    assert config.load(tmp_path / "none.toml") == Config()


def test_partial_config_overrides(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text('group = "Mine"\n[thresholds]\ninbox_days = 3\n[contexts]\ngroups = ["People"]\n')
    cfg = config.load(p)
    assert cfg.group == "Mine"
    assert cfg.thresholds.inbox_days == 3 and cfg.thresholds.waiting_days == 14
    assert cfg.contexts.groups == ("People",)


@pytest.mark.parametrize(
    "text",
    ['grup = "typo"', '[thresholds]\ninbox_days = "seven"', "lists = 3", '[contexts]\ngroups = "Agenda"'],
)
def test_invalid_config_is_rejected(tmp_path, text):
    p = tmp_path / "c.toml"
    p.write_text(text)
    with pytest.raises(ConfigError):
        config.load(p)


def test_template_is_valid_and_all_defaults(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text(config.TEMPLATE)
    assert config.load(p) == Config()
