# agent-team

A Claude Code skill that runs a task with a small team of subagents. The main session plans and coordinates.
It hands code reading to `explorer`, edits and test runs to `worker`, doc lookups to `researcher`, and the
task's acceptance tests to `tester`. The tester writes those tests before the work starts and verifies the
work against them afterwards. The coordinator consults the advisor at fixed checkpoints.

The run survives usage limits. It keeps a handover file and arms a watchdog cron. When the limit resets,
it resumes the run itself.

## Layout

| Path | What it is |
| --- | --- |
| `SKILL.md` | The coordinator's instructions |
| `agents/explorer.md` | Read-only code explorer (Opus, medium effort) |
| `agents/worker.md` | Makes one scoped change and runs its tests (Opus, medium effort) |
| `agents/researcher.md` | Finds and summarises authoritative docs (Opus, medium effort) |
| `agents/tester.md` | Writes the acceptance tests first, then verifies the work against them (Opus, xhigh effort) |
| `scripts/reset-time.py` | Reads the reset time from a usage-limit message and prints the cron for the resume |

## Install

The skill calls `scripts/reset-time.py` by its full path, so clone the repo to exactly this path:

```bash
git clone https://github.com/p-dealwis/agent-team.git ~/.claude/skills/agent-team
mkdir -p ~/.claude/agents
for a in explorer researcher tester worker; do
  ln -s ~/.claude/skills/agent-team/agents/$a.md ~/.claude/agents/$a.md
done
```

Claude Code follows the symlinks, so every edit is made in one place: the repo. If you already have agents
with these names, rename one set first.

## Use

```text
/agent-team <task>
/agent-team resume <path to agent-team-handover.md>
```

You can also ask for something to be done "by the agent team".

## Requirements

- Claude Code with subagents and Opus access. The tester runs at `xhigh` effort, which costs more, so the
  skill uses it only for the write and verify steps.
- The advisor tool, for the checkpoints. Without it, the skill says so once and carries on.
- `CronCreate` for the usage-limit watchdog. Cron jobs live only in their session. If the session closes,
  run `/agent-team resume <handover path>` in a new session.
- Python 3.9 or later for `reset-time.py`. Older versions can't read named time zones.
