#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_heights_e4_2.sh --check
  ./scripts/vla/audit_vla_heights_e4_2.sh --run

E4.2 correlaciona localmente los tasks 0-3, las configuraciones de elevador,
los XML vendor 55/70/85/100/115, el URDF S2 y los frames E1.2. No conecta con
el robot, no inicia inferencia, no crea publicadores y no manda movimiento.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly ANALYZER="$SCRIPT_DIR/analyze_vla_heights_e4_2.py"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly EVIDENCE_ROOT="${VLA_EVIDENCE_ROOT:-/home/lacuna/proyectos/Robots/Humanoide-vla-evidence}"
readonly DATASET_ROOT_REL="cruzrss2_vla_pack-002/data/utars_clamp_and_place_large_box_full_data_bio_lerobot_0319"
readonly PROFILE_ROOT_REL="cruzrss2_vla_pack-002/codes/motion/cruzr_vla_scripts/cruzr_bio_vla"
readonly SDK_URDF_ZIP_REL="Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/URDF/cruzr_s2_description.zip"
readonly SDK_PDF_REL="Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/Cruzr S2 优必选SDK二次开发文档【对外】6.24.pdf"
readonly VIDEO_ROOT_REL="$DATASET_ROOT_REL/videos/chunk-000/observation.images.rgb"

MODE="check"
while (($#)); do
  case "$1" in
    --check|--run) MODE="${1#--}"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'ERROR: argumento desconocido: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

for tool in awk cp cvlc dirname find grep jq montage pdftotext python3 readlink \
  sha256sum sort tee timeout unzip wc xargs; do
  command -v "$tool" >/dev/null || {
    printf 'ERROR: falta herramienta local: %s\n' "$tool" >&2
    exit 1
  }
done
for required in "$ANALYZER" "$EVIDENCE_SCRIPT"; do
  test -s "$required" || { printf 'ERROR: falta %s\n' "$required" >&2; exit 1; }
done

cd "$REPO_ROOT"

declare -A EXPECTED_SHA256=(
  ["$PROFILE_ROOT_REL/cruzr_vla_pick_large_55_ready.xml"]="361d8bb7690cb5f5f29165aa43c3d33031d044518e511ffa165c63ecf37f3c8f"
  ["$PROFILE_ROOT_REL/cruzr_vla_pick_large_70_ready.xml"]="942f4a1625e33a0834163900e44eede74ef916372925c2635894a04af9b538de"
  ["$PROFILE_ROOT_REL/cruzr_vla_pick_large_85_ready.xml"]="ea4e5dddff338e576cfa606bdebb078215851f40da18ad28a8dce8f452790dad"
  ["$PROFILE_ROOT_REL/cruzr_vla_pick_large_100_ready.xml"]="1bd4ddd39d8ca597ab96201dc8d036c213c9419a05629e6e36be09dd1fb21dbe"
  ["$PROFILE_ROOT_REL/cruzr_vla_pick_large_115_ready.xml"]="cbbe0dd1b620958d7e1a2d0df2778e2447c59c95996bffa588f59ba08ab57e79"
  ["$DATASET_ROOT_REL/meta/info.json"]="de9b4150459ef2d1401174f298b8eda31ba56f8fe2e4b216478add19202d2a4f"
  ["$DATASET_ROOT_REL/meta/tasks.jsonl"]="3ece0364756980e406921fddfcdac1c3ab3c1009621bf0244087a83bbc7b1a2d"
  ["$DATASET_ROOT_REL/meta/episodes.jsonl"]="ecb924d516d8a91b2b2483a41bdbb70802d16b52e3b8968fe027db595f9a60e0"
  ["$DATASET_ROOT_REL/meta/episodes_stats.jsonl"]="aed6bebc1a5b50a79e51e014419d24c8d943b8415e6edc616fb005c1651c3c0e"
  ["$SDK_URDF_ZIP_REL"]="7cb7f856223ce99a86d44349be475a2b5925d57ca694ee069a96c808802e297e"
  ["$SDK_PDF_REL"]="4cf441de24c0328a7fc4e991f41cbaa17239e9d9eb7bb6a19e8715c0591a30bd"
)

for source in "${!EXPECTED_SHA256[@]}"; do
  test -s "$source" || { printf 'ERROR: falta artefacto vendor: %s\n' "$source" >&2; exit 1; }
  actual_sha="$(sha256sum "$source" | awk '{print $1}')"
  [[ "$actual_sha" == "${EXPECTED_SHA256[$source]}" ]] || {
    printf 'ERROR: hash inesperado para %s: %s\n' "$source" "$actual_sha" >&2
    exit 1
  }
done

python3 -c 'import ast, pathlib, sys; ast.parse(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))' "$ANALYZER"

latest_e1_2="$(find "$EVIDENCE_ROOT" -mindepth 2 -maxdepth 2 -type f \
  -path '*_E1.2/actual_result.yaml' -printf '%T@ %h\n' \
  | sort -nr | awk 'NR==1 {$1=""; sub(/^ /, ""); print; exit}')"
latest_e4_0="$(find "$EVIDENCE_ROOT" -mindepth 2 -maxdepth 2 -type f \
  -path '*_E4.0/actual_result.yaml' -printf '%T@ %h\n' \
  | sort -nr | awk 'NR==1 {$1=""; sub(/^ /, ""); print; exit}')"
test -n "$latest_e1_2" || { printf 'ERROR: no se encontró evidencia E1.2\n' >&2; exit 1; }
test -n "$latest_e4_0" || { printf 'ERROR: no se encontró evidencia E4.0\n' >&2; exit 1; }

grep -Eq '^status: (PASS|ARTIFACTS_EXTRACTED_PENDING_VISUAL_REVIEW)$' \
  "$latest_e1_2/actual_result.yaml" || {
  printf 'ERROR: E1.2 no tiene el estado esperado: %s\n' "$latest_e1_2" >&2
  exit 1
}
grep -Fq 'status: PARTIAL_RESOLUTION_BLOCKED_NOT_READY_FOR_E4_1_OR_PHYSICAL_USE' \
  "$latest_e4_0/actual_result.yaml" || {
  printf 'ERROR: E4.0 no tiene el estado final esperado: %s\n' "$latest_e4_0" >&2
  exit 1
}
(
  cd "$latest_e1_2"
  sha256sum -c audit_files.sha256 >/dev/null
  sha256sum -c reference_frames.sha256 >/dev/null
  sha256sum -c contact_sheet.sha256 >/dev/null
)
(
  cd "$latest_e4_0"
  sha256sum -c evidence.sha256 >/dev/null
)

for episode in 000090 000091 000120 000121 000290 000291 000360 000361 000430 000431; do
  test -s "$VIDEO_ROOT_REL/episode_${episode}.mp4" || {
    printf 'ERROR: falta vídeo representativo del episodio %s\n' "$episode" >&2
    exit 1
  }
done

printf 'E4.2_CHECK_OK=local-only,dataset:500,profiles:55/70/85/100/115,urdf:S2\n'
printf 'E4.2_SOURCE_E1.2=%s\n' "$latest_e1_2"
printf 'E4.2_SOURCE_E4.0=%s\n' "$latest_e4_0"
printf 'ROBOT_CONNECTIONS=0; INFERENCE_STARTED=0; PUBLISHERS_CREATED=0; MOVEMENT_COMMANDS=0\n'
[[ "$MODE" == "run" ]] || exit 0

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E4.2)"
mkdir -- "$RUN_DIR/artifacts" "$RUN_DIR/representative_frames"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  if ((exit_code != 0)) && [[ ! -e "$RUN_DIR/actual_result.yaml" ]]; then
    cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E4.2
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
status: FAIL_BEFORE_COMPLETING_LOCAL_HEIGHT_AUDIT
robot_connections: 0
inference_started: false
physical_publisher_created: false
physical_movement_commanded: false
recovery_or_stop: NOT_APPLICABLE_LOCAL_ONLY
EOF
  fi
  exit "$exit_code"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

for height in 55 70 85 100 115; do
  cp -- "$PROFILE_ROOT_REL/cruzr_vla_pick_large_${height}_ready.xml" \
    "$RUN_DIR/artifacts/vendor_non_s2_pick_large_${height}_ready.xml"
done
cp -- "$ANALYZER" "$RUN_DIR/artifacts/analyze_vla_heights_e4_2.py"
cp -- "$DATASET_ROOT_REL/meta/info.json" "$RUN_DIR/artifacts/vendor_dataset_info.json"
cp -- "$DATASET_ROOT_REL/meta/tasks.jsonl" "$RUN_DIR/artifacts/vendor_dataset_tasks.jsonl"
cp -- "$DATASET_ROOT_REL/meta/episodes.jsonl" "$RUN_DIR/artifacts/vendor_dataset_episodes.jsonl"
cp -- "$DATASET_ROOT_REL/meta/episodes_stats.jsonl" "$RUN_DIR/artifacts/vendor_dataset_episode_stats.jsonl"
unzip -p "$SDK_URDF_ZIP_REL" '*/urdf/cruzr_s2_v1/cruzr_s2_v1.urdf' \
  > "$RUN_DIR/artifacts/vendor_cruzr_s2_v1.urdf"
pdftotext -layout "$SDK_PDF_REL" - > "$RUN_DIR/artifacts/vendor_sdk_manual.txt"
grep -n -A5 -B3 '60cm\*40cm\*22cm' "$RUN_DIR/artifacts/vendor_sdk_manual.txt" \
  > "$RUN_DIR/artifacts/vendor_sdk_section_7_3_excerpt.txt"

cp -- "$latest_e1_2/reference_frames/contact_sheet.png" \
  "$RUN_DIR/artifacts/e1_2_reference_contact_sheet.png"
cp -- "$latest_e1_2/reference_frames.sha256" \
  "$RUN_DIR/artifacts/e1_2_reference_frames.sha256"
cp -- "$latest_e1_2/actual_result.yaml" "$RUN_DIR/artifacts/e1_2_actual_result.yaml"
cp -- "$latest_e4_0/summary.json" "$RUN_DIR/artifacts/e4_0_summary.json"
cp -- "$latest_e4_0/actual_result.yaml" "$RUN_DIR/artifacts/e4_0_actual_result.yaml"
printf '%s\n' "$latest_e1_2" > "$RUN_DIR/e1_2_source_path.txt"
printf '%s\n' "$latest_e4_0" > "$RUN_DIR/e4_0_source_path.txt"

for source in "${!EXPECTED_SHA256[@]}"; do
  printf '%s  %s\n' "${EXPECTED_SHA256[$source]}" "$source"
done | sort > "$RUN_DIR/vendor_sources.sha256"

python3 "$ANALYZER" --run-dir "$RUN_DIR" | tee "$RUN_DIR/analyzer.log"
jq -e '
  .experiment_id == "E4.2"
  and .source_contract.dataset_episodes == 500
  and .source_contract.sdk_section_7_3_platform_height_m == 1.0
  and .source_contract.numeric_ready_profiles_are_canonical_s2 == false
  and .H_TASK_0_1.scalar_height_m == null
  and .H_TASK_0_1.vendor_named_profile_candidates_m == [0.55,0.7,0.85]
  and .H_TASK_2_3.scalar_height_m == null
  and .H_TASK_2_3.vendor_named_profile_candidates_m == [1,1.15]
  and .one_meter_subset.task_group == [2,3]
  and .cross_task_same_lifter_witnesses[0].lifter_distance_l2_rad < 0.001
  and .cross_task_same_lifter_witnesses[1].lifter_distance_l2_rad < 0.001
  and .e4_2_pass == false
  and .physical_test_authorized == false
  and .status == "PARTIAL_HEIGHT_FAMILIES_RESOLVED_SINGLE_HEIGHT_MAPPING_REJECTED"
' "$RUN_DIR/summary.json" >/dev/null

FRAME_INPUTS=()
while IFS=$'\t' read -r profile task episode; do
  printf -v episode_padded '%06d' "$episode"
  prefix="profile_${profile}_task_${task}_episode_${episode_padded}_start"
  video="$VIDEO_ROOT_REL/episode_${episode_padded}.mp4"
  log="$RUN_DIR/representative_frames/${prefix}.log"
  timeout 15s cvlc --intf dummy --vout dummy --no-audio --no-video-title-show \
    --video-filter=scene --scene-format=png --scene-ratio=1 --scene-replace \
    --scene-path="$RUN_DIR/representative_frames" --scene-prefix="$prefix" \
    --start-time=0.05 --run-time=0.08 "$video" vlc://quit > "$log" 2>&1
  frame="$RUN_DIR/representative_frames/${prefix}.png"
  test -s "$frame" || { printf 'ERROR: no se extrajo %s\n' "$frame" >&2; exit 1; }
  FRAME_INPUTS+=("$frame")
done < <(jq -r '.representative_episodes[] | [.vendor_profile_cm,.task,.episode] | @tsv' \
  "$RUN_DIR/summary.json")

[[ "${#FRAME_INPUTS[@]}" -eq 10 ]] || {
  printf 'ERROR: se esperaban 10 frames representativos; se obtuvieron %s\n' \
    "${#FRAME_INPUTS[@]}" >&2
  exit 1
}
montage "${FRAME_INPUTS[@]}" -thumbnail 480x288 -tile 2x5 -geometry +6+24 \
  -label '%f' "$RUN_DIR/representative_frames/contact_sheet.png"
test -s "$RUN_DIR/representative_frames/contact_sheet.png"
(
  cd "$RUN_DIR"
  sha256sum representative_frames/*.png
) > "$RUN_DIR/representative_frames.sha256"

cat > "$RUN_DIR/height_contract.yaml" <<'EOF'
H_TASK_0_1:
  scalar_height_m: null
  resolution: MULTI_HEIGHT_FAMILY_NOT_SCALAR
  vendor_non_s2_profile_candidates_m: [0.55, 0.70, 0.85]
  support_pose_in_base: null
H_TASK_2_3:
  scalar_height_m: null
  resolution: MULTI_HEIGHT_FAMILY_NOT_SCALAR
  vendor_non_s2_profile_candidates_m: [1.00, 1.15]
  support_pose_in_base: null
one_meter_subset:
  task_ids: [2, 3]
  reference_episodes: [90, 91]
  status: CORRELATED_OFFLINE_NOT_METRICALLY_CALIBRATED
physical_test_authorized: false
EOF

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E4.2
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: PARTIAL_HEIGHT_FAMILIES_RESOLVED_SINGLE_HEIGHT_MAPPING_REJECTED
mode: local_read_only_no_robot_no_inference_no_publisher
dataset_episodes: 500
H_TASK_0_1_scalar_height_m: null
H_TASK_0_1_vendor_non_s2_profile_candidates_m: [0.55, 0.70, 0.85]
H_TASK_2_3_scalar_height_m: null
H_TASK_2_3_vendor_non_s2_profile_candidates_m: [1.00, 1.15]
one_meter_subset_task_ids: [2, 3]
one_meter_subset_reference_episodes: [90, 91]
representative_frame_count: ${#FRAME_INPUTS[@]}
cross_task_same_lifter_proven: true
support_pose_in_base_resolved: false
robot_connections: 0
inference_started: false
physical_publisher_created: false
physical_movement_commanded: false
physical_test_authorized: false
recovery_or_stop: NOT_APPLICABLE_LOCAL_ONLY
next_experiment_authorized: E4.2_VENDOR_CONFIRMATION_OR_METRIC_CALIBRATION_ONLY
EOF

(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 \
    | sort -z \
    | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(
  cd "$RUN_DIR"
  sha256sum -c evidence.sha256 >/dev/null
)

printf 'E4.2_STATUS=PARTIAL_HEIGHT_FAMILIES_RESOLVED_SINGLE_HEIGHT_MAPPING_REJECTED\n'
printf 'H_TASK_0_1=scalar:null,candidates_non_s2:0.55/0.70/0.85m\n'
printf 'H_TASK_2_3=scalar:null,candidates_non_s2:1.00/1.15m\n'
printf 'ONE_METER_SUBSET=tasks:2/3,episodes:90/91,correlated-not-calibrated\n'
printf 'E4.2_EVIDENCE_OK=%s\n' "$RUN_DIR"
