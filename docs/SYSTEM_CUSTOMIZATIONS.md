# Registro de adaptaciones del sistema Cruzr S2

Última consolidación: **2026-09-10, Europe/Madrid**. Política obligatoria:
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
| MOT-01 | HOME interno con brazos abiertos, 20 s | Motion: XML dentro del contenedor | Revisar **antes del primer HOME** |
| MOT-02 | PICO→HOME abierto; 4× por defecto | PC + tareas de Motion | Reinstalar cada perfil requerido y su registro |
| ANL-01 | Comparador offline de trayectorias con abrazaderas | PC, sólo análisis | Conservar fuentes, modelos y evidencia; no se instala en el robot |
| MOT-03 | PICO sólo brazos | Motion: YAML dentro del contenedor | Comparar original/overlay y carga efectiva |
| MOT-04 | Tareas READY/recovery adaptadas a S2 | Motion: XML + task_list | Revisar por tarea; no restaurar task_list entero |
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

### MOT-01 — HOME interno abierto, 20 segundos

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
  Ensayo físico 4× pendiente en la última evidencia.
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

### ANL-01 — Comparación offline de geometría y tiempos

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
