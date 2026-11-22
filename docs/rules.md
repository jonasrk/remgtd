# Rules

Status: **accepted** 2026-11-22.

V = Violation (a Rule is broken), H = Hint (probably drifting, may be fine). Day thresholds are starting values.
Scope: only lists in the remgtd group (In-box, Open Loops, Next Actions, Waiting For, Someday/Maybe, Autopilot).
Rules check open items only; completed items are history.

## In-box

| # | | Rule | From the book |
|---|---|---|---|
| R1 | H | An In-box item is older than **7 days**. | Empty the In-box at least weekly; Stuff that sits there stops being trusted. |

## Open Loops

| # | | Rule | From the book |
|---|---|---|---|
| R2 | V | An Open Loop has no Next Action (no subtask with a Context). | Every project needs at least one next action, or it isn't moving. |
| R3 | V | An Open Loop has Next Actions but no Lead Action (nothing flagged). | Decide the next step now, not when you look at it again. |
| R4 | H | An Open Loop has more than one Lead Action. | The Lead Action is *the* most likely step; two means none. |
| R5 | V | A Lead Action has no Context. | It can never come up in an Engage list. |
| R6 | H | Nothing in an Open Loop has been created or completed in **30 days**. | Stalled projects should be renegotiated or moved to Someday/Maybe at the Weekly Review. |

## Next Actions

| # | | Rule | From the book |
|---|---|---|---|
| R7 | H | An action (an item in Next Actions, or a subtask of an Open Loop) has no Context. | Without a Context it never shows up when you could do it. |
| R8 | H | An item in the Next Actions list has subtasks. | More than one step makes it an Open Loop. |
| R9 | H | A standalone Next Action is flagged. | The flag only means Lead Action inside an Open Loop. |
| R10 | H | A Next Action has a due date. | Only the hard landscape gets dates, and that lives in the Calendar. Use a date only for a real deadline. |

## Waiting For

| # | | Rule | From the book |
|---|---|---|---|
| R11 | V | A Waiting For item names no person (no Agenda). | You need to know whom to follow up with. |
| R12 | H | A Waiting For item is older than **14 days**. | Review it weekly, and follow up when it's overdue. |
| R13 | H | A Waiting For item is flagged or has a non-Agenda Context. | It isn't yours to do, so it shouldn't show up as doable. |

## Someday/Maybe and Autopilot

| # | | Rule | From the book |
|---|---|---|---|
| R14 | V | A Someday/Maybe item or any of its subtasks has a Context or a flag. | Someday items aren't commitments, so they must not appear in Engage lists. |
| R15 | V | An Autopilot item or any of its subtasks has a Context or a flag. | Autopilot needs no action. A real push becomes a Next Action or an Open Loop. |

## Contexts and Sphere

| # | | Rule | From the book |
|---|---|---|---|
| R16 | H | A tag is neither a known Context nor the Sphere tag (e.g. a stray tag from pasted text). A tag is a known Context when it has a smart list in a Context Kind group. | Contexts must be clean to be trusted. |
| R17 | H | The Sphere tag is on something that isn't a Next Action. | Sphere for non-actions lives in the "Work" section (ADR 0001). |
| R18 | H | A Next Action's Sphere tag disagrees with its Open Loop's section. | Otherwise the Work list hides real work, or shows personal items. |

## Structure

| # | | Rule | From the book |
|---|---|---|---|
| R19 | H | The remgtd group contains a list that isn't one of the six known lists. | Every item has exactly one home with a known meaning. |
