#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="$project_dir/.env"
server="$project_dir/.venv/bin/ai-cycling-coach"

if [[ ! -f "$env_file" ]]; then
  echo "Missing .env; run scripts/setup.sh first." >&2
  exit 1
fi

IFS= read -r line < "$env_file"
case "$line" in
  INTERVALS_API_KEY=*) api_key="${line#INTERVALS_API_KEY=}" ;;
  *) echo "Invalid .env; expected INTERVALS_API_KEY on the first line." >&2; exit 1 ;;
esac

if [[ -z "$api_key" ]]; then
  echo "INTERVALS_API_KEY must not be empty." >&2
  exit 1
fi
if [[ ! -x "$server" ]]; then
  echo "Missing installed server; run scripts/setup.sh first." >&2
  exit 1
fi

export INTERVALS_API_KEY="$api_key"
exec "$server"
