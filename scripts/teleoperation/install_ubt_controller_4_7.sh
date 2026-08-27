#!/usr/bin/env bash
set -Eeuo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd -- "$script_dir/../.." && pwd)"
package_path="/home/lacuna/Descargas/ubt_controller_4.7.0_ubuntu22.04_amd64.deb"
backup_path="/home/lacuna/Descargas/ubt-controller-5.3.0-patched-20260826.tar.gz"
expected_package_sha256="4f2b728b689175867ff345bec3e30f319fe7d8567d9e08985aa48a2b67bad61c"
expected_backup_sha256="c085fc4bf05d14e08f3801aa1249dad1650bd2855991fb88bff44bfe048c969c"
unit="ubt-controller.service"
dropin_dir="/etc/systemd/system/${unit}.d"

usage() {
  cat <<'EOF'
Uso:
  sudo ./scripts/teleoperation/install_ubt_controller_4_7.sh --run

Migra de ubt-controller 5.3.0 a la versión oficial 4.7.0 suministrada por
UBTECH. Exige el respaldo validado, mantiene el servicio enmascarado durante
dpkg, instala los drop-ins de locale/abrazaderas/cierre y termina DETENIDO.
No inicia teleoperación ni mueve el robot.
EOF
}

die() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

[[ "${1:-}" == "--run" ]] || { usage; exit 2; }
[[ "$EUID" -eq 0 ]] || die "Ejecute este instalador mediante sudo."
[[ -f "$package_path" ]] || die "No existe $package_path"
[[ -f "$backup_path" ]] || die "No existe el respaldo $backup_path"

package_sha256="$(sha256sum "$package_path" | awk '{print $1}')"
backup_sha256="$(sha256sum "$backup_path" | awk '{print $1}')"
[[ "$package_sha256" == "$expected_package_sha256" ]] ||
  die "SHA-256 inesperado para el paquete 4.7.0: $package_sha256"
[[ "$backup_sha256" == "$expected_backup_sha256" ]] ||
  die "SHA-256 inesperado para el respaldo 5.3.0: $backup_sha256"

installed_version="$(dpkg-query -W -f='${Version}' ubt-controller 2>/dev/null || true)"
[[ "$installed_version" == "5.3.0" ]] ||
  die "Se esperaba ubt-controller 5.3.0 instalado; estado actual: ${installed_version:-ausente}"

if pgrep -f '/opt/ubt-remote-control/ubt-remote-control' >/dev/null; then
  die "La UI ubt-remote-control sigue abierta. Ciérrela con --stop."
fi

printf 'MIGRATION_SOURCE=ubt-controller:%s\n' "$installed_version"
printf 'PACKAGE_4_7_SHA256=%s\n' "$package_sha256"
printf 'BACKUP_5_3_SHA256=%s\n' "$backup_sha256"

systemctl stop "$unit"
systemctl mask --runtime "$unit"

if pgrep -f '/opt/ubt/ubt_controller/(ubt_controller|run.sh)' >/dev/null ||
   ss -Hlnt | grep -qE ':(8082|63901)\b'; then
  die "El backend o sus listeners siguen activos después de detener el servicio."
fi

dpkg -P ubt-controller
dpkg -i "$package_path"

# El postinst del proveedor intenta arrancar el servicio. El mask runtime lo
# mantiene detenido hasta que todos los parámetros seguros estén instalados.
systemctl stop "$unit" >/dev/null 2>&1 || true
install -d -m 0755 "$dropin_dir"
install -m 0644 \
  "$repo_root/config/systemd/system/ubt-controller.service.d/10-numeric-locale.conf" \
  "$dropin_dir/10-numeric-locale.conf"
install -m 0644 \
  "$repo_root/config/systemd/system/ubt-controller.service.d/20-cruzr-clamp.conf" \
  "$dropin_dir/20-cruzr-clamp.conf"
install -m 0644 \
  "$repo_root/config/systemd/system/ubt-controller.service.d/30-service-lifecycle.conf" \
  "$dropin_dir/30-service-lifecycle.conf"

systemctl unmask --runtime "$unit"
systemctl daemon-reload
systemctl enable "$unit"

installed_version="$(dpkg-query -W -f='${Version}' ubt-controller)"
[[ "$installed_version" == "4.7.0" ]] ||
  die "dpkg no confirmó ubt-controller 4.7.0: $installed_version"
if systemctl is-active --quiet "$unit"; then
  systemctl stop "$unit"
  die "El servicio quedó activo inesperadamente después de la migración."
fi
if ss -Hlnt | grep -qE ':(8082|63901)\b'; then
  die "Quedó algún listener 8082/63901 después de la migración."
fi

printf 'MIGRATION_TARGET=ubt-controller:%s\n' "$installed_version"
printf 'UBT_CONTROLLER_SERVICE=inactive\n'
printf 'TELEOPERATION_START_SENT=0\n'
printf 'MIGRATION_OK=1\n'
