# agent-team

A Claude Code skill that runs a task with a small team of subagents. The main session plans and coordinates.
It hands code reading to `explorer`, edits and test runs to `worker`, doc lookups to `researcher`, and the
task's acceptance tests to `tester`. Once the interfaces are pinned, the tester writes those tests while the
workers build in parallel, split by area, and afterwards it verifies the work against them. The coordinator
consults the advisor at fixed checkpoints.

The run survives usage limits. It keeps a handover file and arms a watchdog cron. When the limit resets,
it resumes the run itself.

## Layout

It is a Claude Code plugin, and the repo is also its own one-plugin marketplace.

| Path | What it is |
| --- | --- |
| `.claude-plugin/plugin.json` | The plugin manifest |
| `.claude-plugin/marketplace.json` | Lists this repo as a marketplace with the one plugin |
| `skills/agent-team/SKILL.md` | The coordinator's instructions |
| `skills/agent-team/scripts/reset-time.py` | Reads the reset time from a usage-limit message and prints the cron for the resume |
| `agents/explorer.md` | Read-only code explorer (Opus, medium effort) |
| `agents/worker.md` | Makes one scoped change and runs its tests (Opus, medium effort) |
| `agents/researcher.md` | Finds and summarises authoritative docs (Opus, medium effort) |
| `agents/tester.md` | Writes the acceptance tests while the workers build, then verifies the work against them (Opus, xhigh effort) |

Inside a session the subagents are named `agent-team:explorer`, `agent-team:worker`,
`agent-team:researcher` and `agent-team:tester`.

## Install

In Claude Code:

```text
/plugin install agent-team --marketplace p-dealwis/agent-team
```

On versions before 2.1.275, add the marketplace first:

```text
/plugin marketplace add p-dealwis/agent-team
/plugin install agent-team@agent-team
```

To get updates automatically, open `/plugin`, go to Marketplaces, pick `agent-team` and choose Enable
auto-update. Every push to `main` is a new version, so there is no version number to bump. To update by
hand, run `claude plugin marketplace update agent-team`, then `claude plugin update agent-team@agent-team`.

### Moving from the old install

The skill used to be a clone at `~/.claude/skills/agent-team` with its agents linked into
`~/.claude/agents`. After installing the plugin, remove both, or every name shows up twice:

```bash
for a in explorer researcher tester worker; do
  [ -L ~/.claude/agents/$a.md ] && rm ~/.claude/agents/$a.md
done
rm -rf ~/.claude/skills/agent-team
```

## Use

```text
/agent-team <task>
/agent-team resume <path to agent-team-handover.md>
```

Its full name is `/agent-team:agent-team`, if another skill is also called `agent-team`.

You can also ask for something to be done "by the agent team".

## Requirements

- Claude Code with subagents and Opus access. The tester runs at `xhigh` effort, which costs more, so the
  skill uses it only for the write and verify steps.
- The advisor tool, for the checkpoints. Without it, the skill says so once and carries on.
- `CronCreate` for the usage-limit watchdog. Cron jobs live only in their session. If the session closes,
  run `/agent-team resume <handover path>` in a new session.
- Python 3.9 or later for `reset-time.py`. Older versions can't read named time zones.
