---
name: agent-team
description: Run a task with the agent-team setup - the main session plans and coordinates on high effort, delegates code reading to the explorer subagent, edits and tests to the worker subagent, doc lookups to the researcher subagent, and the task's acceptance tests to the tester subagent (Opus, xhigh), which writes them before the work and verifies the work against them after, and consults the advisor at fixed checkpoints. It survives usage limits: it keeps a handover file, arms a watchdog, and resumes the run itself after the limit resets. Use when the user says "agent-team", "/agent-team", or asks for something to be done "by the agent team", or to resume an agent-team run from its handover file.
---

# agent-team

You are the coordinator. You plan, delegate, verify and report. You do not read
whole files, edit code or fetch docs yourself when a subagent can do it.

## Setup (once, at the start)

1. If a session-effort tool is available (`set_session_effort`), set this session to
   `high`. Otherwise tell the user to set effort to high for this session and continue.
2. Confirm the Advisor tool is available. If it is not, say so once and carry on
   without it.
3. For a task with more than one round of delegation, start the handover file and
   arm the usage-limit watchdog (see [Usage limits](#usage-limits)).

Invoked as `/agent-team resume [handover path]`: skip planning and follow
[On resume](#on-resume) with that handover file.

## Roles

| Need | Delegate to | Never |
| --- | --- | --- |
| Find where something lives, how it works, what a change touches | `agent-team:explorer` | edits |
| Make a scoped change and run its tests | `agent-team:worker` | widen scope, commit, push, edit the tester's tests |
| Authoritative docs, API references, specs, changelogs | `agent-team:researcher` | edit code |
| Turn the goals into tests that must pass (before the work); verify the work against them (after) | `agent-team:tester` (Opus, `xhigh`) | edit production code, weaken a test to make it pass |

The four subagents come with this plugin, so their names carry its prefix: pass
`agent-team:explorer` and so on as the subagent type. The rest of this file calls them
the explorer, worker, researcher and tester.

Give each subagent one job with exact inputs: files, expected behaviour, test
command, or the question to answer. Run independent jobs in parallel. Do not
redo a job you delegated; wait for its report.

## Test-first loop

Use it for any task that changes code and has goals a test can check. Skip it for
docs-only, research, or config with no testable behaviour, and say why.

1. **Write.** After the plan (and advisor checkpoint 1 if it applies), run the
   `tester` in write mode with the goals, acceptance criteria and the interfaces or
   spec, not an implementation. It returns a goal → test table and red output.
   Check each test fails for the right reason and that together they cover the goals.
   **These tests are the contract.**
2. **Build.** Give the `worker` the task, the test command and the test files, marked
   read-only. The worker makes them pass (plus its own tests) and reports. If it thinks
   a test is wrong, it says so instead of changing it.
3. **Verify.** Run the `tester` in verify mode. It reruns everything, checks the test
   files weren't weakened (a tamper check), checks the goals are still covered, and
   diagnoses each failure: code wrong, test wrong, or goal ambiguous.
4. **Resolve.** Subagents can't message each other or call the advisor, so you
   mediate:
   - **Code wrong:** send the tester's diagnosis to the worker (continue it with
     `SendMessage`), then verify again.
   - **Test wrong**, or the worker disputes a test: put both positions to the advisor
     (checkpoint 4) and decide. If the test changes, the tester makes the change, and
     you record why.
   - **Goal ambiguous:** ask the user.
   - **The cap:** after two rounds on the same failure, stop and bring both positions to
     the user.
5. **Done.** Only when the agreed tests pass in verify mode, with a clean tamper check,
   or when the user accepts a documented exception.

The tester runs on Opus at `xhigh`, which is expensive. Use it for the write and
verify steps only. Routine test runs during the build are the worker's.

## Advisor checkpoints

Consult the advisor:

1. before committing to a large plan (more than a few files, or a design choice),
2. when the same error repeats after a fix attempt,
3. before calling a long task done,
4. when the tester and the worker disagree about a failing test.

State what the advisor said and what you changed because of it.

## Usage limits

A usage limit (daily, 5-hour or weekly) pauses the team. It is not a failure: it
never counts toward the two-round cap, never moves a job to another role, and you
never redo a subagent's job yourself because the limit cut it off.

The coordinator and its subagents share one account, so once the limit hits, you
can't act until it resets. Anything that wakes the run must be armed **before** that.

### Before the work

1. **Handover file.** Keep `agent-team-handover.md` in the scratchpad (or the task's
   directory) current: the goal and plan, each delegated job (role, agent ID,
   inputs, state: done / running / interrupted / not started), the contract tests and
   their last verify result, advisor notes, the cron job IDs, and the next step. Update
   it after each subagent report, before each long job and at each checkpoint. A
   resume must work from this file alone.
2. **Watchdog.** Call `CronCreate` with `cron: "7,27,47 * * * *"`, `recurring: true` and
   this prompt (fill in the path):

   > agent-team watchdog for `<handover path>`. If the agent-team run is stalled by a
   > usage limit (its last step was cut off, or a delegated job never reported back)
   > and the limit has reset, resume it as the agent-team skill's "On resume" says. If
   > it is progressing, waiting on running subagents, or finished, do nothing and
   > reply in one line.

   Record the job ID in the handover file. It fires only while the session is idle, so
   it never interrupts work. While the limit lasts its fires fail harmlessly, and the
   first fire after the reset resumes the run (at most 20 minutes late). An idle fire
   costs one short turn.

### When a limit shows up

These are the signals: a subagent result or tool error saying the usage limit is
reached (for example "usage limit reached … resets 3pm (Australia/Sydney)", or
"Claude AI usage limit reached|<epoch>"), or a warning that the limit is close.

1. Mark the job interrupted in the handover file, with the message.
2. Get the resume time:
   `python3 "${CLAUDE_SKILL_DIR}/scripts/reset-time.py" "<the message>"`
   prints `RESET_AT`, `RESUME_AT`, `CRON` (local time, 3 minutes past the reset) and
   `WAIT_MINUTES`. Exit 2 means it found no time: rely on the watchdog.
3. Call `CronCreate` with that `CRON`, `recurring: false`, and the watchdog's prompt.
   This resumes sooner than the watchdog. Make the tool call; saying you will doesn't
   arm anything.
4. Tell the user in one line: paused by a usage limit, resuming at `RESUME_AT`, which
   jobs were in flight. If `WAIT_MINUTES` is more than a day (a weekly limit), ask
   whether to wait or stop.
5. End the turn. Don't poll, sleep or start new jobs.

### On resume

1. **State first.** Read the handover file, `git status`, and which subagents are
   still running. If the run already finished, or another trigger already resumed it,
   do nothing. Delete any leftover one-shot job with `CronDelete`.
2. Continue each interrupted job with `SendMessage` to its agent ID, so it keeps its
   context. If that fails, start the job fresh from the handover file's inputs. The
   tester's contract tests stay as they are.
3. If the limit is still in force, arm a new one-shot from the new message and end
   the turn. After three resumes that hit the limit again, stop and tell the user.
4. Tell the user the run resumed, update the handover file, and continue the plan.

Cron jobs live only in this session. If the session is closed, nothing fires; the
handover file is the backstop, and `/agent-team resume <path>` in a new session
picks up from it.

## Finish

Report what was done, what was verified and how, and what is left. Include the
tester's verify-mode results, the tamper check, and every test that changed and why.
Failures are reported verbatim, not summarised away. List any usage-limit pauses:
when, for how long, and which jobs were re-run.

Then `CronDelete` the watchdog and any one-shot left (`CronList` to check).
