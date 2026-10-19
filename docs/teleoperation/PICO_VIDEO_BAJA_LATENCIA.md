# Vídeo PICO con baja latencia

Fecha: 16-10-2026, Europe/Madrid. Adaptación `PICO-VIDEO-LOW-LATENCY-20261016`.

El operador comunicó unos 3 s de desfase. La conversión anterior del PC añadió
1,273 s de mediana en una prueba con una fuente HTTP-FLV sintética en tiempo
real. Con el ajuste descrito aquí añadió 0,027 s. Estas cifras comparan la
misma etapa del PC; no son una medición de cámara a pantalla del visor.

## Cambios y alcance

| Etapa | Ajuste |
| --- | --- |
| Decodificación en el PC | `avdec_h264 max-threads=1 thread-type=slice`; evita retener varios fotogramas para decodificar en paralelo. |
| Colas del PC | Una imagen decodificada pendiente; si se llena, descarta la más antigua. Cada rama de ojo tiene una plaza y conserva el emparejamiento. Nunca se descartan fragmentos H.264 arbitrarios. |
| Recodificación SBS | x264 ultrafast/zerolatency, sin B-frames ni lookahead, dos hilos por slices, perfil constrained-baseline y keyframe cada 6 imágenes. Mantiene 2560×720 y la imagen completa en ambos ojos. |
| Conexión al visor | TCP_NODELAY, búfer solicitado de envío de 64 KiB y espera máxima de escritura de 1 s; una escritura por imagen con su cabecera. |
| Fuente del robot | GOP de medio segundo: 6 imágenes a 12 fps, frente a las 24 anteriores. No equivale a un límite de latencia total. |
| SRS de Vision | `tcp_nodelay on`, `min_latency on`, `gop_cache off`, `queue_length 1`, `mw_latency 20`, `publish { mr off; }`. |
| Continuidad de la fuente | Heartbeat de vídeo `std_msgs/msg/String` a 2 Hz, conforme al suscriptor CameraPusher; el tipo anterior Empty provocaba cierre por timeout aunque su proceso siguiera vivo. |

El vídeo utiliza Ethernet PC → Vision y USB PC → PICO. El ajuste no modifica
la teleoperación, las protecciones, las cámaras de navegación ni los mandos.
SRS es un servidor compartido de vídeo: su configuración afecta a las nuevas
conexiones de vídeo. La herramienta exige que no existan streams activos antes
de aplicar o restaurar; no detiene sesiones ajenas.

No se instala ni modifica el APK, el SDK, firmware, imágenes Docker o paquetes.
El layout sigue siendo mono duplicado: no proporciona profundidad estéreo.
Una escritura bloqueada durante 1 s termina el relay con error; no se intenta
recuperar automáticamente mientras se controla el robot.

## Aplicación y comprobación

Desde la raíz del repositorio en el PC:

```bash
python3 scripts/teleoperation/configure_pico_srs_latency.py --check
python3 scripts/teleoperation/pico_camera_sbs.py --check
```

SRS ya fue ajustado en esta intervención. Para reaplicarlo tras recrear el
contenedor, revisar primero la ficha en `docs/SYSTEM_CUSTOMIZATIONS.md` y la
compatibilidad con la versión instalada; después, con los streams cerrados:

```bash
python3 scripts/teleoperation/configure_pico_srs_latency.py --apply
```

La herramienta verifica SRS 5.0.213, instancia y ruta conocidas, ausencia de
montaje externo de la configuración y ausencia de streams. Guarda en el PC
original, candidato, hashes y recibo antes de escribir; valida el candidato
con el propio SRS, comprueba de nuevo el hash original y recarga sólo SRS con
HUP. Comprueba lectura posterior y éxito de recarga. Rechaza reglas de entrega
ya personalizadas que no coincidan con este perfil. No recrea contenedores.

Destino actual: Vision `192.168.11.3`, contenedor `walker-backend.srs-1`,
`/usr/local/srs/conf/rtmp2rtc.conf`. La configuración permanece en la capa
escribible del contenedor y se pierde al recrearlo desde la imagen. El script
versionado permite reaplicarla selectivamente; no se cambió Compose ni el
autoarranque. Los cambios del PC se usan al lanzar un proceso nuevo.

## Prueba sólo de vídeo

Mantener el robot inmóvil y los mandos libres. Terminar previamente cualquier
otra sesión propietaria del mismo vídeo; no ejecutar dos relays simultáneos.
El túnel ADB de cámara debe existir según la guía PICO; este comando lo verifica
sin consumir el receptor con una conexión de prueba:

```bash
bash scripts/teleoperation/cruzr_pico_camera.sh --run \
  --camera main --pico-ip 127.0.0.1 --layout mono-sbs-zed --wait 120
```

Si la ventana está cerrada, seleccionar Remote Vision → ZEDMINI → Listen una
sola vez al aparecer `PICO_CAMERA_RECEIVER_WAIT` y confirmar `192.168.11.250`.
Si ya está abierta y preparada, dejarla como está. Mantenerla abierta y no
alternar Listen durante la transmisión. No pulsar Y: la prueba sólo abre vídeo.
El primer keyframe y los contadores deben avanzar. La aplicación puede mostrar
imagen sin que eso garantice una latencia adecuada.

Comparar un evento visual real con la imagen recibida, sin mover el robot.
Para cuantificar el desfase, se puede filmar simultáneamente con un móvil un
cronómetro real visible para la cámara del robot y su imagen en una lente del
visor. Restar ambos tiempos en el mismo fotograma evita depender del reloj
incorrecto del PICO. Repetir varios momentos para distinguir retraso fijo de
acumulación. Una comparación visual subjetiva se registra como OBSERVADO.

Cerrar la prueba con Ctrl+C en su terminal propietaria. El lanzador cierra
relay, heartbeat y stream propios. Antes de pasar a una nueva sesión, seguir
el procedimiento de receptor de la guía PICO; no reusar un receptor cerrado
ni alternar Listen repetidamente si aparece EADDRINUSE.

## Uso posterior en teleoperación

Después de cerrar la prueba independiente y con las condiciones físicas
comprobadas mediante el lanzador habitual:

```bash
PICO_TELEOP_CAMERA=main CRUZR_PICO_CAMERA_LAYOUT=mono-sbs-zed \
PICO_CAMERA_PICO_IP=127.0.0.1 CRUZR_IFACE=eno1 CRUZR_PC_IP=192.168.11.250 \
bash scripts/teleoperation/probar_pico_v4.sh --teleoperate
```

Se conserva el control de primer keyframe y todos los gates existentes. Este
comando sí permite movimiento tras la confirmación y Y; no se usa para medir
la latencia inicialmente. No declara adecuado el vídeo sólo por sus fps.

## Reversión

Con los streams cerrados, usar la carpeta de respaldo que imprimió `--apply`:

```bash
python3 scripts/teleoperation/configure_pico_srs_latency.py \
  --restore /RUTA/PRIVADA/DEL/RESPALDO
```

Sólo restaura si coinciden host, instancia y hashes original/instalado.
Genera un nuevo respaldo y recibo. Si una validación o recarga falla, conservar
los recibos y revisar la fase; no repetir cambios a ciegas.

Para revertir fuentes PC, restaurar selectivamente los fragmentos cambiados
desde `before/` de la evidencia, preservando cambios posteriores. No usar un
reset del repositorio ni restaurar configuraciones completas del robot.

## Evidencia, validación y límites

Evidencia privada de esta intervención:
`../Humanoide-vla-evidence/20261016T093737Z_PICO_VIDEO_LOW_LATENCY/`.
Incluye fuentes/documentos anteriores, benchmark antes/después, recibo
`srs-apply/receipt.json`, configuración original/candidata, validación SRS y
log de recarga. Valores SRS original/instalado:

- Original SHA256: `f17d118c5de55838650975f8275aad354725b18ecf6d941c58ef07dfd5f269af`.
- Instalado SHA256: `753d219b2732eef4422d4b2703e18eaf2c2047c487e53ecae3a152dde2a1b67d`.

24 pruebas offline pasan: conversión FLV real, imagen completa/ojos iguales,
primer frame de fuente en tiempo real, transporte TCP, límites de cambios SRS
y comprobaciones de receptor. Sintaxis Python/Bash y `git diff --check` pasan.
Prueba real: 437 frames / 74 keyframes / ~12,4 fps. El operador confirma «Se ve
y el retraso es mucho menor». Mejora OBSERVADA; el valor final en milisegundos
sigue PENDIENTE de medición. No se promete una latencia máxima extremo a
extremo: carga, red y el decoder nativo influyen.

La fuente terminó después por falta de heartbeat válido. Inspección del binario
y grafo ROS confirman `std_msgs/msg/String`, no Empty; se corrige el lanzador sin
cambiar el timeout del proveedor. Se comprueba por separado la duración de la
fuente con heartbeat String y sin visor: más de 55 s y 113 publicaciones, sin
nuevo timeout y cierre explícito con respuesta code=0. Después se verifica que
no quedan streams SRS ni publicadores de heartbeat de la prueba. No se publican
comandos de movimiento.

Fuentes modificadas: [conversión SBS](../../scripts/teleoperation/pico_camera_sbs.py),
[relay TCP](../../scripts/teleoperation/pico_camera_relay.py),
[lanzador de cámara](../../scripts/teleoperation/cruzr_pico_camera.sh),
[configuración SRS](../../scripts/teleoperation/configure_pico_srs_latency.py),
[pruebas de imagen](../../scripts/teleoperation/test_pico_camera_sbs.py) y
[pruebas de configuración/transporte](../../scripts/teleoperation/test_pico_video_latency.py).

Referencias primarias consultadas: [SRS 5, baja latencia](https://ossrs.io/lts/en-us/docs/v5/doc/low-latency),
[cola GStreamer](https://gstreamer.freedesktop.org/documentation/coreelements/queue.html),
[decodificador H.264](https://gstreamer.freedesktop.org/documentation/libav/avdec_h264.html)
y [x264enc](https://gstreamer.freedesktop.org/documentation/x264/index.html).
