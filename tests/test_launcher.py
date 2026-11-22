import shlex

import pytest

from remgtd import launcher
from remgtd.config import Config


def test_applescript_string_escaping():
    assert launcher._as_str('say "hi" \\ there') == '"say \\"hi\\" \\\\ there"'


def test_serve_command_uses_this_python_and_config():
    cmd = launcher.serve_command("/tmp/my config.toml")
    parts = shlex.split(cmd)
    assert parts[1:] == ["-m", "remgtd", "--config", "/tmp/my config.toml", "serve"]


@pytest.mark.parametrize("terminal, app", [("iTerm2", 'application "iTerm"'), ("Terminal", 'application "Terminal"')])
def test_terminal_scripts(terminal, app):
    assert app in launcher.terminal_script(terminal, "remgtd serve")


def test_unknown_terminal():
    with pytest.raises(launcher.LauncherError):
        launcher.terminal_script("Warp", "x")


@pytest.mark.parametrize("browser", ["Brave Browser", "Google Chrome", "Safari"])
def test_browser_scripts_reuse_existing_tab(browser):
    script = launcher.browser_script(browser, "http://127.0.0.1:8765/")
    assert 'starts with "http://127.0.0.1:8765/"' in script
    assert "make new tab" in script


def test_unknown_browser():
    with pytest.raises(launcher.LauncherError):
        launcher.browser_script("Lynx", "http://x")


def test_placement_script_names_both_processes():
    script = launcher.placement_script("Reminders", "Brave Browser")
    assert 'place("Reminders", x, half)' in script
    assert 'place("Brave Browser", x + half, w - half)' in script


def test_server_not_running_on_closed_port():
    assert launcher.server_running(1) is False


def test_view_url_uses_port():
    assert launcher.view_url(Config()) == "http://127.0.0.1:8765/"
