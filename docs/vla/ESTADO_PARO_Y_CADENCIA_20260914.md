# Estado del paro y cadencia — 2026-09-14

VLA-01. Diagnóstico de sólo lectura; HOME→READY→ENTRY no ejecutado.

## Hallazgo que corrige el diagnóstico anterior

El límite local de3s se diseñó suponiendo un heartbeat. La frecuencia observada
4,495–4,498s no basta para afirmar avería del E-stop. El binario instalado
`/opt/walker/unova_power/lib/unova_power/server`, en Vision,
`walker-embedded.unova_power-1`, SHA256
`13cea0b9e84e10506a31e1c1e9a9015774984fafcb3fbc0ef40e6ab08f7e1a6d`,
contiene publicación por cambio y supresión de duplicados.

VERIFICADO ESTÁTICAMENTE: `CanHubProcessor::processPower`, rama de trama0x5b:
0x35594–0x355a4 compara paro principal previo y contador; publica si cambió
o el contador está a cero. 0x355ac–0x355b8 y0x35c60–0x35c78 hacen lo mismo
para el segundo paro. 0x35670–0x35680 incrementa contador hasta10 y
0x35ed8 lo reinicia. Por tanto estados constantes se publican una vez por
cada11 tramas de esta rama; cambios se publican sin esperar ese contador.
DWARF identifica `estop_key_pub_` en offset416/0x1a0 y `estop_servo_pub_`
en432/0x1b0; las llamadas usan estos miembros. Esto no demuestra la demora
física contacto→CAN ni garantiza la frecuencia futura de las tramas.

INFERENCIA: la supresión de duplicados explica la cadencia observada. Falta
contrastar cambios físicos y, separadamente, seguimiento/parada de los ejes.
No se deduce que cambiar3s por6s constituya una protección equivalente.

El grafo muestra un publicador DDS nativo RELIABLE, VOLATILE, deadline infinito;
UInt8 no contiene marca de adquisición física. El cliente nativo rosa falló
al deserializar UInt8; ese fallo del proceso diagnóstico no acredita caída del
servidor de alimentación. Se conserva su salida fallida. No se modificó ni
reinició ese servicio. Se encontró `/emb/set_report_mode`, pero no se llamó:
su existencia no justifica cambiar el reporte del hardware a ciegas.

## Corrección local y reproducción

`runtime/entry410_single_stage_remote.py` comprueba al menos dos mensajes
por paro y su cadencia antes de enviar acción. Conserva3s y rechaza el canal
actual antes de mover, en lugar de iniciar y fallar después. No habilita ENTRY;
los demás contratos siguen vigentes. Doce tests de cadencia y contrato pasan.
La corrección no se ha ejecutado físicamente ni instalado en el robot.

```bash
PYTHONPATH=scripts/vla .venv/general-home/bin/python -m unittest \
 scripts/vla/test_entry410_stop_cadence.py \
 scripts/vla/test_entry410_stage_executor.py
```

La revisión estática se reproduce con Capstone5.0.6 y pyelftools0.32, instalados
sólo en `analysis-deps/` de la evidencia privada, sin alterar el entorno general:

```bash
EV=../Humanoide-vla-evidence/20260914_ESTOP_SOURCE_DIAG
PYTHONPATH="$EV/analysis-deps" .venv/general-home/bin/python \
 scripts/vla/audit_estop_publication_binary.py \
 --binary "$EV/unova_power_server" --output /tmp/paro-static-nuevo.json
```

El auditor rechaza otro binario y no lo ejecuta. Es extracción e interpretación
estática, no una prueba de respuesta física. Tras firmware volver a analizar.

## Estado y reversión

Pendiente observar pulsación del operador con robot inmóvil, sin liberar
automáticamente el paro. No existe habilitación de HOME→READY→ENTRY.
Evidencia privada: `../Humanoide-vla-evidence/20260914_ESTOP_SOURCE_DIAG/`:
grafo, inventario, binario con hash, desensamblado, miembros DWARF e informe.
Cambios PC: auditor offline, admisión de ENTRY, tests y documentos. Fuentes
previas respaldadas en `before/`; retirar selectivamente fuentes nuevas y
restaurar cambios propios desde ese respaldo para revertir. Ningún cambio
persistente en Motion/Vision. No restaurar una versión insegura para ejecutar.

Resultado de la ventana pasiva15:43:04–15:44:04UTC:2852 muestras de actuadores,
13 mensajes por paro, todos0; sin incidencias del analizador. No se observó
pulsación. La petición al operador sigue pendiente, no equivale a ejecución.
La ventana terminó y no mide eventos posteriores. No se envió movimiento.


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
