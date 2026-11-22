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
