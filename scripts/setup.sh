#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="$project_dir/.env"

if [[ -n "${PYTHON:-}" ]]; then
  python_cmd="$PYTHON"
else
  python_cmd=""
  for candidate in python3.13 python3.12 python3.11 python3; do
    if command -v "$candidate" >/dev/null \
      && "$candidate" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))'; then
      python_cmd="$candidate"
      break
    fi
  done
fi

if [[ -z "$python_cmd" ]] || ! command -v "$python_cmd" >/dev/null; then
  echo "Python 3.11+ is required." >&2
  exit 1
fi
command -v codex >/dev/null || {
  echo "The codex command is required." >&2
  exit 1
}
"$python_cmd" -c 'import sys; raise SystemExit(sys.version_info < (3, 11))' || {
  echo "Python 3.11+ is required." >&2
  exit 1
}

if [[ ! -d "$project_dir/.venv" ]]; then
  "$python_cmd" -m venv "$project_dir/.venv"
fi
"$project_dir/.venv/bin/python" -m pip install -e "$project_dir[dev]"

write_secret=true
if [[ -f "$env_file" ]]; then
  read -r -p ".env already exists. Replace its API key? [y/N] " answer
  [[ "$answer" =~ ^[Yy]$ ]] || write_secret=false
fi
if [[ "$write_secret" == true ]]; then
  read -r -s -p "Intervals.icu API key: " api_key
  echo
  [[ -n "$api_key" && "$api_key" != *$'\n'* ]] || {
    echo "API key must not be empty or contain a newline." >&2
    exit 1
  }
  umask 077
  printf 'INTERVALS_API_KEY=%s\n' "$api_key" > "$env_file"
fi
chmod 600 "$env_file"
chmod u+x "$project_dir/scripts/run-server.sh"

if ! codex mcp add ai-cycling-coach -- "$project_dir/scripts/run-server.sh"; then
  echo "MCP registration already exists or could not be added." >&2
  echo "Inspect it with: codex mcp list" >&2
  echo "To replace it, remove the existing ai-cycling-coach entry and rerun this script." >&2
  exit 1
fi

echo "Setup complete. Restart Codex, then call connection_status."
