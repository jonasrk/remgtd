# remgtd

An opinionated way to run Getting Things Done (David Allen, the original book) on top of Apple Reminders, together with a read-only view that shows the system in GTD terms and checks whether it is still being run by the book.

## Language

### System

**remgtd**:
The whole system: the conventions for GTD in Reminders, its Rules, the View, the Step Guide and the command that opens them.

**Reminders**:
Apple Reminders, the single place where the system's data lives and is edited.
_Avoid_: the database, the backend

**View**:
The browser page that shows the system's data in GTD terms, next to Reminders. It does not change data.
_Avoid_: dashboard, GUI

**Step Guide**:
The part of the View that explains each of GTD's five steps (Capture, Clarify, Organize, Reflect, Engage): its purpose, start point, end point and key questions, with a live status from the data.
_Avoid_: cheat sheet, workflow

### Outside Reminders

**Calendar**:
Whatever calendar the user keeps: GTD's "hard landscape" of things bound to a day or time.
_Avoid_: due dates (a due date in Reminders is not the Calendar)

**Tickler File**:
GTD's tickler for things that should resurface on a future date, kept outside Reminders (e.g. a physical 43-folder file).
_Avoid_: deferred list, pending

### GTD objects

**Stuff**:
Anything captured that has not yet been clarified: its meaning and next step are still open.
_Avoid_: open loop (in this system that word means only a multi-step outcome), inbox item, pending (clarifying and organizing happen together, so nothing waits in between)

**Open Loop**:
A desired outcome that won't be reached by completing its next action. Only the next step needs to be written down. GTD's "project".
_Avoid_: Project

**Autopilot**:
An ongoing commitment that runs on habit (e.g. a weekly sport). It has no end and needs no Next Action, so it is not an Open Loop; it is only looked at during Reflect.
_Avoid_: Area of Focus, routine, project

**Sphere**:
Work or Personal: the part of life something belongs to, used only to focus on one and hide the other.
_Avoid_: Area, Area of Focus (GTD uses that for finer areas like Health or Finances), realm

**Next Action**:
A physical, visible action that can be done as soon as one of its Contexts comes up. An Open Loop can have several at once.
_Avoid_: NA, task, todo

**Lead Action**:
The one Next Action in an Open Loop that is most likely or most important to do next. Only Open Loops have one.
_Avoid_: main NA, P1, "the next action"

**Context**:
A tool, place, person or condition a Next Action needs to be done. A Next Action can have any number of them, and the same Contexts serve both Spheres.
_Avoid_: tag (a tag is how a Context is stored, not what it is), work context

**Context Kind**:
A loose grouping of Contexts by what they describe. The set is open; it starts with Place/Tool, Agenda and Condition.
_Avoid_: context type, context group

**Place/Tool**:
A Context Kind: where you are or what you have at hand (car, gym, outside).

**Agenda**:
A Context Kind: one person, collecting what to raise with them and what they owe you.
_Avoid_: People context

**Condition**:
A Context Kind: the time, energy or urgency a Next Action fits (quick wins, evening, low energy).
_Avoid_: mood

**Waiting For**:
Something someone else has to deliver before you can move on. It always names the person, as an Agenda.
_Avoid_: delegated, pending

**Checklist**:
A reusable list of steps (daily chores, inbox sweep, packing). Reference material, not a commitment, so the Rules ignore it.
_Avoid_: routine, template (a template is how a Checklist is stored)

### Checking

**Rule**:
A statement of how the system should look, derived from the original GTD book.
_Avoid_: policy, guideline

**Violation**:
A spot in the system that breaks a Rule.
_Avoid_: error, issue, non-compliance

**Hint**:
A spot in the system that is probably drifting from GTD but may be fine; a nudge, not a broken Rule.
_Avoid_: warning, smell, suggestion
