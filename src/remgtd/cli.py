"""Command-line entry point."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, config, model, rules, snapshot
from .config import ConfigError
from .remctl import Remctl, RemctlError, find_remctl


def _load_model(args: argparse.Namespace) -> model.Model:
    cfg = config.load(Path(args.config) if args.config else None)
    rc = Remctl(find_remctl(cfg.remctl))
    return model.build(snapshot.read(rc, cfg), cfg)


def cmd_check(args: argparse.Namespace) -> int:
    m = _load_model(args)
    if not m.group_found:
        print(f"List group \"{m.cfg.group}\" not found in Reminders. Set `group` in the config.", file=sys.stderr)
        return 2
    findings = rules.check(m)

    if args.json:
        out = [
            {
                "rule": f.rule,
                "severity": f.severity,
                "title": rules.RULES[f.rule].title,
                "message": f.message,
                "items": [{"id": i, "title": m.label(m.items[i]), "deepLink": m.items[i].deep_link} for i in f.item_ids],
            }
            for f in findings
        ]
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    v = sum(f.severity == rules.VIOLATION for f in findings)
    h = len(findings) - v
    print(f"remgtd check: {v} Violation{'s' * (v != 1)}, {h} Hint{'s' * (h != 1)}")
    if m.missing_lists:
        print(f"Missing GTD lists in \"{m.cfg.group}\": {', '.join(m.missing_lists)}")
    for severity, heading in ((rules.VIOLATION, "Violations"), (rules.HINT, "Hints")):
        group = [f for f in findings if f.severity == severity]
        if not group:
            continue
        print(f"\n{heading}")
        last_rule = None
        for f in group:
            if f.rule != last_rule:
                print(f"  {f.rule:<4} {rules.RULES[f.rule].title}")
                last_rule = f.rule
            labels = "; ".join(m.label(m.items[i]) for i in f.item_ids)
            print(f"       • {labels + ': ' if labels else ''}{f.message}")
    if not findings:
        print("\nEverything is by the book.")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn

    from .server import create_app

    cfg = config.load(Path(args.config) if args.config else None)
    rc = Remctl(find_remctl(cfg.remctl))
    port = args.port or cfg.view.port
    print(f"remgtd: View at http://127.0.0.1:{port}  (Ctrl-C or close this tab to stop)")
    uvicorn.run(create_app(cfg, rc), host="127.0.0.1", port=port, log_level="warning")
    return 0


def cmd_open(args: argparse.Namespace) -> int:
    from .launcher import LauncherError, open_all

    cfg = config.load(Path(args.config) if args.config else None)
    try:
        open_all(cfg, config_path=args.config, place=not args.no_place)
    except LauncherError as exc:
        print(f"remgtd: {exc}", file=sys.stderr)
        return 2
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    from .launcher import server_running

    problems = 0

    def report(good: bool, text: str, fix: str = "") -> None:
        nonlocal problems
        problems += not good
        print(f"  {'✓' if good else '✗'} {text}")
        if fix and not good:
            print(f"      → {fix}")

    path = Path(args.config) if args.config else config.default_path()
    print("remgtd doctor")
    try:
        cfg = config.load(path)
        report(True, f"config: {path}" if path.exists() else f"config: defaults (no file at {path})")
    except ConfigError as exc:
        report(False, f"config: {exc}")
        return 1
    try:
        rc = Remctl(find_remctl(cfg.remctl))
        report(True, f"remctl: {rc.path}")
        snap = snapshot.read(rc, cfg)
        report(True, f"Reminders readable: {len(snap.reminders)} reminders")
    except RemctlError as exc:
        report(False, f"remctl: {exc}", "Install RemCTL and run `remctl doctor`.")
        return 1
    m = model.build(snap, cfg)
    report(m.group_found, f"list group \"{cfg.group}\"", "Create it in Reminders or set `group` in the config.")
    if m.group_found:
        report(not m.missing_lists, "GTD lists present" + (f" (missing: {', '.join(m.missing_lists)})" if m.missing_lists else ""),
               "Create the missing lists inside the group, or rename them in the config [lists].")
        if m.unknown_group_lists:
            print(f"    note: ignored lists in the group: {', '.join(m.unknown_group_lists)}")
    kinds: dict[str, int] = {}
    for ctx in m.contexts.values():
        kinds[ctx.kind] = kinds.get(ctx.kind, 0) + 1
    report(bool(kinds), "Contexts: " + (", ".join(f"{k} {n}" for k, n in kinds.items()) or "none found"),
           "Add one smart list per Context tag inside the groups listed in config [contexts] groups.")
    agenda = cfg.contexts.agenda_group.casefold()
    report(any(k.casefold() == agenda for k in kinds), f"Agenda group \"{cfg.contexts.agenda_group}\" has Contexts",
           "Waiting For items need an Agenda Context (one smart list per person).")
    running = server_running(cfg.view.port)
    print(f"  {'●' if running else '○'} server {'running' if running else 'not running'} on port {cfg.view.port}")
    print("  i window placement needs Accessibility permission for the app that runs `remgtd open`")
    print("\nAll good." if not problems else f"\n{problems} problem{'s' * (problems != 1)}.")
    return 0 if not problems else 1


def cmd_init(args: argparse.Namespace) -> int:
    path = Path(args.config) if args.config else config.default_path()
    if path.exists() and not args.force:
        print(f"{path} already exists (use --force to overwrite).", file=sys.stderr)
        return 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(config.TEMPLATE, encoding="utf-8")
    print(f"Wrote {path}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="remgtd", description="GTD, by the book, on top of Apple Reminders.")
    parser.add_argument("--version", action="version", version=f"remgtd {__version__}")
    parser.add_argument("--config", help="config file (default: ~/.config/remgtd/config.toml)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="read Reminders once and print Violations and Hints")
    p_check.add_argument("--json", action="store_true", help="machine-readable output")
    p_check.set_defaults(func=cmd_check)

    p_serve = sub.add_parser("serve", help="run the local server behind the View")
    p_serve.add_argument("--port", type=int, help="port (default from config: 8765)")
    p_serve.set_defaults(func=cmd_serve)

    p_open = sub.add_parser("open", help="start the server if needed; Reminders left, the View right")
    p_open.add_argument("--no-place", action="store_true", help="don't move or resize windows")
    p_open.set_defaults(func=cmd_open)

    p_doctor = sub.add_parser("doctor", help="check RemCTL, the lists, Contexts and the server")
    p_doctor.set_defaults(func=cmd_doctor)

    p_init = sub.add_parser("init", help="write a commented default config")
    p_init.add_argument("--force", action="store_true", help="overwrite an existing config")
    p_init.set_defaults(func=cmd_init)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ConfigError, RemctlError) as exc:
        print(f"remgtd: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
