# remgtd

**Getting Things Done, by the book, on top of Apple Reminders.**

remgtd is an opinionated set of conventions for running GTD in Apple Reminders, plus a read-only **View**. The View shows your Reminders data in GTD terms and tells you where your system has drifted from the book.

> **Status:** design phase. The method is specified; the View and launcher aren't built yet.

## Idea

- **Reminders stays the only place you edit.** The View opens next to it, never changes anything, and updates within about a second of each edit.
- **The View shows what Reminders' own lists can't:** an Open Loop with all its actions, a Context across all Open Loops, and Work or Personal only.
- **Rules from the book.** Each place the system breaks a Rule is flagged as a *Violation* (a Rule is broken) or a *Hint* (probably drifting).
- **A Step Guide** walks through Capture, Clarify, Organize, Reflect and Engage. Each card shows a live status from your data.

## The method in short

| GTD concept | In Reminders |
|---|---|
| In-box | the **In-box** list |
| Project (*Open Loop*) | a top-level reminder in **Open Loops**, titled as the finished outcome |
| Next Action | a subtask of an Open Loop, or an item in **Next Actions**, with at least one Context tag |
| *Lead Action* | the flagged Next Action of an Open Loop |
| Context | a tag that has a smart list in a Context Kind group (Agenda, Place/Tool, Condition) |
| Waiting For | the **Waiting For** list; each item names a person through an Agenda tag |
| Someday/Maybe | the **Someday/Maybe** list; no Contexts, no flags |
| *Autopilot* (ongoing habit) | the **Autopilot** list; no Contexts, no flags |
| Work / Personal (*Sphere*) | `#work` tag on Next Actions, a "Work" section everywhere else |

Details:
- [GLOSSARY.md](GLOSSARY.md): the vocabulary
- [docs/rules.md](docs/rules.md): the Rules
- [docs/step-guide.md](docs/step-guide.md): the Step Guide
- [docs/adr/](docs/adr/): the decisions behind the structure

## Requirements (planned)

- macOS with iCloud Reminders
- [RemCTL](https://github.com/viticci/remctl), installed and onboarded (remgtd only reads through it)
- [uv](https://docs.astral.sh/uv/)
- Optional: Alfred, for the launcher workflow

## Install (planned)

```bash
uv tool install git+https://github.com/jonasrk/remgtd
remgtd open
```

Personal settings (list names, Sphere tag, thresholds, browser, terminal) live in `~/.config/remgtd/config.toml`, never in this repo.

## License

MIT
