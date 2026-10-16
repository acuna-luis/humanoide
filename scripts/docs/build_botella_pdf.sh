#!/usr/bin/env bash
# Rebuild the bottle plan PDF using the project's Markdown renderer and Chrome.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
SOURCE="${1:-$REPO_ROOT/docs/plan_botella.md}"
OUTPUT="${2:-$REPO_ROOT/docs/plan_botella.pdf}"
command -v google-chrome >/dev/null
TASK_TMP="$(mktemp -d)"
trap 'rm -rf -- "$TASK_TMP"' EXIT
python3 "$SCRIPT_DIR/render_markdown_pdf.py" \
  "$SOURCE" "$TASK_TMP/plan.html"
python3 - "$TASK_TMP/plan.html" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
s = p.read_text()
s = s.replace('Cruzr S2 · VLA · Teleoperación', 'Cruzr S2 · Visión · Manos v4')
s = s.replace('Compatibilidad v0.2.0, PICO 4 Ultra Enterprise, captura de demostraciones, diseño de datasets y estrategia de entrenamiento.',
              'Plan de desarrollo: detección de botella, capturas RGB-D, calibración, planificación y agarre adaptativo.')
s = s.replace('Versión documental 1.2<br>21 de agosto de 2026',
              'Plan de trabajo · 15 de octubre de 2026<br>Integración y validación física pendientes')
s = s.replace('Documento técnico del proyecto. Los elementos marcados como Pendiente DSA requieren confirmación del proveedor.',
              'Plan de desarrollo. Consultar el estado de cada fase antes de ejecutar sus instrucciones.')
# Long code listings may span pages; wrap long commands instead of clipping.
s = s.replace('break-inside: avoid;\n  }\n  a {', 'break-inside: auto;\n    word-break: break-word;\n  }\n  a {')
p.write_text(s)
PY
google-chrome --headless --disable-gpu --no-pdf-header-footer \
  --user-data-dir="$TASK_TMP/chrome" \
  --print-to-pdf="$TASK_TMP/plan_botella.pdf" \
  "file://$TASK_TMP/plan.html" >"$TASK_TMP/chrome.log" 2>&1 || {
    cat "$TASK_TMP/chrome.log" >&2
    exit 1
  }
test -s "$TASK_TMP/plan_botella.pdf"
cp "$TASK_TMP/plan_botella.pdf" "$OUTPUT"
printf 'PDF_OK=%s\n' "$OUTPUT"
