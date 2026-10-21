# APP2 — recuperar el acceso al servidor mediante el BMC

**ID:** APP2-BMC-RECOVERY-20261020. **Fecha/zona:** 20-10-2026, Europe/Madrid.
**Destino exclusivo:** BMC `192.168.1.34`, servidor `aisrv`; **no es el robot**.
Esta receta registra la API web observada en ASMB9-iKVM `1.32`, marzo de 2023.
No es una interfaz Redfish genérica ni una garantía para otras versiones.

**Actual:** después de recuperar Ubuntu/SSH y comprobar guardas/SSD, la KVM pasó
120s/Enter vacío y el CD virtual tuvo SHA coincidente. Se volvió a UEFI, se
guardó **únicamente Launch CSM Disabled → Enabled** mediante F10/OK y se observó
POST. Ubuntu volvió con boot `1c617aab-a3c3-4665-83b7-d6d90477a187`;
el firmware añadió BBS0002/0003 al orden, sin edición explícita del orden.
**BootNext0003/reinicio ejecutado por el operador10:03:15 UTC**; KVM10:05:01 UTC
muestra ISOLINUX6.03 del CD. Después se verificó Drive1/serie187F, se enviaron
dos Y y la utilidad mostró **Firmware Update Completed**. Se respondió N al
siguiente dispositivo y Enter para salir10:07:25 UTC. **Linux10:08:59 UTC confirma
187F8B2QJXD7/live y095A4B2QJXD7/live**, check PASS; BootNext observado ausente.
Después del reboot firmware-setup, cerrar Stop Media/Stop KVM propios y abrir un
visor nuevo desde MAIN recuperó UEFI viva, sin reset BMC adicional. CSM Enabled
se restauró a Disabled; Primary Display se leyó Discrete sin editarlo. F10 sólo
enumeró CSM Enabled → Disabled, confirmado Enter10:17:26 UTC. **Postboot PASS
10:20:03 UTC**, boot e719f517-0709-417a-b521-7bc8c0212bf6, UEFI y guardas correctas;
187F8B/095A4B. EFI posterior: sólo Ubuntu0001, BootNext ausente, BBS retiradas
automáticamente y SecureBoot disabled. No repetir la restauración.
**Estado final verificado11:35–11:36 UTC:** recuperación offline concluida,
configuración original restaurada y datos montados ext4/rw; checker20 PASS y
Docker/containerd activos. Los veinte IDs originales están running, restart0 y
sin diferencias de definición. CVAT2.79.0/API/UI200 conserva cuatro tareas,
cuatro jobs, nueve formas y shape10/frame1 en job5; dos PNG tienen los hashes
originales. El túnel propio localhost18080 está restaurado.
**Reanudación:** continuar anotaciones humanas y vigilar fiabilidad con los
backups/undo conservados. No queda sudo pendiente ni recuperación/arranque que
repetir. Los comandos de esta receta son históricos de esta intervención.
Ver [resultado y punto de reanudación](FIRMWARE_SAMSUNG_990_PRO.md#15-estado-final-dockercvat-recuperados-retomar-las-anotaciones).
El resultado puntual no demuestra estabilidad prolongada. Chrome aislado propio
cerrado y perfil retenido; logout BMC **no comprobado** por timeout de Sign out.

## 1. Estado comprobado y acciones realizadas

- **EJECUTADO:** consultas Redfish con Basic y creación de sesión Redfish
  respondieron HTTP401. Esto no demuestra que las credenciales sean incorrectas
  para la interfaz web; no se repitieron intentos masivos ni se cambiaron cuentas.
- **EJECUTADO:** autenticación de la web con `POST /api/session`, formulario
  `username`/`password`. Respuesta `ok=0` significa éxito en esta implementación;
  se recibió `CSRFToken` y cookie de sesión `QSESSIONID`, conservados sólo en
  evidencia privada. Las consultas posteriores usan cookie y `X-CSRFTOKEN`.
- **EJECUTADO:** lecturas de `/api/chassis-status`, `/api/settings/network`,
  `/api/firmware-info`, `/api/settings/services` y
  `/api/settings/media/remotesession`, HTTP200. El respaldo de configuración
  permanece privado. No se modificaron red, servicios ni usuarios.
- **EJECUTADO:** a las **09:06:23 UTC / 11:06:23 Madrid**, tras autorización
  expresa de recuperación, `POST /api/actions/power` con
  `{"power_command":5}` solicitó apagado ACPI; HTTP200 devolvió el mismo comando.
  La lectura inicial era `power_status=1`; a las **09:06:38 UTC** la consulta
  informó `power_status=0`. Resultado **POWERED_OFF**. No se envió reset forzado.
  La aceptación HTTP por sí sola no se usó como prueba de apagado.
- **EJECUTADO:** a las **09:08:27.993 UTC / 11:08:27.993 Madrid**, lectura nueva
  `power_status=0`, `POST /api/actions/power` con `{"power_command":1}` y
  HTTP200, seguido de lectura `power_status=1`. Se encendió después del apagado
  confirmado, sin reset forzado, force-off, reset BMC ni cambio BIOS.
- **VERIFICADO:** SSH de Ubuntu recuperado a las **09:12:34 UTC**; nuevo Boot ID
  `97a5c584-ff68-4e18-b6b1-c479951083be`, check `CHECK_OK_NO_MOUNT`.
- **VERIFICADO a las09:13:07 UTC:** `post-acpi-ubuntu-protection-check.json`
  confirma ambos SSD `live`/`4B2QJXD7`, cinco unidades `masked`/`inactive`, datos
  sin montar y check correcto. La solicitud de entrada a firmware aparece ya
  `b false`; no quedó activa para el próximo arranque.
- **EJECUTADO a las09:23:18.525 UTC:** `PUT /api/ResetKVM`, sin cuerpo,
  HTTP200/cuerpo vacío, siguiendo el manejador **Reset KVM Service** de la web
  actual. Se cerró antes el visor fallido propio. El postcheck SSH conserva el
  mismo Boot ID; no fue una orden de alimentación, reset del host o firmware.
  Fuente: `bmc-kvm-service-reset-result.json`.
- **VERIFICADO posteriormente:** visor limpio con perfil privado/SPKI recibe
  vídeo: Frame4, WebSocket OPEN, running=true, canvas1280×1024;
  `bmc-clean-kvm-initial.png`. Esto comprueba recepción actual, sin dar aún por
  probados teclado, arranque de ISO o firmware. La prueba Enter y preparación
  del medio siguen en curso; no se envió otro reinicio en esta etapa.
- **VERIFICADO posteriormente:** `bmc-kvm-120s-stability.json`,12/12 muestras
  OPEN durante120s, edades1–160ms, sin reconexión; Enter vacío cambia la imagen
  de login (`bmc-kvm-empty-enter-after.png`), sin usuario ni comando. La ventana
  termina a las09:44:39 UTC. Esto no demuestra estabilidad en el siguiente POST.
- **VERIFICADO:** segunda conexión de AMI Virtual CDROM0,52.428.800bytes;
  `sudo sha256sum /dev/sr0` ejecutado por el operador vuelve a coincidir con
  `f05508f3228960fc1501fe5a27d3a826377332afc8c021aac44487c8fd1c93d5`.
  Fuente `virtual-cdrom-second-attachment-sha256-operator-result.json`,09:42:17 UTC.
- **EJECUTADO posteriormente:** regreso a UEFI, preestado capturado y revisión
  F10 a las09:52:47 UTC con un solo cambio: `Launch CSM Disabled → Enabled`.
  Se confirmó OK/Enter y se observó POST. Boot Device Control ya admitía UEFI y
  Legacy OPROM; Network/Storage/PCIe Legacy only eran valores latentes no
  editados, y Primary Display quedó oculto sin edición explícita. Fuentes
  `uefi-csm-save-reset-review.json`, `bmc-csm-save-reset-review.png` y
  `documentation-csm-save-confirmed-reset-review.json`.
- **VERIFICADO después:** Ubuntu regresó; lectura EFI10:00:20 UTC confirma
  BootCurrent0001 Ubuntu EFI y BootOrder0001,0002,0003, con BBS de discos y CD
  añadidos por el firmware. Boot0003 identifica AMI Virtual CDROM0, tipoCDROM;
  BootNext estaba ausente y se conservaron variables crudas/preestado en
  `post-csm-ubuntu-efi-bootnext-cd-baseline.json`.
- **EJECUTADO por el operador10:03:15 UTC:** check correcto, BootNext0003 y
  reinicio. `bootnext-first-check.png` de10:05:01 UTC muestra ISOLINUX6.03.
  Arranque de CD comprobado; sin pantalla de utilidad/selección ni `Y` observados.
- **EJECUTADO después:** serie187F comprobada antes de confirmar; dos Y,
  finalización correcta visible en `samsung-drive1-flash-progress.png`, N a
  continuar con otro dispositivo y salida visible en
  `samsung-next-device-declined.png`. Enter para salir10:07:25 UTC. Fuente de
  identidad `samsung-updater-device-confirmation.png`; hashes/reporte en
  `vendor-187F-completed-documentation-observation.json`.095A excluido.
- **VERIFICADO10:08:59 UTC:** `post-firmware-ssh-readonly.json` confirma
  Boot ID97828070-b077-4777-9ce6-3ed952d66bb2,187F8B2QJXD7/live,
  095A4B2QJXD7/live y `CHECK_OK_NO_MOUNT`. BootNext se observó ausente; su fuente
  separada y confirmación del siguiente reboot firmware-setup del operador
  constan en `post-fw-linux-and-rollback-reboot-documentation-observation.json`.
- **EJECUTADO por el operador hacia10:10 UTC:** guarda y reboot firmware-setup
  para revertir CSM. Marca exacta pendiente; no se repite la orden. La imagen
  Linux antigua/reconexión posterior no prueba llegada a UEFI.
- **LECTURA BMC10:13:36 UTC:** sólo GET chassis-status y sensors en sesión MAIN
  actual; ambos200, power1 y55 sensores. CPU49°C, DIMM40–46°C, LAN59°C;
  ventiladores CPU/CHA1/CHA2 700rpm, CHA6 1000, SOC2500 y CHIPSET1200.
  API autenticada operativa; sin concluir POST/SO ni interpretar códigos
  discretos de memoria como fallo. Recibo
  `post-fw-rollback-bmc-chassis-sensors-readonly.json`, privado0600.
  Sin acciones UI, energía, reset, logout, nuevo visor o ISO.
- **EJECUTADO por GUI normal:** Stop Media10:14:17.823 UTC, Stop KVM10:14:46.390
  con cierre del visor propio y Launch H5Viewer10:15:21.122 desde MAIN.
  El nuevo visor recuperó UEFI viva sin otro reset del BMC/servicio.
- **RESTAURACIÓN GUARDADA:** CSM Enabled leído en
  `post-fw-rollback-csm-loaded.png`; se eligió Disabled y aceptó su aviso en
  `post-fw-csm-disabled-after-warning.png`. Primary Display ya era Discrete
  graphics card (`post-fw-rollback-primary-read.png`), sin edición.
  F10 mostró sólo CSM Enabled → Disabled
  (`post-fw-csm-rollback-save-review.png`); Enter10:17:26 UTC confirmó reinicio.
- **POSTROLLBACK PASS10:20:03 UTC:** `post-csm-rollback-ssh-readonly.json`,
  boot e719f517-0709-417a-b521-7bc8c0212bf6, UEFI,187F8B/095A4B/live, cinco
  máscaras/inactividad y `CHECK_OK_NO_MOUNT`. Lectura EFI10:20:43 en
  `post-csm-rollback-efi-readonly.json`: Current0001, Order sólo0001 Ubuntu,
  Next ausente, sin BBS y SecureBoot disabled. Retirada BBS automática, sin
  borrado/reordenación manual; arranque y restauración verificados.
- **INFORME REAL10:30:42 UTC:** el operador ejecutó el helper de
  [postcomprobación](POSTFIRMWARE_CHECK.md), instalado y13testsPASS según
  `postcheck-deployment-final.json`. El JSON sudo
  `/home/luisacuna/app2/maintenance/postfirmware-check-20261020T1023Z.json` terminó0:
  SMART de ambos SSD con critical_warning/media_errors/error-log0 y sin I/O/reset
  observados en el extracto kernel. `e2fsck -f -n` omitió journal y mostró dos
  diferencias de contadores globales, Fix?no, aunque terminó0. Su etiqueta
  NO_ERRORS_REPORTED_READ_ONLY no prueba limpieza EXT4. Revisar la
  [interpretación y plan mínimo](FIRMWARE_SAMSUNG_990_PRO.md#12-informe-real-de-lectura-journal-pendiente-y-contadores-globales)
  antes de escribir; no hubo reparación/montaje/reactivación. Integridad/CVAT y
  estabilidad posterior pendientes entonces; el resultado posterior y la
  recuperación real se registran en la cabecera y sección14 de firmware.
  No repetir alimentación, Reset KVM Service, CSM, BootNext ni flash por aparecer aquí.
- **CIERRE propio del PC:** medio ya retirado antes del rollback; Chrome
  aislado PID665887 cerrado tras comprobar propiedad, perfil privado retenido.
  Sign out por CDP agotó su espera: no se comprobó logout ni revocación BMC.
  Sin cambios de alimentación/servicios durante la limpieza. Fuente
  `bmc-session-cleanup-and-sudo-report-pending.json`; no cerrar sesiones ajenas.

Antes de actuar se conservaban los backups verificados de volúmenes,
definiciones, PostgreSQL, medios y capas escribibles. Docker seguía protegido
por cinco máscaras y el origen de datos desmontado. Revalidar ese contexto en
el [incidente](../../../docs/incidents/2026-10-20_APP2_SSD_DOCKER_NO_RESPONDE.md).
Un apagado confirmado por BMC no demuestra por sí solo cierre limpio de todos
los sistemas de archivos; debe verificarse el arranque posterior.

**Fuente reproducible de la API:** JavaScript servido por el BMC real,
`source.min.js`, **6.101.166 bytes**, SHA256
`e9f45ce6977e52f913ded6d48512921225eb003dc23a3c9c5d523f179bcacf31`.
Su código de login y su plantilla de alimentación establecen este mapeo:

| Valor `power_command` | Significado observado | Tratamiento |
|---|---|---|
| `0` | apagado forzado | No expuesto por el ejemplo |
| `1` | encender | Sólo con lectura previa `power_status=0` |
| `2` | ciclo de alimentación | No expuesto por el ejemplo |
| `3` | reset de host | **PLAN condicional**, no realizado en esta instantánea |
| `5` | apagado ACPI | Realizado, apagado posterior medido |

No confundir esta API con `/api/maintenance/reset`: ese endpoint aparece en el
código de flujos de actualización/reset/cancelación, pero **no está mapeado ni
validado como recuperación administrativa genérica**. No se invocó aquí y no se
presenta como una forma segura de reiniciar el BMC. La acción comprobada de
servicio KVM fue `/api/ResetKVM`, separada de alimentación y actualización.

Evidencia privada estable:

```text
../Humanoide-vla-evidence/20261020T061422Z_APP2_RESUME_READONLY/
  bmc-web-source.min.js
  bmc-web-auth-static-inspection.json
  bmc-web-auth-readonly-prestate.json
  bmc-web-auth-capability-prestate.json
  bmc-acpi-shutdown-plan.json
  bmc-acpi-shutdown-result.json
  bmc-power-on-after-acpi.json
  documentation-acpi-off-poweron-ubuntu-recovered-review.json
  post-acpi-ubuntu-protection-check.json
  bmc-kvm-service-reset-result.json
  bmc-clean-kvm-initial.png
  bmc-kvm-120s-stability.json
  bmc-kvm-empty-enter-after.png
  virtual-cdrom-second-attachment-sha256-operator-result.json
```

Los archivos de sesión, credenciales y tokens no deben copiarse a Git ni a esta
receta. No se reproducen cuerpos de login ni cabeceras de autenticación.

## 2. Secuencia de decisión

1. Consultar estado y conservar la evidencia antes de otra acción. Una pantalla
   KVM antigua y la ausencia de SSH no distinguen por sí solas entre host
   bloqueado, host en UEFI o sesión de vídeo congelada.
2. Si el host está apagado después del ACPI, el siguiente paso autorizado es
   **encender**, sin reset ni ciclo adicional. Comprobar después SSH y KVM,
   identidad de ambos SSD y las cinco guardas antes de usar almacenamiento.
3. **Sólo si sigue encendido**, no responde al cierre ordenado y la recuperación
   exige reinicio: valorar el comando `3` de host como etapa separada. Es abrupto,
   no asegura un cierre de Linux. No se encadena automáticamente al agotarse la
   espera de ACPI. Nunca hacerlo durante escritura de firmware o restauración.

No cambiar BootOrder, CSM, Secure Boot, usuarios o LAN como parte de esta
recuperación. El firmware del SSD sigue una
[receta independiente](FIRMWARE_SAMSUNG_990_PRO.md), con serie de destino verificada.
Sus secciones8/11 conservan el cambio CSM temporal, su lectura efectiva Enabled
y la restauración Disabled; **arranque final/EFI normal ya verificados**.
El método exige KVM actual/teclado vivo y capturas de valores anteriores.
La observación ASPEED integrada
de `server-aspeed-console-readonly-observation.json` apoya la evaluación, sin
garantizar el siguiente POST ni autorizar un cambio desde esta receta BMC.

## 3. Ejemplo reproducible desde el PC, sin dependencias externas

Guardar el bloque Python siguiente como `bmc_recovery_local.py` en una carpeta
**privada del PC** (`umask 077`). Usa sólo biblioteca estándar; no requiere sudo.
El ejemplo permanece fijo en la IP revisada y sólo permite cuatro operaciones.
Pide credenciales por terminal sin mostrarlas ni incluirlas en argumentos,
entorno, historial o archivos. Crea y elimina **su propia** sesión web; no cierra
las sesiones del operador, no inicia KVM ni adjunta medios.

La verificación TLS es la predeterminada. Si el certificado local no tiene una
CA de confianza, `--allow-self-signed` permite la excepción explícita utilizada
en el diagnóstico privado; cifra el tráfico, pero **no valida la identidad del
certificado**. Usar sólo la ruta/IP BMC contrastada; no es una opción para Internet.

```python
#!/usr/bin/env python3
import argparse
import datetime
import getpass
import http.cookiejar
import json
import os
from pathlib import Path
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://192.168.1.34"
ACTIONS = {
    "acpi-off": (5, 1, 0, "APAGAR HOST ACPI"),
    "power-on": (1, 0, 1, "ENCENDER HOST"),
    "hard-reset": (3, 1, 1, "REINICIAR HOST FORZADO"),
}
parser = argparse.ArgumentParser()
parser.add_argument("action", choices=["status", *ACTIONS], nargs="?", default="status")
parser.add_argument("--allow-self-signed", action="store_true")
args = parser.parse_args()
os.umask(0o077)
stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
out = Path("bmc-recovery-" + stamp)
out.mkdir(mode=0o700, exist_ok=False)
report = {"utc": stamp, "base": BASE, "action": args.action,
          "tls_certificate_verified": not args.allow_self_signed,
          "power_command_sent": None, "polls": []}

def save():
    (out / "result.json").write_text(json.dumps(report, indent=2) + "\n")

context = (ssl._create_unverified_context() if args.allow_self_signed
           else ssl.create_default_context())
jar = http.cookiejar.CookieJar()
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Unexpected redirect; no authentication forwarded")

opener = urllib.request.build_opener(
    urllib.request.ProxyHandler({}),
    NoRedirect(),
    urllib.request.HTTPCookieProcessor(jar),
    urllib.request.HTTPSHandler(context=context),
)
csrf = None

def request(path, method="GET", value=None, form=False):
    headers = {"Accept": "application/json"}
    if csrf:
        headers["X-CSRFTOKEN"] = csrf
    data = None
    if value is not None:
        data = (urllib.parse.urlencode(value).encode() if form
                else json.dumps(value).encode())
        headers["Content-Type"] = ("application/x-www-form-urlencoded" if form
                                   else "application/json")
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    with opener.open(req, timeout=10) as response:
        raw = response.read(1_000_001)
        if len(raw) > 1_000_000:
            raise ValueError("Response exceeds bound")
        return response.status, json.loads(raw) if raw else None

logged_in = False
try:
    username = input("Usuario BMC: ")
    password = getpass.getpass("Contraseña BMC: ")
    status, login = request("/api/session", "POST",
                            {"username": username, "password": password}, form=True)
    del password
    if status != 200 or login.get("ok") != 0:
        raise ValueError("Web login not successful; no automatic retry")
    logged_in = True
    csrf = login.get("CSRFToken")
    if not isinstance(csrf, str) or not csrf or not any(c.name == "QSESSIONID" for c in jar):
        raise ValueError("Expected CSRF token or session cookie absent")
    del login
    status, before = request("/api/chassis-status")
    report["before"] = {"http_status": status, "body": before}
    save()
    if args.action == "status":
        report["result"] = "READ_ONLY_POWER_QUERY"
    else:
        command, required_state, target_state, phrase = ACTIONS[args.action]
        if status != 200 or before.get("power_status") != required_state:
            raise ValueError("Fresh power state does not match selected action")
        if input("Escriba exactamente " + phrase + ": ") != phrase:
            raise ValueError("Action not confirmed; no power command sent")
        # Releer después de la confirmación; nunca usar sólo el estado antiguo.
        status, fresh = request("/api/chassis-status")
        if status != 200 or fresh.get("power_status") != required_state:
            raise ValueError("Power state changed; no power command sent")
        report["power_command_requested"] = command
        report["power_command_delivery"] = "INDETERMINATE_UNTIL_RESPONSE"
        save()
        status, body = request("/api/actions/power", "POST", {"power_command": command})
        report["power_command_sent"] = command
        report["power_command_delivery"] = "RESPONSE_RECEIVED"
        report["action_response"] = {"http_status": status, "body": body}
        save()
        # Un HTTP200 no demuestra que el host se haya apagado o reiniciado.
        for attempt in range(19):
            status, state = request("/api/chassis-status")
            report["polls"].append({"utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                    "http_status": status, "body": state})
            save()
            if args.action != "hard-reset" and status == 200 and state.get("power_status") == target_state:
                report["result"] = "POWER_STATE_CONFIRMED"
                break
            if attempt < 18:
                time.sleep(5)
        else:
            report["result"] = "NEEDS_REVIEW_NO_FURTHER_ACTION"
        if args.action == "hard-reset":
            report["result"] = "RESET_REQUESTED_VERIFY_NEW_BOOT_AND_SSH_SEPARATELY"
except Exception as exc:
    # No registrar cuerpos de errores de login, cookies, tokens ni contraseñas.
    report["error_type"] = type(exc).__name__
    if isinstance(exc, urllib.error.HTTPError):
        report["error_http_status"] = exc.code
    report["result"] = "STOPPED_NO_AUTOMATIC_RETRY"
finally:
    if logged_in:
        try:
            status, _ = request("/api/session", "DELETE")
            report["own_session_logout_http_status"] = status
        except Exception as exc:
            report["own_session_logout_error_type"] = type(exc).__name__
    save()
print("EVIDENCIA=" + str(out.resolve()))
print("RESULTADO=" + report.get("result", "UNKNOWN"))
sys.exit(0 if report.get("result") in {"READ_ONLY_POWER_QUERY", "POWER_STATE_CONFIRMED"} else 1)
```

Primero sólo consulta; incluso ésta crea y elimina una sesión de autenticación:

```bash
umask 077
python3 bmc_recovery_local.py status --allow-self-signed
```

Órdenes **condicionales**, no instrucciones para ejecutarlas todas:

```bash
# Sólo si todavía hace falta un apagado ordenado y el host está encendido:
python3 bmc_recovery_local.py acpi-off --allow-self-signed
# Sólo tras comprobar apagado y autorizar el siguiente arranque:
python3 bmc_recovery_local.py power-on --allow-self-signed
# Último recurso separado; nunca como continuación automática del anterior:
python3 bmc_recovery_local.py hard-reset --allow-self-signed
```

El ejemplo es una receta revisable, **no se ejecutó contra el BMC** como parte de
su preparación. No reintenta login o POST de alimentación. Ante timeout después
del POST, el resultado puede ser indeterminado: consultar estado antes de decidir,
sin repetir a ciegas. Para un reset, `power_status=1` no demuestra nuevo arranque;
verificar Boot ID por SSH y consola cuando regresen. Si el logout falla, registrar
la deuda de esa sesión sin cerrar todas las sesiones ni reiniciar el BMC.

## 4. Verificación posterior y reversión

Al volver SSH, verificar primero identidad del host, Boot ID, ambos NVMe por
serie/firmware y el check de [`storage_rescue.py`](storage_rescue.py). Mantener
las máscaras y no montar datos ni iniciar Docker por el mero hecho de arrancar.
Registrar el resultado en el incidente y las fuentes globales de esta intervención.

La sesión web es transitoria: `DELETE /api/session` cierra sólo la creada por el
ejemplo. Una orden de alimentación no tiene reversión documental ni se deshace
con otro reset: si se apagó y procede recuperar servicio, encender es una acción
separada. No restaurar ciegamente el respaldo de red o de configuración del BMC.

## 5. Consola gráfica aislada con excepción para el certificado concreto

**APLICADO en el PC**, en un Chrome propio con perfil nuevo y privado fuera del
repositorio: excepción limitada al SPKI del certificado BMC observado. No se
instalaron paquetes ni certificados de confianza del sistema operativo; no se
usó `--ignore-certificate-errors` global. La entrada a la web fue autorizada por
el usuario. El helper de consola preparó la sesión KVM/ISO. El arranque de ISO
y medio se validaron posteriormente; la utilidad informa finalización y Linux
verifica8B en187F/4B en095A según la sección1. CSM Disabled y arranque normal
posterior ya verificados. No derivar la versión
efectiva del SSD de un login correcto ni sólo de la recepción de vídeo.
El gate posterior de vídeo/teclado120s y SHA del medio ya figura en la sección1;
no se confunde con una prueba de arranque o actualización.

| Dato público de la identidad observada | Valor |
|---|---|
| BMC | `https://192.168.1.34/` |
| SHA256 del certificado DER | `5322360a61c251a9934a9c32ef87e250bd3b6c951e3c34fca637fa8a7b41b155` |
| Pin SPKI SHA256 en Base64 | `WTB9qT4VQPw+XsyB18MblgYqJHYv7esAi6e5I+gGhNQ=` |

Los dos hashes no son intercambiables: el primero identifica los bytes del
certificado; el segundo es el argumento del navegador para su clave pública.
Si cambia la identidad presentada, no ampliar la excepción ni copiar otro pin
sin verificarlo. El perfil puede contener cookies y sesiones: permisos0700,
evidencia privada y nunca Git. La receta reproduce el navegador manualmente;
no requiere publicar el helper CDP privado ni sus credenciales/tokens.

En el PC, elegir una carpeta de evidencia privada existente, propia y fuera del
repositorio. La carpeta del perfil debe ser **nueva**, sin reutilizar un Chrome
normal o abierto. Sustituir sólo la ruta de ejemplo:

```bash
umask 077
bmc_evidence_dir='/ruta/privada/fuera/del/repositorio'
test -d "$bmc_evidence_dir" && \
test ! -L "$bmc_evidence_dir" && \
test ! -e "$bmc_evidence_dir/profile-spki-clean" && \
mkdir -m 700 "$bmc_evidence_dir/profile-spki-clean" && \
google-chrome \
  --user-data-dir="$bmc_evidence_dir/profile-spki-clean" \
  --ignore-certificate-errors-spki-list='WTB9qT4VQPw+XsyB18MblgYqJHYv7esAi6e5I+gGhNQ=' \
  --new-window 'https://192.168.1.34/'
```

Iniciar sesión manualmente con la credencial autorizada. No poner usuario,
contraseña, cookies o tokens en la URL, argumentos, historial, capturas públicas
o repositorio. Usar un único visor KVM y comprobar imagen actual/teclado antes
de preparar el medio. Un certificado aceptado o una ventana abierta no prueban
que la consola renueve vídeo ni que el teclado llegue al host.

**Reversión:** cerrar sólo este navegador/perfil y su visor propios, conservando
la evidencia necesaria. La excepción deja de aplicarse al cerrar ese proceso;
otro arranque normal de Chrome no hereda estos argumentos. El directorio privado
puede seguir conteniendo sesiones; tratarlo como secreto hasta archivarlo o
retirarlo de forma deliberada. No matar todos los Chrome, no cerrar sesiones
ajenas ni cambiar la confianza global del PC. Registrar el cierre y el resultado.

**Cierre real registrado:** el agente principal cerró el Chrome propio PID665887
después de comprobar su propiedad; retuvo el perfil privado. Antes se intentó
Sign out por CDP, pero agotó la espera. Por ello no se afirma logout o revocación
de la sesión BMC al cerrar el navegador. El medio ya estaba retirado antes del
rollback; no se enviaron comandos de alimentación/servicios en esta limpieza.
Evidencia `bmc-session-cleanup-and-sudo-report-pending.json`.

La evidencia del helper CDP y su hash se incorporarán al recibo privado al
terminar esa preparación. Su ejecución no se confunde con la del ejemplo API
de la sección3, que se conservó como receta sin ejecutarlo contra el BMC.


## Cierre de esta intervención

La secuencia de restauración de configuración, montaje verificado y START ya se
ejecutó y comprobó; no requiere otra acción BMC, firmware ni sudo. Fuentes
privadas: `docker-activation-system-readonly.json`,
`docker-post-start-compare-20261020T113508Z.json`,
`cvat-post-recovery-api-media.json` y `pc-cvat-tunnel-restored.json`.
La [sección15 de firmware](FIRMWARE_SAMSUNG_990_PRO.md#15-estado-final-dockercvat-recuperados-retomar-las-anotaciones)
conserva hashes, límites y siguiente paso humano. Mantener los backups y la
vigilancia del almacenamiento; no repetir los comandos históricos de recuperación.
