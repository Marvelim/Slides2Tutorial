#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_DIR="$ROOT_DIR/.conda"
ENV_FILE="$ROOT_DIR/environment.yml"
CLI="$ENV_DIR/bin/slides2tutorial"

usage() {
  cat <<'EOF'
Usage:
  ./run.sh input.pdf [slides2tutorial options]

Examples:
  ./run.sh slides.pdf
  ./run.sh slides.pdf --limit-pages 5
  ./run.sh slides.pdf --out output/cn-notes.md --dpi 220 --force

Required configuration:
  Set GEMINI_BASE_URL and GEMINI_API_KEY in your shell or in a local .env file.

Example .env:
  GEMINI_BASE_URL="https://your-openai-compatible-endpoint/v1"
  GEMINI_API_KEY="your_api_key_here"
  GEMINI_MODEL="gemini-3.1-pro"

Defaults:
  output: output/tutorial.md
  dpi:    180
EOF
}

has_option() {
  local expected="$1"
  shift
  local arg
  for arg in "$@"; do
    if [[ "$arg" == "$expected" || "$arg" == "$expected="* ]]; then
      return 0
    fi
  done
  return 1
}

if [[ $# -lt 1 || "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

PDF_PATH="$1"
shift

cd "$ROOT_DIR"

if [[ -f "$ROOT_DIR/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.env"
  set +a
fi

if [[ ! -f "$PDF_PATH" ]]; then
  echo "Error: PDF not found: $PDF_PATH" >&2
  exit 1
fi

if [[ ! -x "$CLI" ]]; then
  if [[ -d "$ENV_DIR" && -x "$ENV_DIR/bin/python" ]]; then
    echo "Installing slides2tutorial into existing local conda environment..."
    "$ENV_DIR/bin/python" -m pip install -e ".[dev]"
  else
    if ! command -v conda >/dev/null 2>&1; then
      echo "Error: conda was not found. Install conda or create ./.conda manually." >&2
      exit 1
    fi
    echo "Creating local conda environment at $ENV_DIR..."
    conda env create -p "$ENV_DIR" -f "$ENV_FILE"
  fi
fi

if [[ -z "${GEMINI_BASE_URL:-}" ]] && ! has_option "--base-url" "$@"; then
  echo "Error: missing GEMINI_BASE_URL. Put it in .env or pass --base-url." >&2
  exit 1
fi

if [[ -z "${GEMINI_API_KEY:-}" ]] && ! has_option "--api-key" "$@"; then
  echo "Error: missing GEMINI_API_KEY. Put it in .env or pass --api-key." >&2
  exit 1
fi

OUTPUT_PATH="${OUTPUT_PATH:-output/tutorial.md}"
DPI="${DPI:-180}"

exec "$CLI" "$PDF_PATH" \
  --out "$OUTPUT_PATH" \
  --dpi "$DPI" \
  "$@"
