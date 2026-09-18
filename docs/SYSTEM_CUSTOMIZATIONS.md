# Registro de adaptaciones del sistema Cruzr S2

**2026-09-16 — HOME-BODY-FIRST-04:** instalado HOME de20 s con cuerpo a cero
antes de apertura/bajada/cierre de brazos, por petición del propietario y con
paro confirmado. Hash e3d06564…69dc49c; diez tests locales pasan. Sin acciones
de movimiento; ensayo físico pendiente. Sustituye open_v3 como archivo vigente.
Reinicio de manipulación completado y hash verificado; carga funcional pendiente:
Motion espera ListControllers y CC WaitStartMotion. Mantener paro; recuperación
por ciclo completo supervisado v0.2.0 antes de ensayo.
[Receta, respaldo y estado](teleoperation/CRUZR_HOME_CUERPO_PRIMERO.md).


**Relevo para la próxima sesión — 2026-09-14:** leer primero el [estado consolidado y secuencia de reanudación](vla/RELEVO_VLA_20260914.md). HOME→READY→ENTRY está probado por el operador; shadow funciona. TRIAL_02 abortó por timeout al cambiar a SDK, con cero frames y sin acuse; el controlador final es desconocido. Prioridad: consultar controlador y logs antes de reintentar. No repetir ensayos ni asumir estado físico a partir del historial.


**2026-09-14 — Corregida la selección de controlador del ensayo mínimo (VLA-01).**
El intento `ENTRY410_ONE_POINT_TRIAL_01-6l8y73xw` publicó 134 consignas en
1,33 s, con brazos inmóviles, y terminó por `Tracking error: R_shoulder_pitch_joint`.
ROSA nativo confirmó `manipulation_controller=running` y ambos SDK `initialized`:
el ejecutor anterior omitía el cambio de controlador. La captura posterior
coincide con el inicio. Se añadió inventario nativo, cambio mediante
`/mc/motion_sdk/switch_to_vla` sólo en `--run`, respuesta positiva y feedback SDK
20D fresco antes de publicar. Conserva chasis y mantiene explícitamente los
seis ejes fuera de los brazos. Sin aumento de tolerancias, reinicio, HOME ni
reintento automático; al acabar conserva SDK activo. Diecisiete tests locales
pasan; --check y --observe en vivo pasan sin activación ni publicador.
**Cambio de controlador y ejecución corregida pendientes de prueba física.**
Plan vigente: `controller-fixed-plan`; el plan anterior queda obsoleto por hash.
[Detalles, comando y reversión](vla/ENSAYO_MINIMO_PUNTO_VLA_ENTRY410.md).


**2026-09-14 — Corregidos directorio de evidencias y admisión del ensayo mínimo.**
El intento guardado terminó antes de crear el publicador; la segunda invocación
falló por directorio existente. Ahora cada nueva invocación conserva el anterior
y obtiene una ruta única. El diagnóstico identificó pequeñas variaciones de
encoders de rueda; se usa velocidad≤0,01rad/s más deriva≤0,002rad, y admisión
articular≤0,01rad/s con posición inicial≤0,002rad durante1s. No se cambian
trayectoria ni límites de seguimiento. Quince tests pasan; --observe pasó en
vivo con cero publicadores creados. Plan regenerado: admission-fixed-plan.
Ensayo físico del prefijo todavía no ejecutado por el agente.
[Comando vigente, evidencia y reversión](vla/ENSAYO_MINIMO_PUNTO_VLA_ENTRY410.md).


**2026-09-14 — Ensayo mínimo VLA preparado, aún no ejecutado.**
Replay parcial del primer punto del chunk2 desde ENTRY410: ambos brazos,
25 % de la transición, máximo 1,396°, 4 s; no agarre ni chunk completo.
El punto completo mantiene un par mano derecha/mesa sin resolver; el prefijo
conserva 1018 pares certificados y los 54 avisos internos históricos, sin nuevos
fallos geométricos. Trece tests y --check pasan. Ejecutor SDK con lectura de
salud/paros/cargador/postura, seguimiento y llegada; sin reintentos ni HOME.
No requiere instalar XML, recargar o reiniciar. Scripts del operador intactos.
[Comando, límites, reproducción y estado pendiente](vla/ENSAYO_MINIMO_PUNTO_VLA_ENTRY410.md).


**Continuación vigente — 2026-09-14: ENTRY medido y shadow task 0 completado.**
98 muestras inmóviles, error final máximo 0,1593° respecto a ENTRY410. Seis
propuestas y seis aceptaciones por el perfil shadow existente de 14 ejes de
brazos; primer cambio máximo 6,1643° (umbral shadow 0,35 rad), sin envío físico.
Inferencia caliente mediana 0,436 s; arranque exterior 79,394 s. Caja completa
visible en la cámara. Sesión cerrada: ambos contenedores VLA exited y cero
publicadores de movimiento. No se cambiaron tareas ni umbrales. Siguiente:
adaptar el ejecutor físico a ENTRY410 y resolver entrada al primer punto;
no repetir HOME/READY/ENTRY ni confundir aceptación shadow con agarre probado.
[Ensayo, tiempos, reproducción y evidencia](vla/ENSAYO_READY_ENTRY410_20260914.md).


**Actualización vigente — 2026-09-14: READY→ENTRY410 probado físicamente,
5/5 etapas con éxito según el operador y sus cinco resultados Motion SUCCEED.**
HOME→READY nuevo y READY→ENTRY410 quedan completados para los ensayos comunicados.
Se conserva `force_entry.sh` del operador. Siguiente: lectura fresca y propuestas
VLA task 0 en shadow desde ENTRY; el agarre VLA aún no se ha probado.
[Registro del ensayo, Goal ID y evidencia](vla/ENSAYO_READY_ENTRY410_20260914.md).


**Actualización vigente — 2026-09-14: HOME→READY nuevo probado físicamente,
5/5 etapas con éxito.** El propietario aporta los cinco resultados Motion
`SUCCEED` (state 1101001, status 4) y confirma el ensayo exitoso desde HOME.
Se cierra el pendiente de primera ejecución del acceso
`ready410_h63_access_01..05_forward` para este ensayo. Se registra lentitud:
122 s nominales; duración real no cronometrada. La ejecución fue mediante ROSA
directo con un `force_ready.sh` modificado por el operador; el agente conserva
ese archivo. ENTRY/VLA y el monitor Python no quedan probados por este ensayo.
Esta actualización prevalece sobre los estados históricos de READY pendiente.
[Resultados, cinco Goal ID, alcance y evidencia](vla/ENSAYO_HOME_READY_NUEVO_20260914.md).


Última consolidación: **2026-09-11, Europe/Madrid**. Política obligatoria:
[`AGENTS.md`](../AGENTS.md). Procedimiento de respaldo y reaplicación:
[guía de actualización](guides/CRUZR_REAPLICAR_CAMBIOS_TRAS_ACTUALIZACION.md).

Este índice identifica el **estado deseado vigente**, sus fuentes y cómo
recuperarlo. La [fuente global](PROJECT_SOURCE_OF_TRUTH.md) y las guías enlazadas
conservan las verificaciones e incidencias. Esta consolidación es documental:
no constituye un inventario nuevo en vivo ni demuestra la postura actual.
Las fechas de las evidencias importan. Al cambiar una adaptación, actualizar
su ficha y añadir el evento a la fuente global, sin borrar la historia.

`VERIFICADO` describe sólo la comprobación indicada. `OBSERVADO` puede proceder
del operador. `PENDIENTE` no equivale a instalado ni validado. Una actualización
no convierte automáticamente los ajustes anteriores en requisitos nuevos.

## Orden y alcance

| ID | Adaptación / datos | Destino | Tratamiento tras actualizar |
|---|---|---|---|
| OPS-01 | Registro obligatorio y respaldo ampliado | Repositorio del PC | Conservar fuentes y revisar cobertura antes de actualizar |
| SYS-01 | Firmware, hardware y servicios opcionales | Ambos ordenadores | Redescubrir; conservar perfil del efector real |
| BOOT-01 | Espera preventiva de Control Center | Vision: host + compose | Revisar contrato/binario; aplicar al compose nuevo |
| BOOT-02 | Voz inglesa una vez por encendido | Vision: host + systemd | Reinstalar fuentes/unidad si siguen compatibles |
| BOOT-03 | Vídeo `巡检` durante la espera inicial | Vision: host + contenedor web | Revisar página/recurso; preparar indicación apagada |
| BOOT-04 | Vigilante de self-check bloqueado por caída del monitor | Vision: host + systemd | Revisar firma/contratos CC; reinstalar si sigue la carrera |
| MOT-01 | HOME interno con brazos abiertos, 20 s | Motion: XML dentro del contenedor | Revisar **antes del primer HOME** |
| MOT-02 | PICO→HOME abierto; 4× por defecto | PC + tareas de Motion | Reinstalar cada perfil requerido y su registro |
| ANL-01 | Comparadores y planificador HOME general offline | PC, sólo análisis | Conservar fuentes, dependencias, modelos y evidencia; no se instala en el robot |
| MOT-03 | PICO sólo brazos | Motion: YAML dentro del contenedor | Comparar original/overlay y carga efectiva |
| MOT-04 | Tareas READY/recovery adaptadas a S2 | Motion: XML + task_list | Revisar por tarea; no restaurar task_list entero |
| MOT-05 | HOME original de fábrica como `cruzr/originalhome` | Motion: XML + task_list | Reinstalar si se desea conservar; no sustituye `cruzr/home` |
| PC-01 | Ethernet y Wi-Fi de robot | PC: NetworkManager | Conservar/exportar; redescubrir interfaces |
| PC-02 | Controller 4.7, UI 4.1, XR y udev | PC + PICO | Recuperar versiones/configuración sin autoSTART |
| PC-03 | Credencial SSH privada para los tres scripts migrados | Sólo PC, fuera de Git | Recuperar de copia privada o usar variable de entorno |
| VLA-01 | Paquete VLA y adaptaciones S2 | PC + Motion + Vision | Inferencia/shadow; contenedores detenidos |
| NAV-01 | Mapas, mesas, referencias y geometría | Robot + `config/` del PC | Conservar datos; comprobar vigencia física |
| NAV-02 | Percepción temporal de carga | Vision: configuración de navegación | Conservar original; no activar al restaurar |

La copia de una tarea en la capa escribible de Docker suele sobrevivir a un
reinicio del mismo contenedor, pero **puede desaparecer al recrearlo**, aunque
no cambie la versión del firmware. Los scripts locales tampoco bastan si sus
XML o entradas de `task_list.yaml` no están instalados/cargados en Motion.

## Fichas vigentes

### OPS-01 — Política de registro y respaldo reproducible

- **VERIFICADO local 2026-09-10:** `AGENTS.md` exige documentar todo cambio
  persistente o temporal en robot, PC y PICO durante la misma intervención.
  Este registro y la guía de reaplicación reúnen las adaptaciones conocidas.
- **Fuentes/destinos:** [`AGENTS.md`](../AGENTS.md), este documento, la guía
  enlazada arriba y [`preupgrade_backup_remote.sh`](../scripts/upgrade/preupgrade_backup_remote.sh)
  en el repositorio. El script se copia y ejecuta en cada host sólo al preparar
  un respaldo; no se instaló como servicio del robot.
- **Cambio del respaldo:** añade boot, systemd, overlays, backups de tareas,
  configuraciones dentro de contenedores detenidos, inventario de cambios,
  estado parcial explícito, permisos privados desde el inicio y checksums
  relativos para comprobar la copia externa. No es una imagen de disco.
- **Higiene de Git, 2026-09-10:** los dos paquetes originales
  `cruzr_s2_description/` y `cruzr_s2_description_splint/` son entradas externas
  ignoradas, conservadas completas en disco (130 archivos, aproximadamente
  107 MB). `.gitignore` también cubre credenciales privadas, entornos/cachés
  Python, salidas de colcon y grabaciones ROS. Conservar esos modelos y las
  evidencias fuera de Git para reproducir los análisis; un clon no los incluye.
  El índice previo y los hashes de los modelos están respaldados en
  `../Humanoide-vla-evidence/20260910T122441Z_COMMIT-CLEANUP/`.
- **Reaplicar/verificar:** conservar la carpeta de trabajo, no sólo el commit;
  seguir la guía de respaldo. Cuatro pruebas offline con Docker simulado:
  captura y permisos/checksums, rechazo de sobrescritura, copia fallida,
  nombres nuevos e inventario fallido. Sintaxis Bash y enlaces locales
  comprobados. **PENDIENTE:** primera captura con esta versión en ambos hosts.
- **Backup/reversión:**
  `../Humanoide-vla-evidence/20260910T110924Z_SYSTEM-CHANGE-POLICY/` conserva
  anteriores, fuentes finales y hashes. Los anteriores de AGENTS/README/script
  proceden de HEAD porque estaban limpios al iniciar esta solicitud; los de
  las guías/fuente global preservan el trabajo pendiente previo. Para revertir,
  retirar sólo esta sección/enlaces o restaurar selectivamente el script;
  no sobrescribir documentación posterior. El script anterior tiene menor
  cobertura de respaldo. Ningún servicio ni parámetro del robot fue cambiado.

### PC-03 — Credencial SSH privada del PC

- **Cambio local 2026-09-10:** se retira la contraseña literal de
  `cruzr_blue_workbin_cycle.sh`, `teleoperation/cruzr_pico_to_home_owner.sh` y
  `vla/audit_vla_live_preflight_e6_0g.sh`, todos bajo `scripts/`. Sus ramas
  SSH_ASKPASS usan [`cruzr_ssh_askpass.py`](../scripts/lib/cruzr_ssh_askpass.py).
  No se cambió la contraseña del robot ni se abrió una conexión para migrarla.
- **Prioridad:** `CRUZR_SSH_PASSWORD` no vacío; en su ausencia,
  `CRUZR_SSH_PASSWORD_FILE` o `.secrets/cruzr_ssh_password` en la raíz del repo.
  El archivo debe pertenecer al usuario actual, ser regular, sin enlace
  simbólico ni permisos para grupo/otros y contener una única línea no vacía.
  Un archivo inválido rechaza la autenticación, sin alternativa embebida.
- **Recrear:** recuperar la credencial desde un respaldo privado o escribirla
  en el archivo con un editor local. Directorio `.secrets/` con permisos `700`
  y archivo con `600`; no ponerla en documentación ni argumentos de comandos.
  También puede proporcionarla el entorno existente. `--help` y las pruebas
  locales no necesitan leer la credencial. No ejecutar el helper directamente
  en una terminal registrada: su stdout es la respuesta destinada a SSH.
- **Respaldo/reversión:** durante esta migración se conservó la credencial
  existente en el archivo privado ignorado y se respaldaron los tres scripts
  en `20260910T122441Z_COMMIT-CLEANUP/before-auth/`, dentro del directorio externo
  indicado en OPS-01. Conservar esa copia con acceso restringido. Para cambiar
  la fuente, usar el entorno o el archivo indicado; no reintroducirla en Git.
- **Verificación:** ocho pruebas offline de prioridad, contenido, permisos,
  archivos especiales, ramas reales ASKPASS y ayuda sin credencial.
  **Alcance:** sólo estos tres scripts; no se migraron todos los scripts antiguos
  ni se reescribió el historial de Git. Queda pendiente una migración general
  y decidir la rotación de credenciales ya presentes en el historial.

### SYS-01 — Baseline y servicios opcionales

- **Estado/evidencia:** baseline v0.2.0 documentado en la unidad
  `WAE001UBT60000669`; abrazaderas, `HW_TYPE=cruzr_s2_v1`. Motion
  `192.168.11.2`, Vision `192.168.11.3`. El perfil histórico de manos v4
  `cruzr_s2_v1_sps` no corresponde a estas abrazaderas.
- **Destinos:** `/etc/walker/system`, configuración uDoke de cada host,
  imágenes y políticas de reinicio Docker. `TELE_DEVICE=pico`, `transmit=local`;
  `MC_SCENE` observado vacío, build DAC del SOP no demostrada.
- **Cambios documentados:** plantillas `main.x86`/`main.orin` sin comando y
  MQTT cloud defectuoso detenidos, sin reinicio automático; MQTT local/upilot
  conservados. No confundirlos con todos los servicios MQTT.
- **Reaplicar/verificar:** comparar `docker inspect`, imágenes/digests,
  variables y servicios con la nueva entrega. Sólo reproducir esos workarounds
  si sigue existiendo el problema. Registrar nombres reales, nunca seleccionar
  un contenedor sólo por una IP o un nombre histórico.
- **Backup/reversión:** compose, inspect y políticas anteriores en el respaldo
  de ambos hosts. Reversión selectiva según versión; no restaurar todo el
  compose antiguo. Netdata no saludable y frecuencia GPU discrepante son
  deudas de proveedor, no correcciones locales aplicadas.
- **Detalle:** [fuente global, sección 4](PROJECT_SOURCE_OF_TRUTH.md#4-cambios-persistentes-realizados-en-el-robot).

### BOOT-01 — Espera preventiva de Control Center

- **VERIFICADO 2026-09-10:** evita iniciar CC antes de respuestas funcionales
  de Motion; ampliado a seis cámaras con marcas crecientes. Arranque en frío
  observado con la espera de Motion; no elimina self-check ni HOME del arranque.
- **Fuente → destino:**
  [`cruzr_cc_start_when_ready.py`](../scripts/upgrade/cruzr_cc_start_when_ready.py)
  → Vision `/etc/walker/boot/cruzr_cc_start_when_ready.py`;
  `/home/walker/.config/udoke/walker/compose.yml`, sólo
  `services.system.control_center.command` →
  `python3 /etc/walker/boot/cruzr_cc_start_when_ready.py --start`.
- **Compatibilidad:** v0.2.0, hash del binario CC y contratos de servicios
  comprobados por el script. Una versión distinta exige revisar el código;
  no cambiar sólo el hash esperado para conseguir que pase.
- **Reaplicación/activación:** receta BOOT en la guía; helper
  [`patch_cc_readiness_compose.py`](../scripts/upgrade/patch_cc_readiness_compose.py)
  prepara exclusivamente ese cambio. Activación en encendido supervisado;
  modificar el archivo no demuestra que el contenedor actual use el comando.
- **Verificación:** [`cruzr_boot_ready.sh --check`](../scripts/cruzr_boot_ready.sh)
  durante la primera espera; comprobar identidad/log de CC, respuestas y cámaras.
- **Backup:** `compose.yml.before-cc-ready-20260910T065831Z` junto al compose;
  wrapper anterior en `/etc/walker/boot/`. Rollback selectivo para próximo
  arranque: retirar el comando wrapper sólo tras resolver/revisar la carrera.
  **El guard antiguo permanece deshabilitado.**
- **Detalle/evidencia:** [guía boot](guides/CRUZR_V020_BOOT_GUARD.md),
  `../Humanoide-vla-evidence/20260910T064413Z_BOOT-READONLY/` y
  `20260910T081749Z_BOOT-VOICE/`.

### BOOT-02 — Aviso hablado de arranque

- **VERIFICADO 2026-09-10:** el usuario oyó claramente “Ready to release the
  emergency stop.”; TTS real status4/Success. Una ejecución por boot observada.
- **Fuentes:** [`cruzr_boot_voice.py`](../scripts/upgrade/cruzr_boot_voice.py) en
  Vision `/etc/walker/boot/`; [`cruzr-boot-voice.service`](../scripts/upgrade/cruzr-boot-voice.service)
  en `/etc/systemd/system/`, enabled, Type=simple, User=walker, grupo docker,
  Restart=no. Depende de BOOT-01 y del módulo BOOT-03 en la versión actual.
- **Reaplicar:** receta BOOT; `daemon-reload` y `enable` preparan el siguiente
  arranque, no ejecutar `--watch` como comprobación de instalación.
  ROS 2 para UInt8/paros; ROSA/TTS sólo según contratos comprobados.
- **Verificar/revertir:** `--check` no reproduce voz; `--check --announce`
  es una prueba de audio explícita. Deshabilitar esta unidad retira el aviso;
  conservar el wrapper preventivo. No reiniciar CC para probar el sonido.
- **Estado transitorio:** `/etc/walker/boot/cc_ready_voice_boot_id` identifica
  el boot ya intentado. No copiarlo como configuración al restaurar, ni
  borrarlo para forzar un segundo aviso durante una recuperación.
- **Backup/evidencia:** `/etc/walker/boot/backups/20260910T102219Z_BOOT-VISUAL/`;
  [guía de voz y pantalla](guides/CRUZR_AVISO_VOZ_ARRANQUE.md).

### BOOT-03 — Pantalla con `巡检`

- **VERIFICADO 2026-09-10:** vídeo real `inspection.mp4`, anillo azul con barrido.
  23 pruebas Python, Node y Chromium; captura de pantalla real. **PENDIENTE:**
  próximo encendido completo con voz y vídeo combinados.
- **Fuentes:** [`cruzr_boot_visual.py`](../scripts/upgrade/cruzr_boot_visual.py) y
  [`cruzr-boot-ready.js`](../scripts/upgrade/cruzr-boot-ready.js) →
  Vision `/etc/walker/boot/`; el preparador añade el JS a `index.html` en
  `/usr/share/nginx/html` de `walker-web.web-expression-1`.
- **Contrato:** imagen observada `expression-web:v0.2.20`; index original
  SHA256 `fb294b019cfef37b3e3d9441da099c3b76af8ceb062c7e4cdf121be18cc93566`.
  Recurso nativo servido en `http://127.0.0.1:5000/expression/inspection.mp4`.
  Sólo se superpone a `breath`, otras expresiones tienen prioridad; caduca
  en 12 s sin renovaciones válidas. No modifica la base de fallos.
- **Reaplicar:** `cruzr_boot_voice.py --prepare-display` en Vision, después de
  revisar la imagen/página. Deja la indicación apagada. Un index desconocido
  se rechaza. El navegador cargará el añadido en el próximo arranque; no
  cerrar a la fuerza LoadingScreen, que es el proceso de la sesión kiosk.
- **Verificar/revertir:** `--check --visual` prueba explícita sin voz; se retira
  al perder requisitos. Restaurar selectivamente `index.before.html`/fuentes
  del backup, según la guía. No reiniciar Motion/CC. No restaurar el JSON de
  permiso visual ni la unidad temporal de preview como estado de arranque.
- **Backup/evidencia:** `/etc/walker/boot/backups/20260910T102219Z_BOOT-VISUAL/`,
  `../Humanoide-vla-evidence/20260910T102219Z_BOOT-VISUAL/`.

### BOOT-04 — Vigilante de self-check bloqueado

- **2026-09-18 Europe/Madrid — INSTALADO y habilitado para el próximo arranque;
  detección VERIFICADA en vivo (`--check`: `STUCK=1`) sobre el incidente real.
  Recuperación completa VERIFICADA el mismo día (arranque manual del servicio
  sobre el bloqueo real, hora robot CST): 14:58:47 voz pedir E-stop → 14:59:17
  paro 2/2 → 14:59:30 reinicio sólo CC → 15:00:45 nueva WaitEStopRelease →
  15:00:52 voz lista → liberación humana 15:01:08 → self-check y StartMotion OK,
  `JoystickMode` 15:01:54. Cero comandos de movimiento del vigilante.**
- **Motivo:** [incidente 2026-09-18](incidents/2026-09-18_SELFCHECK_MONITOR_SIGSEGV.md):
  SIGSEGV del proveedor en `self_check_monitor` durante el self-check deja CC
  en `SelfChecking` sin timeout ni StartMotion.
- **Fuentes → destino (Vision):**
  [`cruzr_selfcheck_watchdog.py`](../scripts/upgrade/cruzr_selfcheck_watchdog.py)
  (SHA `d9c8652c…acbd78`) → `/etc/walker/boot/`;
  [`cruzr-selfcheck-watchdog.service`](../scripts/upgrade/cruzr-selfcheck-watchdog.service)
  (SHA `3ba1836d…aca6a`) → `/etc/systemd/system/`, enabled, User=walker,
  grupo docker, Restart=no. Tests: [`test_cruzr_selfcheck_watchdog.py`](../scripts/upgrade/test_cruzr_selfcheck_watchdog.py).
- **Dependencias:** importa BOOT-01/BOOT-02 instalados (`cruzr_cc_start_when_ready.py`
  `19f06f68…`, `cruzr_boot_voice.py` `a76e57ca…`); la receta los verifica por hash.
- **Contrato:** actúa sólo si CC (camino de arranque inicial) lleva ≥120 s en
  `SelfChecking`, sin `selfcheck result` ni `StartMotion`, y
  `walker-system.self_check_monitor-1` arrancó después de entrar en SelfChecking.
  Entonces pide por voz pulsar el E-stop, exige principal=1 y cargador=0 dos
  lecturas seguidas y proceso CC idéntico, reinicia **sólo**
  `walker-system.control_center-1`, espera la nueva `WaitEStopRelease` inicial
  (1/0/0) y anuncia por voz. Una vez por arranque del host
  (`/etc/walker/boot/selfcheck_watchdog_boot_id`, estado transitorio: no copiar).
  Nunca libera paros, llama StartMotion, cambia modos ni mueve. La liberación
  y el HOME interno posteriores siguen siendo decisión del operador.
- **Reaplicar:** [`install_selfcheck_watchdog.sh`](../scripts/upgrade/install_selfcheck_watchdog.sh)
  (tests locales, hashes de dependencias, backup, `enable` sin `start`).
- **Verificar:** en Vision `python3 /etc/walker/boot/cruzr_selfcheck_watchdog.py --check`
  (sólo lectura) y `journalctl -u cruzr-selfcheck-watchdog -b`.
- **Revertir:** `sudo systemctl disable --now cruzr-selfcheck-watchdog.service`,
  borrar los dos archivos y `daemon-reload`. Backups:
  `/etc/walker/boot/backups/20260918T065359Z_BOOT-04/` (instalación inicial,
  `absent.txt`) y `20260918T065433Z_BOOT-04/` (reinstalación idéntica).
- **Tras actualizar CC/self_check_manager:** revisar si el proveedor corrigió la
  carrera o cambió estados/log; si el hash del CC cambia, `--control-snapshot`
  devuelve error y el vigilante no actúa.

### MOT-01 — HOME interno abierto, 20 segundos

- **2026-09-18 — body-first v7 (13,45 s) INSTALADO (12:44 Madrid, E-stop pulsado,
  cargador 0, MetaMove esperado; verificado por hash) por decisión del propietario,
  con ensayo físico supervisado por él. Primer arranque FALLÓ por postura previa
  fuera de HOME (hombro izq. fuera de límite; no por la estructura v7). Ensayo
  supervisado desde brazos al frente/cuerpo flexionado VERIFICADO 19:01 CST: SUCCEED
  15,06 s, 0 avisos de límite, seguimiento máx. 0,012 rad, sin fallos. Ver
  [incidente](incidents/2026-09-18_HOME_V7_ARRANQUE_HOMBRO_FUERA_LIMITE.md).
  Arranque completo con v7 desde HOME VERIFICADO 19:13 CST: self-check OK,
  StartMotion/LimbMotion succ en 15,1 s, `AutoTaskMode`, 11 MetaMove correctos,
  final |q| ≤ 0,00288 rad. Captura (3.635 muestras): brazos error ≤ 0,0052 rad,
  vmax 0,17 rad/s, 0 fallos; muestras deshabilitadas sólo antes de StartMotion.
  Cabeza: salto desde la postura baja de arranque (−0,694, fuera de límite blando)
  con 118 consignas rechazadas, error 0,047 rad y pico 1,19 rad/s; mismo tramo
  que v4/v5, no introducido por v7. Evidencia `../Humanoide-vla-evidence/20260918_V7_BOOT_HOME_TRACE/`.**
  **Instalador (18-09, 19:18 CST):** `--install` exige además un registro
  `--measure-home` (E-stop liberado, 20D ≤ 0,02 rad, motores habilitados) del mismo
  boot y log de `robot_app`, < 30 min y sin `BTree task` posterior
  (`../Humanoide-vla-evidence/HOME_POSTURE_LATEST.json`, estado transitorio: no
  restaurar). Procedimiento en [la guía body-first](teleoperation/CRUZR_HOME_CUERPO_PRIMERO.md).
  Sustituye a v5-18s
  (`adc24aba…`, backup `/etc/walker/trajectory-overlays/20260918T104358.711252Z_home_body_first_v5/home.before.xml`;
  evidencia `../Humanoide-vla-evidence/20260918T104425.242019Z_INTERNAL-HOME-CHANGE/`).
  Fuente [`cruzr_internal_home_body_first_v7_13s.xml`](../scripts/teleoperation/tasks/cruzr_internal_home_body_first_v7_13s.xml)
  SHA `1e6e2fb7ddc598dc3793d093c283c82063507df0e53b70a18e161cab883a6f03`.
  Cambios frente a v5-18s: (1) cada brazo ejecuta en secuencia codos −0,03 (1 s) y
  apertura −0,2 (1,8 s) **en paralelo** con cabeza/elevador/cintura (3,75 s,
  `Sequence` dentro de `Parallel`, patrón usado por 22 tareas del proveedor);
  (2) bajada 7 s (antes 10 s). Cierre 2,7 s. El pico de la bajada no supera el pico
  ya ejecutado desde el mismo inicio por el HOME directo de fábrica o por v4 (test).
  Barrido `--v7` (cuerpo→brazos, brazos→cuerpo, diagonal): mínimo PICO 133,1 mm
  (cota 68,9), brazos abajo y `separate_right` 181,6 mm. Evidencia
  `../Humanoide-vla-evidence/20260918_V7_AUDIT/`. Candidata intermedia v6 (16,45 s,
  bajada 10 s) sólo en repo: `tasks/cruzr_internal_home_body_first_v6_16s_CANDIDATE.xml`
  (`1472de86…`). La v5-18s sigue reconocida por el contrato workbin para revertir.
- **2026-09-18 — body-first v5 (18,25 s) INSTALADO y luego SUSTITUIDO por v7 (12:12 Madrid, E-stop pulsado,
  cargador 0, MetaMove esperado); verificado por hash. Primer arranque y ensayo
  físico PENDIENTES.** Sustituye a la v5 de 21,5 s (`212f3ad8…`, instalada 11:52 y
  nunca ejecutada), que a su vez sustituyó a la v4 (`e3d06564…`).
  Backups: v4 `/etc/walker/trajectory-overlays/20260918T095221.811178Z_home_body_first_v5/home.before.xml`;
  v5-21s `/etc/walker/trajectory-overlays/20260918T101211.525540Z_home_body_first_v5/home.before.xml`.
  Evidencia `../Humanoide-vla-evidence/20260918T095250.040820Z_INTERNAL-HOME-CHANGE/` y
  `20260918T101234.670337Z_INTERNAL-HOME-CHANGE/`. Revertir: reinstalar el `home.before.xml`
  elegido bajo E-stop.
  Motivo: [incidente codo fuera de límite](incidents/2026-09-18_HOME_ARRANQUE_CODO_FUERA_LIMITE.md)
  y peticiones del propietario (abrir la mitad, acelerar). Cambios frente a v4:
  (1) ambos codos `delta −0,03 rad` en paralelo con cabeza/elevador/cintura
  (3,75 s, threshold 5); (2) apertura mitad: `delta` roll −0,2 en 1,8 s (v4 −0,4 en
  2,5 s); (3) bajada 10 s con roll −0,3 (v4 −0,6); (4) cierre 2,7 s (v4 3,75 s).
  Total 18,25 s. Velocidad/aceleración pico quintic de los tramos fijos ≤ v4
  (comprobado en test); la bajada conserva los 10 s de v4.
  Fuente [`cruzr_internal_home_body_first_v5_18s.xml`](../scripts/teleoperation/tasks/cruzr_internal_home_body_first_v5_18s.xml)
  SHA `adc24aba387ceb94a229db14d28668a04e7b9a64432ffa9989dd7145cc9cbf4c`,
  generador `cruzr_internal_home_body_first.py` (v4 byte-idéntico).
  **Barrido offline** [`audit_body_first_v5_opening.py`](../scripts/teleoperation/audit_body_first_v5_opening.py),
  501 muestras, abrazadera ↔ enlaces que no son de su brazo: desde PICO mínimo
  133,1 mm (v4 164,3; cota condicional 68,9 vs 101,9); brazos abajo 171,9 mm;
  `separate_right` real 181,6 mm. Calibración: HOME directo de fábrica 2,7–10,2 mm
  desde PICO (coincide con el acercamiento real). Sólo geometría archivada; sin
  seguimiento, frenado, carga ni obstáculos. Evidencia
  `../Humanoide-vla-evidence/20260918_V5_18S_AUDIT/` (y `20260918_V5_HALF_OPENING_AUDIT/`, 21,5 s).
  [`cruzr_install_internal_home_body_first.py`](../scripts/teleoperation/cruzr_install_internal_home_body_first.py)
  instala v5-18s desde open-v3, v4 o v5-21s; [`cruzr_blue_workbin_cycle.sh`](../scripts/cruzr_blue_workbin_cycle.sh)
  reconoce `body-first-v5-18s`. Tests body-first y contrato workbin pasan.
  **Norma operativa:** no pulsar E-stop ni apagar con los brazos fuera de HOME;
  terminar cada escenario con `cruzr/home`. v5 sólo cubre los codos.

- **VERIFICADO instalado y proceso recargado 2026-09-10; ensayo físico PENDIENTE.**
  Sustituye `cruzr/home`: apertura relativa, bajar abiertos, cuerpo HOME y
  cierre con brazos abajo. No es una recuperación universal tras contacto.
- **Fuente:** [`cruzr_internal_home_open_v3_20s.xml`](../scripts/teleoperation/tasks/cruzr_internal_home_open_v3_20s.xml).
  Motion, `walker-motion.manipulation_robot_app-1`:
  `/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/cruzr/home.xml`.
  SHA256 instalado `05174d2b4cf003b9b1c5274cd445b0d4faefe4276c5fbe8e59e68e6b64ee8cbe`.
- **Reaplicación:** [`cruzr_install_internal_home.py`](../scripts/teleoperation/cruzr_install_internal_home.py)
  `--check` local → `--preflight` → `--install`. `--reload` es una operación
  separada que reinicia manipulación. Requiere brazos abajo/vacíos, paro
  mantenido y contrato MetaMove exacto; seguir [su guía](teleoperation/CRUZR_HOME_INTERNO_APERTURA.md).
- **Verificación:** hash de XML y MetaMove, registro de carga e instancia del
  proceso; luego ensayo físico supervisado independiente. No liberar el paro
  por haber terminado una copia o recarga.
- **Integración PC corregida 10-09-2026:** conservar también
  [`cruzr_blue_workbin_cycle.sh`](../scripts/cruzr_blue_workbin_cycle.sh) y
  [`audit_vla_live_preflight_e6_0g.sh`](../scripts/vla/audit_vla_live_preflight_e6_0g.sh).
  El contrato reconoce este HOME exacto y exige MetaMove exacto; un hash
  desconocido se rechaza sin diagnosticar automáticamente un fallo de arranque.
  Seis regresiones nuevas y cinco previas pasan; preflight PICO4× completo
  verificado en vivo con cero movimientos. Backup PC y log:
  `../Humanoide-vla-evidence/20260910T114627Z_HOME-PREFLIGHT-CONTRACT/`.
  No requiere instalación/recarga remota. Revertir sólo estos scripts devuelve
  el rechazo local; no restaura el HOME antiguo del robot.
- **Backup:** `/etc/walker/trajectory-overlays/20260910T100528.529307Z_home_open_v3/`.
  Restaurar `home.before.xml` devuelve el HOME directo que causó acercamiento
  al cuerpo: **no es un rollback automático seguro**.

### MOT-02 — Ejecutor PICO→HOME abierto

- **Ensayo H02, 11-09-2026 — VERIFICADO físicamente en `pico_body_zero`,
  abrazaderas vacías, perfil4× de20s.** XML
  `config/cruzr/pico_to_home_open_v2_4x.xml` del gestor Motion,
  SHA `6dd482a70e8ec55e02f125eb442b483a12a7c591959e72965214fcc9e02027dc`.
  Instalación exacta, registro anterior al proceso y preflight comprobados.
  Un objetivo SUCCEED/4; 2.103 muestras válidas, ningún fault/deshabilitado,
  HOME final0,00297209rad máximo/velocidad0. Operador: «resultado ok, suave y sin
  contacto, libres, sigamos». Sin cambios de XML, ejecutor, modo o protección;
  no instalación/recarga/reinicio. No se valida cuerpo flexionado o retorno
  general, otros perfiles/cargas ni frenado. Receta, destino completo, alcance,
  límites y siguiente captura: [H02](teleoperation/CRUZR_HOME_ENSAYOS_SUPERVISADOS.md).
  Evidencia y backups documentales ANL-01:
  `../Humanoide-vla-evidence/20260911T084247Z_H02-PICO-SUPERVISED/`.
  Sin rollback remoto; conservar evidencia, restaurar documentos selectivamente
  desde `before/` si fuera necesario sin borrar trabajo previo/posterior.

- **Mejora PC 10-09-2026:** salida sin movimiento `ALREADY_HOME_MEASURED`
  después de preflight y dos lecturas nuevas sanas; tolerancia HOME0,005rad y
  velocidad≤0,002rad/s.22pruebas pasan. No reduce tiempos ni apertura del XML.
  Backup selectivo del ejecutor/pruebas/docs en
  `../Humanoide-vla-evidence/20260910T120838Z_ADAPTIVE-HOME/before/`;
  restaurarlo sólo si se quiere retirar esta salida, preservando cambios posteriores.
  No requiere instalación ni recarga remota. Prueba real de esta salida pendiente:
  la lectura actual encontró principal1/servo0 y no produjo JointState utilizable.
- **OBSERVADO:** el usuario confirmó que open_v2 original funciona. **VERIFICADO**
  perfiles locales 1×/3×/4×; 4× instalado por el usuario y comprobado por hash.
  La deuda de ensayo4× para `pico_body_zero` queda cubierta por H02; otras
  referencias/condiciones permanecen fuera de ese resultado.
- **Fuente/receta:** [`cruzr_pico_to_home_owner.sh`](../scripts/teleoperation/cruzr_pico_to_home_owner.sh)
  y [guía open_v2](teleoperation/CRUZR_PICO_HOME_OPEN_V2.md). Por defecto 4×,
  20 s; 1×=80 s y 3×=26,666 s. Cada velocidad tiene XML/tarea propios.
- **Destino:** directorio `config/cruzr/` y `config/task_list.yaml` del gestor
  de tareas indicado en MOT-01. Tareas `cruzr/pico_to_home_open_v2`,
  `cruzr/pico_to_home_open_v2_3x`, `cruzr/pico_to_home_open_v2_4x`.
  No demuestra que 3× esté instalado por existir en el repositorio.
- **Reaplicar/verificar:** `--check --speed 4` local; `--install --speed 4`
  con requisitos de su guía. `--reload` separado. `--preflight --speed 4`
  sólo es válido en una referencia PICO reconocida con Motion operativo;
  no debe pasar desde brazos abajo. No enviar `--run` para verificar copia.
- **Backup/reversión:** `/home/walker/cruzr-owner-backups/`, manifiesto por
  operación con XML/task_list anterior. Retirar sólo esa entrada/archivo,
  preservando tareas posteriores. No recuperar la antigua ruta directa.

### ANL-01 — Comparación y planificación offline de geometría y tiempos

- **Preparador desde postura actual, 11-09-2026 Europe/Madrid — IMPLEMENTADO
  Y PROBADO; recuperación física H03 NO resuelta.** Nuevo PC
  `scripts/teleoperation/cruzr_prepare_recovery.py` y `test_prepare_recovery.py`.
  Usa captura pasiva existente y dos JointState; evita dependencia de PICO y
  conserva cada articulación medida. Sin --run/transporte de movimiento o
  modificación de robot/protecciones. Prueba live inicial detectó signos de
  motores distintos del URDF; descartado su falso START_OUTSIDE_LIMITS.
  Corrección: sólo JointState canónico para planificar, motores para salud.
  Diez pruebas pasan; live corregido101muestras válidas, control libre/paros0/0,
  START_GEOMETRY_REJECTED/54avisos. No significa contacto físico ni permiso.
  Dependencias: venv general-home existente, ninguna instalación nueva.
  Fuente reproducible, aplicación sólo PC, verificación y límites en
  [recuperación sin teleoperación](teleoperation/CRUZR_RECUPERACION_SIN_TELEOPERACION.md).
  Docs global/PICO/ensayos/README/índice actualizados: el operador no dispone
  de teleoperación; la petición de preparar PICO queda retirada.
  Fuentes anteriores/posteriores, hashes, pruebas, lecturas y resultados:
  `../Humanoide-vla-evidence/20260911T092355Z_RECOVERY-FROM-CURRENT/`.
  Reversión: retirar esos dos archivos nuevos/guía y restaurar selectivamente
  sus notas desde `before/`, preservando otros cambios. No existe rollback
  remoto ni tarea instalada/cargada; no restaurar el prototipo de signos erróneos.

- **H03, 11-09-2026 Europe/Madrid — lectura y análisis, SIN movimiento.**
  Capturada postura asimétrica real, sana e inmóvil; no es una referencia PICO.
  Candidato de HOME interno: mínimo nominal36,599mm abrazadera derecha–codo,
  sin separación demostrada al aplicar5° independientes (resto−8,330mm).
  Modelo completo START_GEOMETRY_REJECTED/54avisos; no contactos reales
  demostrados. No se alteran márgenes, geometría, restricciones o ejecutores.
  Cambios PC: fuentes global/PICO, guía de ensayos e índice; ninguna dependencia
  nueva. Consultas robot de lectura, sin cambio remoto que activar/restaurar.
  Evidencia, programa PC/argumentos, fuentes, resultados y backups documentales:
  `../Humanoide-vla-evidence/20260911T085902Z_H03-ASYMMETRIC-READONLY/`.
  Reproducción, alcance y recuperación solicitada:
  [H03](teleoperation/CRUZR_HOME_ENSAYOS_SUPERVISADOS.md).
  Reversión: documentos selectivos desde `before/`, sin borrar otros cambios.

- **H02, 11-09-2026:** segundo ensayo supervisado registrado, ahora desde
  `pico_body_zero` con perfil4×. Resultado y reproducción en MOT-02 y
  [ensayos supervisados](teleoperation/CRUZR_HOME_ENSAYOS_SUPERVISADOS.md).
  Cambios PC: guía de ensayos, fuente global/PICO, guía de captura e índice.
  Ningún cambio de dependencias, geometría, criterios de aceptación o ejecutor.
  Backup previo/fuentes posteriores/hashes y evidencia:
  `../Humanoide-vla-evidence/20260911T084247Z_H02-PICO-SUPERVISED/`.
  La captura está validada para este movimiento; no mide una cota de parada.

- **Ensayo H01, 11-09-2026 Europe/Madrid — EJECUTADO; operador confirma
  «suave sin contacto». H01 cerrado para el caso ensayado.** Una acción `cruzr/home` sobre Motion `.11.2`, contenedor
  `walker-motion.manipulation_robot_app-1`, v0.2.0. Desde HOME medido, abrazaderas
  vacías y condiciones confirmadas, apertura/cierre de brazos bajos con XML
  `/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/cruzr/home.xml`
  SHA `05174d2b4cf003b9b1c5274cd445b0d4faefe4276c5fbe8e59e68e6b64ee8cbe`.
  Fuente intacta `scripts/teleoperation/tasks/cruzr_internal_home_open_v3_20s.xml`.
  Instalado y ejecutado; Motion SUCCEED/4, HOME final 0,00278034 rad máximo,
  velocidad0; 2.103 muestras válidas, ningún fault/deshabilitado. No frenado
  medido ni aprobación general. Captura pasiva validada durante movimiento.
  Sin instalación, recarga, reinicio ni modificación persistente remota.
  Dependencias y modelo sin cambios; no hay restauración remota pendiente.
  Antes del envío se corrigió un lector auxiliar YAML tras abortar con cero
  órdenes; evidencia fallida preservada. Fuente reproducible, controles previos,
  comando exacto, alcance y reanudación en
  [CRUZR_HOME_ENSAYOS_SUPERVISADOS.md](teleoperation/CRUZR_HOME_ENSAYOS_SUPERVISADOS.md).
  Cambios PC: ese documento y actualización de índice/SOT global/PICO/captura.
  Cierre observacional posterior: «suave sin contacto», sin nuevas órdenes.
  Backup y registro de esa confirmación:
  `../Humanoide-vla-evidence/20260911T084056Z_H01-OPERATOR-CONFIRMATION/`.
  Evidencia, fuentes, comandos, hashes y backup de documentos:
  `../Humanoide-vla-evidence/20260911T082510Z_SUPERVISED-HOME-PREPARATION/`.
  Reversión documental: restauración selectiva desde `before/`, preservando
  modificaciones anteriores y posteriores; conservar el registro del ensayo.
  Después de firmware, repetir descubrimiento/compatibilidad y gates; no
  reproducir automáticamente el movimiento ni tomar esta evidencia por vigente.

- **Interfaces y bucle nativo, 11-09-2026 Europe/Madrid — VERIFICADO offline;
  punto 1 de calificación NO CERRADO.** Destino PC `scripts/teleoperation/`:
  modificación de `audit_home_interfaces.py` y `test_home_interfaces.py`;
  nuevos `general_home/contact_witnesses.py`, `general_home/native_collision_policy.py`,
  `audit_home_interface_sweeps.py`, `audit_native_collision_policy.py`,
  `test_interface_sweeps.py`, `test_native_collision_policy.py`.
  Objetivo: comprobar si interfaces de reposo justifican excepciones generales.
  Corregidos puntos FCL fuera de la intersección; reconstrucción sobre ambos
  triángulos a 10 nm. Contraejemplos CAD: 8 en dominio URDF y 4 en ±0,5 rad;
  primeras cifras 13/9 DESCARTADAS por testigos sin verificar. 64 pruebas pasan,
  ninguna omitida. El modelo mantiene 45 formas/982 pares/2 mm/54 rechazos.
  Bucle revisado de `librobot.so` SHA `7322b075…` interpreta grupos sintéticos,
  distancia sustituida y llamadas interceptadas; no es el contrato de control
  activo ni autoriza excepciones de CAD. Datos mecánicos pendientes: zonas
  permitidas por interfaz y dominio, o modelo de colisión validado equivalente.
  Dependencias: venv ANL-01 existente; ninguna instalación/servicio/permiso nuevo.
  Aplicación/activación: sólo comandos PC de la
  [receta versionada](teleoperation/CRUZR_HOME_GEOMETRIA_Y_MOTION.md#resultado-de-la-revisión-de-interfaces-11-09-2026).
  Se descubrieron contenedores y archivaron bibliotecas desde Motion mediante
  lecturas; manifiesto identifica host, contenedor, ruta, fecha y SHA completo.
  No movimiento, recarga, reinicio, cambio de modo ni mutación remota.
  Evidencia/backup de trabajo previo, fuentes posteriores y hashes:
  `../Humanoide-vla-evidence/20260911T075508Z_HOME-INTERFACE-CLOSURE/`.
  Verificación: cinco suites, auditoría de interfaces, dos barridos y traza nativa.
  Reversión: restaurar selectivamente los dos archivos modificados de `before/`,
  retirar los seis nuevos si no tienen consumidores y actualizar documentos,
  preservando trabajo previo/posterior. La reversión recuperaría testigos FCL
  no verificados: no usarlos como zonas de exclusión. No hay rollback remoto.
  Tras firmware/CAD nuevo, volver a archivar/revisar: nunca ampliar la lista de
  hashes para aceptar una build sin inspección. No instalar las bibliotecas
  privadas ni estos auditores sobre Motion.

- **Interfaces y prismas del elevador, 11-09-2026 Europe/Madrid — VERIFICADO offline:**
  objetivo: conservar huecos entre componentes sin perder volumen del CAD e
  identificar la causa de cada rechazo. Destino PC, `scripts/teleoperation/`:
  modificación de `general_home/geometry.py`; nuevos `general_home/prism_enclosure.py`,
  `audit_home_interfaces.py`, `test_prism_enclosure.py`, `test_home_interfaces.py`.
  Venv existente, sin dependencias/servicios/permisos nuevos. No hay instalación
  ni activación en Motion. Cinco prismas abiertos reconocidos en el tercer tramo
  del elevador; envolventes generales11→10. Conserva45formas/982pares/margen2mm,
  sin exenciones nuevas. Persisten54avisos en las tres referencias;52pruebas pasan.
  Diagnóstico diferencia superficies originales de volumen/margen y limita
  explícitamente sus testigos; no autoriza trayectorias ni mejoras de velocidad.
  [Receta versionada, resultados y límites](teleoperation/CRUZR_HOME_GEOMETRIA_Y_MOTION.md#refinamiento-del-elevador-y-diagnóstico-de-interfaces-11-09-2026).
  Aplicación: fuentes PC y comandos offline de la receta. Verificación: auditoría
  completa y tres suites, fuentes/CAD con hashes antes/después. Evidencia,
  backups de archivos previamente no incluidos en commit y fuentes posteriores:
  `../Humanoide-vla-evidence/20260911T073642Z_HOME-INTERFACE-REFINEMENT/`.
  Reversión: restaurar sólo el cambio de `geometry.py` desde `before/`, retirar
  los cuatro archivos nuevos si ya no tienen consumidores y ajustar documentos,
  preservando trabajo previo/posterior. No hay rollback remoto: no se conectó
  al robot. Tras firmware/CAD nuevos, volver a auditar y comparar hashes;
  estos resultados no se heredan a otra geometría ni constituyen calibración.

- **Cobertura rígida muñeca/útil, 11-09-2026 Europe/Madrid — VERIFICADA offline:**
  objetivo: comprobar unión de formas nativas y conservar todo el CAD. Destino
  sólo PC, bajo `scripts/teleoperation/`: nuevos `audit_wrist_clamp_union.py`,
  `general_home/native_arm_frames.py`, `general_home/union_coverage.py`,
  `test_wrist_clamp_union.py`, `render_wrist_clamp_review.py` y
  `general_home/wrist_clamp_review.html`. Venv ANL-01 existente, sin dependencias,
  servicios, permisos o activación nuevos. Sin instalación/recarga remota.
  Ocho pruebas pasan; cobertura de frontera/volumen en CAD completa con complemento
  conservador. Formas nativas solas dejan vértices fuera hasta8,64mm. No cambia
  `RobotGeometry`, pares, márgenes, XML ni calificación física. Visor Chromium
  comprobado en ambos lados y tamaños de pantalla, sin errores JS/WebGL.
  [Receta reproducible y límites](teleoperation/CRUZR_HOME_GEOMETRIA_Y_MOTION.md#unión-muñeca-y-abrazadera-11-09-2026).
  Lectura remota y copias privadas de configuración/bibliotecas; ninguna mutación
  ni movimiento. Modelo nominal de archivos contrastado; memoria calibrada y
  montaje físico PENDIENTES. Evidencia/backups/fuentes completas/checksums:
  `../Humanoide-vla-evidence/20260911T070352Z_WRIST-CLAMP-UNION/`.
  Aplicación: ejecutar auditor y renderizador con archivos privados según receta;
  no copiar el complemento a Motion. Reversión: retirar sólo esos seis archivos
  nuevos y su documentación, preservando cambios previos/posteriores; `before/`
  contiene los documentos previos. No hay rollback remoto. Después de firmware,
  volver a archivar configuración/URDF/bibliotecas y revisar cambios; el emulador
  rechaza hashes desconocidos. No ampliar hashes permitidos sin auditar la build.

- **Auditoría nativa, 11-09-2026 Europe/Madrid — VERIFICADA offline:**
  objetivo: contrastar interfaces del CAD con formas del proveedor antes de
  sustituir geometría. Fuentes nuevas PC bajo `scripts/teleoperation/`:
  `audit_native_collision_geometry.py`, `general_home/native_geometry.py` y
  `test_native_geometry.py`. Sin dependencias nuevas: venv ANL-01 existente.
  No instalación/activación remota; el comando trabaja sólo con archivos locales.
  Cinco pruebas pasan, incluida extracción de tres bibliotecas con hashes fijados
  y comparación de constantes de abrazadera repetidas. La S2Clamp aislada deja
  vértices del CAD fuera44,396mm L/44,395mm R bajo correspondencia URDF y anclaje
  supuesto; falta la unión muñeca+abrazadera y la selección/anclaje reales.
  No cambia modelo operativo, pares, márgenes, XML ni aprobaciones físicas.
  [Receta, hashes runtime y límites](teleoperation/CRUZR_HOME_GEOMETRIA_Y_MOTION.md#extracción-de-las-formas-nativas-11-09-2026).
  Evidencia privada/backup/fuentes posteriores/checksums:
  `../Humanoide-vla-evidence/20260911T063949Z_NATIVE-COLLISION-INTERFACES/`.
  Reversión: retirar sólo esos tres archivos nuevos y sus entradas documentales,
  conservando cambios ajenos/posteriores; `before/` guarda los documentos previos.
  No hay rollback remoto. Tras firmware, copiar bibliotecas de nuevo y contrastar
  hashes; el auditor rechaza builds no revisadas. No cambiar hashes para forzar
  aceptación ni reinstalar defaults extraídos sobre configuración activa.

- **Corrección del lector, 11-09-2026 — VERIFICADA en HOME real:**
  `general_home/passive_trace_remote.py` usa ahora JSON nativo multilínea;
  `--print-compact` produce texto no JSON y se retira. Enmarca objetos antes
  de parsear, evitando reparsar cada línea; termina un objeto en curso durante
  un máximo de0,5s al cierre y rechaza truncados/estancados. Quince pruebas
  de `test_home_motion_trace.py` pasan, con subprocesses ficticios de corte y
  timeout. Captura real en HOME:252 muestras articulares, ambos paros0, sin
  errores de lectura/análisis; hueco máximo22,875ms. La captura previa del
  arranque falló y no acredita seguimiento o frenado. Se conservan los intentos.
  Destino sólo PC, sin nuevas dependencias ni instalaciones/configuración
  remotas. El arranque CC llegó a HOME tras liberación humana supervisada,
  sin comandos de movimiento del agente; confirmación visual final pendiente.
  Fuentes, hashes, backup/rollback selectivo en
  `../Humanoide-vla-evidence/20260911T062619Z_BOOT-AFTER-CONFIRMATION/`:
  restaurar sólo lector/pruebas desde `before/` si se retira la corrección;
  las versiones anteriores no sirven para medir movimiento nativo. Preservar
  documentos históricos y cambios posteriores. No hay rollback remoto.
  [Receta actualizada](teleoperation/CRUZR_HOME_CAPTURA_Y_PROGRESO_INDEPENDIENTE.md).
- **Ampliación 11-09-2026, Europe/Madrid — VERIFICADA local y lectura de paros;
  ejecución física PENDIENTE.** Objetivo: comprobar progreso independiente de
  ejes y recoger evidencia sin mover. Fuentes PC: `cruzr_plan_home.py`,
  `general_home/planner.py`, `capture_home_motion_trace.py`,
  `analyze_home_motion_trace.py`, `general_home/passive_trace_remote.py`,
  `general_home/trace_analysis.py` y pruebas `test_general_home.py` /
  `test_home_motion_trace.py`, todas bajo `scripts/teleoperation/`.
  [Receta y alcance](teleoperation/CRUZR_HOME_CAPTURA_Y_PROGRESO_INDEPENDIENTE.md).
- **Destino/dependencias/activación:** sólo archivos PC; no hay nuevas
  dependencias, cambios de permisos de sistema, servicios o autoarranque.
  Planificador usa el venv previo. Lector/analizador usan stdlib; captura
  requiere SSH privado PC-03 y contenedores descubiertos con ROSA/ROS 2.
  El lector se transmite por stdin a Python del host Motion y crea únicamente
  suscripciones temporales, limitadas dentro de cada contenedor. Sin instalación
  remota ni acoplamiento a los mandos. Capturar no inicia ni detiene acciones.
- **Verificación y runtime observado:** 90 pruebas offline pasan; auditoría
  completa conserva 54 conflictos por referencia y once envolventes. Captura
  de ocho segundos: principal `1`, servo `0`, sin muestras articulares; rechazo
  correcto, no se acredita seguimiento/parada. Primer intento ROSA en paros
  falló; corregido a ROS 2 y preservada evidencia de ambos intentos.
  Control Center de este arranque llegó a `WaitEStopRelease`. Se copiaron nueve
  archivos runtime; el perfil JSON/MetaClamp deshabilita autocolisión/anomalías
  y no se usó como adaptador. Sin movimiento, cambio de modo, reinicio, recarga,
  rearme, instalación o modificación de configuración remota. MOT-01/MOT-02
  siguen intactos; no hay nuevo ejecutor físico general instalado/cargado/probado.
- **Versiones, backup, reversión y firmware:**
  `../Humanoide-vla-evidence/20260911T054510Z_GENERAL-HOME-COMPLETION/` contiene
  `before/`, `before.sha256.json`, fuentes posteriores con
  `after.sha256.json`, `runtime-manifest-complete.json` y pruebas/capturas.
  Los hashes de fuentes locales incluyen el trabajo sin commit. Retirar
  selectivamente los cinco archivos nuevos de captura/análisis/pruebas y
  restaurar sólo los cambios de esta ampliación en planificador/docs desde
  `before/`, preservando todo cambio ajeno/posterior. No hay rollback remoto;
  los lectores caducan solos y no son servicios. Tras firmware, repetir
  descubrimiento, contrastar `.msg`, IDs, significado de `cmd_pos`, clientes
  y formatos con una captura pasiva antes de interpretar datos nuevos.
  Conservar runtime/CAD/evidencia privada fuera de Git. No reutilizar un
  informe como autorización ni confundir captura con mecanismo de parada.
- **Ampliación 10-09-2026, Europe/Madrid — VERIFICADA offline; ejecución física
  PENDIENTE:** corrección topológica exacta de dos piezas y unión numérica acotada
  a 10 nm en otras cinco, conservando todos los triángulos y descontando el error
  de las distancias. Once envolventes restantes, 54 pares de conflicto/margen
  conservados por referencia (30 invariantes condicionados y 24 móviles).
  Nuevo visor `render_home_geometry_review.py`/`general_home/geometry_review.html`.
  `audit_motion_interpolation.py` y `general_home/native_spline.py` contrastan
  1.312 casos del binario numérico real mediante emulación, sin `dlopen` ni ROS;
  `audit_home_runtime_contract.py` registra límites y conversiones de marcos
  en archivos archivados. Nueva temporización opcional offline `cubic-rest`.
- **Destino/instalación de esta ampliación:** sólo fuentes y documentación del
  PC y `unicorn==2.1.4` en `.venv/general-home`, fijado en `requirements.txt`.
  Son nueve dependencias fijadas en total. No se modifica Python del sistema,
  SDK/CAD original, MOT-01/MOT-02 ni ningún archivo del robot. Las consultas SSH
  copiaron configuración/bibliotecas a evidencia privada por Wi-Fi. Paro leído
  en `1`; suscripción de actuadores sin muestra y consultas finales con timeout
  SSH. No se ejecutó movimiento, cambio de modo, recarga ni reinicio.
- **Verificación de esta ampliación:** 37 pruebas del paquete + 38 regresiones
  pasan. Auditoría numérica: error máximo 2,67e-15 rad, pero no prueba de despacho,
  seguimiento, frenado ni estabilidad. Visor comprobado en Chrome: vista de
  robot completo, selección HOME/muñeca y cambio de geometría, sin errores WebGL.
  [Resultado completo y recetas](teleoperation/CRUZR_HOME_GEOMETRIA_Y_MOTION.md).
- **Backup/rollback/firmware:**
  `../Humanoide-vla-evidence/20260910T142312Z_HOME-GEOMETRY-MOTION-QUALIFICATION/`,
  `before/` y `before.sha256.json`, runtime copiado con manifiestos, auditorías,
  HTML privado y `verification-final.json`. Para retirar sólo esta ampliación,
  restaurar selectivamente los archivos existentes desde `before/`, retirar
  los tres auditores/visor y módulos nuevos de esta ampliación y recrear el venv
  con los requisitos anteriores; preservar el planificador previo y cambios
  posteriores. No hay rollback remoto. Tras firmware, volver a copiar/auditar
  configuraciones, marcos, símbolos y hash del interpolador: un hash distinto
  se rechaza. Nunca ampliar la lista de hashes sin revisar/emular el nuevo código.
  Conservar CAD, bibliotecas copiadas y HTML fuera de Git en backup privado.
- **Planificador general implementado, VERIFICADO offline 10-09-2026,
  Europe/Madrid; integración física PENDIENTE.** Objetivo: buscar desde una
  postura20D asimétrica, sin forzar PICO ni una apertura fija. Fuentes:
  [`cruzr_plan_home.py`](../scripts/teleoperation/cruzr_plan_home.py),
  `scripts/teleoperation/general_home/`, `test_general_home.py` y los dos
  ejemplos `config/examples/cruzr_general_home_*.example.json`.
- **Destino y dependencias PC:** nuevo entorno aislado
  `/home/lacuna/proyectos/Robots/Humanoide/.venv/general-home`, Python3.12.3;
  Cython3.3.0, networkx3.6.1, NumPy2.5.3, python-fcl0.7.0.11, PyYAML6.0.3,
  rtree1.4.1, SciPy1.18.1 y trimesh5.1.0. Versiones fijadas y receta reproducible
  de venv/pip en [README](../scripts/teleoperation/general_home/README.md).
  Usa el paquete original splint local, ignorado por Git, sin modificarlo.
  No altera Python del sistema ni instala paquetes en Motion/Vision.
- **Verificación/estado:**28pruebas funcionales y38regresiones previas pasan;
  auditoría de45geometrías/982pares
  internos. Conserva ocho pares rígidos fuera del chequeo interno, mantiene sus
  piezas contra el resto. El modelo devuelve54conflictos de geometría/margen
  en cada referenciaHOME/PICO, con18envolventes de mallas abiertas. La escena
  sintética da73conflictos enPICO; no representa el taller. Se rechaza la
  planificación desde esa entrada. No son contactos físicos demostrados.
  Los informes tienen hashes completos de código/entradas/modelo y versiones.
- **Activación pendiente:** no existe exportación de trayectoria/ejecutor
  físico general. Resolver modelo y montaje, Motion/interpolación y supervisor,
  dinámica/estabilidad/parada, escena actual e integración HOME del arranque.
  No cambia MOT-01/MOT-02 ni el tiempo operativo20s. Cero SSH/ROS/movimientos,
  instalaciones remotas, recargas o reinicios en esta implementación.
- **Backup/evidencia/reversión de esta ampliación:**
  `../Humanoide-vla-evidence/20260910T134348Z_GENERAL-HOME-IMPLEMENTATION/`,
  con documentos anteriores en `before/`, `model-audit-final.json` y
  `pico-example-plan.json`. No existían el paquete, los ejemplos ni este venv.
  Para retirar: eliminar selectivamente esas fuentes nuevas y sólo
  `.venv/general-home`, restaurar sus entradas documentales preservando cambios
  posteriores. No requiere rollback en el robot. Tras firmware, conservar
  fuentes/pins y volver a contrastar modelo y contrato; no restaurar un informe
  anterior como permiso de movimiento.
- **Revisión general VERIFICADA offline 10-09-2026:**
  [HOME desde posturas generales](teleoperation/CRUZR_HOME_DESDE_POSTURA_GENERAL.md).
  Estudio splint/4.000 posturas, límites, cobertura y uniones rígidas; arquitectura
  propuesta para planificación, escena, validación y ejecución. No implementa
  todavía un ejecutor general ni altera MOT-01/MOT-02. Evidencia y reproducción
  en `../Humanoide-vla-evidence/20260910T124156Z_GENERAL-HOME-3D-REVIEW/`.
  Respaldo documental en `before/`; reversión sólo documental selectiva.
  No requiere instalar ni recargar nada para reproducir esta revisión.
- **Ampliación VERIFICADA local 10-09-2026:**
  [`plan_clamp_home_adaptive.py`](../scripts/teleoperation/plan_clamp_home_adaptive.py)
  y `test_plan_clamp_home_adaptive.py` implementan apertura según postura y lado,
  etapas omitidas sólo por igualdad y tiempos según desplazamiento. Ocho pruebas
  pasan; siete casos nominales auditados. No está integrado ni instalado en HOME
  automático. Error5°/parada/interpolación dejan la activación física pendiente.
  [Detalle](teleoperation/CRUZR_HOME_ADAPTATIVO.md), backup y evidencia:
  `../Humanoide-vla-evidence/20260910T120838Z_ADAPTIVE-HOME/`.
  Para reproducir se usa el mismo snapshot explícito del08-09; para retirarlo,
  quitar esas dos fuentes nuevas sin revertir rutas Motion.
- **VERIFICADO local 10-09-2026; sin activar candidatas.** Compara rutas PICO/HOME
  actuales y alternativas sin emitir XML ni comandos de robot. Perfil vigente20s.
- **Fuentes:**
  [`review_clamp_trajectory_optimization.py`](../scripts/teleoperation/review_clamp_trajectory_optimization.py)
  y su prueba `test_review_clamp_trajectory_optimization.py`; usa NumPy ya
  disponible, modelos de trayectoria existentes y snapshots explícitos.
- **Resultado:** candidato prioritario20→16,25s cuando cuerpo ya está a cero;
  exige comprobar asentamiento real. No hay aprobación física ni cota de parada.
  Ocho pruebas pasan; fuentes operativas conservan hashes previos.
- **Reproducir y límites:** [informe](reports/2026-09-10_OPTIMIZACION_TRAYECTORIAS_ABRAZADERAS.md).
  Evidencia/modelos/hashes:
  `../Humanoide-vla-evidence/20260910T113554Z_CLAMP-TRAJECTORY-OPTIMIZATION/` y
  snapshot original del08-09 indicado allí. Conservarlos fuera de una actualización.
- **Activación/reversión:** no requiere despliegue. Para retirar el comparador,
  quitar selectivamente sus fuentes nuevas y referencias; no revertir archivos
  del robot ni la corrección independiente del preflight MOT-01.

### MOT-03 — PICO limitado a brazos

- **VERIFICADO histórico 2026-08-27:** `clamp, waist_mode=0, leg_mode=0`, torso
  quieto. Fuente/receta [`install_cruzr_pico_arms_only.sh`](../scripts/teleoperation/install_cruzr_pico_arms_only.sh)
  `--check`, `--install`, `--rollback`; rechaza hashes desconocidos.
- **Destino Motion:**
  `/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config/meta_teleoperation/cruzr_clamp_pico_tele.yaml`.
  Vendor `5f08b30c…3fc62a` → overlay `4e8d79a4…117a44`; hashes completos
  protegidos en el instalador. Sólo cambian modos de cintura/piernas.
- **Backup:** `/home/walker/.local/share/cruzr-pico-arms-only/`, vendor y overlay.
  Restaurar YAML vendor retira la limitación; no hacerlo durante teleoperación.
- **Activación/verificación:** copiar YAML no demuestra carga. Revisar modos
  del nuevo log y exclusividad de control. La antigua receta de cambio
  `teleop→auto_task→teleop` puede iniciar HOME: **no ejecutarla automáticamente
  tras restaurar**, especialmente con brazos elevados. Seguir guía actual.
- **Detalle:** [fuente PICO](teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md).

### MOT-04 — READY, recovery y tareas auxiliares

- **2026-09-14 — uso de tarea existente, sin adaptación persistente:**
  una preparación de cabeza `cruzr/move_head_lower`, SUCCEED/status4; final
  pitch−0,430665rad, velocidades0, resto de ángulos sin cambio entre extremos.
  Cabeza observación y brazos/cuerpo HOME; no HOME20D completo. Captura pasiva
  RGB/nube/TF nueva, escena parcial observada. No instalar/reaplicar postura
  transitoria tras firmware. Fuente/receta, objetivo, destino, hashes, evidencia
  y continuidad: [observación actual](vla/OBSERVACION_ENTRY_20260914.md).

- **2026-09-11, Europe/Madrid — prueba temporal de observación VERIFICADA:**
  única acción instalada `cruzr/move_head_lower`, yaw0/pitch−0,43rad en2s,
  SHA `f3a73626f97b471d4a0a03c98c24de32243651116c497328e69b5ddc57ea46c1`.
  Uso reproducible: `cruzr_blue_workbin_cycle.sh --check` y, tras condiciones
  físicas actuales, `--prepare-vision --yes`. Acción SUCCEED/4, cabeza final
  −0,430473rad e inmóvil; otros ángulos sin cambio entre extremos. Caja completa
  en RGB VLA; detector de lectura aporta pose en cámara, no aprobación de avance.
  Destino: Motion, XML existente bajo config/cruzr/move_head_lower.xml del
  paquete manipulation_task_manager; ninguna modificación de archivo/servicio.
  Estado final cabeza en observación, cuerpo/brazos HOME; no HOME20D completo.
  Restauración no ordenada: conservar observación; no usar HOME genérico ante
  la mesa. Estado inicial/backup documental, fuentes y hashes en
  `../Humanoide-vla-evidence/20260911T111951Z_VLA-OBSERVATION-HEAD/`.
  No hubo instalación/recarga/reinicio ni inferencia/publicación VLA. Los
  mecanismos y dependencias del wrapper existente se mantienen.

- **VERIFICADO histórico:** corrección de cintura de dos valores a uno para
  S2 en READY y recovery; otras tareas de pruebas registradas individualmente.
- **Fuentes:** [`scripts/vla/runtime/tasks/`](../scripts/vla/runtime/tasks/),
  [`patch_vla_ready_s2_waist_e6_0p.sh`](../scripts/vla/patch_vla_ready_s2_waist_e6_0p.sh)
  y demás instaladores de [la guía VLA](guides/CRUZR_S2_VLA_SAFE_ENABLEMENT.md).
  READY usa `s2_vla_e6_0_ready_s2.xml`, hash `c767f739…e2a9b2`;
  destino `config/s2_bio_vla/s2_vla_pick_large_teleop_ready.xml` del gestor.
- **Reaplicar:** inventariar XML y entradas reales a partir del respaldo.
  Revisar primero `--help`/`--check` del instalador de cada tarea y su guía.
  El parche READY tiene requisitos de HOME y paros liberados: no incluirlo
  en un bloque genérico de instalación bajo E-stop. Un hash de task_list
  distinto exige revisión, no anular la comprobación.
- **Backup:** `/home/walker/cruzr-vla/backups/`, incluidos E6.0P/E6.0Q;
  copia de ambos directorios de configuración de manipulación en el respaldo.
  Comparar/revertir sólo la tarea afectada. Ni el fichero presente ni una
  prueba antigua autorizan ejecutar todos los árboles recuperados.

### MOT-05 — HOME original de fábrica como `cruzr/originalhome`

- **2026-09-18 Europe/Madrid — PREPARADO en PC; instalación en robot PENDIENTE.**
  Añade el HOME original UBTECH como tarea adicional; `cruzr/home` sigue siendo
  el HOME propio (body-first v4, SHA `e3d0656424a3611d89262ae645f127d975920fd09c437f9ef9c07725d69dc49c`,
  comprobado por lectura el 18-09). No modifica `home.xml`.
- **Fuente:** [`cruzr_home_original_factory.xml`](../scripts/teleoperation/tasks/cruzr_home_original_factory.xml),
  SHA `50d819d6d6190280c6efee1dc275877362c3f7c807ec733fbc3c7ed217daed88`, idéntico
  a `scripts/hands/factory_tasks.sha256` y a
  `../Humanoide-vla-evidence/20260910T095255Z_HOME-ROUTE-REVIEW/home-original.xml`.
  Cabeza, elevador, cintura y ambos brazos a cero en paralelo, 6 s: es la
  trayectoria directa que acercó los brazos al cuerpo (ver MOT-01).
- **Destino:** Motion, `walker-motion.manipulation_robot_app-1`:
  `config/cruzr/originalhome.xml` y entrada `cruzr_originalhome` en
  `config/task_list.yaml` (mismos `json_args` que `cruzr_home`: `TimeRatio 0.5`).
- **Reaplicación:** [`cruzr_install_original_home.sh`](../scripts/teleoperation/cruzr_install_original_home.sh)
  `--check` → `--status` → `--install` → `--reload`. Install y reload exigen
  E-stop accionado, cargador desconectado y confirmación escrita en terminal.
  El script nunca envía la tarea.
- **Verificación:** `--status` debe dar `INSTALL_STATE=exact` y
  `TASK_PROCESS_ORDER=after-task-list`. Ejecución física: no ensayada.
- **Dependencias:** la recarga cambia el hash de `task_list.yaml` y la identidad
  del proceso; las etapas `entry410` cualificadas deben volver a cualificarse.
- **Backup/reversión:** `/home/walker/cruzr-owner-backups/<token>-originalhome/`
  con `task_list.yaml` anterior. Retirar sólo la entrada `cruzr_originalhome` y
  el XML, conservando entradas posteriores, y recargar bajo E-stop.

### PC-01 — Red de trabajo

- **VERIFICADO histórico 2026-08-26:** perfil Ethernet `cruzr-s2`, `eno1`,
  `192.168.11.250/24`, autonegociación 1 Gb/s full duplex, never-default.
  Wi-Fi USB `wlx80afcad40bd6`, perfil observado `Cruzr S2-0669 1`:
  DHCP en `.42.0/24`, ruta `.11.0/24` vía `.42.2`, never-default,
  ignore-auto-DNS y powersave deshabilitado. Internet por `wlo1`.
- **Fuente/receta y evidencia:** sección de conexión de la
  [fuente PICO](teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md).
  Guardar perfiles reales en backup privado de
  `/etc/NetworkManager/system-connections/`, rutas y salida de `nmcli`.
- **Reaplicar/verificar:** importar sólo perfiles del robot si se perdieron;
  adaptar interfaz/UUID al PC actual. Comprobar IP, ruta preferida, DHCP y
  persistencia sin alterar el perfil de Internet. No fijar la IP DHCP del
  PICO o PC basándose en una observación antigua.
- **Rollback:** perfiles anteriores privados; no publicar claves Wi-Fi.
  Los resets del adaptador Realtek son una deuda de hardware/conectividad,
  no se solucionan restaurando una trayectoria.

### PC-02 — Teleoperación, servicios y permisos

- **VERIFICADO histórico:** `ubt-controller 4.7.0`, UI `4.1.0`, XRoboToolkit
  PC Service `1.0.0.0`; control de abrazaderas y STOP oficiales.
- **Fuentes/receta:** [`install_ubt_controller_4_7.sh`](../scripts/teleoperation/install_ubt_controller_4_7.sh),
  [fuente PICO](teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md),
  [`config/systemd/`](../config/systemd/) y [`config/udev/`](../config/udev/).
  Instalador del backend `--run` requiere sus paquetes y condiciones; no
  ejecutarlo sólo por actualizar firmware del robot si el PC sigue intacto.
- **Destinos:** `/opt/ubt-controller`, `/opt/ubt-remote-control`, servicio
  `ubt-controller.service`, drop-ins `10-numeric-locale`, `20-cruzr-clamp`,
  `30-service-lifecycle`; unidad de usuario `ubt-remote-control.service`;
  `/etc/udev/rules.d/51-pico-ubt.rules` (vendor 2d40, plugdev/uaccess).
  Revisar DISPLAY/XAUTHORITY/UID de la unidad UI en otro PC.
- **Ajustes:** locale numérico C; `arm=clamp`; apagado SIGTERM/mixed/15 s;
  UI a demanda sin reinicio automático. Backend `transmit=local`,
  `signal_server=ws://192.168.11.3:4000`, `channel_name=walker28`.
- **Verificación:** versiones/hashes, `systemctl cat`, estado STOP y writers.
  **Abrir el WebSocket de controller 4.7 puede disparar START**: no usar una
  conexión de UI/cliente como consulta de sólo lectura. No arrancar UI al restaurar.
- **Backup/reversión:** `/opt/` específico, unidades/drop-ins y configuración
  del usuario en copia externa privada. Instalador conserva paquete anterior
  en Descargas; no reponer automáticamente el 5.3 parcheado retirado.

### VLA-01 — Instalación y adaptaciones S2

**Último intento TRIAL_02, 2026-09-14:** solicitud de switch_to_vla con timeout
sin acuse; cero frames. Estado efectivo del controlador PENDIENTE de consulta.
No se ejecutó recuperación automática. [Relevo y diagnóstico siguiente](vla/RELEVO_VLA_20260914.md).

**Estado vigente 2026-09-14, corrección de controlador:** el intento del operador
publicó sin seguimiento porque SDK estaba initialized y manipulación running.
El ejecutor PC ahora usa inventario ROSA nativo y switch_to_vla (sólo --run),
con feedback SDK 20D antes de publicar y seis ejes retenidos explícitamente.
Plan vigente controller-fixed-plan; no modifica XML/firmware ni reinicia.
--observe no activa controladores; el cambio y el prefijo corregidos quedan
pendientes de ensayo físico. Tras --run SDK queda activo, sin vuelta automática.
[Fuentes, evidencia, aplicación, verificación y rollback](vla/ENSAYO_MINIMO_PUNTO_VLA_ENTRY410.md).

**Corrección de ensayo mínimo 2026-09-14:** evidencias únicas sin sobrescribir,
diagnóstico de admisión y modo --observe. Nueva admisión con deriva de ruedas
acotada comprobada en vivo sin publicador; no requiere cambios robot. Plan
anterior admission-fixed-plan (sustituido); [receta](vla/ENSAYO_MINIMO_PUNTO_VLA_ENTRY410.md).

**Preparación 2026-09-14:** ejecutor PC de prefijo de un punto VLA grabado
(25 %, ≤1,396°, 4 s), comprobado localmente; sin ensayo físico aún. Sin
instalación robot. [Receta y reversión](vla/ENSAYO_MINIMO_PUNTO_VLA_ENTRY410.md).

**Continuación 2026-09-14:** sesión task 0 desde ENTRY410, seis propuestas
aceptadas en shadow; salto inicial máximo 6,1643°, sin ejecución física.
Contenedores restaurados a exited, cero publicadores. Receta, tiempos y
fuentes en [registro del ensayo](vla/ENSAYO_READY_ENTRY410_20260914.md).

**Último resultado 2026-09-14:** también READY→ENTRY410 completado físicamente
por el operador, cinco SUCCEED. Reanudar en lectura/validación shadow task 0,
sin repetir el acceso. [Evidencia](vla/ENSAYO_READY_ENTRY410_20260914.md).

**Estado actualizado 2026-09-14:** acceso al READY nuevo probado físicamente
por el operador, cinco tareas con SUCCEED. Pendiente optimizar duración
(122 s nominales). VLA físico/ENTRY no probados por este ensayo.
[Registro e identidad del script actual](vla/ENSAYO_HOME_READY_NUEVO_20260914.md).

**2026-09-14 13:50 UTC — Nuevo ciclo completo comunicado; comprobación técnica de liberación correcta.**
`cruzr_boot_ready.sh --check` devuelve0, Motion3/3, cámaras2/2 en seis topics
con marcas crecientes y RELEASE_TECHNICAL_CHECK=passed. Cero comandos de movimiento.
Sustituye WaitStartMotion como último resultado técnico de arranque. Liberación
condicionada a brazos abajo/vacíos/estables y zona libre con persona junto al paro;
puede iniciar HOME interno. Liberación y fin de arranque aún no observados.
No aprueba ENTRY410 ni verifica todavía su ejecución. Evidencia:
`../Humanoide-vla-evidence/20260914T135018Z_ENTRY410-BOOT-RELEASE/`. BOOT-01/VLA-01.


**2026-09-14 — ENTRY410 instalada en Motion y contenedor recargado una vez; paro mantenido.**
Diez XML y registro82ac1bc8…d2e434e verificados; respaldo copiado y comprobado en PC.
Principal1 verificado antes de instalar/recargar. Motion reiniciado13:32:04UTC;
hashes intactos. No se envió ninguna tarea o movimiento. Control Center queda
en WaitStartMotion y el guard responde not_initial_boot_release: NO liberar
paro ni repetir recarga. Pendiente recuperación de arranque supervisada, carga
efectiva y ensayo. VLA-01; recibos/backups en la ficha enlazada.
[Ficha vigente](vla/EJECUTOR_ENTRY410_POR_ETAPAS.md).

**2026-09-14 — Instalación ENTRY410 preparada; pendiente paro principal pulsado.**
Instalador en disco con respaldo, preservación literal de registro y reversión
ante fallo; no recarga ni ejecuta. Plan vivo sin conflictos para diez tareas,
registro c4873861…78c84f1 →82ac1bc8…d2e434e. Quince tests pasan. No se ha instalado
ni movido; requiere E-stop principal activo antes de aplicar. VLA-01.
[Ficha](vla/EJECUTOR_ENTRY410_POR_ETAPAS.md).

**2026-09-14 — Ejecutor específico ENTRY410 implementado; integración física pendiente.**
Una etapa por invocación, XML/extremos/hashes comprobados, extremo20D fresco,
trazas, cancelación solicitada ante fallo y sin reintentos. Paquete aditivo de
diez XML preparado sólo en PC. Once tests y diez etapas reales verificados.
Consulta pasiva confirma ArmTask y servidor ROS2; Motion usa SWIG sin rclpy,
por lo que admisión de archivos queda en Motion y cliente en contenedor ROS.
Sin goal enviado, instalación o recarga. Contrato de habilitación basado en
evidencia, instalación/carga y prueba del transporte/monitor aún pendientes;
no se genera autorización automática ni se usa el ejecutor040 retirado. VLA-01.
[Ficha y reproducción](vla/EJECUTOR_ENTRY410_POR_ETAPAS.md).

**2026-09-14 — Condiciones físicas confirmadas; preflight vivo correcto, ensayo ENTRY410 no ejecutado.**
Operador confirma HOME, abrazaderas vacías/sin contacto, ruedas bloqueadas,
cargador desconectado, sin otros mandos, recorrido libre y persona junto al paro.
Auditor vivo sólo lectura: batería83,1/83,6%, paros0/0, velocidad0, control exclusivo
y preflight canónico correctos. ENTRY410 sólo dispone de generador de borradores;
el ejecutor E6.1C antiguo es de ENTRY040 y su auditor está retirado con salida78.
La confirmación física no transforma esos borradores en un ejecutor validado.
No se instaló, recargó ni movió. Evidencia:
`../Humanoide-vla-evidence/20260914T125702Z_ENTRY410-PHYSICAL-PRECHECK/`.
Reproducir lectura con `scripts/vla/audit_vla_live_preflight_e6_0g.sh --check --expect-released`.
No hay cambio remoto que revertir; respaldo documental en `before/`. VLA-01.


**2026-09-14 — Reutilización de cálculos de trayectorias documentada.**
Separados métodos, pruebas reutilizables por inclusión de dominio y resultados
que dependen de escena/ejecución. Incluye matriz de cambios, flujo de reutilización,
recetas, uso de cámaras y recuperación tras firmware. Los 220 mm, ±1° y50 mm no
son valores universales; las exclusiones de ENTRY no se generalizan. Cambio sólo
documental, sin modificar modelos, filtros, tareas o robot. ANL-01 / VLA-01.
[Guía y recetas](vla/REUTILIZACION_CALCULOS_TRAYECTORIAS.md).

**2026-09-14 — Retroceso confirmado a unos 220 mm: margen externo recuperado en el modelo.**
Recalculados acceso y retorno de ENTRY410, también desde nueva lectura pasiva:
1018 pares certificados, 54 marcas internas y cero pendientes. Pasa abrazadera
derecha–tablero bajo las hipótesis ±1°/+50 mm. 361 muestras inmóviles, paros0/0,
sin errores observados. Etapas offline75 s revisadas, sin instalar o mover.
Exclusiones internas del propietario conservadas; incertidumbre física total y
ensayo de ejecución/parada siguen separados del resultado geométrico. VLA-01.
[Ficha](vla/REVISION_ENTRY410_MESA725_20260914.md).

**2026-09-14 — ENTRY410 anclada a separación medida de 160 mm desde punta del chasis.**
Modelo de escena desplazado −59,71 mm en X, conservando giros estimados por cámara.
Registrada la exclusión offline solicitada de 13 pares internos, sin alterar
protecciones ni informes brutos. Nuevo contraejemplo verificado: abrazadera
derecha frente al tablero expandido 50 mm, con error articular máximo 0,956°.
No es contacto físico observado; impide aprobar el margen externo de esta
configuración. Seis tests pasan, sin movimiento ni cambios remotos. VLA-01.
[Ficha](vla/REVISION_ENTRY410_MESA725_20260914.md).

**2026-09-14 — Diagnóstico adicional ENTRY410: no corregir la extrínseca con el residuo RGB/nube.**
El desacuerdo de 25,70 mm se conserva bajo la transformación común cámara–robot.
El plano de profundidad depende fuertemente de la región: extrapola fondos de
65,5–80,0 cm frente a los 84 cm asumidos. No se cambió calibración ni geometría.
Localizadas las 13 interfaces pendientes: diez uniones directas y tres pares
entre elevador/cintura/torso/cabeza; ninguna con abrazaderas, sin exenciones nuevas.
Nueva herramienta offline, siete tests pasan. Sin intervención remota. VLA-01.
[Diagnóstico y reproducción](vla/REVISION_ENTRY410_MESA725_20260914.md).

**2026-09-14 — ENTRY410 recalculada para la escena de 72,5 cm.**
Acceso y retorno: 1018 intervalos certificados y 54 infracciones del margen del
modelo, sin intervalos pendientes. Once separaciones continuas de superficies
CAD demostradas en el dominio410; 13 interfaces móviles con intersecciones aún
sin justificación mecánica. Preparadas cinco etapas (75 s READY→ENTRY) y sus
inversas, sólo borradores. Nueva lectura inmóvil y hashes Motion contrastados.
RGB y profundidad discrepan 25,70 mm de mediana en el tablero: registro físico,
cobertura completa y ejecución/parada siguen pendientes. 16 tests pasan.
Sin movimiento, instalación, recarga ni VLA físico. VLA-01.
[Ficha de esta revisión](vla/REVISION_ENTRY410_MESA725_20260914.md).

**2026-09-14 — Mesa ajustada por el operador a 72,5 cm; ENTRY410 se conserva.**
Confirmación «72,5, hecho»: dimensión suelo–superficie del tablero, precisión no
aportada. Perfiles offline actualizados y selección repetida para 0,725 m.
Nueva captura pasiva en Vision: RGB completo de caja/mesa y nube de 9179 puntos,
marcas imagen/nube coincidentes. No demuestra zona libre ni postura articular.
La escena cambió: revisiones geométricas con mesa de 80 cm quedan históricas;
registro y revisión de la nueva escena pendientes. No se ha movido, instalado,
recargado o cambiado ninguna protección del robot. VLA-01.
[Evidencia y reversión](vla/SELECCION_ENTRY410_20260914.md#actualización-mesa-confirmada-a-725-cm).

**2026-09-14 — ENTRY410 seleccionada como base de adaptación para mesa de 80 cm.**
Comparadas 360/380/410 con sus parquets y primeros fotogramas originales.
Posturas prácticamente equivalentes: diferencia máxima de muñeca 0,701 mm.
Apoyo de entrenamiento inferido: 64,18 / 64,17 / 72,65 cm; 410 queda más cerca
bajo hipótesis comunes, sin certificar alturas. Las tres conservan acceso y
retorno con 1018 pares certificados y 54 avisos. Selección sólo offline:
config/vla/offline/selected_entry_adaptation.json; ENTRY runtime sin cambios.
Conservar trabajo de360 como referencia, sin heredar automáticamente su validación.
Sin consulta o movimiento del robot, instalación o cambio del checkpoint. VLA-01.
[Ficha de selección](vla/SELECCION_ENTRY410_20260914.md).

**2026-09-14 — ENTRY360 por etapas y once fronteras CAD resueltas de forma continua.**
Nuevo método de órbitas resuelve lifter2/torso; las otras diez parejas sin cruce
se prueban por subdivisión angular. Permanecen trece interfaces con cruces CAD,
sin exenciones. Propuesta offline READY→360 en cinco etapas, 75 s nominales:
1018 pares certificados, mismos 54 avisos, sin timeout; incluye 90/90 contra escena.
Hashes actuales de YAML/URDF/cúbica coinciden; seis límites de cabeza/cuerpo
comprobados con ±1°. Comparar suelo/tablero en una captura da 75,47–82,11 cm:
no establece cota metrológica ni justifica recolocar la mesa. Borradores no
instalados; seguimiento, parada y correspondencia mecánica siguen pendientes.
18 tests pasan. Sin movimiento, instalación, recarga ni cambio de protecciones. VLA-01.
[Ficha y reproducción](vla/ENTRY360_ETAPAS_E_INTERFACES_20260914.md).

**2026-09-14 — Preparación de ensayo ENTRY360, no cualificado físicamente.**
PC: nuevos `prepare_entry360_trial_review.py`, su test y
`review_entry_from_passive_state.py`; ámbito sólo offline. Se corrige el texto
ENTRY440 fijado en el auditor genérico de interfaces. Revisión actual de acceso
/retorno: 1018 certificados, 54 avisos, 0 pendientes; 696 muestras de interfaces.
Dataset360 verificado; altura inferida64 cm, pendiente para mesa80 cm.
Propuesta cúbica65 s con caps de diseño no cualificados; no genera XML instalable
ni transporte de ejecución. 15 tests pasan; antiguo auditor040 conserva salida78.
Motion/Vision: lectores temporales finalizados, 354 mensajes pasivos y nueva
captura RGB/nube/TF. Sin movimiento, instalación, recarga o cambio persistente.
Fuentes, destinos, hashes, dependencias existentes, backups y reversión:
[ficha](vla/REVISION_PRUEBA_ENTRY360_20260914.md).

**2026-09-14 — Contraejemplo ENTRY440/escena50mm, sólo PC.**
Nuevos buscador/verificador `scripts/vla/search_entry_fixture_witness.py`,
explicador/vista3D `scripts/vla/explain_entry_fixture_witness.py` y test.
Selector offline `screen_entry_fixture_candidates.py`: 113 extremos revisados;
ENTRY360/380/410 pasan geometría de acceso/retorno (mismos 54 avisos), pendiente
compatibilidad con mesa de 80 cm y VLA. No se cambia candidato del ejecutor.
Dos testigos articulares dentro de ±1° recomputados con intersección del modelo;
el extremo también falla. La traslación explícita49,95mm de la caja original
reproduce contacto hipotético. No observación física ni autorización VLA.
11 tests y rechazo de postura inválida pasan. Se corrige el orden invertido de
puntos próximos FCL en el explicador comprobando pertenencia a superficies.
Sin conexión al robot, instalación, recarga ni configuración física modificada.
Fuentes, hashes, dependencias existentes, backups, estado, reproducción y
reversión: [ficha](vla/CONTRAEJEMPLO_ENTRY50_20260914.md).

**2026-09-14 — Perfil de incertidumbre de escena y comprobaciones pasivas.**
PC: perfil `config/vla/offline/entry_scene_uncertainty_review.json` con 50 mm
provisionales, ampliación de revisores, FK relativo, comparación de planos y
capturador RGB/nube/TF con marcas. Sin aplicar al ejecutor: separación mínima
2 mm conservada, aprobación física falsa. 11 tests y 192 comparaciones pasan.
Motion/Vision: sólo suscripciones temporales, finalizadas; 356 muestras válidas
y nueva captura sincronizada por marcas. No movimiento, instalación o recarga.
Correspondencia de escena y parada aún no validadas; no se habilita VLA.
Fuentes, destinos, hashes, backups, estado y restauración:
[ficha](vla/CIERRE_Y_TOLERANCIAS_ENTRY_20260914.md).

**2026-09-14 — Interpretación de interfaces ENTRY440, sólo PC.**
Nuevos `audit_entry_route_interfaces.py`, `prove_entry_interface_boundaries.py`
y sus tests. Clasificación de 54 avisos: 30 invariantes, 10 fronteras separadas
continuamente, 13 cruces CAD de referencias y 1 prueba continua pendiente.
696 muestras, sin testigo nuevo fuera de cajas de referencia; no prueba física.
Seis tests pasan. Sin cambios de pares, geometría, margen ni instalación remota.
Destino, fuentes, dependencias existentes, backups, hashes, reproducción y
reversión: [ficha](vla/INTERFACES_ENTRY440_20260914.md). VLA físico sigue pendiente.

**2026-09-14 — Subdivisión de incertidumbre y validación geométrica ENTRY440.**
Módulo/test PC nuevos `entry_subdivided_scene_bounds.py`, revisores offline
ampliados con `--uncertainty-partition-nodes`; ninguna instalación en robot.
Acceso y retorno vacío: 1018 certificados, 54 avisos nominales, 0 pendientes,
sin cambiar proxy, ±1° o margen 2 mm. Treinta tests pasan. Aprobación física
pendiente por registro, interfaces y seguimiento/parada; no se habilita VLA.
Fuentes, destino, backups, hashes, aplicación y reversión en
[ficha de validación](vla/VALIDACION_ENTRY440_20260914.md). Sin cambios remotos.

**2026-09-14 — Ampliación offline del análisis ENTRY, no instalada en robot.**
Se añaden ajuste visual de útiles, revisión de acceso/retorno con hipótesis de
escena, cotas direccionales con resto de segundo orden y recomprobador de
contraejemplos. Revisor existente ampliado con `--directional-bounds` explícito.
ENTRY372 tiene intersección demostrada en el modelo a <1°; alternativa ENTRY440
conserva un par de escena sin demostrar y 54 interfaces nominales. No aprobado.
28 tests y 3216 comparaciones pasan. No movimiento, consultas, instalación,
recarga o nuevas dependencias. Fuentes, destino PC, hashes, backups, aplicación,
reversión y evidencia: [ficha detallada](vla/CIERRE_GEOMETRICO_ENTRY_20260914.md).
Registro visual, interfaces y seguimiento/parada permanecen pendientes;
no se cambia el estado de habilitación física del VLA.

- **2026-09-14 — comparación de superficie visible, PC:** nuevos
  `scripts/vla/inspect_entry_table_observation.py` y su test. Lectura offline
  de nube/regiones, ajuste robusto y comparación con proxy, sin sustituir escena
  ni límites de error. Tres tests pasan. Identificada naturaleza horizontal del
  ejemplo2,107mm. No consultas/cambios remotos. Fuente, dependencias, evidencia,
  hashes, receta y rollback: [registro de mesa](vla/REGISTRO_MESA_ENTRY_20260914.md).
  Estado: análisis parcial observado; calibración y ENTRY PENDIENTES.

- **2026-09-14 — uso de tarea existente, sin adaptación persistente:**
  una preparación de cabeza `cruzr/move_head_lower`, SUCCEED/status4; final
  pitch−0,430665rad, velocidades0, resto de ángulos sin cambio entre extremos.
  Cabeza observación y brazos/cuerpo HOME; no HOME20D completo. Captura pasiva
  RGB/nube/TF nueva, escena parcial observada. No instalar/reaplicar postura
  transitoria tras firmware. Fuente/receta, objetivo, destino, hashes, evidencia
  y continuidad: [observación actual](vla/OBSERVACION_ENTRY_20260914.md).

- **2026-09-14 — captura pasiva y preflight, sin adaptación nueva:** cámara
  estéreo actual recorta caja/base y borde cercano de mesa. `--check` canónico
  termina sin movimiento; preparación de cabeza sólo revisada, no ejecutada.
  Evidencia/receta de captura/comando preflight/hashes:
  `../Humanoide-vla-evidence/20260914T081839Z_ENTRY-CAMERA-CHECK/`.
  No requiere reaplicación ni rollback remoto; observación, no calibración.

- **2026-09-14, Europe/Madrid — hipótesis mesa/caja−20mm, PC:**
  `scripts/vla/review_vla_entry_error_bound.py` añade `--scene-z-offset-mm`
  (default0); nuevo `test_review_vla_entry_error_bound.py`. Traslación explícita
  de escena, sin cambiar fuentes originales, márgenes o ejecutores. Afinado exige
  igual escenario. Ruta372 sigue1016/54/2; ejemplo derecho2,107→3,408mm, sin
  demostrar mínimo global ni aprobar ENTRY.20tests pasan; sin paquetes nuevos,
  robot consultado/modificado o movimiento. Dependencias, fuentes/hash, backup,
  receta y rollback: [ficha](vla/ENTRY_MESA_MENOS20MM_20260914.md).
  Evidencia privada `../Humanoide-vla-evidence/20260914T080700Z_ENTRY-TABLE-MINUS20MM/`.
  Estado: herramienta PC verificada; modificación física de mesa NO realizada.

- **2026-09-14, Europe/Madrid — cotas locales y censo con incertidumbre, PC:**
  destino `scripts/vla/`: tres revisores modificados, helpers nuevos
  `entry_local_displacement_bounds.py`, `entry_interval_boxes.py`, sus dos tests,
  y `screen_entry_uncertainty.py`. Radio finito por postura, consultas selectivas
  y cajas FK por intervalos; conserva1072pares,±1° explícito/2mm y default5°.
  Ruta372:1016/54/2 en11,527s; censo69 sin aprobación.25 tests y regresión real
  pasan. Consultas pasivas nuevas a Motion/Vision: HOME inmóvil, ambos VLA
  detenidos. No movimiento, instalación, reinicio ni cambio de límites remotos.
  Backups/fuentes/hashes, dependencias existentes, receta reproducible y rollback:
  [ficha detallada](vla/ENTRY_COTAS_LOCALES_20260914.md). Evidencia privada
  `../Humanoide-vla-evidence/20260914T072438Z_ENTRY-LOCAL-BOUNDS/`.
  Estado: herramientas PC verificadas; ENTRY y VLA físico PENDIENTES.

- **2026-09-14, Europe/Madrid — afinado PC del escenario±1°:**
  Modificado `scripts/vla/review_vla_entry_error_bound.py`; nuevos
  `scripts/vla/refine_entry_pair_distances.py` y su test. Añade refinamiento
  opcional de sólidos y verificación de correspondencia/proveniencia; conserva
  todos los pares, modelo y márgenes. Predeterminado del revisor sigue5°.
  [Motivo, resultado, receta y rollback](vla/ERROR_ARTICULAR_TRAZAS_20260914.md#afinado-posterior-del-escenario-1).
  Probado sólo offline:997/54/21, dieciséis tests pasan. Dependencias existentes
  de `.venv/general-home`; sin paquetes nuevos ni instalación/carga física.
  Sin consulta, cambio, reinicio, publicación o movimiento remoto. Backup y
  fuentes/hashes: `../Humanoide-vla-evidence/20260914T070658Z_ENTRY-ERROR1-REFINEMENT/`.
  Reaplicar sólo tres fuentes PC y receta; rollback del revisor desde `before/`
  y retirada selectiva de helper/test/entradas, preservando cambios anteriores.

- **2026-09-14, Europe/Madrid — revisión de seguimiento y sensibilidad PC:**
  Nuevos `scripts/vla/review_tracking_error_traces.py` y test homónimo con
  prefijo `test_`; sólo Python estándar y decodificador canónico existente.
  [Motivo, resultados, receta, límites y rollback](vla/ERROR_ARTICULAR_TRAZAS_20260914.md).
  Se ejecutaron offline sobre diez capturas archivadas y se compararon cuatro
  escenarios con el revisor existente, sin modificarlo. Cinco tests pasan.
  H01/H02 máximo0,444207°/0,433667°; ocho ejes dinámicamente observados.
  ±1° es hipótesis de estudio, no cambio runtime ni aprobación física.
  Robot/PC: sin paquetes, servicios, control, despliegue o consulta remota.
  Sólo herramientas/resultado/documentación PC; no probado físicamente.
  Backups, fuentes exactas y hashes:
  `../Humanoide-vla-evidence/20260914T065216Z_TRACKING-SENSITIVITY/`.
  Reaplicar las dos fuentes y receta con trazas privadas verificadas; retirar
  sólo esas fuentes/informe y revertir sus entradas usando `before/` para
  rollback, preservando todo el trabajo anterior. No hay rollback remoto.

- **2026-09-14, Europe/Madrid — segunda revisión PC del error de acceso:**
  `scripts/vla/prepare_vla_entry_bundle.py` evita repetir pares ya sin resolver
  y conserva testigos de incertidumbre; test ampliado a11casos. Nuevo
  `scripts/vla/review_vla_entry_error_bound.py`, sólo archivos/CPU local.
  [Resultado, receta, límites y rollback](vla/ENTRY_Y_RECUPERACION_20260914.md#segunda-revisión-separar-tiempo-resolución-e-incertidumbre).
  Escenario5° y margen2mm intactos; cálculo terminado en26,490s con325pares
  sin resolver,54avisos nominales y693certificados; no aprobación física.
  Dependencias existentes, ningún paquete nuevo. Sin instalación, carga,
  consulta o cambio remoto en esta segunda intervención. Probado sólo offline.
  Fuentes exactas/hashes/backups en
  `../Humanoide-vla-evidence/20260914T062738Z_VLA-ERROR-BOUND-CLOSURE/`.
  Reaplicar sólo archivos PC y receta; rollback de dos fuentes existentes con
  `before/` y retirada de la herramienta nueva, preservando el resto del trabajo.

- **2026-09-14, Europe/Madrid — herramientas PC, ejecución sólo offline:**
  `scripts/vla/survey_vla_entry_scene.py`, `scripts/vla/prepare_vla_entry_bundle.py`,
  `scripts/vla/test_prepare_vla_entry_bundle.py` y
  `config/vla/offline/entry80_rim_annotations_20260914.json`, todos nuevos.
  [Motivo, fuentes, recetas, resultados, límites y reversión](vla/ENTRY_Y_RECUPERACION_20260914.md).
  Dependencias existentes: `.venv/general-home` y `.venv/vla-scene`; no paquetes
  nuevos. Censo150, candidata372 y tres rutas revisadas conservando todos los
  pares; diez tests nuevos y ocho del ranking pasan. Modelo completo/escena/
  seguimiento no cerrados; no probado físicamente ni habilitado VLA.
  Robot: sólo descubrimiento y suscripciones acotadas a estados/cámara/TF;
  no cambio persistente, reinicio, instalación, publicación física o arranque VLA.
  Estado leído HOME, inmóvil, writers0 y VLA detenidos. Sin rollback remoto.
  Evidencia, fuentes exactas, versiones, hashes y documentos previos:
  `../Humanoide-vla-evidence/20260914T055526Z_VLA-ENTRY80-OFFLINE/`.
  `sources-filtered-run/` conserva la versión de las tres rutas;
  `final-sources/` añade el final HOME, validado aparte. Reaplicación: recuperar
  los cuatro archivos PC y ejecutar las recetas del informe con los archivos
  privados; no instalarlos en el robot. Rollback: retirar sólo esos archivos
  y sus referencias documentales usando `before/`, preservando cambios ajenos.

- **2026-09-11, Europe/Madrid — comparación de entradas offline en PC/Vision:**
  tres fuentes nuevas PC: `scripts/vla/evaluate_vla_entry_candidates.py`,
  `scripts/vla/audit_vla_entry_candidate_geometry.py` y
  `scripts/vla/estimate_vla_entry_support_height.py`. Sin versiones anteriores.
  [Motivo, fuentes, receta, resultados y reversión](vla/DECISION_ENTRY_VLA_20260911.md).
  Dependencias existentes: helpers/evaluador, entorno general-home y la imagen
  NVIDIA; no nuevos paquetes.15inferencias completadas, cinco tests del helper
  pasan; extremos aún rechazados. No probado físicamente ni habilitado VLA.
  Vision: contenedor temporal `cruzr-vla-entry-offline-1239`, network=none,
  checkpoint/overlay:ro, staging propio `/tmp/cruzr-vla-entry-offline.6HO18F4m`.
  Exit0; contenedor y staging retirados tras exportar. Sin cambios persistentes
  remotos ni arranque de los contenedores VLA de operación.
  Backup previo, fuentes completas/versiones/hashes y evidencia reproducible:
  `../Humanoide-vla-evidence/20260911T123920Z_VLA-ENTRY-CANDIDATE-DECISION/`.
  Rollback: retirar sólo tres fuentes nuevas y ediciones de esta intervención
  con `before/`, preservando trabajo anterior. No hay activación física.

- **2026-09-11, Europe/Madrid — instalado y cargado en Vision, probado en shadow:**
  reparación de evidencia `shm_msgs/String` en
  `scripts/vla/runtime/cruzr_s2_inference_shadow.py`. Destino y backup exactos,
  versiones, dependencias, activación y reversión en
  [prueba mesa80](vla/PRUEBA_VLA_MESA80_20260911.md).
  SHA anterior840c93e2…b7cac22 →173b55da…cce67b81. Cambian sólo frame_id/encoding
  del JSON; checkpoint, perfil P14, límites y comandos físicos intactos.
  Nuevo instalador `scripts/vla/install_shadow_inference_adapter.py` exige
  hash previo y contenedor detenido, respalda y sustituye un único archivo.
  Nuevo test de evidencia;9 tests pasan. No hay dependencias nuevas.
  Primer arranque temporal:0chunks por fallo de serialización; sesión detenida.
  Segundo arranque con corrección:2chunks, ambos rechazados por discontinuidad
  (máximo81,039° frente a5,73°);2RGB+20D guardados y hashes verificados.
  Final ambos contenedores exited/restart=no, cero RobotCommand y postura sin
  cambio entre extremos. **No probado físicamente ni habilitado flujo VLA.**
  Evidencia, fuentes completas y backups documentales:
  `../Humanoide-vla-evidence/20260911T122137Z_VLA-TABLE80-SHADOW/`.

- **2026-09-11, Europe/Madrid — instalado en PC y probado offline:**
  `scripts/vla/analyze_vla_entry_fixture_sweep.py`,
  `scripts/vla/refine_vla_entry_fixture_sweep.py` y
  `scripts/vla/scene_decode_requirements.txt`, sin versiones anteriores.
  Motivo: comparar acceso a ENTRY430/438 frente a tablero/caja, sin movimiento.
  Analizador admite límites explícitos `--obstacles-json`, valida forma,
  finitud y orden; refiner conserva límites. Resultados no otorgan aprobación.
  Dependencias geométricas existentes en `.venv/general-home`; entorno nuevo
  `/home/lacuna/proyectos/Robots/Humanoide/.venv/vla-scene`, creado con
  `--system-site-packages`, añade PyAV18.1.0/PyArrow25.0.1 para vídeo/parquet.
  [Aplicación, verificación, reversión y límites](vla/REVISION_ENTRY_CON_MESA_20260911.md).
  Ambas recetas reprodujeron exactamente resultados anteriores; nueva escena
  se guarda aparte tras recolocación manual por operador. Sin activación remota,
  reinicio, XML, publicador físico o prueba de brazos; ENTRY40 permanece vigente.
  Fuentes completas, versiones, hashes, capturas y backups en
  `../Humanoide-vla-evidence/20260911T114330Z_VLA-ENTRY-SCENE/`.
  Reversión selectiva: retirar nuevo entorno y tres fuentes nuevas, restaurar
  sólo ediciones de esta intervención desde `before/`; preservar trabajo previo.

- **2026-09-11, Europe/Madrid — añadido y VERIFICADO offline en PC:**
  [`rank_vla_entry_postures.py`](../scripts/vla/rank_vla_entry_postures.py) y
  `scripts/vla/test_rank_vla_entry_postures.py`, sin versión anterior.
  Motivo: revisar ENTRY inclinada sin alterar un frame20D ni el checkpoint.
  150 entradas task0,113 con filtro≤5° y límites válidos; ocho tests pasan.
  Dependencias existentes Python3/NumPy/PyYAML, helper FK versionado, URDF
  splint externo y reporte E6.0Z de hash congelado. Sin nuevas instalaciones.
  [Receta, resultado y pendientes](vla/REVISION_ENTRY_ERGUIDA_20260911.md).
  Fuentes/versiones/hashes y backups documentales en
  `../Humanoide-vla-evidence/20260911T103734Z_VLA-ENTRY-UPRIGHT/`.
  No requiere activación/recarga ni destino remoto; no probado físicamente.
  Rollback: retirar dos fuentes nuevas y deshacer sólo esta edición documental
  mediante `before/`; preservar cambios previos. ENTRY40 y perfiles intactos.

- **VERIFICADO histórico:** imágenes y `checkpoint-40000` instalados; dos
  contenedores detenidos, `restart=no`. Inferencia produce chunks; no existe
  autorización de publicación física por restaurar el paquete.
- **Fuente:** [`install_ubtech_vla.sh`](../scripts/vla/install_ubtech_vla.sh),
  [`scripts/vla/runtime/`](../scripts/vla/runtime/) y
  [guía de activación](guides/CRUZR_S2_VLA_SAFE_ENABLEMENT.md).
  Perfil S2 20D, `/mc/whole_joint_states` de lectura, metadatos/modelo y
  validadores locales. Binarios/checkpoints del paquete externo, fuera de Git.
- **Destino:** `/home/walker/cruzr-vla/` en ambos hosts; montajes de
  `cruzr-vla-inference` y `cruzr-vla-control`. El backup ligero no incluye
  automáticamente todas las imágenes ni pesos: conservar el paquete original
  y copia del workspace modificado/metadata con sus hashes por separado.
- **Reaplicar/verificar:** `--check`, después etapas necesarias `--stage`,
  `--load-images`, `--create-containers`, `--verify` según guía. Crear
  contenedores **detenidos**; revisar compatibilidad antes de reutilizar perfil.
- **Rollback:** backup de workspace/inspect/manifiestos y originales de cada
  overlay; preservar `restart=no`, sin habilitar clientes de movimiento.

### NAV-01 — Mapas, transferencia, referencias y geometría

- **OBSERVADO reciente:** trabajo en `MESAS2`, `CRUZR_MAP_TYPE=uslam`;
  `test_route_01` es otro mapa histórico/default, no sustituye MESAS2.
  Guardar nombre, tipo, fingerprint, puntos con orientación y referencias.
- **Datos:** `/etc/walker/map`, `/etc/walker/task`, calibración del robot;
  PC [`config/cruzr_mesa2_drop.json`](../config/cruzr_mesa2_drop.json), sus
  backups y `config/clamp_*.json`. Referencias AprilTag y evidencia de montaje
  en guías y carpeta externa. Guardar también modelos locales no versionados
  que se usaron en cálculos de colisión; no regenerarlos de una foto.
  Las carpetas `cruzr_s2_description` y `cruzr_s2_description_splint` se
  revisaron sin modificarlas el 10-09: base con pinzas de dedos, splint con
  abrazaderas cuyas mallas ya estaban en el runtime archivado. Ambas comparten
  nombre ROS; no hay instalación nueva ni sustitución automática de los
  modelos de los auditores. [Informe y manifiesto](reports/2026-09-10_MODELOS_CRUZR_S2_DESCRIPTION.md).
- **Fuentes de comportamiento:**
  [`cruzr_blue_workbin_table_transfer.sh`](../scripts/cruzr_blue_workbin_table_transfer.sh),
  [`cruzr_blue_workbin_table_transfer_no_tag.sh`](../scripts/cruzr_blue_workbin_table_transfer_no_tag.sh),
  [guía sin AprilTag](guides/TRANSFERENCIA_CAJA_ENTRE_MESAS_SIN_APRILTAG.md) y
  [guía con AprilTag](guides/TRANSFERENCIA_CAJA_ENTRE_MESAS_CON_APRILTAG.md).
  Umbral local de batería 20 % en ciclo/ruta; no es un ajuste del firmware.
- **Reaplicar/verificar:** recuperar mapa/perfil correctos; volver a comprobar
  localización, waypoint, altura/disposición real y transformaciones. El
  modo `--check` de algunos flujos puede cargar mapa/relocalizar: leer su
  alcance antes de usarlo como verificación. No reenseñar mesa 2 desde PRE;
  `--teach-mesa2` se hace en la pose real de depósito. Medir desde la referencia
  definida, no interpretar el error al waypoint como distancia hasta la mesa.
- **Rollback:** copia previa del perfil/mapa. Restaurar datos no renueva una
  validación física ni levanta bloqueos derivados de contacto. Conservar
  fechas, incertidumbres y condiciones de los modelos.

### NAV-02 — Perfil temporal de percepción con carga

- **Adaptación temporal:** [`cruzr_cargo_perception_profile.sh`](../scripts/cruzr_cargo_perception_profile.sh)
  `--check`, `--enable`, `--restore`. Desvía RGB-D de la caja durante tránsito;
  mantiene LiDAR, odometría, mapa, bumpers y paros.
- **Destino Vision:** `walker-nav.vnav_perception-1`,
  `/opt/walker/nav_perception2d_config_utars/share/nav_perception2d_config_utars/config/perception/perception_params.yaml`.
  Estado/backup en `/home/walker/.config/udoke/cruzr-cargo-perception-profile`.
  Contrasta LiDAR en `walker-nav.freepnc_task-1`.
- **Reaplicar/verificar:** guardar original y transacción, pero recuperar
  configuración **normal**, no el perfil de carga activado. `--restore`
  reinicia el componente indicado por el script; no es una consulta inocua.
  Una transacción interrumpida exige resolverla antes de volver a habilitar.
- **Rollback/evidencia:** restauración byte a byte y hashes del script; guía
  de transferencia y registro de la ejecución que habilitó el perfil.

## Retirado, temporal o no aprobado para reinstalar

| Elemento | Estado vigente / razón |
|---|---|
| `cruzr-v020-boot-guard.service` y `/usr/local/sbin/cruzr-v020-boot-guard` | **DESCARTADO como autoarranque actual**: disabled/inactive; reemplazado por BOOT-01. El guard histórico podía reiniciar CC y mover. Conservar sólo evidencia/backup. |
| Ruta directa antigua `cruzr/pico_to_home_owner` | **Retirada tras contacto**; sustituida por open_v2. No recuperar por similitud del nombre. |
| `cruzr_internal_home_open_v3_6s_DRAFT.xml` | **Borrador local**, no instalado ni validado. El HOME interno vigente es de 20 s. |
| Parches de backend 5.3 (GRIPPER→CLAMP, trigger Y, watchdog) | **Retirados** al usar 4.7 oficial. No aplicar a su binario. |
| `cruzr-boot-visual-preview.service`, JSON del visor, registro de boot | **Transitorios**: no habilitar/restaurar para el próximo arranque. |
| Reinicio LightDM del 10-09 para recargar el visor | **Intervención puntual**, no modificación de autologin ni requisito de cada arranque. |

## Plantilla obligatoria para cambios nuevos

Copiar una ficha, asignar un ID estable y añadirla al índice. Para cambios
temporales basta enlazar la intervención y dejar claro el estado final; si
permanecen activos pasan a tener ficha vigente.

```text
ID / nombre:
Fecha y zona / autor o intervención:
Motivo y comportamiento esperado:
Estado: VERIFICADO / OBSERVADO / INFERENCIA / PENDIENTE / DESCARTADO
Destino: PC/PICO/Motion/Vision, host, contenedor, ruta/servicio/clave exacta
Versión, imagen/digest, hardware y dependencias compatibles:
Antes: valor/hash, backup privado externo y checksum
Después: valor/hash, fuente o receta versionada (incluye cambios sin commit)
Aplicación: comando/receta y requisitos; efecto sobre procesos/control
Activación: si necesita recarga/reinicio; separado de instalar y de mover
Verificación: prueba, salida/evidencia, instalado/cargado/ensayo físico
Reversión: pasos selectivos, backup y límites de la reversión
Tras actualizar: conservar / revisar y reaplicar / recalibrar / no restaurar
Evidencia y pendientes concretos; ficha que reemplaza, si existe:
```

Un registro sólo está cerrado cuando otro operador puede localizar la fuente,
el estado anterior, el procedimiento y la evidencia sin consultar el chat.
No marcar como completos los componentes que sólo se han revisado en papel.

## 2026-09-14 — VLA-01: comprobación posterior al arranque completo

VERIFICADO: el preflight vivo con paros liberados termina correctamente;
20 articulaciones, velocidad máxima cero, baterías75,5/77,1%, cargador
desconectado, ambos paros0, servidor de manipulación disponible, sin otros
publicadores de control y contenedores VLA detenidos. Los diez XML instalados
y el registro conservan los hashes del recibo después del reinicio. Esto
verifica archivos persistentes, no la identidad efectiva de tareas cargadas.
HOME es la postura comunicada ahora por el usuario; este preflight no demuestra
por sí solo coincidencia de las20 posiciones con el extremo HOME.

PENDIENTE: el ejecutor de cinco etapas comienza en READY. El wrapper
`scripts/vla/cruzr_vla_ready_pose.sh` mantiene bloqueado HOME→READY y exige
validación independiente. No ejecutar etapa1 desde HOME. También sigue sin
emitirse la habilitación de ensayo documentada en el ejecutor ENTRY410.
No se enviaron movimientos, no se reinició ningún servicio y no se modificó
el robot en esta comprobación. El arranque correcto no elimina estos pendientes.
Evidencia: `../Humanoide-vla-evidence/20260914T135826Z_ENTRY410-POSTBOOT/`,
con preflight, hashes posteriores al arranque y respaldo documental.
Punto de reanudación: resolver el acceso HOME→READY y la habilitación del
ensayo, conservando el robot en su estado actual; no repetir el ciclo de
encendido para resolver un requisito del ejecutor.

## 2026-09-14 — VLA-01: acceso medido a READY calculado por grupos

OBSERVADO: captura pasiva posterior al arranque, 14:07:23–14:07:33 UTC,
347 muestras articulares, ambos paros0, sin incidencias del analizador.
VERIFICADO OFFLINE: `scripts/vla/prepare_home_ready_access.py` genera cinco
tramos desde la última postura medida hasta el READY exacto del informe410.
Comprueba identidad de traza, ausencia de movimiento/fallos en toda la traza,
variación articular≤0,002rad, identidad del modelo y fuentes inmutables durante
el cálculo. Genera diez XML DRAFT para ambos sentidos; no instala ni publica.

Resultado bajo las hipótesis del informe GAP220:1018 pares con intervalos
geométricos certificados,54 con violación del margen del modelo,0 pendientes
y sin timeout. Los54 pares son exactamente los mismos del informe de etapas
ENTRY410; no se convierten en aprobados ni se eliminan del resultado. La
correspondencia de pares no transfiere automáticamente pruebas de otro tramo.
Duración propuesta136s: cabeza20, cintura1, elevador1, brazo izquierdo57 y
derecho57. Son tiempos de propuesta, no una medición ni una ejecución aprobada.

PENDIENTE: comprobar límites dinámicos/configuración efectiva, correspondencia
runtime de grupos, identidad cargada y protocolo del ensayo. Los XML de acceso
NO están instalados, el wrapper activo permanece bloqueado y no se ha emitido
habilitación física. No hubo reinicios ni movimientos. No es aún una ruta
HOME→ENTRY ejecutable.

Evidencia externa: `../Humanoide-vla-evidence/20260914_HOME_READY_ACCESS/`
(traza, análisis, access/review.json, diez borradores, comparación y fuentes).
Tests: cinco casos de admisión de postura pasan, incluidos movimiento anterior,
deriva con velocidad cero, fallo y dato no finito; los tres tests existentes
de construcción por grupos también pasan. No cubren movimiento real.
Receta reproducible: `docs/vla/ACCESO_HOME_READY_20260914.md`. Reversión local:
retirar selectivamente las dos fuentes nuevas y restaurar documentos desde
`before/` de la evidencia, preservando otros cambios. Ningún cambio persistente
en el robot.

## 2026-09-14 — contraste vivo de configuración HOME→READY

VERIFICADO: consultas de lectura a Motion recuperaron YAML y URDF, con hashes
idénticos al contrato archivado. Tipo, lado y dimensión de los cinco grupos
coinciden. Las20 articulaciones cumplen límites de posición (incluido el error
del informe) y velocidad para el perfil cúbico propuesto. Los seis ejes de
cabeza/cuerpo cumplen además la aceleración configurada. No se localizaron
fuentes MetaMove en los dos paquetes consultados; esto no demuestra su ausencia
en todo el sistema. El orden articular efectivo dentro de MetaMove y su
interpolador no quedan demostrados por tipo/lado/dimensión.

PENDIENTE concreto: las14 articulaciones de brazo no tienen aceleración en
estos archivos. No se infiere un límite ni se marca la ejecución como aprobada.
No hubo cambios, instalaciones, reinicios ni movimientos del robot.
Evidencia: `../Humanoide-vla-evidence/20260914_HOME_READY_CONTRAST/`. La primera
lectura normalizó saltos de línea y falló la comprobación hash; se conservó y
se repitió con bytes exactos en base64 (`runtime-bytes.json`), cuyos hashes
pasan. `limits-comparison.json` conserva cada eje y sus resultados.

Reproducción local:
```bash
.venv/general-home/bin/python scripts/vla/contrast_home_ready_limits.py \
 --review ../Humanoide-vla-evidence/20260914_HOME_READY_ACCESS/access/review.json \
 --snapshot ../Humanoide-vla-evidence/20260914_HOME_READY_CONTRAST/runtime-bytes.json \
 --output /tmp/contraste-ready-nuevo.json
```

Cambio persistente sólo PC: nuevo comparador offline y este registro VLA-01.
Reversión: retirar el comparador y restaurar documentos desde before/ de la
evidencia, preservando cambios ajenos. No habilita el wrapper de movimiento.

## 2026-09-14 — VLA-01: contraste de bibliotecas internas Motion

VERIFICADO: se copiaron al PC mediante lectura las bibliotecas actuales
libmeta_move.so, libinterpolation_path_planner.so y libs2_arm_kinematics.so.
Hashes en binary-hashes.json. La biblioteca de interpolación tiene SHA256
1267e370614d5350706caa061a24c162e3333248b9b1af74b8ea319a3d5ee329.
El emulador existente verifica1312 casos de su rutina numérica: error máximo
2,6645352591003757e-15 frente a Hermite cúbica; con velocidad cero en extremos
q=q0+(q1-q0)*(3u²−2u³). Este resultado NO verifica el despacho de MetaMove,
sincronización, configuración de velocidades extremas ni control físico.

Búsqueda en YAML de cinco paquetes instalados: los perfiles CruzrS2 examinados
no declaran aceleración de brazos. Hay valores en perfiles WalkerS2/S3, pero
no son límites acreditados para esta unidad y no se reutilizan. No se encontró
una tabla explícita joint_names/joint_order en esa búsqueda. Los símbolos
exponen SetJointLimits; su existencia no demuestra los valores cargados.

PENDIENTE: demostrar el orden efectivo y la llamada completa de MetaMove, y
obtener límites efectivos de brazos. El análisis numérico del interpolador
queda cerrado en su alcance limitado. No se habilitó ejecución ni se enviaron
movimientos, instalaciones, reinicios o cambios de protecciones.
Evidencia: ../Humanoide-vla-evidence/20260914_MOTION_INTERNAL_CONTRAST/.
Las bibliotecas privadas quedan fuera de Git. Sólo cambios documentales enPC;
respaldo en before/. Revertir únicamente esta adición documental si se necesita.

Reproducción offline:
```bash
.venv/general-home/bin/python scripts/teleoperation/audit_motion_interpolation.py \
 --binary ../Humanoide-vla-evidence/20260914_MOTION_INTERNAL_CONTRAST/libinterpolation_path_planner.so \
 --output /tmp/interpolacion-contraste-nuevo.json
```

## 2026-09-14 — VLA-01: límites compilados y decisión de habilitación

VERIFICADO: se extrajo sin cargar código vendor la tabla de7 registros de48
bytes en VA0x2fe20 de libs2_arm_kinematics.so (SHA2562a41cf55…ad251c).
Las ramas izquierda/derecha del constructor copian esa tabla y llaman a
SetJointLimits; los primeros dos doubles son límites de posición. Se mantienen
sin calificar los nombres de los cuatro campos escalares restantes. Los
límites compilados NO se presentan como lectura efectiva de la memoria del
controlador: pueden existir sustituciones posteriores. Tres tests locales
verifican extracción por segmento ELF, rechazo de hash distinto y datos mutables.

HALLAZGO: todos los extremos nominales del acceso quedan dentro de estos
límites bajo la correspondencia propuesta. Sin embargo, el error independiente
±1° produce máximos0,01639868/0,01841203rad en codoL/R frente a0,01rad compilado.
El error positivo que cabe desde los máximos nominales es0,63338°/0,51803°.
Esto es una incompatibilidad del dominio de error revisado con esos defaults,
no una colisión física observada ni prueba de que la trayectoria nominal falle.
No se redujo el error para conseguir un resultado favorable. El contraste
anterior con URDF/YAML era incompleto frente a estos defaults compilados.

Consulta viva: bibliotecas MetaMove, interpolación y cinemáticaS2 mapeadas
en PID66. No se adjuntó depurador ni se suspendió el proceso. Los topics
individuales de brazo/cintura/elevador no devolvieron estado; rosa puede
terminar con código0 y mensaje de error en stderr, por lo que no se tomó ese
código como éxito. /mc/whole_joint_states y /mc/joint_states sí dieron estados
con nombres, pero en órdenes diferentes. Esto confirma la necesidad de
mapear por nombre y no prueba el orden interno de MetaMove.

DECISIÓN: no habilitar todavía. No se fabricó una habilitación ni se cambiaron
protecciones. Siguen sin demostrarse orden/despacho efectivo de MetaMove,
límites efectivos frente a defaults y seguimiento/parada para el ensayo.
No hubo objetivos de movimiento, instalación o recarga del robot. Los borradores
de acceso permanecen sólo en PC. Evidencia y decisión explícita:
`../Humanoide-vla-evidence/20260914_MOTION_INTERNAL_CONTRAST/enablement-decision.json`.

Nuevo extractor reproducible:
```bash
.venv/general-home/bin/python scripts/vla/extract_s2_compiled_limits.py \
 --binary ../Humanoide-vla-evidence/20260914_MOTION_INTERNAL_CONTRAST/libs2_arm_kinematics.so \
 --review ../Humanoide-vla-evidence/20260914_HOME_READY_ACCESS/access/review.json \
 --output /tmp/limites-compilados-nuevo.json
```

Registro global VLA-01: cambios persistentes sólo PC (extractor, tests y docs).
Respaldo de esta adición en before-final/ de la evidencia, copia de fuentes
y hashes. Reversión: retirar selectivamente las dos fuentes nuevas y restaurar
esta adición documental desde el respaldo, preservando el trabajo previo.

## 2026-09-14 — corrección del criterio de banda de error (VLA-01)

CORRECCIÓN de la conclusión anterior: el desbordamiento de la banda±1°
respecto a los límites compilados NO es por sí solo un incumplimiento de
consignas ni invalida una envolvente geométrica calculada sobre esa banda
más amplia. No se debe exigir sin distinguir que toda la banda geométrica
sea una consigna admisible. Tampoco se puede deducir seguimiento o parada
seguros del límite configurado. Se conservan los resultados previos como
historia, pero se retira ese desbordamiento como motivo suficiente de bloqueo.

VERIFICADO: las consignas nominales de los14 ejes de brazo siguen dentro
de los límites de posición compilados, bajo la correspondencia propuesta.
Las20 articulaciones pasan posición/velocidad nominal con YAML/URDF y perfil
cúbico. No se modifican límites, trayectorias, tiempos ni la banda±1°; no se
recorta esa banda a los límites. El análisis geométrico anterior no se repite
porque sus entradas geométricas y su dominio de error no han cambiado.

Cambios locales: extract_s2_compiled_limits.py distingue nominal_inside y
uncertainty_inside mediante position_domains; contrast_home_ready_limits.py
añade el resultado nominal sin cambiar la semántica de su campo previo.
Seis tests pasan: extracción ELF, hash, datos mutables, desbordamiento de banda
sin incumplimiento nominal, incumplimiento nominal real y errores no válidos.
Nuevos informes en ../Humanoide-vla-evidence/20260914_LIMIT_DOMAIN_CORRECTION/.

La habilitación física sigue sin emitirse por los pendientes independientes:
orden/despacho efectivo de MetaMove y contrato de seguimiento/parada del
ensayo, identidad/configuración efectiva frente a defaults y revisión de
los campos dinámicos de brazo. No se modifica ningún gate ni se presenta
una corrección lógica como ensayo físico completado. No hubo comandos al robot.

Registro global: sóloPC; backups anteriores en before/ de la evidencia.
Reversión: restaurar selectivamente estas fuentes/documentos desde before/
preservando otras modificaciones. Las fuentes de reproducción son los mismos
comandos de contraste y extracción documentados arriba, con directorio de
salida nuevo. Evidencia de decisión actual: decision.json.

## 2026-09-14 — VLA-01: ensayo físico de cabeza MetaMove y fallo de admisión

AUTORIZACIÓN: usuario confirmó HOME, abrazaderas vacías, cabeza/cuello libres,
ruedas bloqueadas, cargador desconectado, ningún mando y persona junto al paro.
Se verificó preflight vivo y XML oficial fijo cruzr/move_head_lower, SHA256
f3a73626…ea46c1, cabeza [yaw=0,pitch=−0,43]rad en2s. Revisión geométrica desde
estado nominal por nombre:1018 pares certificados,54 solapamientos del modelo
ya conservados,0 pendientes. No se reutilizó etapa1 ENTRY410 desde HOME.

EJECUTADO: una sola petición de acción, aceptada. La cabeza pasó de−0,00297209
a−0,42817239rad. Giro constante0,00057524rad; cambio observado máximo de otros
18 ejes0rad.312 muestras de motor; separación máxima entre muestras globales
0,03178306s. Velocidad máxima observada de pitch0,339292rad/s y discrepancia
máxima cmd_pos/posición0,364709°. cmd_pos es solicitado SIN LIMITAR, no la
consigna efectiva del servo: estos valores no califican el seguimiento futuro.
El usuario confirmó posteriormente suavidad y ausencia de contacto.

RESULTADO DEL EJECUTOR: FAILED_NO_RETRY, NO éxito validado. A1,97046s desde
dispatch, se detectó que la última muestra del paro principal tenía más de3s
y se solicitó cancelación. Se recibió respuesta, pero el registro de esta
versión no incluía código/lista de goals de la cancelación ni resultado final
de la acción. No se puede atribuir la detención a cancelación ni afirmar que
el E-stop se ejercitó. No hubo reintento ni HOME automático.

VERIFICACIÓN POSTERIOR: captura pasiva10s/348 muestras, sin incidencias, ambos
paros0 y velocidad máxima0 en todos los ejes. Estado al cierre: brazos/cuerpo
en su postura previa y cabeza baja estable, NO HOME completo. El E-stop físico
no fue accionado durante este ensayo según lo observado en los topics.

CORRECCIÓN PC: el monitor inicial admitía una sola muestra fresca de paro sin
comprobar su cadencia; eso permitió iniciar aunque su canal no sostenía el
umbral de3s. Ahora exige al menos dos muestras y comprueba intervalos antes
de dispatch. El intervalo posterior observado4,495s se rechaza antes de mover
en la regresión offline. Se mantiene el umbral3s: no se aceleran republicaciones
de valores cacheados ni se cambia el robot. Se registrarán además UUID del
goal, respuesta completa de cancelación y resultado tardío si está disponible.
Seis tests de envolvente/cadencia pasan. No se probó físicamente esa nueva
versión, no se volvió a ejecutar. Resolver la disponibilidad/semántica del
canal de paro sigue pendiente para este monitor.

Alcance cerrado: ejecución física del segundo componente de MetaMove/head y
detención posterior observada en este ensayo. NO califica cancelación, E-stop,
seguimiento/parada de brazos/elevador ni habilita ENTRY410.

Evidencias: ../Humanoide-vla-evidence/20260914_METAMOVE_TRIAL_PREP/;
../Humanoide-vla-evidence/20260914_METAMOVE_HEAD_CHECK/;
../Humanoide-vla-evidence/20260914_METAMOVE_HEAD_RUN/ (incluye fuentes EXACTAS
del ensayo antes de corregirlas, intent/result/trace/analysis);
../Humanoide-vla-evidence/20260914_METAMOVE_HEAD_AFTER/ (captura y regresión).
Fuente reproducible: docs/vla/ENSAYO_METAMOVE_CABEZA_20260914.md.

Registro global: robot sólo recibió la tarea citada y solicitud de cancelación;
ninguna instalación, recarga, cambio de fichero/firmware/protección. PC: nuevos
revisor, ejecutor de cabeza, monitor, analizador y tests. Reversión de código:
retirar selectivamente estos archivos nuevos y restaurar docs desde before-docs/
de la evidencia, preservando cambios ajenos. La postura física no se revierte
restaurando archivos: cualquier retorno requiere su propia orden comprobada.

## 2026-09-14 17:12 Europe/Madrid — VLA-01: nueva comprobación del paro antes de HOME→READY→ENTRY

El usuario confirma supervisión activa y solicita la secuencia. Captura pasiva
nueva de15s:601 muestras de actuadores, tres mensajes de cada paro, ambos0,
sin incidencias del analizador. Los intervalos de recepción siguen siendo
4,495–4,498s, superiores al máximo3s del monitor. Esto no demuestra fallo del
paro físico; demuestra que el canal observado no cumple la admisión continua
actual. No se envió HOME, READY, ENTRY ni cancelación, ni se alteró el robot.
La captura no acredita por sí sola coincidencia con HOME por nombre articular.
No se amplía el umbral ni se sustituye la evidencia por la presencia del operador.
Pendiente resolver la disponibilidad/semántica del canal y la habilitación del
acceso y etapas antes de ejecutar la secuencia solicitada.
Evidencia: `../Humanoide-vla-evidence/20260914_ENTRY_REQUEST_STOP_RECHECK/`
(captura, análisis y cadence.json). Sólo registro documental en PC, sin cambios
remotos que revertir; copias documentales previas en before/ de esa evidencia.

## 2026-09-14 — VLA-01: semántica del topic de paro identificada

VERIFICADO estáticamente en unova_power/server13cea0b9…e1a6d: la rama CAN0x5b
publica cambios de ambos paros y suprime duplicados hasta reiniciar un contador
cada11 tramas. La cadencia4,5s no demuestra avería del paro; el monitor local
lo había tratado incorrectamente como heartbeat continuo3s. No se aumentaTTL
ni se cambia firmware/reporte/protección; notificación física y parada no quedan
probadas por análisis estático. ENTRY comprueba ahora cadencia antes de dispatch,
como el ensayo de cabeza, para evitar iniciar y fallar después. Doce tests pasan.
Sin HOME, READY, ENTRY, instalaciones o reinicios remotos. Auditor y dependencias
Capstone5.0.6/pyelftools0.32 sólo enPC/evidencia privada, sin SDK modificado.
Ver `docs/vla/ESTADO_PARO_Y_CADENCIA_20260914.md` para receta, hashes, evidencia,
respaldo/reversión y pendientes. Observación de pulsación estática solicitada;
no confundir solicitud con pulsación realizada ni liberar automáticamente.

Resultado de la ventana pasiva15:43:04–15:44:04UTC:2852 muestras de actuadores,
13 mensajes por paro, todos0; sin incidencias del analizador. No se observó
pulsación. La petición al operador sigue pendiente, no equivale a ejecución.
La ventana terminó y no mide eventos posteriores. No se envió movimiento.

## 2026-09-14 — VLA-01: rendimiento VLA medido en escena fija

Adaptador shadow instrumentado e instalado enVision con backup/hash anterior;
no se alteran pesos, frecuencia ni mando. Inicialización27,467s; primera
iteración1,697s; cinco siguientes mediana0,444s/máximo0,474s. Fuente runtime
verificada DEFAULT_HZ=0.2:5s entre inferencias; cálculo del modelo caliente
mediana0,401s. Sincronización de buffer0,243ms; evidencia RGB43,779ms.
Son tiempos anidados de pared, no sumar ni tratar como garantía de plazo.

Task0 durante30,029s: seis chunks, seis rechazos por saltos iniciales en ocho
ejes. Estado leído por nombre: cuerpo/brazos cerca deHOME, cabeza−0,428268rad,
velocidades0. No es ENTRY ni ensayo físico VLA. La primera orquestación fue
interrumpida antes del trigger; se recuperó estado y usó modelo ya cargado,
reiniciando sólo validador shadow agotado. Cierre verificado ambos contenedores
VLA exited, cero publicadores de RobotCommand; ningún movimiento enviado.

Fuente/receta, instalación, backup/rollback, evidencia, límites y secuencia
física pendiente: docs/vla/PRUEBA_VLA_ESCENA_FIJA_Y_TIEMPOS.md. Cambios PC:
benchmark_vla_shadow.py y adaptador instrumentado; Vision sólo adaptador propio
sha86f6a2ee…23fe7, backup remoto sufijo20260914T161513486568Z y copiaPC.
No se modifica SDK, Motion, tiempo de trayectoria ni protecciones. Se ha medido
shadow, no se habilitó acceso aENTRY ni agarre físico. Evidencia privada:
../Humanoide-vla-evidence/20260914_VLA_TIMING/.

## 2026-09-14 — VLA-01: acceso desde estado articular por nombre

VERIFICADO: captura nueva sólo lectura,98 pares de estados en5s, nombres
articulares completos, marcas de fuente crecientes y salud de actuadores.
Cabeza pitch−0,428268rad; cuerpo/brazos próximos a cero, inmóviles. El preparador
usa ahora /mc/whole_joint_states por nombre para geometría; los actuadores se
usan para salud/velocidad y no para inferir signo o posición articular.
El monitor ENTRY se corrigió con la misma separación y exige ambas fuentes
frescas, nombres completos/únicos, datos finitos y actuadores habilitados.
No confundir esta correspondencia del estado con el orden interno MetaMove.

Acceso medido→READY:1018 pares certificados,54 avisos internos conocidos,
0UNRESOLVED, sin timeout, duración nominal123s. Los54 avisos se conservan.
Contraste offline con snapshots archivados: posición/velocidad nominal20D
correctas; brazos nominales dentro de defaults compilados. No es lectura actual
de límites efectivos ni verifica aceleración de brazos, despacho o parada.
Veinte tests pasan, incluyendo orden permutado, nombres ausentes/duplicados,
no finitos y desacoplamiento entre posiciones motor y posiciones articulares.

Cambio PC: capture_named_entry_state.py, prepare_home_ready_access.py,
runtime/entry410_single_stage_remote.py y test_entry_named_state.py. Sin
instalación/reinicio ni movimiento remoto; no se generó habilitación física.
XML de acceso nuevos siguen siendo borradores locales, NO instalados.
La CLI del preparador exige ahora --named-capture; el antiguo --trace no se
usa para geometría. measured_start se conserva sólo como helper histórico.

Reproducción:
```bash
python3 scripts/vla/capture_named_entry_state.py --output-dir /ruta/captura-nueva
.venv/general-home/bin/python scripts/vla/prepare_home_ready_access.py \
 --reference ../Humanoide-vla-evidence/20260914T124504Z_ENTRY410-GAP220/route-review.json \
 --named-capture /ruta/captura-nueva/capture.json --output-dir /ruta/acceso-nuevo
```

Evidencia: ../Humanoide-vla-evidence/20260914_ENTRY_NAMED_STATE/ con captura,
access/review.json, límites, fuentes y hashes. Los backups están en before/.
Reversión sóloPC: restaurar selectivamente fuentes propias desde before/ y
retirar fuentes nuevas; no restaurar el monitor antiguo para habilitar movimiento.
Después de una actualización, contrastar ambos schemas/nombres y rehacer
captura/revisión; no transportar un contrato de otro robot/firmware.

PENDIENTE: semántica temporal y prueba de notificación física del paro,
despacho/carga efectivos de los grupos y contrato del ensayo. No hay GOAL
HOME/READY/ENTRY enviado. No se reclama retorno seguro desde cualquier postura.

Observación de paro solicitada 2026-09-14T16:40:45.820007+00:00: captura
pasiva independiente acotada a120s en stop-transition/ de la evidencia
ENTRY_NAMED_STATE; no publica ni cancela acciones. Pulsación del operador
pendiente de respuesta. No confundir solicitud con ejecución ni liberar el paro.


## 2026-09-14 18:47 Europe/Madrid — paro reconocido y fallo de hardware (VLA-01 / BOOT-01)

**OBSERVADO.** El operador confirmó el paro principal pulsado durante el ensayo
pasivo, sin órdenes de movimiento. A las 16:40:43.395 UTC Control Center registró
`EstopPressed`, `Ready -> WaitStartMotion` y `disableAllMotionAbility`.
El registro del hardware también recibió el paro y, a las 16:40:43.732 UTC,
terminó con `terminate called without an active exception`, `SIGABRT`, con
`std::thread::~thread()` en la pila. Esto documenta un fallo del proceso;
la causa exacta en el código del proveedor sigue PENDIENTE.
Docker muestra un reinicio de `walker-motion.hw-1` (16:40:44.028 UTC) y otro de
`walker-motion.manipulation_robot_app-1` (16:40:48.723 UTC). No se ordenaron
reinicios desde esta intervención. El hardware espera `/mc/rosa_control/start`;
Motion espera ListControllers; no hay servidor de manipulación ni estados
articulares actuales. Los logs del proveedor imprimen UTC+8: su fecha local
2026-09-15 00:40 corresponde al 2026-09-14 16:40 UTC.

La captura terminó: 26 mensajes de cada paro, principal=1 y segundo=0,
ninguna muestra de actuadores, `usable_capture=false` y una suscripción
interrumpida con exit=137. El registro del monitor no contiene el flanco 0->1;
no mide latencia desde el botón ni distancia de parada. Queda comprobada la
recepción funcional del paro en Control Center y hardware, sin aprobar por ello
el seguimiento/parada de brazos ni ENTRY/VLA físico. No repetir una pulsación
sólo para recuperar el flanco que faltó en esta captura.

Estado de reanudación: mantener el paro pulsado; recuperación mediante el ciclo
completo supervisado de la guía v0.2.0, sin improvisar StartMotion ni liberar
ahora para intentar recuperar el servidor. Después del ciclo, redescubrir
procesos, endpoints y estados; no reutilizar identidades de carga anteriores.
No se instalaron cambios remotos ni se modificaron límites o watchdogs.
Evidencia privada: `../Humanoide-vla-evidence/20260914_ENTRY_NAMED_STATE/`
(`stop-transition/capture.json`, `stop-transition/trace.jsonl`,
`after-estop/cc.json`, `inspect.json`, `hwlog.json`, `motionlog.json`,
`actions.json`, `joints.json`). Copia documental previa en
`before-stop-documentation/`; manifiesto `after-estop/SHA256SUMS`.


## 2026-09-14 18:58 Europe/Madrid — recuperación tras ciclo completo (BOOT-01 / VLA-01)

**VERIFICADO por lectura; ciclo realizado por el operador.** Tras confirmar el
usuario el nuevo encendido y HOME, Control Center registra SelfCheck y
StartMotion completados, entrada en JoystickMode a las 16:55:13 UTC. A las
16:57 UTC vuelven el servidor de manipulación (1) y los estados articulares:
20 ejes de cuerpo/brazos/cabeza próximos a cero (máximo 0,002877 rad),
velocidades medidas cero; ambos paros=0, cargador=0, baterías 53,2/54,4 %.
VLA control e inferencia siguen detenidos con restart=no; publicadores de
/mc/sdk/robot_command=0. No se enviaron movimientos ni reinicios.
La recuperación operativa está verificada; no demuestra corregida la caída
SIGABRT al pulsar el paro ni aprueba ENTRY/VLA físico. No hace falta repetir
el ensayo de pulsación para comprobar recepción. Antes de ejecutar, renovar
la identidad de tareas/procesos y las condiciones de la prueba tras el arranque.
Evidencia: ../Humanoide-vla-evidence/20260914T165743Z_ESTOP-AVAILABLE/
(results.json y evidence.sha256); copia documental previa en before-docs/.


## 2026-09-14 — solicitud de continuación física tras recuperación (VLA-01)

Operador autoriza continuar y confirma condiciones y supervisión junto al paro.
El preflight canónico de este arranque termina PASS_READ_ONLY_LIVE_AUDIT_PHYSICAL_GATES_REMAIN:
20 actuadores habilitados/inmóviles, ambos paros liberados, sin cargador,
servidor disponible, VLA detenido y cero publicadores de comandos SDK.
Evidencia: ../Humanoide-vla-evidence/20260914T165743Z_ESTOP-AVAILABLE/preflight-resume.log.

Revisión del ejecutor: entry410_single_stage_remote.py exige cadencia máxima3s
tanto en admisión como durante movimiento; el canal observado repite cada~4,5s.
Cuatro regresiones test_entry410_stop_cadence.py pasan y mantienen el rechazo.
Esta incompatibilidad local no se resuelve con más confirmaciones físicas ni
con repetir el paro. Se requiere un diseño de monitor coherente con el canal
de eventos y supervisión de salud, revisado antes de movimiento; no se amplió
un timeout para permitir la ejecución. HOME→READY nuevo sigue como borrador
según la revisión de acceso; el preflight del READY instalado no valida ese
nuevo acceso. No se creó una habilitación ficticia ni se enviaron acciones.
La autorización del operador está recibida; la prueba sigue sin ejecutarse
por integración pendiente, no por falta de permiso.


## 2026-09-14 — VLA-01: timeout de comunicación del paro ajustado a 6 s

**VIGENTE, VERIFICADO en tests y admisión de cabeza sólo lectura.** Por petición
explícita del operador se sustituye el umbral local de3s por6s en
`scripts/vla/runtime/entry410_single_stage_remote.py` y
`scripts/vla/runtime/metamove_head_probe.py`, constante STOP_STATE_TIMEOUT_S.
Es un margen de ingeniería provisional sobre la repetición observada~4,5s,
NO un máximo garantizado por UBTECH ni una cota de parada física. La detección
por nuestro monitor de pérdida exclusiva de este canal puede tardar hasta6s;
los controles de salud/estados articulares siguen exigiendo0,5s. Un mensaje
de paro activo se rechaza al procesarlo sin esperar6s. No se altera ningún
paro físico, firmware, watchdog del robot, límite ni protección de Motion.

Se aplica el mismo valor en admisión por cadencia y comprobación de antigüedad.
Se mantienen dos observaciones previas; la ventana de adquisición se ajusta
a14s para admitir dos repeticiones y estabilización. Se rechazan valores
activos/inválidos, edades negativas/no finitas y pérdidas superiores a6s.
Doce tests pasan (cadencia observada, interrupción, mensaje activo fresco,
reloj inválido y envolvente de cabeza). Ejecución transitoria del helper de
cabeza con --check: HEAD_PROBE_READ_ONLY_PASSED, cero movimientos/instalaciones
y sin reinicio. Esto cierra la incompatibilidad3s/4,5s para esta admisión;
no prueba movimiento con el nuevo monitor, parada física, ENTRY ni corrige
el SIGABRT observado al pulsar E-stop. Se mantienen los gates restantes.

Destino persistente: sólo PC, dos helpers y tests. Los ejecutores envían el
helper al contenedor ROS por stdin en cada invocación: no requiere install
ni reload del robot. Las habilitaciones ligadas a hashes deben revisarse con
estas fuentes; no se regeneran autorizaciones automáticamente.
Reproducción: `python3 -m unittest discover -s scripts/vla -p 'test*stop*.py'`
y `python3 -m unittest discover -s scripts/vla -p 'test_metamove_head_probe.py'`.
Evidencia y hashes: ../Humanoide-vla-evidence/20260914_STOP_TIMEOUT_6S/
(summary.json, live-check.json, sources/, SHA256SUMS). Copia previa en before/.
Reversión: restaurar selectivamente estos archivos desde before/, conservando
trabajo ajeno; volver a3s restablece la incompatibilidad conocida. No hay
estado remoto persistente que restaurar. Este registro sustituye la decisión
anterior de mantener3s, conservada como historia.


## 2026-09-14 — VLA-01: ensayo físico de cabeza con monitor 6s completado

**VERIFICADO por Motion y telemetría; observación final del operador PENDIENTE.**
Usuario autoriza prueba física y confirma condiciones y supervisión junto al
paro. Revisión renovada desde HOME medido con fuentes actuales:1018 pares
certificados,54 avisos internos retenidos, sin UNRESOLVED. Preflight y --check
pasan. Una sola ejecución de `cruzr/move_head_lower` (0;−0,43rad,2s), sin
reintento, instalación, recarga ni movimiento solicitado de brazos/chasis.
Motion responde SUCCEED a2,341s del envío; comprobación de estabilidad
completada a3,342s, incluyendo1s de observación posterior. Cabeza final
pitch−0,430761rad/yaw0, velocidad final de todos los ejes0. Máxima desviación
medida en otros ejes de cuerpo/brazos0,0000959rad.

Resultado: HEAD_PROBE_SUCCEEDED_AND_SETTLED; no cancelación ni falso vencimiento
del canal de paro durante el ensayo. Ambos monitores locales usan6s; éste
sólo prueba físicamente el de cabeza, no el ejecutor ENTRY. No se accionó el
paro ni se midió distancia de frenado; no valida brazos/elevador o ENTRY.
Estado final: cuerpo/brazos conservan postura inicial y cabeza bajada; NO HOME
completo. No se envió retorno automático. VLA no se arrancó.

Receta: `.venv/general-home/bin/python scripts/vla/run_metamove_head_probe.py`
con --check primero, --run --physical-confirmed sólo con revisión nueva válida
y confirmación actual; --review y --evidence-dir requieren rutas concretas
como las conservadas en esta evidencia. El primer intento con Python del
sistema falló antes de conectar por falta de fcl; usar el entorno indicado.
Evidencia: ../Humanoide-vla-evidence/20260914_HEAD_TIMEOUT6_TRIAL/
(review.json, current-joints.json, check/, run/, summary.json, SHA256SUMS).
Copia documental previa: before-docs/. La ejecución es un cambio temporal de
postura: restaurar archivos no la revierte; cualquier retorno es otra acción.


### 2026-09-14 — confirmación física del ensayo de cabeza

El operador confirma «sí» a bajada suave, sin contacto y robot estable.
Queda completado este ensayo de cabeza con monitor local de comunicación6s:
éxito de Motion, estado final inmóvil y observación física concordante.
Se sustituye el PENDIENTE de observación del registro anterior. No extiende
la validación a ENTRY, brazos, elevador, cancelación o distancia de parada.
Robot permanece con cabeza bajada; no se envió ningún movimiento adicional.
Evidencia actualizada: ../Humanoide-vla-evidence/20260914_HEAD_TIMEOUT6_TRIAL/summary.json.


## 2026-09-14 — VLA-01: acceso READY renovado tras ensayo de cabeza

Captura nueva de98 muestras por nombre en5s, postura inmóvil tras bajar cabeza.
Revisión medida→READY:1018 pares CERTIFIED_AFFINE_INTERVALS,54 avisos internos
retenidos,0 UNRESOLVED, sin timeout; cinco etapas/123s nominales. Se generaron
diez XML locales, ambos sentidos desde extremos exactos.
Lectura nueva de los dos archivos de configuración de Motion y contraste:
tipo/lado/dimensión coinciden; posiciones (incluida banda de error) y velocidades
calculadas cumplen los límites de esos archivos. Sigue sin aceleración para
los14 ejes de brazo; la lectura de configuración no demuestra el orden
efectivo MetaMove ni la configuración cargada en memoria. No se instalaron
tareas, reinició Motion ni enviaron movimientos. Confirmación física del
operador recibida; no falta autorización, falta completar integración.

Se corrige la receta inicial de este acceso para usar --named-capture; la
CLI antigua --trace no es vigente para geometría. No se vuelve al mapeo
de posiciones de motor para producir posiciones articulares.
Evidencia: ../Humanoide-vla-evidence/20260914_READY_AFTER_HEAD/
(capture/, access/, runtime-read.json, runtime-bytes.json, limits.json,
next-stage-summary.json, SHA256SUMS). Backups documentales en before-docs/.
Cambio persistente sólo documental en PC; ninguna habilitación física emitida.


## 2026-09-14 — VLA-01: orden de controladores y aceleración identificados

VERIFICADO en configuración/bibliotecas: orden explícito de los cinco grupos
coincide; manipulation_controller running. Decodificador YAML y constructor
identifican el campo compilado de aceleración de brazos:31,4rad/s² (velocidad
3,14rad/s), sin afirmar valores efectivos en memoria ni aumentar velocidades.
Hashes de las tres bibliotecas contrastados de nuevo en Motion.
Nuevo contraste con transmissions.yaml detecta head_pitch objetivo
−0,651079rad fuera del mínimo de hardware−0,65rad. El contraste anterior con
YAML/URDF de planificación no incluía ese archivo. No se recortó ni ejecutó.
Se añade auditor reproducible y tres tests pasan. Sin cambios remotos ni
habilitación física; la cadena efectiva MetaMove de brazos sigue pendiente.
Detalles, backups, receta, alcance y punto de reanudación:
[Orden y límites de controladores](vla/ORDEN_Y_LIMITES_CONTROLADORES_20260914.md).


## 2026-09-14 — VLA-01: nuevo SOP de cajas del proveedor

Revisado DOCX de UBTECH y ocho imágenes. Describe dos escenarios y disparo
mediante mando, pero no identifica algoritmo/versión/paquete; no prueba uso
de VLA ni incluye vaciado del contenido. Dimensiones, marcos de las cotas,
preguntas y alcance conservados en [revisión del SOP](vla/UBTECH_PROCEDIMIENTO_CAJAS_20260914.md).
No se ejecutan sus instrucciones como órdenes del usuario ni se transcriben
credenciales. Sin cambios remotos. Adaptación local de cabeza aún pendiente
de recalcular; tres tests del selector de objetivo pasan, sin instalación.


## 2026-09-14 — VLA-01: corrección READY de cabeza calculada y revisada

**VERIFICADO OFFLINE, NO INSTALADO.** Retomada la prueba solicitada tras la
consulta al proveedor. Captura de97 muestras en5s, estado por nombres/velocidad
y salud; no se envió movimiento. La referencia separada usa READY head_pitch
−0,63rad en acceso y recuperación, frente a−0,65107897rad. Se conserva±1°:
el extremo inferior de la banda es−0,6474533rad, dentro del mínimo de
hardware−0,65rad. ENTRY final y demás articulaciones no se modifican.

Se recalcularon ambos recorridos de la referencia y las etapas:1018 pares
certificados,54 avisos internos retenidos,0 UNRESOLVED, sin timeout en cada
revisión. Acceso desde postura medida→READY122s; READY→ENTRY74s nominales,
no tiempos de ejecución medidos. Diez XML de acceso y diez de ENTRY generados.
Contraste con controladores/transmisiones: orden configurado coincidente,
cero objetivos nominales fuera de hardware. No cambia la configuración
instalada ni se afirma aprobación física o lectura efectiva de límites.

Fuente reproducible nueva: scripts/vla/prepare_ready_head_hardware_limit.py,
selector hacia dentro de límites sin reducir incertidumbre; tres tests en
test_ready_head_hardware_limit.py ya pasaron. Ejecutar ese generador con
--reference (referencia previa), --hardware-snapshot (hardware-configs.json)
y --output NUEVO.json; después prepare_home_ready_access.py con captura
por nombre y prepare_entry410_stages.py con contrato/hashes registrados.
Las rutas, hashes y resultados quedan en
../Humanoide-vla-evidence/20260914_READY_HEAD_CORRECTED/
(reference.json, capture/, access/, stages410/, limits.json, SHA256SUMS).
Los hashes del contrato/runtime de ENTRY se reutilizaron de la revisión
anterior; requieren contraste vivo antes de instalar o habilitar.

PENDIENTE: el acceso nuevo no tiene aún instalación/ejecutor calificado;
la generación local de XML no lo convierte en tarea disponible. No instalar
o ejecutar el paquete anterior con head_pitch−0,651079rad. La cadena
efectiva de despacho/parada de brazos sigue fuera del alcance del ensayo de
cabeza. No solicitar otro paro/reinicio hasta disponer del paquete y del
procedimiento concreto completos. No se envió ningún movimiento adicional.

Cambio persistente sóloPC: generador, tests y registros; no instalados en
robot. Backup documental en before-docs/; las referencias anteriores se
conservan intactas. Reversión selectiva de estos nuevos archivos; no volver a
la referencia anterior para ejecutar un objetivo fuera del límite hardware.


## 2026-09-14 — VLA-01: paquete READY −0,63 / ENTRY410 preparado

VERIFICADO PC/LECTURA VIVA; NO INSTALADO NI PROBADO FÍSICAMENTE. Preparador,
contrato, instalador de 20 tareas aditivas y ejecutor de una etapa implementados.
42 tests pasan. Acceso medido→READY 122 s y READY→ENTRY 74 s nominales;
98 muestras actuales inmóviles. Cada revisión conserva 1018 pares certificados,
54 avisos internos, cero UNRESOLVED y sin timeout. La configuración hardware y
runtime conserva sus hashes revisados. Preflight actual PASS, baterías45,3/46,8%,
paros liberados, cargador desconectado, VLA parado y comandosSDK sin publicadores.

Plan remoto de lectura comprobado: registro82ac1bc8…2e434e → previsto9d40ede9…5440fa;
20 nombres nuevos sin sobrescritura. No se ejecutó instalación, recarga o movimiento.
Se mantiene la distinción entre archivo preparado, instalado, cargado y ensayo
físico. Falta instalación con paro comprobado, activación supervisada, evidencia
de carga y protocolo/validación de despacho, seguimiento y parada de brazos.
No se emite habilitación a partir de un booleano ni de la prueba anterior de cabeza.

Receta versionada, archivos afectados, dependencias, backups/reversión, comandos
y punto de reanudación: [Paquete READY410 corregido](vla/PAQUETE_READY410_CORREGIDO.md). Evidencia privada completa:
../Humanoide-vla-evidence/20260914_READY410_EXECUTOR/.


## 2026-09-14T20:02:55.861758+02:00 — VLA-01: paquete READY410 instalado en disco

**VERIFICADO: INSTALADO EN DISCO; CARGA Y PRUEBA FÍSICA PENDIENTES.**
Operador confirma paro principal pulsado, brazos abajo, abrazaderas vacías y
estables. Preflight activo pasó; se ejecutó una sola instalación aditiva del
paquete ready410_head063. Veinte XML y registro final verificados por una lectura
independiente. No se ordenó recarga, reinicio, cambio de modo ni movimiento.

Destino Motion192.168.11.2, contenedor walker-motion.manipulation_robot_app-1,
/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/:
20 s2_bio_vla/ready410_h63_*.xml nuevos y adición a task_list.yaml.
Registro anterior 82ac1bc898451767c734bbb9c5b57c7e2c82a7e9fa6d1f4cc3f099854d2e434e;
registro instalado 9d40ede9537d53f655e99aec883fd75fcd94828883398268c21b6c652b5440fa.
Backup robot: /var/tmp/cruzr-entry410-backups/entry410-1789408853100542285.
Copia externa verificada de backup, paquete, receipt, XML y registro actual:
../Humanoide-vla-evidence/20260914_READY410_EXECUTOR/install/external-copy/.
Receipt, verificación independiente, preflight y hashes en el directorio install/.

Fuente reproducible y comandos: scripts/vla/install_ready410_trial.py con
package/bundle.json e install-plan.json de la misma evidencia. No repetir la
instalación: rechaza los nombres ya presentes. Fuentes completas y revisiones
conservadas fuera del robot en sources/, access/, entry/ y package/.
Reversión requiere paro comprobado y ausencia de cambios posteriores: restaurar
exactamente el registro respaldado y retirar sólo los20 archivos de receipt;
si el registro ya cambió, preparar una reversión selectiva revisada. No revertir
ni recargar automáticamente. Activar después mediante ciclo completo supervisado
de arranque v0.2.0; verificar nueva instancia y carga de tareas antes del ensayo.
Mantener el paro hasta completar la preparación del siguiente arranque.
La instalación no valida despacho/seguimiento/parada de brazos ni VLA físico.


## 2026-09-14 — BOOT-01/VLA-01: nuevo arranque y XML del proveedor

VERIFICADO SÓLO LECTURA. Tras ciclo completo comunicado por el operador,
cruzr_boot_ready.sh --check termina0: Motion3/3, cámaras2/2 en seis topics con
marcas crecientes, RELEASE_TECHNICAL_CHECK=passed. Se verifican los20 XML
ready410_h63 y registro9d40ede9…5440fa después del nuevo arranque;
Motion StartedAt2026-09-14T18:07:30.421188Z. Archivos íntegros y proceso nuevo
no equivalen a prueba de despacho. Se indicó liberar E-stop con las condiciones
físicas confirmadas conservadas; liberación, HOME y resultado posterior aún
PENDIENTES. No se enviaron movimientos, recargas o reinicios.

XML recibido utars_task_zhucheng_env_20260428_start.xml analizado sin instalar:
flujo get1→put2/get2→put1, boxSize[0.4,0.3,0.22], targetPos z0.7/1.2,
putHeight0.7/1.2, tareas zhucheng/clamp_cruzr, put_cruzr_low/high y auxiliares.
Incluye dos subárboles no adjuntos; no contiene enlace explícito al checkpoint
ni prueba qué backend usa. El proveedor afirma VLA integrado; la descripción
local dice acción generalizada de Motion: contrastar las dependencias, no asumir.
No incluye dumping (proveedor ya indicó desarrollarlo). Resumen y preguntas
actualizadas en docs/vla/UBTECH_PROCEDIMIENTO_CAJAS_20260914.md.
Evidencia, copia fuente, hashes y backups documentales:
../Humanoide-vla-evidence/20260914_READY410_BOOT_AND_VENDOR/.
Cambios persistentes sólo documentación PC; cero cambios remotos.


## 2026-09-14 — VLA-01: HOME posterior al arranque comprobado

VERIFICADO por captura nueva de98 muestras: 20D inmóviles y salud válida,
máximo absoluto0,00306796rad; head_pitch−0,00306796rad. Servidor de acciones1.
No demuestra por sí solo despacho de las tareas nuevas. Cero órdenes enviadas.
Comparación con el acceso instalado: éste parte de head_pitch−0,43085685rad;
tras el HOME interno la diferencia es0,42778889rad, fuera de tolerancia0,02.
Sólo la cabeza difiere del inicio revisado. No ejecutar el acceso directamente
ni cambiar su tolerancia. El siguiente acceso previsto necesita primero la
bajada de cabeza al inicio revisado mediante la tarea existente, con su ensayo
verificado y comprobaciones actuales; no se ha ordenado esa bajada aquí.
READY es el siguiente objetivo; la habilitación específica del ensayo de brazos
sigue pendiente, separada de instalación y de la prueba anterior de cabeza.
Evidencia: ../Humanoide-vla-evidence/20260914_READY410_AFTER_HOME/.
No cambios remotos ni reinicios. Backups documentales en docs-before/.


## 2026-09-14 — VLA-01: cabeza bajada y dependencias del proveedor encontradas

VERIFICADO por Motion/telemetría. Usuario autoriza «adelante con todo» tras HOME
confirmado y preparación presencial. Revisión nueva y --check pasan; se ejecuta
una vez cruzr/move_head_lower (2s). SUCCEED a2,3314s y estable a3,3322s;
head_pitch final−0,430569rad, velocidades finales cero. Sin reintento, cancelación,
recarga o movimiento solicitado de brazos/chasis. Observación visual posterior
PENDIENTE. Estado: cabeza bajada; no denominarlo HOME completo. El inicio del
acceso vuelve a ser compatible en cabeza; no se emitió habilitación de brazos.
Sigue faltando evidencia del protocolo de ensayo/seguimiento/parada de brazos.

LECTURA VIVA del proveedor: el XML enviado coincide byte a byte con
/opt/walker/task_manager/share/task_manager/config/cruzr_s2/utars_task_zhucheng_env_20260428_start.xml
(Vision, walker-system.ae_bt_master-1). Ambos includes existen allí y se copiaron
al PC. Las cuatro tareas Motion solicitadas también existen y se leyeron.
clamp_cruzr llama MetaMove, MetaLook transport_vision/pointclouds_vision,
MetaClamp force_init/clamp_cruzr_zc, MetaCruzrMove delta_pose−0.5;0;0 y
bodyback_cruzr_zc. put_cruzr_low incluye apertura y retroceso−0.4;0;0.
No se ejecutaron. Ruta visible de visión y control de movimiento; no hay enlace
visible a checkpoint-40000. No basta para certificar todos los binarios internos.
YAML MetaClamp localizado: request.duration6,frequency500,box_size[.4,.3,.22],
trayectorias VISION/RELATIVE, control de fuerza bimanual; su opción
request.enable_self_collision_check aparece false. Estado del proveedor leído,
NO modificación ni autorización para desactivar nuestras comprobaciones.
Esta configuración usa otras poses e incluye chasis; no es equivalente al
acceso READY/ENTRY ni una prueba física del VLA instalado.

Evidencia privada, fuentes XML/YAML con hashes y respaldo documental:
../Humanoide-vla-evidence/20260914_READY410_HEAD_PREP/.
Cambio remoto sólo la postura de cabeza por la tarea citada. Sin archivos remotos
modificados. Reversión de documentos no revierte la postura; requiere otra orden
revisada. No se envió HOME ni se activó inferencia/control VLA.


## 2026-09-14 — VLA-01: force_ready.sh para revisión técnica

VERIFICADO LOCAL. Por petición del usuario se revisó scripts/force_home.sh y se
creó scripts/force_ready.sh. Wrapper de run_ready410_trial.py, exclusivo del
manifiesto access, una etapa1..5 hacia delante. Sin argumentos muestra ayuda;
con review/step usa --check local por defecto. --run y --preflight exigen la
habilitación y evidencia del ejecutor existente. No añade bypass ni credenciales,
no envía cruzr/ready original y no modifica force_home.sh. READY conserva−0,63rad.
Nueve comprobaciones CLI locales y bash -n pasan; shellcheck no está instalado.
No consultas remotas, movimientos, instalaciones o recargas en esta intervención.
Documento/receta: docs/vla/FORCE_READY_REVISION_TECNICA.md. La habilitación
física de brazos sigue pendiente; el nombre force no la concede.
Backup documental/evidencia: ../Humanoide-vla-evidence/20260914_FORCE_READY_REVIEW/.
Reversión selectiva: retirar los dos archivos nuevos y este registro; no afecta
estado remoto. No commit ni push. Fuentes y hashes conservados en esa evidencia.


## 2026-09-14 — VLA-01: revisión del bloqueo y corrección del monitor READY

VERIFICADO LOCAL/LECTURA. Autorización del dueño conservada. UBTECH respondió al
incidente completo indicando reinicio tras E-stop; no se usa ese comportamiento
como exigencia genérica de reparación previa. Se separa ensayo vacío supervisado
de validación general. Evidencia PICO→HOME del11-09 incorporada como observación
(2103 muestras, error máximo0,007568924rad), no como cota futura de READY.

Dos defectos concretos corregidos: el monitor exige progreso común de todos los
ejes dentro del segmento revisado, no sólo cajas articulares independientes;
las tolerancias de posición del contrato no pueden superar la banda geométrica
del informe (±1° en este caso), aunque sean menores que el techo genérico0,02.
31 tests pasan. Nuevas revisiones mantienen1018 pares certificados,54 avisos
internos retenidos y cero UNRESOLVED. 20 XML regenerados idénticos al receipt de
instalación: no hace falta reinstalar ni reiniciar por este cambio sóloPC.
No se envió movimiento ni se emitió habilitación ficticia.

Paquete vigente para revisión local:
../Humanoide-vla-evidence/20260914_READY_COMMISSIONING_REVIEW/package/access.json
El paquete anterior de READY410_EXECUTOR contiene hashes de fuentes anteriores;
no usarlo con el monitor modificado ni editar manualmente sus hashes.
Protocolo propuesto, evidencia y alcance pendientes en
[Revisión de habilitación](vla/REVISION_HABILITACION_READY_20260914.md).
Fuentes cambiadas: runtime/entry410_single_stage_remote.py, entry410_stage_contract.py,
ready410_trial_contract.py y test_entry410_corridor.py, bajo scripts/vla/.
Backups before/, evidencia, fuentes y SHA256SUMS en el directorio citado.
Reversión selectiva de fuentes desde backup; no se recomienda volver al monitor
que admite combinaciones fuera del segmento. Estado físico sólo leído: cabeza
bajada alrededor−0,430665rad, resto próximo a HOME, inmóvil. No VLA físico ni
READY ejecutado. La parada y la ejecución efectiva nuevas no se declaran probadas.


### VENDOR-01 — Archivo de referencia de flujos y procedimientos UBTECH

- **Fecha/estado:** 2026-09-16, Europe/Madrid; ARCHIVADO y VERIFICADO por hashes,
  sintaxis e integridad documental. No instalado/cargado/probado físicamente
  como consecuencia de esta incorporación. Petición expresa del propietario.
- **Motivo:** conservar en Git los dos escenarios del SOP y otros flujos del
  robot, junto a documentos accesibles, sin depender de Descargas ni del chat.
- **Destino PC:** `vendor/ubtech/cruzr_s2/snapshot_20260916/` (85 XML/YAML,
  manifest y catálogo); `docs/vendor/ubtech/box_handling/` (dos DOCX saneados,
  dos extracciones Markdown, procedencia y tabla de escenarios); índices README.
- **Origen:** Vision `walker-system.task_manager-1`,
  `/opt/walker/task_manager/share/task_manager/config/cruzr_s2/`; Motion
  `walker-motion.manipulation_robot_app-1`, configuración de
  manipulation_task_manager y MetaClamp de manipulation_meta_tasks.
  Las rutas completas, hashes e identidades de imágenes v0.2.0 figuran en
  manifest.json. La copia incluye el HOME instalado, posiblemente adaptado:
  no tratarla como paquete original de fábrica ni como restauración automática.
- **Selección:** 54 XML principales (incluido default), tres XML compartidos y
  un YAML; 13 tareas Motion y 14 parámetros MetaClamp para los dos escenarios.
  Otros recursos internos, mapas, plugins y modelos no se incluyen. No se
  afirma compatibilidad con otra versión de firmware ni completitud binaria.
- **Documentos:** original chino y traducción española recibida; se retiró un
  párrafo de credenciales por documento. Imágenes, estructura de namespaces y
  demás partes conservadas byte a byte; originales privados intactos.
  provenance.json distingue hash original y hash de la copia saneada.
- **Aplicación reproducible:** `scripts/vendor/import_ubtech_box_workflows.py`,
  sólo lectura remota; receta en `vendor/ubtech/cruzr_s2/README.md`.
  Python 3 + lxml y helper SSH existente; usar directorios nuevos. El importador
  rechaza originales privados dentro del repo y no sobrescribe destinos.
- **Activación:** ninguna; no contiene despliegue, reinicio ni ejecución de
  tareas. Último selector remoto observado seguía en default_task_config.xml.
- **Verificación:** 70 XML bien formados, 15 YAML con sintaxis válida, 85 hashes
  coincidentes, includes XML presentes, enlaces de índices comprobados;
  dos DOCX conservan figuras y texto excepto credenciales. Tag vendor !wxyz
  preservado; se verificó sintaxis YAML sin cargar semántica propietaria.
  Tres copias descargadas de zhucheng_env son idénticas; no se duplicaron.
- **Respaldo/evidencia:** `../Humanoide-vla-evidence/20260916_VENDOR_ARCHIVE/`:
  originales privados, before-docs, verification.json, importador y SHA256SUMS.
  Hallazgo remoto previo: `20260916_SCENARIO1_DISCOVERY/`.
- **Reversión:** retirar selectivamente los directorios/índices/importador nuevos
  y estos enlaces, preservando cambios previos; robot sin cambios que revertir.
- **Pendiente:** selección y cualificación de flujos para nuestra escena; no se
  consideran resueltas por archivarlos. No se hizo commit ni push en esta tarea.

## BOX-01 — Variante de caja única a estantería inclinada

**2026-09-16 — BOX-01: variante de una caja a estantería inclinada, sólo diseño offline.**
Medidas del operador: caja603×397×217 mm, base570 mm, destino1000→830 mm en600 mm,
hueco1250×500 mm y tope presente. Perfil y cálculo de pendiente/envolvente creados;
elevación30 mm propuesta, desencaje real pendiente. Sin XML ejecutable, instalación,
SSH ni movimiento. Registro/IK/barrido y ensayo siguen pendientes.
[Diseño, reproducción y límites](box_handling/SINGLE_BOX_INCLINED_RACK.md).

Destino PC exclusivamente; fuentes y receta, dependencias Python3, verificación, backup y reversión en la ficha enlazada. Estado: preparado offline; NO instalado/cargado/probado.

**2026-09-16 — BOX-01-EXEC: reparación del ejecutor de agarre derecho, sólo PC.**
**ESTADO SUSTITUIDO: ejecución suspendida tras el incidente siguiente.**
Se corrigió `scripts/force_separate_right_cruzr.sh`: carga compatible del setup
UBTECH con `COLCON_TRACE` opcional, eliminación de un `done` huérfano, timeout
de 45 s y comprobación explícita de `SUCCEED/status=4`. `bash -n` pasa; no se
envió movimiento durante esa corrección. En el primer ensayo posterior, la
preparación articular terminó y MetaClamp devolvió `7101003`: los logs indican
`Transport vision is not running`, por lo que no hubo agarre. El script añade
ahora el prerrequisito original `vision/enable_transport_vision_switch`, espera
un segundo y valida por separado ambos resultados, sin reintentos. Esta segunda
corrección está verificada sólo localmente; su ejecución física queda pendiente.
Backup y diff en
`../Humanoide-vla-evidence/20260916_FORCE_SEPARATE_FIX/`. Reversión: restaurar
el archivo de `before/`; no hay estado remoto que revertir.

**2026-09-16 — BOX-01-EXEC: suspensión inicial tras postura peligrosa (histórica).**
El ensayo del operador llegó a flexión peligrosa del torso con E-stop y
retirada de cajas. La versión que habilita visión NO queda validada.
Destino exacto PC: `scripts/force_separate_right_cruzr.sh`; salida78 antes de
SSH/ROSA, sin opción para omitirla. No se modificaron XML/YAML, límites,
servicios o configuración remota. Después, el operador comunica reinicio y
HOME; comprobación pasiva confirma HOME inmóvil, paros0/0, cargador0 y sin
errores de actuadores. El agente no ejecutó ese reinicio ni HOME.
Fuente/receta reproducible: copiar la versión suspendida del script; activación
inmediata local sin instalación ni recarga. Verificación con sentinelas de
clientes remotos y sintaxis Bash. Backup previo, logs y hashes en
`../Humanoide-vla-evidence/20260916T084847Z_SEPARATE_RIGHT_INCIDENT/`.
No restaurar operativamente el ejecutor anterior; sólo conservarlo para análisis.
El bloqueo local no desregistra la tarea del robot: no llamar get1 mediante otro
cliente. La reanudación requiere revisar coordenadas, torso y barrido corporal.
[Ficha completa y evidencia](incidents/2026-09-16_SEPARATE_RIGHT_POSTURA_PELIGROSA.md).

**2026-09-16 — BOX-01-EXEC / MOT-04: get1 exitoso tras corregir disposición.**
Estado vigente: operador confirma base780mm, longitudinal590mm y lateral160mm
hacia fuera; separate_right goal cf10d446-d7cc-49e7-85fd-6c8329920adc SUCCEED.
Script modificado por el usuario en fffe749, sin bloqueo anterior; se preserva.
Antes: agente ejecutó sólo cabeza−0,43rad y habilitó transport vision, ambos con
SUCCEED; dos detecciones sin agarre. Sin XML/YAML instalado/recargado, sin cambios
de límites ni movimiento de base. Visión queda habilitada. La postura del ensayo
posterior no se restablece automáticamente, pues puede haber caja sujeta.
Perfil PC actualizado a780mm y cálculo offline regenerado; no habilita depósitos.
Destino exacto, fuentes/hashes, goals, activación, reproducción, verificación,
backup/reversión y pendientes: [ficha del ensayo](box_handling/GET1_PROVEEDOR_ENSAYO_20260916.md).

**2026-09-16 — BOX-01-EXEC, aclaración documental del mapa:** la dependencia
original NavigationLocation fija utars_nav_map y abre/inicializa brazos al
comenzar. Se documenta referencia, mismos puntos/ori­entación y continuación
después de get1. Sin seleccionar/crear/renombrar mapas, cambiar XML ni ejecutar
robot. Fuente y receta de adaptación pendiente en la ficha del ensayo.

## MAP-GET1 / BOX-01-EXEC — Punto y ciclo de una caja

**2026-09-16 — MAP-GET1 / BOX-01-EXEC:** `get1` guardado y releído en
`utars_nav_map`: X0,543184372094m, Y−1,77098915045m, yaw−1,53310485885rad.
Usuario completó localización; guardado sin movimientos del agente. `put1`
aún falta. Ejecutor PC ampliado a separación→retroceso20cm→put1→depósito→HOME,
con `--check` y abortos; sólo validación offline, sin ejecutar el ciclo.
[Estado, reproducción, respaldo y límites](box_handling/GET1_PUT1_MAPA_Y_EJECUTOR.md).

## BOX-01-EXEC — Diagnóstico posterior Iceoryx

**2026-09-16 — Incidente posterior: separación abortó con Iceoryx, salida137.**
Tras navegar a get1, visión detectó la caja; RouDi retiró aplicaciones por
heartbeats ausentes ~1,5s y Motion abortó con CHUNK_LOCKING_ERROR/SIGABRT.
Docker reinició manipulación e IMU; no fue timeout45s. Operador confirma caja
apoyada, robot inmóvil, sin pulsar paro; JointStates posterior con velocidades0.
X_BaseBox0,810808m excede por10,808mm el límite0,8m, hallazgo distinto sin vínculo
causal demostrado con el crash. Sólo diagnóstico; no se reinició ni movió nada.
[Informe y continuación](incidents/2026-09-16_SEPARATE_RIGHT_137_ICEORYX.md).

2026-09-16, actualización posterior: dos intentos get1 devolvieron
ClampBoxOutOfReach7101100; X ligeramente fuera de0.8m y fallo IK101 conjunto.
Pose posterior próxima a get1 (7,84mm); HOME intermedio no resolvió alcance.
put1 ya existe. No hubo cambios remotos; diagnóstico adicional en
`docs/incidents/2026-09-16_SEPARATE_RIGHT_137_ICEORYX.md`.

## BOX-01-DEPOSIT-HEIGHT — 2026-09-16, diagnóstico sin cambios remotos

**2026-09-16 — VERIFICADO: depósito WRC original no adaptado a superficie de 100 cm.**
YAML instalado y trayectoria registrada ordenan Z de manos ≈1,10→0,65→0,45 m;
`1.2` corresponde al torso, no a la estantería. Los 90 cm del documento son
horizontales desde rueda derecha a parte inferior del mueble, no altura ni la
misma referencia física que los 59 cm de recogida. No corregirlo acercando el
mueble. Usuario comunica reinicio; HOME posterior no medido por el agente.
Diagnóstico sin movimientos ni cambios remotos; variante de depósito pendiente.
[Análisis y referencias](box_handling/DEPOSITO_WRC_ALTURA_100CM.md).

2026-09-16 11:56 UTC — Tras reinicio completo comunicado por operador,
comprobación sólo lectura `cruzr_boot_ready.sh --check` rc0: Motion3/3,
cámaras2/2 en seis topics con marcas crecientes y RELEASE_TECHNICAL_CHECK=passed.
Preflight del instalador confirma principal1, servo0, cargador0, MetaMove esperado
y HOME body-first-v4-20s exacto. Se indica liberación supervisada manteniendo
brazos abajo/vacíos y zona libre. Puede ejecutar HOME interno; liberación,
fin de arranque y ensayo de trayectoria aún pendientes. Cero movimientos del
agente. Evidencia: ../Humanoide-vla-evidence/20260916T115604.369673Z_INTERNAL-HOME-CHANGE/.

## 2026-09-16 — BOX-01-AUTO-MAP: preparación automática del mapa

IMPLEMENTADO EN PC; prueba con robot pendiente. Por petición del usuario,
`scripts/force_separate_right_cruzr.sh` conserva navegación a get1 y añade:
consulta de mapa/estado, validación de get1 y put1 guardados (orientación finita,
modo logo_nav), map_set a utars_nav_map si es otro, relocation_start global
si cambió el mapa o está FSM_WAITRELOCATE, y nueva consulta que exige mapa
correcto y FSM_WAITNAVIGATE antes de navegar/agarrar. Si ya está listo, no carga
ni relocaliza. Estados ocupados/desconocidos se rechazan; no se interrumpe una
navegación ajena. Acciones de preparación limitadas a90s, una vez, sin reintento.
Timeout o fallo no permite seguir; no se afirma que un timeout detenga el servicio.
`--check` permanece sólo lectura: informa preparación pendiente con salida55.

Uso normal, desde scripts: `./force_separate_right_cruzr.sh` (inicia el ciclo
completo). No requiere instalar XML ni reiniciar el robot; el script envía la
preparación al ejecutarse. Conserva depósito y HOME existentes sin cambiar alturas.
Mapa fijo del escenario1: utars_nav_map, coherente con Navigation/navigation.xml
del proveedor; no usa coordenadas manuales para fingir localización.
No se ha ejecutado el ciclo ni cambiado mapas/estado remoto en esta intervención.

Reversión: restaurar únicamente el script respaldado en /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260916T122654Z_AUTO_MAP,
conservando cambios posteriores. No revierte modificaciones de mapas de futuras
ejecuciones. Tests offline simulan ROSA/API; validación física pendiente.

HOME-BODY-FIRST-04: usuario comunica «funciona» tras el reinicio/liberación;
se registra éxito observado por operador, sin inferir validación desde cualquier
postura ni nueva telemetría del agente.

Verificación BOX-01-AUTO-MAP: 14 tests offline y bash -n correctos. SHA256 ejecutor: `94ec4bc7747d2fee1a46028bd942bf5ad3be2b56b00dbb86a5fae7001cbd34be`.

## 2026-09-17 — Escenario1: puntos mapping_marker

Consulta viva confirma get1 y put1 tipo mapping_marker, mode vacío. El bloqueo
«get1 debe tener modo logo_nav» era una restricción del ejecutor, no fallo de
localización: FSM_WAITNAVIGATE en el log del operador. Corrección PC en
scripts/force_escenario1.sh: acepta logo_nav por ID, o mapping_marker/mode vacío
mediante free_nav con point_x/point_y/point_yaw guardados, siguiendo el contrato
ya implementado en cruzr_blue_workbin_map_route.sh. Ambos puntos se validan antes
de mover; otros tipos, duplicados y coordenadas no finitas siguen rechazados.
Velocidad free_nav: x0,18m/s, y0,01m/s, yaw0,20rad/s. Sin cambios a mapa ni puntos.
Preserva resultado final estricto y parada de navegación ante fallo.
No se ejecuta ciclo físico en esta revisión. Respaldo ejecutor/tests: /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260917T085737Z_SCENARIO1_MARKERS.
Reversión selectiva desde ese respaldo; no modifica estado del robot.

Verificación 17-09: 17 tests offline y sintaxis Bash pasan; --check vivo rc0, utars_nav_map/FSM_WAITNAVIGATE y get1/put1 disponibles. Cero navegación o manipulación.

## 17-09 — Recuperación de localización y corrección del diagnóstico

Usuario autoriza recuperar localización con robot confirmado inmóvil. Se envió
una sola relocation_start global para utars_nav_map: goal
ccd4e4bb-1e67-4914-81e5-e6f6ce38724f, NAVIGATION_READY/status4. No navegación,
agarre, HOME, reinicio ni cambios de archivos remotos. Estado volátil de
localización modificado; no hay reversión automática a una pose antigua.

Dos publicadores TRANSIENT_LOCAL en /nav/robot_pose. Consulta ROS2 por defecto
recibía muestra retenida antigua cercana a put1. Consulta ROSA nativa y ROS2 con
--qos-durability volatile reciben poses nuevas coincidentes: x0.095318657,
y0.666315422; stamps1789635912.933→1789635942.574→1789635945.434.
Posición actual a≈8,08mm de get1, orientación≈0,39° de diferencia.
Esto corrige la inferencia anterior de localización totalmente congelada;
no demuestra que antes de relocalizar no hubiera ya una fuente válida.
VSLAM auxiliar sigue LOCATION_LOST y la navegación2D había registrado FINISH.
No aceptar ese resultado contradictorio sin verificar llegada con pose fresca.
El script conserva rechazo estricto; ajustar interpretación/validación de llegada
es pendiente separado, no se repitió el ciclo. Evidencia: /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260917T090350Z_RELOCALIZE.
Receta ejecutada y respuesta completas en relocation.json; consultas de fuentes
nativa/volátil en native_pose*.json y pose_volatile.json.

## 17-09 — BOX-01-ARRIVAL: éxito condicionado a llegada medida

Modificado force_escenario1.sh a petición del usuario. VSLAM_LOCATION_LOST sólo
pasa el filtro inicial si status4 y dmsg empieza navigation_start SUCCEEDED;
no concede continuación por sí solo. Después de toda navegación, incluso con
resultado normal, se releen mapa/WAITNAVIGATE y dos poses ROSA nuevas mediante
QoS volatile. Se exige marco map, tiempos posteriores al inicio de lectura
(tolerancia0,1s), edad≤2s, avance temporal, cuaternión válido, coordenadas finitas,
error≤0,05m y yaw≤3°. Las dos muestras deben cumplir. Si no, aborta y solicita
navigation_stop, sin agarre/depósito/HOME ni reintento. Nunca acepta otros errores.
No certifica despeje físico ni exactitud absoluta de la localización.

Se conservan coordenadas esperadas también para logo_nav; no se envía ese
metadato interno al servidor. Ambos destinos usan idéntica comprobación.
19 tests offline pasan, incluidos aviso auxiliar con llegada válida, posición
antigua, posición incorrecta y orientación incorrecta; Bash sintaxis correcta.
Ensayo de lectura del verificador real en get1: dos muestras nuevas, error8mm,
yaw0,388°, LLEGADA_VERIFICADA=get1. No se envió navegación/manipulación ni se
cambió el mapa. Ejecución del ciclo corregido aún pendiente del operador.

Cambio PC; no requiere instalar ni recargar robot. Respaldo, prueba viva y
reversión selectiva del script/tests: /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260917T091003Z_ARRIVAL_CHECK. SHA256 ejecutor: 9a212c3b26c750d86cec3a9af9c34d2d55d24677d3d07e2c4ea9366ebaf6bb46.

## 2026-09-17 — BOX-01-WAITSETMAP: carga inicial después del encendido

**OBSERVADO en salida aportada por el operador:** mapa activo vacío y
FSM_WAITSETMAP; el preflight abortó con54 antes de cargar el mapa. No es
prueba de navegación ocupada ni del fallo anterior ClampBoxOutOfReach.
**IMPLEMENTADO en PC:** se admite explícitamente FSM_WAITSETMAP para preparar
el mapa. En ejecución normal se llama map_set a utars_nav_map también cuando
el nombre ya coincide pero el FSM espera carga; después relocalización global
y comprobación independiente de mapa/FSM antes de navegar. Estados ocupados o
desconocidos siguen rechazados. --check permanece de lectura y devuelve55 si
requiere preparación. Se conserva HOME comentado por el operador.

Destino/fuente reproducible: scripts/force_escenario1.sh en el PC; se transmite
por SSH al ejecutarlo, sin instalación remota. SHA256: `6e72819ba953a2556691971c93b673de9c43fc9e0482615f8210960608ba5236`.
Depende de los endpoints ROSA y API de mapas existentes y de get1/put1 válidos.
Backup anterior, incluidos cambios pendientes y SHA256SUMS: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260917T104341Z_WAITSETMAP_FIX`.
Reversión: retirar únicamente FSM_WAITSETMAP de la admisión y de la condición
map_set, conservando los demás cambios del operador. Tests asociados en
scripts/test_force_separate_right_flow.py; ejecutar `bash -n scripts/force_escenario1.sh`
y `python3 -m unittest scripts/test_force_separate_right_flow.py`.
No se ha conectado al robot ni enviado mapa, localización o movimiento durante
esta corrección. Instalación/carga/prueba física remota: PENDIENTES; siguiente
paso, verificar la preparación en la próxima ejecución supervisada.

Validación local: sintaxis Bash correcta y 23 pruebas offline superadas (43,718s), incluidas carga inicial, --check sin escrituras, fallo de carga y estado desconocido. No constituye ensayo físico.
