# Sourced configuration only: no commands, network calls or movement.
pico_effector="${PICO_EFFECTOR:-clamp}"
backend_required_arm="clamp" # Existing 4.7.0 service baseline; client overrides explicitly.
case "$pico_effector" in
  clamp)
    required_arm="clamp"
    expected_motion_hand="clamp"
    expected_hw_types="cruzr_s2_v1"
    expected_teleop_task="teleoperation/cruzr_clamp_pico_teleoperation"
    arms_only_config_path="/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config/meta_teleoperation/cruzr_clamp_pico_tele.yaml"
    arms_only_config_sha256="4e8d79a40e8b1f1fa5915de27ef60676fce4c9b5cec41cacfc0a1d9a7d117a44"
    vendor_full_body_config_sha256="5f08b30cd5032a9fccd6b3becd933ff3884d9795d02f98cc2433fc0da33fc62a"
    effector_description="abrazaderas"
    ;;
  v4)
    required_arm="hand"
    expected_motion_hand="v4"
    # Both generations require additional live task and 7-joint hand gates.
    expected_hw_types="cruzr_s2_v1 cruzr_s2_v1_sps"
    expected_teleop_task="teleoperation/cruzr_v4_pico_teleoperation"
    arms_only_config_path="/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config/meta_teleoperation/cruzr_v4_pico_tele.yaml"
    arms_only_config_sha256="01a5ca8acba16bbe136a3bdbcb4a593667d672f8ee9613b98631699fc429b582"
    vendor_full_body_config_sha256="48d2ee0f61ab3dddaceec31e7468d0a764ef0900b2e09b687281b5e02465e74e"
    effector_description="manos v4"
    ;;
  *) printf 'ERROR: PICO_EFFECTOR debe ser clamp o v4.\n' >&2; exit 2 ;;
esac
