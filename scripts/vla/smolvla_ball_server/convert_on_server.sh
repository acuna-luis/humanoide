#!/usr/bin/env bash
# Local-only conversion of the staged ball candidates. No robot or model.
set -euo pipefail
IMAGE='cruzr-smolvla-ball:0.5.1-1396b9fa'

usage() {
  cat <<'EOF'
Uso: convert_on_server.sh --help
     convert_on_server.sh --check --staging /ruta/staging --output /ruta/nueva
     convert_on_server.sh --run   --staging /ruta/staging --output /ruta/nueva

--check valida hashes del staging, imagen Docker y destino, sin crear archivos.
--run crea un directorio exclusivo nuevo y convierte SOLO datos experimentales.
El contenedor no tiene red, GPU, modelo, robot ni acceso de escritura al staging.
Los datos incluyen personas y son privados. El resultado no autoriza control físico.
EOF
}

if [[ $# == 1 && ( "$1" == '--help' || "$1" == '-h' ) ]]; then usage; exit 0; fi
[[ $# == 5 ]] || { usage >&2; exit 2; }
ACTION="$1"; shift
[[ "$ACTION" == '--check' || "$ACTION" == '--run' ]] || { usage >&2; exit 2; }
STAGING=''; OUTPUT=''
while [[ $# -gt 0 ]]; do
  case "$1" in
    --staging) [[ -z "$STAGING" && $# -ge 2 ]] || { usage >&2; exit 2; }; STAGING="$2"; shift 2 ;;
    --output) [[ -z "$OUTPUT" && $# -ge 2 ]] || { usage >&2; exit 2; }; OUTPUT="$2"; shift 2 ;;
    *) usage >&2; exit 2 ;;
  esac
done
[[ -n "$STAGING" && -n "$OUTPUT" && "$STAGING" == /* && "$OUTPUT" == /* ]] || { usage >&2; exit 2; }
[[ -d "$STAGING" && ! -e "$OUTPUT" && ! -L "$OUTPUT" ]] || { echo 'ERROR: staging ausente o output ya existe.' >&2; exit 1; }
STAGING="$(realpath -e -- "$STAGING")"
OUTPUT="$(realpath -m -- "$OUTPUT")"
[[ -d "$(dirname -- "$OUTPUT")" ]] || { echo 'ERROR: debe existir el directorio padre de output.' >&2; exit 1; }
[[ "$STAGING" =~ ^/[A-Za-z0-9_./-]+$ && "$OUTPUT" =~ ^/[A-Za-z0-9_./-]+$ ]] || { echo 'ERROR: rutas con caracteres no admitidos.' >&2; exit 1; }
if [[ "$OUTPUT" == "$STAGING" || "$OUTPUT" == "$STAGING/"* || "$STAGING" == "$OUTPUT/"* ]]; then
  echo 'ERROR: output no puede solaparse con staging.' >&2; exit 1
fi

# Verify every staged file against the transfer metadata; no writes occur here.
# SHA metadata verifies transfer consistency, not trust against an attacker who
# can rewrite both data and metadata. Keep the staging directory private.
SOURCE_PATH="$(python3 -B - "$STAGING" <<'PY'
import hashlib,json,re,sys
from pathlib import Path
root=Path(sys.argv[1]); metadata=json.loads((root/'STAGING_METADATA.json').read_text())
if metadata.get('no_hub_upload') is not True or metadata.get('no_robot_control') is not True:
    raise SystemExit('Staging sin marcas de experimento local')
expected=metadata.get('file_sha256');source=metadata.get('source_container_path')
if not isinstance(expected,dict) or not expected or not isinstance(source,str):
    raise SystemExit('Metadatos de staging incompletos')
if not re.fullmatch(r'/[A-Za-z0-9_./-]+',source) or '..' in Path(source).parts or source.startswith('/work/') or source in ('/work','/tmp'):
    raise SystemExit('Ruta original no válida para el contenedor')
for name,value in expected.items():
    if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z0-9_./-]+',name) or '..' in Path(name).parts:
        raise SystemExit('Ruta insegura en staging')
    path=root
    for part in Path(name).parts:
        path=path/part
        if path.is_symlink(): raise SystemExit('Symlink en staging')
    if root not in path.resolve(strict=True).parents or not path.is_file():
        raise SystemExit('Archivo de staging ausente o fuera de directorio')
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(2**20),b''):h.update(block)
    if h.hexdigest()!=value: raise SystemExit(f'Hash de staging incorrecto: {name}')
required=['candidate_bundle/manifest.json','source_capture/samples.jsonl',
          'tools/prepare_ball_observations.py','tools/prepare_ball_candidate_targets.py',
          'tools/convert_ball_candidates_to_lerobot.py','tools/convert_on_server.sh']
if any(name not in expected for name in required):raise SystemExit('Faltan archivos requeridos en staging')
if expected['source_capture/samples.jsonl']!=metadata.get('source_samples_sha256'):
    raise SystemExit('Hash de muestras no coincide con metadatos')
if expected['candidate_bundle/manifest.json']!=metadata.get('candidate_manifest_sha256'):
    raise SystemExit('Hash de bundle no coincide con metadatos')
bundle=json.loads((root/'candidate_bundle'/'manifest.json').read_text())
segments=bundle.get('segments')
if not isinstance(segments,list) or not segments or any(s.get('source_dir')!=source for s in segments):
    raise SystemExit('El origen del bundle no coincide con el montaje')
print(source)
PY
)"
command -v docker >/dev/null
docker image inspect "$IMAGE" >/dev/null || { echo 'ERROR: imagen local ausente; no se hace pull.' >&2; exit 1; }
printf 'Staging verificado: %s\nOrigen dentro del contenedor: %s\nOutput nuevo: %s\n' "$STAGING" "$SOURCE_PATH" "$OUTPUT"
if [[ "$ACTION" == '--check' ]]; then
  echo 'Solo comprobación. No se creó output ni se ejecutó contenedor.'
  exit 0
fi

umask 077
mkdir -m 700 -- "$OUTPUT"
echo 'Directorio creado. Si la conversión falla, conservar el directorio parcial para diagnóstico.'
docker run --rm --pull=never --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges --user "$(id -u):$(id -g)" \
  --tmpfs /tmp:rw,nosuid,nodev,noexec \
  --env HOME=/tmp --env HF_HUB_OFFLINE=1 --env HF_HUB_DISABLE_TELEMETRY=1 \
  --env TRANSFORMERS_OFFLINE=1 --env PYTHONDONTWRITEBYTECODE=1 \
  --mount "type=bind,src=$STAGING/candidate_bundle,dst=/work/candidates,readonly" \
  --mount "type=bind,src=$STAGING/source_capture,dst=$SOURCE_PATH,readonly" \
  --mount "type=bind,src=$STAGING/tools,dst=/work/tools,readonly" \
  --mount "type=bind,src=$OUTPUT,dst=/work/output" \
  "$IMAGE" python -B /work/tools/convert_ball_candidates_to_lerobot.py \
  --candidates /work/candidates --output /work/output/lerobot-experiment --offline-experiment
echo 'Conversión experimental finalizada; no está validada para robot ni autorizada para publicación.'
