"""Configuration: names, thresholds and launcher settings.

Every value has a default that matches the conventions in the docs, so an
empty or missing config file is valid. Personal settings live in
``~/.config/remgtd/config.toml`` (or ``$REMGTD_CONFIG``), never in the repo.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any


class ConfigError(ValueError):
    """The config file can't be read or contains invalid values."""


@dataclass(frozen=True)
class Lists:
    inbox: str = "In-box"
    open_loops: str = "Open Loops"
    next_actions: str = "Next Actions"
    waiting_for: str = "Waiting For"
    someday: str = "Someday/Maybe"
    autopilot: str = "Autopilot"


@dataclass(frozen=True)
class Contexts:
    groups: tuple[str, ...] = ("Agenda", "Place/Tool", "Condition")
    agenda_group: str = "Agenda"


@dataclass(frozen=True)
class Sphere:
    tag: str = "work"
    section: str = "Work"


@dataclass(frozen=True)
class Thresholds:
    inbox_days: int = 7
    waiting_days: int = 14
    stalled_days: int = 30


@dataclass(frozen=True)
class View:
    port: int = 8765
    weekly_review_url: str = ""
    inbox_sweep_checklist: str = "Clarify In-boxes"


@dataclass(frozen=True)
class Launcher:
    browser: str = "Brave Browser"
    terminal: str = "iTerm2"


@dataclass(frozen=True)
class Config:
    group: str = "GTD"
    remctl: str = ""
    lists: Lists = field(default_factory=Lists)
    contexts: Contexts = field(default_factory=Contexts)
    sphere: Sphere = field(default_factory=Sphere)
    thresholds: Thresholds = field(default_factory=Thresholds)
    view: View = field(default_factory=View)
    launcher: Launcher = field(default_factory=Launcher)


def default_path() -> Path:
    env = os.environ.get("REMGTD_CONFIG")
    if env:
        return Path(env).expanduser()
    return Path.home() / ".config" / "remgtd" / "config.toml"


def load(path: Path | None = None) -> Config:
    """Load the config file, or return defaults if it doesn't exist."""
    path = path or default_path()
    if not path.exists():
        return Config()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(f"{path}: {exc}") from exc
    return parse(data, where=str(path))


def parse(data: dict[str, Any], where: str = "config") -> Config:
    return _build(Config, data, where)


def _build(cls: type, data: dict[str, Any], where: str) -> Any:
    known = {f.name for f in fields(cls)}
    unknown = sorted(set(data) - known)
    if unknown:
        raise ConfigError(f"{where}: unknown key(s): {', '.join(unknown)}")
    defaults = cls()
    kwargs: dict[str, Any] = {}
    for name, value in data.items():
        default = getattr(defaults, name)
        key = f"{where}: {name}"
        if is_dataclass(default):
            if not isinstance(value, dict):
                raise ConfigError(f"{key} must be a table")
            kwargs[name] = _build(type(default), value, f"{where} [{name}]")
        elif isinstance(default, tuple):
            if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                raise ConfigError(f"{key} must be a list of strings")
            kwargs[name] = tuple(value)
        elif isinstance(default, bool) or type(value) is not type(default):
            raise ConfigError(f"{key} must be a {type(default).__name__}")
        else:
            kwargs[name] = value
    return cls(**kwargs)


TEMPLATE = """\
# remgtd configuration. Every line is optional; the values shown are the defaults.
# List and group names are matched case-insensitively.

# The Reminders list group that holds the GTD lists. Only lists inside it are checked.
# group = "GTD"

# Path to the remctl binary. Empty means: look on PATH, then ~/bin and ~/.local/bin.
# remctl = ""

[lists]
# inbox = "In-box"
# open_loops = "Open Loops"
# next_actions = "Next Actions"
# waiting_for = "Waiting For"
# someday = "Someday/Maybe"
# autopilot = "Autopilot"

[contexts]
# List groups whose smart lists define Contexts; each group is a Context Kind.
# groups = ["Agenda", "Place/Tool", "Condition"]
# The Context Kind whose Contexts are people (used for Waiting For).
# agenda_group = "Agenda"

[sphere]
# Tag on Next Actions that belong to the Work Sphere (without '#').
# tag = "work"
# Section that marks everything else as Work.
# section = "Work"

[thresholds]
# inbox_days = 7
# waiting_days = 14
# stalled_days = 30

[view]
# port = 8765
# Optional link shown on the Reflect card, e.g. your weekly-review tracker.
# weekly_review_url = ""
# The Checklist that lists your in-boxes (shown on the Capture card).
# inbox_sweep_checklist = "Clarify In-boxes"

[launcher]
# browser = "Brave Browser"   # or "Google Chrome", "Safari"
# terminal = "iTerm2"         # or "Terminal"
"""
