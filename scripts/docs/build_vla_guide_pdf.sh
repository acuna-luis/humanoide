#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
SOURCE="$REPO_ROOT/docs/vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md"
OUTPUT="$REPO_ROOT/docs/vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.pdf"
RENDERER="$SCRIPT_DIR/render_markdown_pdf.py"

if ! command -v google-chrome >/dev/null 2>&1; then
  echo "ERROR: google-chrome no está instalado." >&2
  exit 1
fi

temporary_dir="$(mktemp -d)"
trap 'rm -rf -- "$temporary_dir"' EXIT
html_file="$temporary_dir/vla-guide.html"

python3 "$RENDERER" "$SOURCE" "$html_file"

google-chrome \
  --headless \
  --disable-gpu \
  --no-pdf-header-footer \
  --print-to-pdf="$OUTPUT" \
  "file://$html_file" >/dev/null 2>&1

test -s "$OUTPUT"
printf 'PDF_OK=%s\n' "$OUTPUT"
