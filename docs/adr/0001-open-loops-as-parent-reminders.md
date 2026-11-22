# Open Loops are parent reminders; the flag marks the Lead Action; Sphere is a tag on actions and a section elsewhere

An Open Loop is a top-level reminder in the Open Loops list, and its actions are its subtasks. A Next Action is any action with at least one Context tag. The Reminders flag marks an Open Loop's Lead Action. The Work Sphere is stored as a `#work` tag on Next Actions only, and as a "Work" section in the lists that hold everything else (Open Loops, Waiting For, Someday/Maybe, Autopilot). Personal is the default and isn't marked. Tag and section names are configurable; `#work` and "Work" are the defaults. We chose parent reminders over one list per project, sections, or one tag per project. Those options either can't be completed or archived as a unit, aren't visible in smart lists, or cause tag sprawl. We store Sphere in two ways because a smart list can include only one list and can't require "has a Context". A `#work` tag on Open Loops or Waiting For items would therefore clutter the single Work smart list.

## Consequences

- A test on macOS/iOS 27 (2026-11-22) showed that custom smart lists and Flagged show subtasks flat, without their parent, and leave out untagged subtasks. Reminders' own lists therefore show *what* can be done, and only the View shows which Open Loop an action belongs to. Next Action titles have to make sense on their own.
- At work, one smart list (`#work`) shows all Work Next Actions, and its flagged items are the Lead Actions. The Personal list excludes `#work`. That works on the Mac and isn't needed on the iPhone.
- Subtasks don't inherit tags or sections. The View works out Sphere from both, and gives a Hint when an action's tag and its Open Loop's section disagree.
- Completing an Open Loop completes all its subtasks.
