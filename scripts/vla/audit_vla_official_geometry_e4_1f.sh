#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Uso:
  ./scripts/vla/audit_vla_official_geometry_e4_1f.sh --check
  ./scripts/vla/audit_vla_official_geometry_e4_1f.sh --run

Audita exclusivamente especificaciones y modelos suministrados/oficiales para
el efector clamp. No exige mediciones manuales, no conecta con el robot, no
inicia inferencia, no publica y no mueve.
EOF
}

readonly SCRIPT_PATH="$(readlink -f -- "$0")"
readonly SCRIPT_DIR="$(dirname -- "$SCRIPT_PATH")"
readonly REPO_ROOT="$(readlink -f -- "$SCRIPT_DIR/../..")"
readonly CONTRACT="$SCRIPT_DIR/runtime/cruzr_s2_official_geometry_contract_e4_1f.yaml"
readonly EVIDENCE_SCRIPT="$SCRIPT_DIR/new_vla_evidence_run.sh"
readonly SDK_PDF_REL='Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/Cruzr S2 优必选SDK二次开发文档【对外】6.24.pdf'
readonly PRODUCT_PDF_REL='docs/vendor/2-Cruzr_S2_Product_Manual.pdf'
readonly USD_ZIP_REL='Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/USD/Collected_cruzr_s2_v1.zip'
readonly USD_MEMBER='Collected_cruzr_s2_v1/cruzr_s2_v1.usd'
readonly URDF_ZIP_REL='Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/URDF/cruzr_s2_description.zip'
readonly URDF_MEMBER='cruzr_s2_description/urdf/cruzr_s2_v1/cruzr_s2_v1.urdf'
readonly READY_XML_REL='cruzrss2_vla_pack-002/codes-S2/motion/s2_vla_scripts/s2_bio_vla/s2_vla_pick_large_teleop_ready.xml'
readonly INFO_JSON_REL='cruzrss2_vla_pack-002/data/utars_clamp_and_place_large_box_full_data_bio_lerobot_0319/meta/info.json'
readonly SDK_PDF_SHA256='4cf441de24c0328a7fc4e991f41cbaa17239e9d9eb7bb6a19e8715c0591a30bd'
readonly PRODUCT_PDF_SHA256='63e7bc4318f6ec27efd9f3ff18ad31b1dcdb36fb978fd4d3b2265606af304d62'
readonly USD_ZIP_SHA256='7380c52227a9ca99c69121effbbbaff18b9807e72e8759ee3376bd47ac3f4c30'
readonly URDF_ZIP_SHA256='7cb7f856223ce99a86d44349be475a2b5925d57ca694ee069a96c808802e297e'
readonly READY_XML_SHA256='f4025124491eba995ec824db3e3be91875f781a4b4e98928654bde9a021d8323'
readonly INFO_JSON_SHA256='de9b4150459ef2d1401174f298b8eda31ba56f8fe2e4b216478add19202d2a4f'

MODE=check
while (($#)); do
  case "$1" in
    --check|--run) MODE="${1#--}"; shift ;;
    --help|-h) usage; exit 0 ;;
    *) printf 'ERROR: argumento desconocido: %s\n' "$1" >&2; usage >&2; exit 2 ;;
  esac
done

for tool in awk cp dirname find grep mkdir pdftotext readlink rg sed sha256sum sort strings tee unzip xargs; do
  command -v "$tool" >/dev/null || { printf 'ERROR: falta herramienta local: %s\n' "$tool" >&2; exit 1; }
done

cd "$REPO_ROOT"
check_hash() {
  local expected="$1"
  local path="$2"
  test -s "$path" || { printf 'ERROR: falta fuente oficial: %s\n' "$path" >&2; exit 1; }
  [[ "$(sha256sum "$path" | awk '{print $1}')" == "$expected" ]] || {
    printf 'ERROR: cambió fuente oficial: %s\n' "$path" >&2
    exit 1
  }
}

check_hash "$SDK_PDF_SHA256" "$SDK_PDF_REL"
check_hash "$PRODUCT_PDF_SHA256" "$PRODUCT_PDF_REL"
check_hash "$USD_ZIP_SHA256" "$USD_ZIP_REL"
check_hash "$URDF_ZIP_SHA256" "$URDF_ZIP_REL"
check_hash "$READY_XML_SHA256" "$READY_XML_REL"
check_hash "$INFO_JSON_SHA256" "$INFO_JSON_REL"
test -s "$CONTRACT"

sdk_text="$(pdftotext -layout "$SDK_PDF_REL" -)"
product_text="$(pdftotext -layout "$PRODUCT_PDF_REL" -)"
grep -Fq 'PGC-140-50' <<<"$sdk_text"
grep -Fq 'HW_TYPE=cruzr_s2_v1_gripper' <<<"$sdk_text"
grep -Fq '60cm*40cm*22cm' <<<"$sdk_text"
grep -Fq '1m ⾼的平台处' <<<"$sdk_text"
grep -Fq 'clamp hands and two-finger grippers' <<<"$product_text"
grep -Fq 'official_outer_envelope_m: null' "$CONTRACT"
grep -Fq 'manual_measurements_required: false' "$CONTRACT"

printf 'E4.1F_CHECK_OK=official-supplier-sources-only,no-manual-measurements\n'
printf 'OFFICIAL_FIXTURE=box:0.60x0.40x0.22m,platform-height:1.0m\n'
printf 'OFFICIAL_PGC=body:0.1385x0.075x0.075m,stroke:0.05m,excluded:not-installed\n'
printf 'OFFICIAL_PASSIVE_CLAMP_ENVELOPE=not-published\n'
printf 'ROBOT_CONNECTIONS=0; INFERENCE_STARTED=0; PUBLISHERS_CREATED=0; MOVEMENT_COMMANDS=0\n'
[[ "$MODE" == run ]] || exit 0

RUN_DIR="$($EVIDENCE_SCRIPT --experiment E4.1F)"
mkdir -- "$RUN_DIR/artifacts" "$RUN_DIR/results"
printf 'VLA_RUN_DIR=%s\n' "$RUN_DIR"
START_TIME="$(date --iso-8601=seconds)"

cleanup() {
  local exit_code=$?
  trap - EXIT INT TERM
  if ((exit_code != 0)) && [[ ! -e "$RUN_DIR/actual_result.yaml" ]]; then
    cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E4.1F
run_id: $(basename -- "$RUN_DIR")
status: FAIL_BEFORE_COMPLETING_OFFICIAL_SOURCE_AUDIT
robot_connections: 0
inference_started: false
physical_publisher_created: false
physical_movement_commanded: false
physical_test_authorized: false
EOF
  fi
  exit "$exit_code"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

cp -- "$CONTRACT" "$RUN_DIR/artifacts/cruzr_s2_official_geometry_contract_e4_1f.yaml"
pdftotext -layout "$SDK_PDF_REL" "$RUN_DIR/artifacts/ubtech_sdk.txt"
pdftotext -layout "$PRODUCT_PDF_REL" "$RUN_DIR/artifacts/ubtech_product_manual.txt"
unzip -p "$URDF_ZIP_REL" "$URDF_MEMBER" > "$RUN_DIR/artifacts/vendor_cruzr_s2_v1.urdf"
unzip -p "$USD_ZIP_REL" "$USD_MEMBER" | strings -a -n 8 | \
  rg -i '(L_gripper|R_gripper|EndEffector|PGC-140-50|clamp)' | sort -u \
  > "$RUN_DIR/artifacts/vendor_usd_effector_tokens.txt"
sed -n '3037,3042p;3210,3230p;3365,3369p;5895,5905p' \
  "$RUN_DIR/artifacts/ubtech_sdk.txt" > "$RUN_DIR/artifacts/sdk_relevant_excerpt.txt"
sed -n '190,214p' "$RUN_DIR/artifacts/ubtech_product_manual.txt" \
  > "$RUN_DIR/artifacts/product_manual_relevant_excerpt.txt"

grep -Fq 'PGC-140-50' "$RUN_DIR/artifacts/vendor_usd_effector_tokens.txt"
grep -Fq 'pgc_base_link' "$RUN_DIR/artifacts/vendor_cruzr_s2_v1.urdf"
if grep -Eiq '(^|[^[:alpha:]])clamp([^[:alpha:]]|$)' "$RUN_DIR/artifacts/vendor_usd_effector_tokens.txt"; then
  echo 'ERROR: apareció geometría clamp explícita en el USD; revisar contrato' >&2
  exit 1
fi
if grep -Eiq '(clamp|抱箍|夹具)' "$RUN_DIR/artifacts/vendor_cruzr_s2_v1.urdf"; then
  echo 'ERROR: apareció geometría clamp explícita en el URDF; revisar contrato' >&2
  exit 1
fi

cat > "$RUN_DIR/results/official_geometry_inventory.yaml" <<'EOF'
experiment_id: E4.1F
source_policy: supplier_artifacts_only
manual_measurements_required: false
manual_measurements_used: false
official_fixture:
  box_lwh_m: [0.60, 0.40, 0.22]
  platform_surface_height_m: 1.0
official_robot:
  bimanual_max_payload_kg: 15.0
  replaceable_effector_family_clamp_listed: true
official_pgc_140_50:
  body_size_lwh_m: [0.1385, 0.075, 0.075]
  stroke_m: 0.05
  applicable_to_installed_clamp: false
official_passive_clamp:
  outer_envelope_m: null
  cad_or_collision_mesh: null
vendor_models:
  usd_contains_pgc_140_50: true
  urdf_contains_pgc_finger: true
  explicit_passive_clamp_geometry_found: false
physical_test_authorized: false
next_offline_experiment: E5.0
EOF

cat > "$RUN_DIR/source_hashes.sha256" <<EOF
$SDK_PDF_SHA256  $SDK_PDF_REL
$PRODUCT_PDF_SHA256  $PRODUCT_PDF_REL
$USD_ZIP_SHA256  $USD_ZIP_REL
$URDF_ZIP_SHA256  $URDF_ZIP_REL
$READY_XML_SHA256  $READY_XML_REL
$INFO_JSON_SHA256  $INFO_JSON_REL
EOF

cat > "$RUN_DIR/actual_result.yaml" <<EOF
experiment_id: E4.1F
run_id: $(basename -- "$RUN_DIR")
operator: ${USER:-unknown}
start_time: $START_TIME
end_time: $(date --iso-8601=seconds)
status: OFFICIAL_SOURCES_AUDITED_PASSIVE_CLAMP_DIMENSIONS_NOT_PUBLISHED_PGC_EXCLUDED
mode: local_read_only_official_supplier_artifacts
manual_measurements_required: false
manual_measurements_used: false
official_fixture_dimensions_available: true
official_pgc_dimensions_available: true
pgc_applicable_to_installed_clamp: false
official_passive_clamp_outer_envelope_available: false
official_passive_clamp_cad_available: false
robot_connections: 0
inference_started: false
physical_publisher_created: false
physical_movement_commanded: false
physical_test_authorized: false
next_offline_experiment_authorized: E5.0
EOF

(
  cd "$RUN_DIR"
  find . -type f ! -name evidence.sha256 -print0 | sort -z | xargs -0 sha256sum
) > "$RUN_DIR/evidence.sha256"
(
  cd "$RUN_DIR"
  sha256sum -c evidence.sha256 >/dev/null
)

printf 'E4.1F_STATUS=OFFICIAL_SOURCES_AUDITED_PASSIVE_CLAMP_DIMENSIONS_NOT_PUBLISHED_PGC_EXCLUDED\n'
printf 'MANUAL_MEASUREMENTS_REQUIRED=0\n'
printf 'PHYSICAL_FIXTURE_AUTHORIZED=0\n'
printf 'NEXT_OFFLINE_EXPERIMENT=E5.0\n'
printf 'E4.1F_EVIDENCE_OK=%s\n' "$RUN_DIR"
