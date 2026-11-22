"""`remgtd open`: start the server if needed, then Reminders left, the View right.

Uses AppleScript for the terminal and browser, and JXA + System Events for
window placement (needs Accessibility permission for the app that runs it,
e.g. your terminal or Alfred).
"""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
import time
import urllib.request

from .config import Config

CHROMIUM = {"brave browser", "google chrome", "chromium", "microsoft edge", "vivaldi"}
TERMINAL_APPS = {"iterm2": "iTerm", "iterm": "iTerm", "terminal": "Terminal"}


class LauncherError(RuntimeError):
    pass


def view_url(cfg: Config) -> str:
    return f"http://127.0.0.1:{cfg.view.port}/"


def server_running(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=0.7) as resp:
            return json.load(resp).get("app") == "remgtd"
    except Exception:
        return False


def _as_str(value: str) -> str:
    """Quote a Python string as an AppleScript string literal."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def osascript(script: str, language: str = "AppleScript", timeout: float = 30) -> str:
    try:
        proc = subprocess.run(
            ["osascript", "-l", language, "-e", script], capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired as exc:
        raise LauncherError(f"osascript timed out ({language})") from exc
    if proc.returncode != 0:
        raise LauncherError(proc.stderr.strip() or f"osascript failed ({proc.returncode})")
    return proc.stdout.strip()


def serve_command(config_path: str | None) -> str:
    parts = [sys.executable, "-m", "remgtd"]
    if config_path:
        parts += ["--config", config_path]
    parts.append("serve")
    return " ".join(shlex.quote(p) for p in parts)


def terminal_script(terminal: str, command: str) -> str:
    app = TERMINAL_APPS.get(terminal.casefold())
    if app == "iTerm":
        return f"""tell application "iTerm"
  activate
  if (count of windows) = 0 then
    create window with default profile
  else
    tell current window to create tab with default profile
  end if
  tell current session of current window to write text {_as_str(command)}
end tell"""
    if app == "Terminal":
        return f"""tell application "Terminal"
  activate
  do script {_as_str(command)}
end tell"""
    raise LauncherError(f"Unsupported terminal {terminal!r}; use \"iTerm2\" or \"Terminal\".")


def browser_script(browser: str, url: str) -> str:
    """Focus a tab already showing the View, or open one; bring its window to the front."""
    app = _as_str(browser)
    base = _as_str(url)
    if browser.casefold() in CHROMIUM:
        return f"""tell application {app}
  activate
  set found to false
  repeat with w in windows
    set i to 0
    repeat with t in tabs of w
      set i to i + 1
      try
        if URL of t starts with {base} then
          set active tab index of w to i
          set index of w to 1
          set found to true
          exit repeat
        end if
      end try
    end repeat
    if found then exit repeat
  end repeat
  if not found then
    if (count of windows) = 0 then make new window
    tell front window to make new tab with properties {{URL:{base}}}
  end if
end tell"""
    if browser.casefold() == "safari":
        return f"""tell application "Safari"
  activate
  set found to false
  repeat with w in windows
    repeat with t in tabs of w
      try
        if URL of t starts with {base} then
          set current tab of w to t
          set index of w to 1
          set found to true
          exit repeat
        end if
      end try
    end repeat
    if found then exit repeat
  end repeat
  if not found then
    if (count of windows) = 0 then make new document
    tell front window to set current tab to (make new tab with properties {{URL:{base}}})
  end if
end tell"""
    raise LauncherError(f"Unsupported browser {browser!r}; use Brave Browser, Google Chrome or Safari.")


def placement_script(left_process: str, right_process: str) -> str:
    """JXA: split the main screen's usable area 50/50 between two apps' front windows."""
    return f"""
ObjC.import('AppKit');
const vis = $.NSScreen.mainScreen.visibleFrame;
const primaryHeight = $.NSScreen.screens.objectAtIndex(0).frame.size.height;
const x = vis.origin.x, w = vis.size.width, h = vis.size.height;
const top = primaryHeight - (vis.origin.y + h);
const half = Math.floor(w / 2);
const se = Application('System Events');
function frontWindow(name) {{
  for (let i = 0; i < 50; i++) {{
    try {{
      const p = se.processes.byName(name);
      if (p.windows.length > 0) return p.windows[0];
    }} catch (e) {{}}
    delay(0.1);
  }}
  throw new Error('No window for ' + name);
}}
function place(name, px, width) {{
  const win = frontWindow(name);
  win.position = [px, top];
  win.size = [width, h];
}}
place({json.dumps(left_process)}, x, half);
place({json.dumps(right_process)}, x + half, w - half);
'ok';
"""


def open_all(cfg: Config, config_path: str | None = None, place: bool = True, log=print) -> None:
    port = cfg.view.port
    url = view_url(cfg)

    if not server_running(port):
        log(f"Starting the server in a new {cfg.launcher.terminal} tab…")
        osascript(terminal_script(cfg.launcher.terminal, serve_command(config_path)))
        deadline = time.monotonic() + 30
        while not server_running(port):
            if time.monotonic() > deadline:
                raise LauncherError(f"The server didn't start on port {port}. Check the {cfg.launcher.terminal} tab.")
            time.sleep(0.3)

    subprocess.run(["open", "-a", "Reminders"], check=False)
    osascript(browser_script(cfg.launcher.browser, url))

    if place:
        try:
            osascript(placement_script("Reminders", cfg.launcher.browser), language="JavaScript")
        except LauncherError as exc:
            log(
                "Couldn't place the windows side by side: "
                f"{exc}\nAllow the app running remgtd (your terminal, or Alfred) under "
                "System Settings → Privacy & Security → Accessibility, then run it again."
            )
