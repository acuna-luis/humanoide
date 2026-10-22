# Captura pasiva de episodios RGB y movimiento

**VLA-PASSIVE-EPISODE-CAPTURE-20261022 — 22-10-2026, Europe/Madrid.**
Implementado en PC y verificado con lecturas reales; no envía movimiento,
entrena, arranca VLA ni instala/reinicia servicios del robot.

## Uso directo en el PC Linux del robot

Abrir una terminal del PC que contiene este repositorio:

```bash
cd /home/lacuna/proyectos/Robots/Humanoide
python3 -B scripts/vla/capture_passive_episode.py --seconds 300 --max-mib 4096 --task demo_caja
```

El comando prepara un episodio nuevo y muestra su carpeta. Esperar
**`CAPTURA_LISTA`** antes de iniciar una demostración autorizada por separado.
Graba durante300 s después de reunir las señales iniciales y termina solo.
`Ctrl+C` interrumpe exclusivamente esta captura; no es un paro del robot.
No se lanza ni reanuda un ciclo al ejecutar este comando.

Por defecto guarda en
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/FECHA_EPISODE_ID/`.
Para elegir otra carpeta NUEVA: `--output-dir /ruta/nueva`. Nunca sobrescribe
una toma existente. Reserva espacio para varios GB; `--max-mib` limita bytes
transportados, incluyendo base64, y aborta con captura no validada si se supera.
Los límites por defecto son5 imágenes/s,30 muestras/s por canal y2048 MiB;
son techos de muestreo, no frecuencias garantizadas. El ejemplo amplía sólo el
presupuesto de transporte a4096 MiB para cinco minutos. Duración admitida1–1800 s.

## PowerShell en un Windows distinto

El programa corre en el PC Linux; PowerShell sólo serviría para iniciarlo por SSH:

```powershell
ssh -t lacuna@IP_DEL_PC_LINUX 'cd /home/lacuna/proyectos/Robots/Humanoide && python3 -B scripts/vla/capture_passive_episode.py --seconds 300 --max-mib 4096 --task demo_caja'
```

**Prerrequisito pendiente:** el22-10 el servidor SSH de este PC estaba `inactive`;
no se ha instalado/activado en esta intervención. La IP LAN observada fue
192.168.40.127, dinámica; comprobarla otra vez al configurar acceso. El comando
PowerShell requiere que ese acceso exista; el uso local anterior funciona ya.
No confundir la IP del PC con Motion192.168.11.2 o Vision192.168.11.3.

## Datos guardados y significado

| Archivo | Contenido |
| --- | --- |
| `rgb/*.png` | Píxeles reales960×576 en el piloto, PNG sin pérdida; decodificación bgr8/rgb8/mono8 con padding de fila |
| `samples.jsonl` | Muestras originales de imagen, JointState, ActuatorState y ambas fuerzas; marcas de origen, recepción Vision y llegada PC |
| `aligned.jsonl` | Pares por imagen con posiciones20D, `actuator_cmd_pos20`, fuerza6D por muñeca y diferencias temporales explícitas |
| `manifest.json` | Etiqueta de tarea, orden20D, límites, fuentes/hash, identidad y resultado de transporte |
| `quality.json` | Cobertura, cadencias/huecos reales, muestras válidas, emparejamiento y limitaciones |
| `discovery.json`, `container-identity*.json` | Contenedor ROS Vision descubierto e identidad antes/después |
| `SHA256SUMS`, `sources/`, `collector_remote.py`, `capture.log` | Integridad, fuente enviada y diagnósticos de la toma |

Canales obligatorios:
`/sensor/camera/stereo/color/raw` (`shm_msgs/msg/Image2m`),
`/mc/whole_joint_states`, `/mc/actuator_state`,
`/mc/ft_states/L_hand_ft`, `/mc/ft_states/R_hand_ft`.
El SDK `/mc/sdk/robot_command` se suscribe adicionalmente si su tipo coincide;
0 mensajes no se presenta como una fuente de acción obtenida.

Todo se lee en un solo nodo del contenedor ROS ya existente de Vision,
descubierto antes de cada toma, y se transmite al PC. Sin escribir configuración
ni paquetes en el robot; el proceso/nodo temporal termina al cerrar. Rosout y
servicios de parámetros del nodo están deshabilitados. No hay publicadores de
control, clientes de servicio/acción, cambios de parámetros o modo.
La compresión PNG se realiza en un trabajador con cola acotada; sus descartes
quedan en el registro final, sin crear imágenes repetidas para llenar huecos.

Las posiciones20D se reordenan por nombres. Las consignas se conservan aparte,
leyendo `cmd_pos` de los actuadores y relacionando sufijos `_motor`/`_joint`.
No se sustituyen articulaciones ausentes por0. Fuerzas son6 valores por muñeca
(fuerzaXYZ, torqueXYZ), con mensaje original conservado.

## Sincronización y criterios de aceptación

Se guardan sellos de origen sin corregirlos; recepción monotónica/común de
Vision, reloj de pared Vision y llegada PC quedan separados. No se resta
monotónico PC de monotónico Vision ni se finge NTP/sincronía física.
Se comparan edades de origen respecto al reloj receptor: fuera de−50 a500 ms
se registra advertencia y no pasa QC. Este chequeo no calibra relojes/sensores.

Emparejamiento: vecino más cercano por sello de origen, máximo80 ms, y diferencia
de recepción común≤500 ms. Son umbrales de QC de la captura, **no** límites de
control del robot ni certificación de sincronía de obturadores. No se interpola.
Se excluyen explícitamente los fotogramas de borde fuera de cobertura común.
Los fotogramas interiores sin pareja hacen fallar la comprobación.

También se exige cierre auténtico sin errores/interrupción, resultado de
transporte0, identidad del contenedor conservada, dos muestras válidas por canal,
cuentas recibidas iguales a las declaradas, sellos crecientes, píxeles con hash
correcto y vectores20D completos/finitos. Cada flujo debe cubrir≥80 % del tiempo
pedido; huecos máximos0,5 s para telemetría y max(0,5 s,3/FPS) para RGB.
`capture_checks_passed=true` significa únicamente que se cumplen estas reglas.

**`training_ready` permanece `false`.** Falta cualificar `cmd_pos` como señal
supervisada para el modelo elegido, revisar resultado físico/etiquetas y convertir
a LeRobot con splits y frecuencia adecuados. No se fabrica una columna `action`
ni se copia una posición observada bajo ese nombre. Una misión completa se
puede guardar en bruto, pero PICK/PLACE deben segmentarse antes de entrenar.

## Verificación de esta intervención

14 pruebas offline correctas: píxeles BGR/padding y CRC PNG; orden y separación
estado/consigna; fuentes faltantes, corrupción, duplicación, desfase, interrupción,
cuentas perdidas, cobertura corta y protección contra sobrescritura. Contrato
estático sin API de publicación/control en el recolector remoto.

Piloto final real de5 s, límites5 FPS/30 Hz:23 PNG,135 JointState,112 ActuatorState,
110 fuerzas izquierdas,109 derechas; SDK0.21 imágenes emparejadas y2 de borde
excluidas; máximo desfase de origen49,081052 ms.0 imágenes descartadas por cola;
`capture_checks_passed=true`, sin errores. Imagen PNG inspeccionada visualmente
en el piloto previo. El piloto03 también pasó; piloto01/02 quedaron rechazados
por QC de tiempos/transporte, conservados como evidencia y no convertidos en éxitos.

Sólo se validaron capturas pasivas cortas, **no una demostración en movimiento,
una sesión de300 s ni entrenamiento**. No se han enviado movimientos. No asumir
que esta lectura describe la postura actual o autoriza un ensayo físico.

Evidencia privada, hashes y backup documental:
`../Humanoide-vla-evidence/20261022_PASSIVE_DATASET_PREP_173629Z/`:
`before/`, `before.json`, descubrimientos Motion/Vision, cuatro pilotos,
`tests.txt`, `verification.json`. Las imágenes/datos no se añaden a Git.

Fuentes: `scripts/vla/capture_passive_episode.py`, `passive_episode_remote.py`,
`passive_episode_quality.py`, `test_passive_episode.py`.
Reversión: retirar selectivamente esos cuatro archivos y estas referencias,
preservando episodios/evidencias y otros cambios. Ningún servicio/configuración
persistente del robot que restaurar. El nodo de captura ya terminó en los pilotos.
