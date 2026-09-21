# AI Cycling Coach

A small local MCP server that gives Codex controlled access to one Intervals.icu
account. Intervals.icu remains the source of truth and syncs planned workouts.

## Setup

1. In Intervals.icu, open **Settings → Developer Settings** and generate a
   personal API key.
2. Run `scripts/setup.sh` and enter the key when prompted.
3. Restart Codex.
4. Ask Codex to call `connection_status` before any other operation.

The key is stored only in `.env`, which is gitignored and set to owner-only
permissions. The setup script creates a local virtual environment and registers
`scripts/run-server.sh` as a local stdio MCP server named `ai-cycling-coach`.
Set `PYTHON` before running setup if you want to use a specific Python 3.11+
interpreter.

## Approval workflow

Codex may read training data automatically. Before writing, it presents the
complete plan outline and asks once for approval. Only then may it call
`replace_training_plan` with `approved=true`. The tool can replace only events
created with the `ai-cycling-coach:` ownership prefix.

## First live verification

Run `connection_status` first and review the returned athlete identity. The
first calendar write should be a short visible test plan that you explicitly
approve.
