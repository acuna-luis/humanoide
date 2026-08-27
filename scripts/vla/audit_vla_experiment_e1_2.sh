#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso: ./scripts/vla/audit_vla_experiment_e1_2.sh [--output-dir DIR]

Audita localmente el XML S2, el catálogo de tasks y doce frames de referencia
del dataset. No conecta con el robot, no arranca inferencia y no publica mando.
Si no se indica DIR crea Humanoide-vla-evidence/<timestamp>_E1.2.
EOF
}

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/../.." && pwd)"
EVIDENCE_ROOT="${VLA_EVIDENCE_ROOT:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence}"
RUN_ID="$(date +%Y%m%dT%H%M%S)_E1.2"
RUN_DIR=""

while (($#)); do
  case "$1" in
    --output-dir)
      (($# >= 2)) || { echo "ERROR: --output-dir requiere DIR" >&2; exit 2; }
      RUN_DIR="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "ERROR: argumento desconocido: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

[[ -n "$RUN_DIR" ]] || RUN_DIR="$EVIDENCE_ROOT/$RUN_ID"

XML_REL="cruzrss2_vla_pack-002/codes-S2/motion/s2_vla_scripts/s2_bio_vla/s2_vla_pick_large_teleop_ready.xml"
TASKS_REL="cruzrss2_vla_pack-002/data/utars_clamp_and_place_large_box_full_data_bio_lerobot_0319/meta/tasks.jsonl"
VIDEOS_REL="cruzrss2_vla_pack-002/data/utars_clamp_and_place_large_box_full_data_bio_lerobot_0319/videos/chunk-000/observation.images.rgb"
EXPECTED_XML_SHA256="f4025124491eba995ec824db3e3be91875f781a4b4e98928654bde9a021d8323"

for tool in cvlc find jq montage sed sha256sum timeout wc; do
  command -v "$tool" >/dev/null || {
    echo "ERROR: falta herramienta local: $tool" >&2
    exit 1
  }
done

cd "$REPO_ROOT"
test -s "$XML_REL"
test -s "$TASKS_REL"
for episode in 000000 000001 000090 000091; do
  test -s "$VIDEOS_REL/episode_${episode}.mp4"
done

mkdir -p "$RUN_DIR/reference_frames"
test -w "$RUN_DIR"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
printf 'E1.2_MODE=local-read-only,no-robot,no-inference,no-publisher\n'

sha256sum "$XML_REL" > "$RUN_DIR/s2_ready.sha256"
ACTUAL_XML_SHA256="$(awk '{print $1}' "$RUN_DIR/s2_ready.sha256")"
[[ "$ACTUAL_XML_SHA256" == "$EXPECTED_XML_SHA256" ]] || {
  echo "ERROR: hash XML inesperado: $ACTUAL_XML_SHA256" >&2
  exit 1
}

sed -n '1,120p' "$XML_REL" > "$RUN_DIR/s2_ready.xml.txt"
grep -Fq 'name="clamp_s2_joints_trajectory"' "$RUN_DIR/s2_ready.xml.txt"
grep -Fq 'type="waist"' "$RUN_DIR/s2_ready.xml.txt"
grep -Fq 'type="head"' "$RUN_DIR/s2_ready.xml.txt"
grep -Fq 'location="right"' "$RUN_DIR/s2_ready.xml.txt"
grep -Fq 'location="left"' "$RUN_DIR/s2_ready.xml.txt"

jq -r '[.task_index,.task] | @tsv' "$TASKS_REL" > "$RUN_DIR/tasks.tsv"
EXPECTED_TASKS=$'0\tPick up the large box from the lowest level of shelf\n1\tPlace the large box on the lowest level of shelf\n2\tPick up the large box from the middle level of shelf\n3\tPlace the large box on the middle level of shelf'
[[ "$(<"$RUN_DIR/tasks.tsv")" == "$EXPECTED_TASKS" ]] || {
  echo "ERROR: catálogo task ID/texto inesperado" >&2
  exit 1
}

FRAME_SPECS=(
  "000000 start 0.05"
  "000000 middle 0.94"
  "000000 end 1.82"
  "000001 start 0.05"
  "000001 middle 0.65"
  "000001 end 1.25"
  "000090 start 0.05"
  "000090 middle 1.07"
  "000090 end 2.09"
  "000091 start 0.05"
  "000091 middle 1.43"
  "000091 end 2.80"
)
CONTACT_SHEET_INPUTS=()

for spec in "${FRAME_SPECS[@]}"; do
  read -r episode position second <<<"$spec"
  video="$VIDEOS_REL/episode_${episode}.mp4"
  frame="$RUN_DIR/reference_frames/episode_${episode}_${position}.png"
  log="$RUN_DIR/reference_frames/episode_${episode}_${position}.log"
  timeout 15s cvlc --intf dummy --vout dummy --no-audio \
    --no-video-title-show --video-filter=scene --scene-format=png \
    --scene-ratio=1 --scene-replace \
    --scene-path="$RUN_DIR/reference_frames" \
    --scene-prefix="episode_${episode}_${position}" \
    --start-time="$second" --run-time=0.08 "$video" vlc://quit \
    > "$log" 2>&1
  test -s "$frame"
  CONTACT_SHEET_INPUTS+=("$frame")
done

FRAME_COUNT="$(find "$RUN_DIR/reference_frames" -maxdepth 1 -type f -name '*.png' -size +0c | wc -l)"
[[ "$FRAME_COUNT" -eq 12 ]] || {
  echo "ERROR: se esperaban 12 frames; se obtuvieron $FRAME_COUNT" >&2
  exit 1
}
sha256sum "$RUN_DIR"/reference_frames/*.png > "$RUN_DIR/reference_frames.sha256"
montage "${CONTACT_SHEET_INPUTS[@]}" -thumbnail 480x288 -tile 3x4 \
  -geometry +6+6 "$RUN_DIR/reference_frames/contact_sheet.png"
test -s "$RUN_DIR/reference_frames/contact_sheet.png"
sha256sum "$RUN_DIR/reference_frames/contact_sheet.png" \
  > "$RUN_DIR/contact_sheet.sha256"

cat > "$RUN_DIR/confirmed_unresolved.yaml" <<EOF
confirmed:
  xml_sha256: $ACTUAL_XML_SHA256
  xml_prepositions: [waist, head, right_arm, left_arm]
  xml_final_action: clamp_s2_joints_trajectory
  task_ids: [0, 1, 2, 3]
  reference_frame_count: 12
  frame_sampling: vlc_time_seek_near_requested_timestamp
  frame_hashes_are_integrity_per_run_not_canonical: true
  sdk_platform_height_m: 1.0
unresolved:
  installed_canonical_ready_task: null
  clamp_s2_joints_trajectory_definition: null
  task_low_height_m: null
  task_middle_height_m: null
  bumper_to_platform_m: null
  platform_in_base: null
EOF

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E1.2
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
end_time: $(date --iso-8601=seconds)
status: ARTIFACTS_EXTRACTED_PENDING_VISUAL_REVIEW
scenario_id: LOCAL_VENDOR_ARTIFACT_AUDIT
commands_executed:
  - ./scripts/vla/audit_vla_experiment_e1_2.sh
actual_observations:
  - xml_sha256=$ACTUAL_XML_SHA256
  - task_catalog_exact=true
  - reference_frame_count=$FRAME_COUNT
  - frame_sampling=vlc_time_seek_not_bit_exact_between_runs
  - robot_connections=0
  - inference_started=false
  - command_publishers_started=false
files:
  - s2_ready.sha256
  - s2_ready.xml.txt
  - tasks.tsv
  - reference_frames.sha256
  - reference_frames/contact_sheet.png
  - contact_sheet.sha256
  - confirmed_unresolved.yaml
failure_reason: null
recovery_or_stop: NOT_APPLICABLE_LOCAL_READ_ONLY
next_experiment_authorized: false
EOF

sha256sum \
  "$RUN_DIR/s2_ready.sha256" \
  "$RUN_DIR/s2_ready.xml.txt" \
  "$RUN_DIR/tasks.tsv" \
  "$RUN_DIR/reference_frames.sha256" \
  "$RUN_DIR/contact_sheet.sha256" \
  "$RUN_DIR/confirmed_unresolved.yaml" \
  > "$RUN_DIR/audit_files.sha256"

printf 'E1.2_ARTIFACTS_OK=%s\n' "$RUN_DIR"
printf 'E1.2_STATUS=ARTIFACTS_EXTRACTED_PENDING_VISUAL_REVIEW\n'
