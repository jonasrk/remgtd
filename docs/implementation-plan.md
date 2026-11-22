# Implementation plan

Status: **implemented** (v0.1.0, 2026-11-22). Additions beyond the plan: the System overview tab and `remgtd serve --demo`.

## Shape

One Python package, `remgtd`, run with `uv`. It has four commands:

| Command | What it does |
|---|---|
| `remgtd check` | Reads Reminders once and prints all Violations and Hints in the terminal. |
| `remgtd serve` | Runs the local server that keeps the View live. |
| `remgtd open` | The launcher: makes sure the server runs, then arranges Reminders (left) and the View (right). |
| `remgtd init` / `remgtd doctor` | Write a commented default config / check that RemCTL, the lists and the Context groups exist. |

```
Reminders ──(remctl, read-only)──▶ snapshot ──▶ model ──▶ rules ──▶ state ──(SSE)──▶ View (browser)
                                                                       ▲
                                         click item ──▶ server ──▶ `open x-apple-reminderkit://…` ──▶ Reminders
```

remgtd never writes to Reminders. Clicking an item asks the local server to open that reminder's deep link. Opening isn't editing.

## Package layout

```
src/remgtd/
  config.py        # TOML config, defaults, validation (~/.config/remgtd/config.toml)
  remctl.py        # the only module that runs remctl; returns raw JSON
  snapshot.py      # one consistent read: export + groups/lists + smart lists + sections
  model.py         # pure: snapshot → Open Loops, Next Actions, Lead Actions, Contexts, Spheres
  rules.py         # pure: model → findings; one function per Rule (R1…R19), ids match docs/rules.md
  state.py         # model + findings → the JSON the View renders (open items only)
  server.py        # Starlette app: /, /events (SSE), /open/{id}, /health
  launcher.py      # `remgtd open`: start server in a terminal tab, browser tab, window placement
  cli.py           # entry points
  web/             # index.html, app.js, app.css: no build step, no framework
  content/step_guide.md   # Step Guide text, rendered into the cards (docs/step-guide.md points here)
integrations/alfred/remgtd.alfredworkflow   # keyword → `remgtd open`
tests/             # pytest; synthetic fixture snapshots only, never real data
```

Dependencies are kept small: `starlette` and `uvicorn` for the server, and `tomllib` from the standard library for config. Tests use `pytest`.

## Key design decisions

**Reading Reminders.**
- `remctl --format json export` returns every reminder, with ids, lists, parents, tags, flags and dates, in about 0.8s.
- It doesn't include **sections**, which the Sphere needs for Open Loops, Waiting For, Someday/Maybe and Autopilot. Each `show <list>` takes about 0.8s more.
- Plan: every tick runs `export`, plus one `show` for one sectioned list in rotation. Item changes appear in about 1s. A section change (Sphere) appears within about 4 ticks.
- Milestone 1 first checks whether parallel remctl calls, or the `remctl workspace` snapshot command, can fetch everything in one tick. If so, the rotation goes away.

**Change detection.**
- The server hashes each snapshot and recomputes only when the hash changes.
- It then pushes the full state over Server-Sent Events. The state is small: open items only.
- It polls fast (every tick) while a View is connected and slowly (every 30s) when none is. With no client, it does nothing.

**Contexts.**
- A Context is a smart list inside a Context Kind group, configured as group name → kind.
- The tag comes from the smart list's filter, in either the current or the legacy format. If the filter can't be decoded, the tag is taken from the name `#tag`.

**Sphere.**
- A Next Action is Work if it has the Sphere tag.
- Any other item is Work if it's in the Sphere section.
- A subtask falls back to its Open Loop's Sphere for display. R18 flags disagreement.

**Rules.**
- Each rule is a pure function from model to findings: `{rule_id, severity, item_ids, message}`.
- Thresholds come from config.
- Tests cover each rule with a minimal synthetic snapshot.

**The View.**
- Top bar with the Sphere switch and Violation and Hint counts.
- Step Guide row with five collapsible cards. Collapse state is remembered in `localStorage`.
- Tabs: Open Loops (the default), Contexts, Waiting For, Reflect.
- Badges on items, and a "problems only" filter.
- When the server is unreachable, a banner says "not connected, run `remgtd open`".

**The launcher (`remgtd open`).**
1. If `/health` doesn't answer, open a new terminal tab (iTerm2 or Terminal.app, from config) running `remgtd serve`, and wait for `/health`.
2. In the browser (Brave by default; also Chrome or Safari), focus an existing tab on the View's URL, or open one.
3. Open Reminders.
4. Read the main screen's usable area through JXA (`NSScreen.visibleFrame`), then place Reminders on the left half and the browser window on the right half with System Events. This needs Accessibility permission once. `remgtd doctor` explains it.

**Config.**
- `remgtd init` writes a fully commented file holding every default:
  - list, group and section names
  - Context Kind groups
  - Sphere tag and section
  - thresholds
  - weekly-review link
  - inbox-sweep Checklist name
  - browser, terminal, port
- Nothing personal ships in the repo.

## Milestones

1. **Core and `remgtd check`**: config, remctl reader, snapshot, model, all 19 Rules, tests. It's useful on its own: you can run `remgtd check` in the terminal right away.
2. **Server and View**: live updates, all tabs, badges, click-to-open.
3. **Step Guide**: cards rendered from `content/step_guide.md`, live statuses, collapse.
4. **Launcher and Alfred**: `remgtd open`, window placement, the Alfred workflow, `doctor`.
5. **Release**:
   - README install section
   - `uv tool install git+https://github.com/jonasrk/remgtd` tested on a second Mac
   - a short demo with synthetic data

Each milestone ends with tests passing, a commit, and a short check on your real data. Your data isn't committed.

## Out of scope (for now)

- Writing to Reminders, such as fixing a Violation from the View. The door is left open: `remctl.py` is the only place that touches RemCTL.
- Other devices, logins, and anything beyond localhost.
- Calendar integration.
