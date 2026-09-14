# See the whole team's work

Build an overview you can return to without searching each conversation for a
summary. This walkthrough uses two KiroCrew sessions: one implementing a change
and one reviewing it. Use your own sessions; the example text below is fictional.

## Start with two sessions

Install and enable Multiplex using the [installation instructions](../README.md#install).
Open or create two dashboard sessions and give them clear titles, such as
“Search improvements” and “Search review”. Creating these sessions does not
start work; use their conversations to assign any tasks you want the agents to do.

Open **Multiplex** from the dashboard sidebar. Select the relevant workspace
and choose **Cards** to read sessions side by side. **List** gives each session
more room; **Grid** fits more cards into the overview.

## Put useful context on each card

On the implementation card, choose **Add work state**, or **Edit state** if it
already has a checkpoint. Record a concise update, for example:

- **Current work:** “Search grouping implemented; keyboard navigation review pending.”
- **Next action:** “Ask the reviewer to check keyboard focus order.”
- **Notes / changes:** “Search grouping checks passed.”

Expand **Goal, status, identity and attention** to set the goal to “Make search
results easier to scan”, then choose **Save work state**. Do the same on the
review card, using its own current work and next action—for example, “Review
keyboard focus order” and “Return findings to the implementation session”.

Stock KiroCrew supports these manual edits. Hosts with a session-bound checkpoint
tool can also let agents publish their work state. The overview uses those
explicit records alongside available activity signals; the age of a record
matters when judging whether it still describes current work.

## Follow the handoff

Read the two cards together. One shows what is ready for review; the other shows
what the reviewer is checking. As the work advances, record a short result or
blocker in **Notes / changes** and keep the next action current.

The cards make the recorded handoff readable in one place. Coordinate the actual
handoff through your conversations or existing agent workflow; saving a note in
Multiplex records context and does not send a message to another agent.

## Open only the conversation you need

When a card needs your attention, read the request and choose **Open** to continue
in that session. Return to Multiplex afterward to see how that session's recorded
work fits alongside the rest of the team.

Before stepping away, leave each unfinished session with one concrete next
action. On your next visit, its goal, updates, and next step are already together
on the card.
