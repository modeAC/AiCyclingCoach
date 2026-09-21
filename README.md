# AI Cycling Coach

A small local stdio MCP server that gives compatible AI agents controlled access
to one Intervals.icu account. Intervals.icu remains the source of truth and
syncs planned workouts.

## Codex setup (tested)

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

## Other MCP clients (untested)

The server uses standard MCP over stdio, so other MCP clients should be able to
launch the same `scripts/run-server.sh` command. These integrations have not
been tested yet.

Before registering another client, install the server and create its private
environment file from the repository root:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e .
read -r -s -p "Intervals.icu API key: " api_key
printf '\n'
umask 077
printf 'INTERVALS_API_KEY=%s\n' "$api_key" > .env
unset api_key
chmod u+x scripts/run-server.sh
```

Use a different Python 3.11+ executable if `python3.11` is unavailable.

### Claude Code

```bash
claude mcp add --scope user ai-cycling-coach -- \
  /absolute/path/to/AiCyclingCoach/scripts/run-server.sh
```

### OpenClaw

```bash
openclaw mcp add ai-cycling-coach \
  --command /absolute/path/to/AiCyclingCoach/scripts/run-server.sh
openclaw mcp doctor ai-cycling-coach --probe
```

### DeepSeek

The DeepSeek API supports tool calling but does not launch local MCP servers by
itself. Use DeepSeek through an MCP-capable host, such as OpenClaw, and register
the server with that host.

## Approval workflow

The agent may read training data automatically. Before writing, it must present
the complete plan outline and ask once for approval. Only then may it call
`replace_training_plan` with `approved=true`. Configure every MCP client to
require confirmation for this write tool: the server trusts the client's
`approved` value. The tool can replace only events created with the
`ai-cycling-coach:` ownership prefix.

## First live verification

Run `connection_status` first and review the returned athlete identity. The
first calendar write should be a short visible test plan that you explicitly
approve.
