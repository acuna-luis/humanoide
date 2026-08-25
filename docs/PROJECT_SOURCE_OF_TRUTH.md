# Cruzr S2 — fuente de verdad global del proyecto

**Última actualización:** 25 de agosto de 2026  
**Unidad:** Cruzr S2, SN `WAE001UBT60000669`  
**Propósito:** relevo técnico y operativo entre sesiones, personas y agentes

Este documento es el índice vivo del proyecto completo. Conserva el estado
conocido del robot, las modificaciones persistentes, lo que ya funciona, los
bloqueos y el punto de reanudación. No sustituye las guías especializadas ni
certifica el estado físico actual.

`AGENTS.md` obliga a Codex a leer esta fuente al iniciar una sesión desde el
repositorio. Si se modifica aquí una condición material, debe actualizarse
también la fuente especializada enlazada.

## 1. Cómo interpretar el documento

- **VERIFICADO:** demostrado en esta unidad mediante estado, archivos, hashes,
  logs, topics, servicios o una prueba controlada.
- **OBSERVADO:** visto durante una prueba, pero sin causa interna totalmente
  demostrada.
- **INFERENCIA:** explicación compatible con la evidencia que requiere otra
  prueba o confirmación del proveedor.
- **PENDIENTE:** no probado, no resuelto o no contestado por DSA/UBTECH.
- **DESCARTADO:** hipótesis o workaround contradicho por la evidencia.

Una observación histórica no autoriza movimiento. Al retomar, comprobar de
nuevo el estado físico y lógico.

## 2. Relevo vigente

### 2.1 Último estado conocido

| Elemento | Último estado documentado | Confianza |
|---|---|---|
| Postura | `cruzr/home` terminó con `SUCCEED/status=4` | **VERIFICADO** |
| Modo web | restaurado a `JoystickMode` | **VERIFICADO** |
| Efector | abrazaderas laterales vacías; `HW_TYPE=cruzr_s2_v1` | **VERIFICADO** |
| Teleoperación PC | procesos, UI y listeners detenidos intencionadamente | **VERIFICADO** |
| Servicio PC | puede seguir habilitado y reaparecer tras reiniciar el PC | **PENDIENTE DE RECOMPROBAR** |
| VLA | contenedores detenidos, `restart=no`, sin mando físico | **VERIFICADO** |
| Cargador | el último preflight lo detectó conectado | **HISTÓRICO; RECOMPROBAR** |
| Paros, ruedas y zona | no se deben inferir del relevo | **ESTADO ACTUAL DESCONOCIDO** |
| Mapa/localización | `test_route_01` se conservó; activación y localización son volátiles | **RECOMPROBAR** |

La rama `main` estaba limpia y sincronizada con `origin/main` en el commit
`4536f8a` antes de crear esta fuente global. El estado Git actual prevalece
sobre esa referencia.

### 2.2 Primeros pasos de la siguiente sesión

Sin mover el robot:

```bash
git status --short --branch

# Elegir sólo los diagnósticos relacionados con la tarea.
./scripts/cruzr_blue_workbin_cycle.sh --check
./scripts/cruzr_blue_workbin_table_transfer.sh --check --fast
./scripts/teleoperation/cruzr_pico_teleop_pc.sh --check
./scripts/vla/run_ubtech_vla_shadow.sh --status
```

El diagnóstico de teleoperación exige que estén presentes los enlaces que
pretende comprobar; no debe interpretarse un fallo por PICO desconectado como
un defecto nuevo del robot. Consulte siempre `--help` antes de usar modos de
movimiento o recuperación.

## 3. Inventario técnico consolidado

### 3.1 Robot y red

| Componente | Valor conocido | Estado |
|---|---|---|
| Modelo | Cruzr S2 | **VERIFICADO** |
| Número de serie | `WAE001UBT60000669` | **VERIFICADO** |
| Software | genérico `v0.2.0` en Motion y Vision | **VERIFICADO** |
| Motion | Ubuntu 22.04, `192.168.11.2` | **VERIFICADO** |
| Vision/web | `192.168.11.3` | **VERIFICADO** |
| PC Ethernet | `192.168.11.250/24` | **VERIFICADO** |
| Efector actual | abrazaderas | **VERIFICADO** |
| `HW_TYPE` | `cruzr_s2_v1` | **VERIFICADO** |
| `TELE_DEVICE` | `pico` | **VERIFICADO** |
| `transmit` | `local` | **VERIFICADO** |
| `MC_SCENE` | vacío en contenedores inspeccionados | **VERIFICADO; DIFERENCIA CON SOP** |

Las credenciales del robot no se versionan. Las rutas Wi-Fi pueden diferir de
las rutas Ethernet; deben descubrirse en cada sesión.

### 3.2 Efectores

- Las abrazaderas son el efector operativo actual. La configuración coherente
  es `HW_TYPE=cruzr_s2_v1`.
- Las manos v4 se instalaron físicamente, se detectaron mediante
  `/mc/left_hand/joint_states` y `/mc/right_hand/joint_states`, y se probaron
  tareas de fábrica. Después se retiraron y se restauraron las abrazaderas.
- Con manos v4 se observó `HW_TYPE=cruzr_s2_v1_sps`. No reutilizar ese valor
  con abrazaderas.
- Las demostraciones de manos son trayectorias fijas, no manipulación autónoma.
  La coreografía de corazón requirió iteración y llegó a dejar un dedo en
  contacto con el torso; no debe ejecutarse desde una postura desconocida.

Guía: [`../scripts/hands/README.md`](../scripts/hands/README.md).

### 3.3 Mapa, estaciones y referencias

- Mapa: `test_route_01`.
- Waypoints conocidos: `START`, `PASO1`, `PASO2`, `PASO 3`, `PASO4`,
  `FINISH`, `MESA2_PRE`.
- La misión mesa 1 → mesa 2 no necesita pasar por `PASO1`; el destino global
  es `MESA2_PRE`, seguido de alineación local.
- AprilTag mesa 1: ID 112, familia `tag36h11`, lado negro medido 75 mm,
  `tag_size=0.075`; uso opcional.
- AprilTag mesa 2: ID 113, familia `tag36h11`, lado negro medido 73,5 mm,
  `tag_size=0.0735`; referencia del depósito.
- El tag 113 se detectó con márgenes de decisión altos y medidas estables. Hay
  referencias separadas para robot vacío y con caja sujeta porque la postura
  de transporte cambia la transformación cámara-tag.
- Activar el mapa no equivale a estar bien localizado. Después de un arranque,
  actualización o movimiento manual hay que validar la pose contra el entorno
  LiDAR antes de navegar.

Guía y valores completos:
[`guides/TRANSFERENCIA_CAJA_ENTRE_MESAS_CON_APRILTAG.md`](guides/TRANSFERENCIA_CAJA_ENTRE_MESAS_CON_APRILTAG.md).

### 3.4 Caja de ensayo y carga

- Contenedor azul de plástico, aproximadamente `600 × 400 × 220–230 mm`.
- Las pruebas descritas se hicieron con la caja vacía o ligera.
- DSA/UBTECH indicó por chat una carga útil máxima bimanual de 20 kg y un rango
  recomendado de 10–15 kg. Es una afirmación del proveedor, no una curva de
  payload validada para cualquier alcance, centro de gravedad o aceleración.
- No extrapolar las pruebas de caja vacía a carga industrial sin commissioning
  mecánico y límites documentados.

## 4. Cambios persistentes realizados en el robot

### 4.1 Actualización v0.2.0

**VERIFICADO:** se aplicó el paquete offline genérico v0.2.0 en Motion y
Vision. Antes se respaldaron configuraciones y mapas. El flujo estándar
`udoke replace` no recibió `upload-confirm` en tres intentos, por lo que se
aplicó el fallback manual incluido en el SOP: preinstalación, sustitución de
configuración, despliegue uDoke y postinstalación.

Se preservaron:

- mapa `test_route_01` y su checksum;
- configuración de abrazaderas `HW_TYPE=cruzr_s2_v1`;
- acceso web, navegación, manipulación y visión.

Detalles y reporte al proveedor: [`../upgrade.txt`](../upgrade.txt) y
[`../upgrade_summary.txt`](../upgrade_summary.txt).

### 4.2 Servicios estabilizados tras la actualización

- `main.x86` y `main.orin`: plantillas sin comando que reiniciaban en bucle;
  se dejó su reinicio automático deshabilitado.
- Cliente MQTT cloud: se bloqueaba con `segmentation fault` en el callback de
  batería; se dejó detenido y sin reinicio automático. El MQTT local/upilot
  permaneció estable.
- Netdata Vision: contenedor activo pero health check local de `19999` no
  saludable; pendiente de corrección oficial.
- Frecuencia GPU Vision: el script oficial informó 1,224 GHz frente a objetivo
  1,122 GHz; pendiente de confirmación del proveedor.

Estos cambios son workarounds locales y deben revisarse después de cualquier
actualización oficial.

### 4.3 Guard de arranque v0.2.0

**VERIFICADO:** Vision arrancaba Control Center antes de que Motion ofreciera
servicios x86 funcionales. El self-check fallaba, la cara quedaba roja y la
cabeza baja. Se instaló en Vision un guard reversible que:

- espera versión exacta v0.2.0 y servicios Motion funcionales;
- exige respuestas reales de self-check y muestras de las seis cámaras;
- sólo recupera el patrón `Fault` conocido con paros/cargador seguros;
- reinicia Control Center una vez, exige `StartMotion` y `JoystickMode`;
- devuelve la cabeza a la tarea oficial de home.

Archivos instalados en Vision:

```text
/usr/local/sbin/cruzr-v020-boot-guard
/etc/systemd/system/cruzr-v020-boot-guard.service
/usr/local/share/doc/cruzr-v020-boot-guard.md
```

Guía, comprobación y rollback:
[`guides/CRUZR_V020_BOOT_GUARD.md`](guides/CRUZR_V020_BOOT_GUARD.md).

### 4.4 VLA suministrado

**VERIFICADO:** se instalaron las imágenes, workspaces y
`checkpoint-40000` suministrados. Los dos contenedores se mantienen detenidos
con `restart=no`.

Se añadió un overlay local para:

- usar el perfil S2 correcto de 20 ejes;
- leer `/mc/whole_joint_states` como fuente read-only, porque
  `/mc/sdk/robot_state` no entregaba muestras;
- montar la variante GR00T suministrada y los metadatos de inferencia;
- validar chunks sin importar ni publicar `RobotCommand`.

La inferencia shadow produjo chunks finitos de forma esperada y confirmó cero
publicadores en `/mc/sdk/robot_command`. Desde `home`, los chunks se rechazaron
por diferencias de hasta aproximadamente 1,35 rad en ocho articulaciones. No
se habilitó movimiento VLA.

Fuente: [`guides/CRUZR_S2_VLA_SAFE_ENABLEMENT.md`](guides/CRUZR_S2_VLA_SAFE_ENABLEMENT.md).

### 4.5 Teleoperación del robot

Se verificaron `TELE_DEVICE=pico`, `transmit=local`, `signal_server`,
`rtm_receiver` y la tarea
`teleoperation/cruzr_clamp_pico_teleoperation`. No se renombraron topics,
colas o servicios del robot.

`walker28` es exclusivamente el `channel_name` del backend PC. El nombre
`walker28_web` no se encontró en el frontend ni en el sistema inspeccionado.

### 4.6 Tareas auxiliares y scripts

El repositorio contiene XML auxiliares y scripts para brazos, voz, manos,
cajas, navegación, recovery, VLA y teleoperación. Algunos scripts pueden
instalar tareas versionadas en el árbol de manipulación del robot antes de
ejecutarlas; su presencia debe comprobarse mediante los modos `--check` y los
hashes incorporados. No asumir que una tarea local está instalada tras una
actualización.

Los scripts se migraron a los nombres de imágenes/tareas observados en v0.2.0.
La migración se validó sin instalar tareas nuevas ni mover el robot.

## 5. Cambios persistentes en el PC de teleoperación

### 5.1 Paquetes instalados

- XRoboToolkit PC Service `1.0.0.0` para Ubuntu 24.04.
- `ubt-controller` `5.3.0` entregado con nombre Ubuntu 22.04.
- `ubt-remote-control` `4.1.0`.
- ADB y regla udev para PICO.
- Servicio systemd `/etc/systemd/system/ubt-controller.service`.

Instaladores grandes y SOP se mantienen fuera de Git; sus hashes están en la
fuente de teleoperación y en [`../utats/README.md`](../utats/README.md).

### 5.2 Configuración y workarounds PC

- Ethernet al robot fijada en `192.168.11.250/24`.
- Backend con `transmit=local`, señalización
  `ws://192.168.11.3:4000`, `channel_name=walker28`, dispositivo PICO y pedal
  deshabilitado.
- Se corrigió la selección de efector del backend de `GRIPPER` a `CLAMP`.
- Se reconstruyó el binario del backend de forma reproducible para mapear el
  gatillo izquierdo al booleano que el proveedor asigna a Y. La estructura se
  verificó, pero el flanco físico extremo a extremo no llegó a validarse.
- Se mejoró orden de arranque: servicio XR y PICO antes del backend; UI al
  final. Una desconexión/suspensión del visor puede exigir reinicio del
  servicio.

El binario original permanece respaldado; los hashes original y activo están
en la fuente especializada.

### 5.3 Último estado PC

El cliente quedó detenido intencionadamente: sin `ubt_controller`,
`RoboticsServiceProcess`, UI ni listeners `8082/63901`. El servicio systemd
puede seguir habilitado, de modo que este hecho debe recomprobarse tras cada
arranque antes de intentar PICO directo u otro cliente.

Fuente completa:
[`teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md`](teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md).

## 6. Capacidades verificadas

### 6.1 Operación y diagnóstico

- Lectura de batería, cargador, paros, sensores y estado de potencia.
- Control web y cambio de modos de trabajo.
- Mando físico para elevador/chasis después de rearme correcto y desbloqueo de
  ruedas.
- TTS en inglés y ASR capaz de transcribir inglés; español funciona peor.
- Cámaras, LiDAR, RGB-D/estéreo y navegación con evitación de obstáculos.

### 6.2 Manipulación tradicional, sin VLA

- Detector especializado `workbin` de UBTECH/DSA para pose 6D de contenedores.
- Centrado visual, agarre bimanual BYD, elevación y depósito mediante tareas
  deterministas.
- Control de separación y fuerzas durante el agarre.
- Transferencia de la caja azul desde mesa 1 a mesa 2 mediante detector,
  navegación, waypoint y AprilTag; un ciclo `--resume-held` completó depósito,
  retroceso de aproximadamente 0,484 m y `home`.
- AprilTag 113 detectado y calibrado para pose vacía y pose con carga.

GR00T/VLA no intervino en esas pruebas. La adaptación procede de detección 6D,
transformaciones, realimentación de fuerza y secuencias programadas.

### 6.3 Manos

Con manos v4 instaladas se verificaron topics y tareas de fábrica para apertura,
cierre, pinzas de dedos, gestos y secuencias. Las manos ya no están instaladas.

### 6.4 VLA

- Checkpoint suministrado cargable en v0.2.0 mediante overlay.
- Inferencia y validación shadow sin publicar a control físico.
- Cuatro IDs documentados: recoger/depositar caja grande en nivel inferior y
  medio.
- No se ha demostrado una ejecución física segura del checkpoint.

Catálogo detallado:
[`guides/CATALOGO_FUNCIONALIDADES_CRUZR_S2.md`](guides/CATALOGO_FUNCIONALIDADES_CRUZR_S2.md).

## 7. Problemas conocidos y decisiones vigentes

### 7.1 PICO/teleoperación — bloqueo P0

La cadena PICO → PC → robot llegó a `Working`, señalización, DataChannel y
recepción de tele-data. No se obtuvo movimiento físico sostenido y validado:
el PC no recibió el heartbeat de aplicación esperado y el robot deshabilitó
la sesión aproximadamente cada 11,1 s.

El SOP exige `utars-udoke-config-v0.2.0-dac-beta.2.tar.gz`, pero sólo está
demostrada la build genérica v0.2.0. Además, `MC_SCENE` está vacío y no se
encontró `pico_control`, aunque ambos aparecen en el SDK/SOP.

Decisiones:

- no puentear el watchdog;
- no declarar lista la teleoperación por ver sólo `Working`, `TeleopMode` o un
  topic existente;
- no ejecutar a la vez el cliente PC y un supuesto cliente PICO directo;
- exigir un gate monitorizado de 60 s antes de cualquier movimiento mínimo;
- pedir a DSA paquete DAC exacto, hashes, matriz de versiones, componente de
  heartbeat y procedimiento directo.

Fuente viva obligatoria:
[`teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md`](teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md).

### 7.2 Navegación transportando caja

La caja puede aparecer ante las cámaras RGB-D/estéreo como obstáculo propio y
bloquear el costmap dinámico. Se creó un perfil temporal de percepción de
carga que redirige únicamente tres entradas de nube de puntos; mantiene LiDAR,
odom, mapa, bumpers y paros. El último preflight registró
`CARGO_PERCEPTION_PROFILE=disabled`, es decir, restaurado.

Nunca desactivar toda la evitación ni dejar el perfil activo después del
transporte.

### 7.3 Depósito y AprilTag

- Una tolerancia demasiado estricta causaba múltiples correcciones aunque la
  caja ya estuviera razonablemente sobre la mesa.
- El perfil `--fluid` acepta hasta 50 mm en la estación validada, con límites
  duros y menos muestras/iteraciones.
- Una lectura vertical no se corrige con el chasis. La postura de cabeza y
  brazos debe coincidir con la calibración.
- La aproximación autónoma se interrumpe si la orientación o la detección es
  inestable; no debe abrir las abrazaderas al fallar.

### 7.4 Arranque y apagado

- La carrera de arranque v0.2.0 está mitigada mediante boot guard local.
- El manual oficial exige un `Servo Control Button` no identificable en esta
  revisión física.
- La máquina de estados v0.2.0 pide pulsar el paro rojo después de aceptar un
  apagado, aunque el manual no lo incluye como apagado normal.
- Usar `KEY1` aisladamente produjo un corte compatible con apagado abrupto y
  corrupción de logs Docker. No debe usarse como sustituto del apagado lógico.
- El procedimiento definitivo aplicable a este número de serie sigue
  pendiente de DSA.

Fuente:
[`support/UBTECH_SHUTDOWN_PROCEDURE_MISMATCH_V020.md`](support/UBTECH_SHUTDOWN_PROCEDURE_MISMATCH_V020.md).

### 7.5 Baterías/BMS

Históricamente se observó gran diferencia de SOC y truncamiento del segundo
número de serie. Tras la actualización se registraron SOC equilibrados y
números completos, pero la respuesta técnica del proveedor sobre el fallo
histórico sigue pendiente. La UI también llegó a mostrar “fault” sin error de
powerboard. No borrar alarmas ni asumir que son falsas sin comprobar BMS.

### 7.6 Voz

ASR transcribió frases inglesas cuando `run_record`/chatting estaban en el
estado adecuado. Los topics no siempre emitían; se llegó a recuperar texto del
log del motor ASR. El español se reconocía peor. No existe una lista completa
confirmada de órdenes industriales por voz.

### 7.7 Soporte documental y proveedor

Siguen abiertos, entre otros: build DAC exacta, heartbeat, apagado actualizado,
corrección oficial del boot race, cliente MQTT, Netdata, GPU, documentación de
payload, pipeline teleoperación → LeRobot, certificado de conformidad y reporte
de inspección de fábrica.

Seguimiento:
[`support/UBTECH_SUPPORT_TRACKER.md`](support/UBTECH_SUPPORT_TRACKER.md) y
[`support/UBTECH_OPEN_QUESTIONS.md`](support/UBTECH_OPEN_QUESTIONS.md).

## 8. Matriz de reanudación por tarea

### 8.1 Diagnóstico o recuperación de postura

1. Confirmar visualmente efector, carga y obstáculos.
2. Ejecutar `./scripts/cruzr_recover_to_home.sh --check`.
3. Leer `--help` y elegir el modo de recuperación compatible con el estado.
4. No enviar `home` con una carga o contacto dentro de la trayectoria.

### 8.2 Caja mesa 1 → mesa 2

1. Leer la guía AprilTag completa.
2. Ejecutar `--check --fast` o preparar `--check --fluid`.
3. Primera puesta en servicio: `--stage-held`; inspeccionar en `MESA2_PRE`.
4. Con caja ya sujeta, usar el modo de reanudación apropiado; no reiniciar el
   ciclo completo.
5. Confirmar visualmente tag, mesa y estabilidad antes del depósito.

Script canónico:
`scripts/cruzr_blue_workbin_table_transfer.sh`.

### 8.3 PICO

1. Leer la fuente PICO completa, incluida la checklist P0.
2. Comprobar que no hay otro cliente ni servicio reactivado.
3. Recuperar ADB/red/`Working`; verificar tracking y backend por separado.
4. Resolver o demostrar heartbeat estable durante 60 s.
5. Sólo después considerar una prueba física mínima con deadman y paro.

### 8.4 VLA suministrado

1. Mantener contenedores detenidos salvo diagnóstico solicitado.
2. Usar `--status` y shadow, nunca un ejecutor físico implícito.
3. Registrar la postura oficial ready y repetir shadow desde ella.
4. Resolver task-ID, primitiva de trayectoria, límites y deadman antes de
   publicar a control.

### 8.5 Nuevo dataset/checkpoint

1. No iniciar una campaña grande hasta exportar y auditar un episodio piloto.
2. Capturar misión, fases, observaciones sincronizadas, acciones, estado,
   fuerza, cámaras, transformaciones, mapa/waypoints, AprilTags y resultado.
3. Separar navegación global, alineación local, pick, transporte y place.
4. Mantener variantes de caja/pose/iluminación y negativos/recovery en splits
   por escenario, no por frames.

Fuente:
[`vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md`](vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md).

### 8.6 Manos

Las manos no están instaladas. Para retomarlas: SOP físico, `HW_TYPE` correcto,
homing, `check_hands.sh`, ensayo `--check` y luego demostración vacía. No usar
scripts de manos con abrazaderas.

## 9. Qué no debe darse por hecho

- Que la postura o el modo descritos aquí siguen vigentes.
- Que mapa cargado significa localización correcta.
- Que `Working` del PICO significa teleoperación autorizada.
- Que un topic DDS anunciado está publicando muestras frescas.
- Que `status=6` con `RUNNING` es éxito; en acciones ROS 2, el éxito observado
  ha sido `status=4` con `SUCCEED`.
- Que una tarea de manos, caja o VLA sigue instalada después de actualizar.
- Que `KEY1` es el botón de apagado lógico.
- Que una caja ligera valida la carga nominal.
- Que un detector workbin generaliza a botellas u otras clases.
- Que una reproducción `.motion` es una política adaptativa.

## 10. Estructura y fuentes canónicas

| Tema | Fuente canónica |
|---|---|
| Contexto global | este documento |
| Teleoperación PICO/PC/robot | [`teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md`](teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md) |
| Handoff histórico PICO | [`teleoperation/CRUZR_S2_PICO_TELEOP_HANDOFF_2026-08-24.md`](teleoperation/CRUZR_S2_PICO_TELEOP_HANDOFF_2026-08-24.md) |
| Captura y entrenamiento VLA | [`vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md`](vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md) |
| VLA instalado y shadow | [`guides/CRUZR_S2_VLA_SAFE_ENABLEMENT.md`](guides/CRUZR_S2_VLA_SAFE_ENABLEMENT.md) |
| Cajas y AprilTags | [`guides/TRANSFERENCIA_CAJA_ENTRE_MESAS_CON_APRILTAG.md`](guides/TRANSFERENCIA_CAJA_ENTRE_MESAS_CON_APRILTAG.md) |
| Capacidades y ejemplos | [`guides/CATALOGO_FUNCIONALIDADES_CRUZR_S2.md`](guides/CATALOGO_FUNCIONALIDADES_CRUZR_S2.md) |
| Manos | [`../scripts/hands/README.md`](../scripts/hands/README.md) |
| Boot guard | [`guides/CRUZR_V020_BOOT_GUARD.md`](guides/CRUZR_V020_BOOT_GUARD.md) |
| Apagado | [`support/UBTECH_SHUTDOWN_PROCEDURE_MISMATCH_V020.md`](support/UBTECH_SHUTDOWN_PROCEDURE_MISMATCH_V020.md) |
| Soporte | [`support/UBTECH_SUPPORT_TRACKER.md`](support/UBTECH_SUPPORT_TRACKER.md) |
| SDK original | [`../Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/`](<../Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/>) |

## 11. Protocolo de actualización de esta fuente

Después de cada intervención material, añadir o corregir:

1. fecha y evidencia;
2. estado físico/lógico final **sin asumir que persistirá**;
3. cambio persistente en robot, PC o repositorio;
4. verificación realizada y resultado;
5. rollback disponible;
6. bloqueo o riesgo nuevo;
7. siguiente comando de sólo lectura y documento a consultar.

No copie logs completos aquí. Resuma y enlace la fuente detallada. Si la
evidencia contradice este documento, prevalece la evidencia actual y debe
actualizarse este archivo antes de cerrar la sesión.

## 12. Historial global

| Fecha | Hito | Resultado |
|---|---|---|
| 2026-08-10/11 | diagnóstico inicial BMS | se observó desequilibrio SOC y SN truncado; pendiente proveedor |
| 2026-08-14 | AprilTag mesa 2 | tag 113 y referencias empty/held calibrados |
| 2026-08-17 | manos v4 | detección y demos de fábrica; luego se restauraron abrazaderas |
| 2026-08-20/21 | upgrade v0.2.0 | sistema actualizado, mapa y `HW_TYPE` preservados |
| 2026-08-21 | boot guard | recuperación controlada del race Vision→Motion validada |
| 2026-08-21 | VLA shadow | inferencia funcional; chunks rechazados desde `home`; cero mando físico |
| 2026-08-21 | apagado | discrepancia manual/hardware/software documentada |
| 2026-08-24/25 | PICO | cadena hasta DataChannel validada; heartbeat sigue bloqueando sesión estable |
| 2026-08-25 | relevo global | `AGENTS.md` y esta fuente hacen el contexto descubrible automáticamente |

