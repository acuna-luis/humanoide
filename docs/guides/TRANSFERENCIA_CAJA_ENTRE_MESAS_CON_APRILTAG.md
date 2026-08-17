# Transferencia de una caja entre dos mesas con AprilTag

## Objetivo y alcance

Esta guía define la preparación y la secuencia prevista para recoger el
contenedor azul en la mesa 1, transportarlo hasta la mesa 2, depositarlo y
terminar con el robot en `home`.

La arquitectura recomendada es:

```text
detector workbin -> agarre -> MESA2_PRE -> alineación AprilTag 113
                 -> depósito -> retirada -> home
```

El detector especializado `workbin` reconoce y localiza la caja. El AprilTag
no reconoce la caja: proporciona una referencia geométrica para la alineación
fina frente a la mesa 2. GR00T/VLA no interviene en esta operación.

> **Estado actual:** la detección AprilTag está instalada, pero los scripts de
> transporte todavía no consumen su pose para corregir el chasis. No debe
> intentarse la misión autónoma completa hasta implementar y validar ese
> alineador.

## 1. Etiquetas y puntos de navegación

| Estación | AprilTag | Lado negro medido | Necesidad | Función |
| --- | ---: | ---: | --- | --- |
| Mesa 1 | 112 | 75 mm | Opcional | Referencia de origen y recuperación futura |
| Mesa 2 | 113 | 73,5 mm | Recomendada | Alineación fina para el depósito |

La unidad revisada usa la familia `tag36h11`. En la configuración de
validación BYD aparecen los IDs 112–115 con un tamaño de `0,10 m`, aunque la
validación integrada está desactivada mediante `use_apriltag_val: false`. Los
tags finalmente instalados deben detectarse con sus medidas reales: `0.075`
para el ID 112 y `0.0735` para el ID 113. Para esta guía se utiliza el detector
AprilTag independiente.

También debe crearse en el mapa `test_route_01` un waypoint llamado
`MESA2_PRE`. Este punto realizará únicamente la aproximación global; el
AprilTag se utilizará después para la corrección local.

## 2. Generar los AprilTags en Ubuntu

Los diseños ya generados se obtienen del repositorio oficial
[AprilRobotics/apriltag-imgs](https://github.com/AprilRobotics/apriltag-imgs/tree/master/tag36h11).
No es necesario generar una familia personalizada.

Los siguientes comandos se ejecutan en el PC Ubuntu:

```bash
sudo apt install -y git python3-pil inkscape

cd /home/lacuna/proyectos/Robots/Humanoide
mkdir -p assets/apriltags

apriltag_source="$(mktemp -d)"

git clone --depth 1 \
  https://github.com/AprilRobotics/apriltag-imgs.git \
  "$apriltag_source/apriltag-imgs"

python3 "$apriltag_source/apriltag-imgs/tag_to_svg.py" \
  "$apriltag_source/apriltag-imgs/tag36h11/tag36_11_00112.png" \
  assets/apriltags/mesa1_tag112.svg \
  --size=125mm

python3 "$apriltag_source/apriltag-imgs/tag_to_svg.py" \
  "$apriltag_source/apriltag-imgs/tag36h11/tag36_11_00113.png" \
  assets/apriltags/mesa2_tag113.svg \
  --size=125mm
```

El conversor utilizado es el
[`tag_to_svg.py` oficial](https://github.com/AprilRobotics/apriltag-imgs/blob/master/tag_to_svg.py).

Generar los PDF:

```bash
inkscape assets/apriltags/mesa1_tag112.svg \
  --export-filename=assets/apriltags/mesa1_tag112.pdf

inkscape assets/apriltags/mesa2_tag113.svg \
  --export-filename=assets/apriltags/mesa2_tag113.pdf
```

## 3. Imprimir y medir

Imprimir cada PDF por separado con estas opciones:

- papel A4 blanco y mate;
- escala `100 %` o `Tamaño real`;
- desactivar `Ajustar a página`;
- no plastificar con acabado brillante;
- conservar completo el margen blanco;
- pegarlo sobre una superficie plana y rígida.

El SVG completo mide 125 mm, pero el cuadrado exterior negro detectable debe
medir 100 mm. La biblioteca define `tag_size` como la distancia entre las
esquinas de detección, no como el tamaño exterior incluido el margen blanco.
La definición oficial puede consultarse en
[Pose Estimation](https://github.com/AprilRobotics/apriltag#pose-estimation).

Después de imprimir, medir el lado negro con una regla. Si, por ejemplo, mide
99,2 mm, debe utilizarse `tag_size: 0.0992` en lugar de `0.10`.

## 4. Montaje físico en las mesas

Para la mesa 2:

1. Fijar el ID 113 en un panel vertical rígido unido a la mesa.
2. Colocarlo detrás de la mesa y aproximadamente centrado.
3. Dejarlo visible por encima de la caja transportada.
4. Mantener su plano paralelo al borde frontal de la mesa.
5. Evitar que el panel pueda desplazarse respecto a la mesa.
6. Registrar la altura de su centro y sus desplazamientos lateral y
   longitudinal respecto al centro de depósito.

No conviene colocarlo en el frontal bajo de la mesa porque la caja agarrada
podría ocultarlo. El ID 112 puede montarse de igual forma en la mesa 1, pero no
es necesario para la recogida actual: el detector `workbin` ya centra el robot
respecto a la caja.

Para la primera prueba, la mesa 2 debe ser estable, soportar la carga y tener
la misma altura verificada que la mesa 1. Una altura distinta exige adaptar y
validar por separado la trayectoria vertical de depósito.

## 5. Crear `MESA2_PRE` en el mapa

En `http://192.168.11.3/map/navigation`, sobre `test_route_01`:

1. Crear un waypoint llamado `MESA2_PRE`.
2. Situarlo aproximadamente entre 0,8 y 1,0 m delante de la mesa 2.
3. Orientarlo hacia el AprilTag 113 y perpendicular al borde de la mesa.
4. Dejar espacio para los giros considerando la anchura total de la caja.
5. No situarlo pegado a la mesa: la aproximación fina se hará con el tag.
6. Guardar el mapa y probar la navegación hasta el punto sin caja y con los
   brazos en `home`.

Los scripts calculan una huella de `umap.json`, `task.json` y de las instancias
del navegador. Si el mapa cambió o se reinició el runtime, lo recargan y
relocalizan una sola vez antes de navegar. Para sincronizar y navegar sin
entrar manualmente al Docker:

```bash
./scripts/cruzr_blue_workbin_map_route.sh \
  --navigate-waypoint MESA2_PRE --yes --fast
```

Puede añadirse `MESA1_PRE` como referencia de origen, aunque la aproximación
visual actual puede seguir utilizándose en la mesa 1.

## 6. Comprobar el detector AprilTag

Conectarse desde el PC mediante la Wi-Fi del robot:

```bash
ssh walker@192.168.42.2
docker exec -it walker-ros.ros2-1 bash
source /opt/ros/humble/setup.bash
```

Activar la detección del ID 113 usando el tamaño físico medido:

```bash
ros2 service call /apriltag/start_detecting \
  sensor_task_msgs/srv/AprilTagStartDetecting \
  "{start_detecting: true, img_topic_name: '/sensor/camera/stereo/color/raw', tag_id: 113, tag_size: 0.0735, tag_frame: 'mesa2_tag113'}"
```

Observar los resultados en otro terminal ROS 2:

```bash
timeout 20 ros2 topic echo \
  /sensor/camera/stereo/april_tag/results
```

Comprobar:

- ID 113 correcto;
- familia `tag36h11`;
- ausencia de correcciones Hamming inesperadas;
- `pose.header.frame_id` conocido;
- distancia y orientación físicamente razonables;
- poca variación de pose con el robot inmóvil.

Detener la detección:

```bash
ros2 service call /apriltag/start_detecting \
  sensor_task_msgs/srv/AprilTagStartDetecting \
  "{start_detecting: false, img_topic_name: '/sensor/camera/stereo/color/raw', tag_id: 113, tag_size: 0.0735, tag_frame: 'mesa2_tag113'}"
```

El contrato general del detector también está recogido en
[CATALOGO_FUNCIONALIDADES_CRUZR_S2.md](CATALOGO_FUNCIONALIDADES_CRUZR_S2.md#7-detector-apriltag).

## 7. Calibrar la pose de depósito

La calibración debe hacerse inicialmente sin transportar la caja:

1. Dejar la mesa 2 vacía, fija y estable.
2. Navegar hasta `MESA2_PRE` con los brazos en `home`.
3. Colocar la cabeza siempre en la misma postura reproducible.
4. Aproximar lentamente el robot hasta una pose válida para depositar.
5. Registrar al menos 20 poses consecutivas del AprilTag 113.
6. Guardar la mediana de posición y orientación como
   `MESA2_DROP_TARGET`.
7. Alejar el robot y repetir la aproximación al menos tres veces.

El alineador deberá comparar la pose observada con `MESA2_DROP_TARGET` y
corregir X, Y y giro mediante movimientos pequeños y limitados. Como criterio
inicial de desarrollo puede utilizarse un error máximo de 20 mm y 2 grados,
pero estos límites no son valores certificados y deben validarse físicamente.

La calibración realizada el 14 de agosto de 2026 utilizó tres aproximaciones
independientes de 20 muestras. La diferencia máxima entre ejecuciones fue de
18,30 mm y 1,62 grados. La referencia consolidada es:

```text
MESA2_DROP_TARGET
POSITION_M=-0.027403734 0.021092044 1.138346576
QUATERNION_XYZW=-0.976405603 0.011121442 -0.014522428 0.215168563
RPY_DEG=-155.126 -1.351 -1.603
TAG_ID=113
TAG_SIZE_M=0.0735
FRAME=stereo_left_rectified_optical_frame
```

Una medición independiente realizada después de integrar el alineador dio un
error planar de 0,43 mm, un error angular de 0,38 grados y `PLAN=READY`.

Al sujetar la caja, la postura de transporte cambia la transformación entre
cámara y tag. Por ello se calibró una segunda referencia específica en la misma
pose física de depósito:

```text
MESA2_DROP_TARGET_HELD
POSITION_M=-0.022617825 -0.122600795 0.803420107
QUATERNION_XYZW=-0.975321264 0.009621669 -0.004721560 0.220530186
TAG_ID=113
TAG_SIZE_M=0.0735
FRAME=stereo_left_rectified_optical_frame
```

La referencia con carga procede de 20 muestras con desviaciones posicionales
de 0,017, 0,058 y 0,223 mm. Una lectura independiente previa al depósito dio
un error planar de 0,10 mm, 0,088 grados de error angular y `PLAN=READY`.

La cabeza debe adoptar exactamente la misma postura durante la calibración y
la ejecución. Si la caja oculta el tag, habrá que elevar o desplazar su soporte
antes de continuar.

## 8. Integración disponible

El orquestador `scripts/cruzr_blue_workbin_table_transfer.sh` implementa:

1. comprobación de paros, cargador, batería, mapa y detector;
2. centrado y agarre en la mesa 1;
3. retirada de 0,50 m;
4. navegación hasta `MESA2_PRE`;
5. detección estable del ID 113;
6. alineación local con `MESA2_DROP_TARGET`;
7. verificación de que la caja continúa sujeta;
8. aproximación final y depósito;
9. retirada de la mesa 2 y recuperación a `home`.

Comprobar toda la cadena sin movimiento:

```bash
./scripts/cruzr_blue_workbin_table_transfer.sh --check --fast
```

La primera prueba con caja debe detenerse en `MESA2_PRE`:

```bash
./scripts/cruzr_blue_workbin_table_transfer.sh --stage-held --fast
```

Este modo coge la caja, se separa de mesa 1, navega hasta `MESA2_PRE`, verifica
el agarre y mide el tag 113. No alinea ni deposita. Después de confirmar que
la caja sigue estable, que el tag permanece visible y que mesa 2 está libre:

```bash
./scripts/cruzr_blue_workbin_table_transfer.sh --resume-held --fast
```

Cuando ambos modos hayan sido validados repetidamente puede ejecutarse el
ciclo completo con una sola confirmación:

```bash
./scripts/cruzr_blue_workbin_table_transfer.sh --run --fast
```

### Perfil fluido para demostraciones

El perfil `--fluid` mantiene el perfil conservador anterior sin cambios y
aplica estas optimizaciones solamente cuando se solicita expresamente:

- tolerancia planar y por eje de 50 mm para aceptar pronto una caja que ya
  está suficientemente centrada sobre una mesa con margen;
- tolerancia de oscilación del tag de 3,5 grados, manteniendo un rechazo duro
  por encima de 5 grados;
- tres muestras AprilTag, correcciones longitudinales de hasta 0,18 m y un
  máximo de cuatro iteraciones;
- una muestra del detector workbin durante las correcciones intermedias y dos
  muestras obligatorias inmediatamente antes del agarre;
- aproximación limitada a 0,12 m/s, con tramos de hasta 0,42 m. El retroceso
  utiliza siempre un único tramo odométrico de 0,50 m y, en modo fluido, queda
  limitado a 0,08 m/s;
- reutilización de comprobaciones de mapa, AprilTag y canal ya superadas;
- medición del tiempo empleado por cada etapa y del total.

La preparación completa tarda aproximadamente 26 segundos en la instalación
actual y no mueve el robot. Su resultado puede reutilizarse durante 180
segundos; los paros y el cargador se vuelven a comprobar antes de los
movimientos físicos:

```bash
./scripts/cruzr_blue_workbin_table_transfer.sh --check --fluid
./scripts/cruzr_blue_workbin_table_transfer.sh --run --fluid
```

El segundo comando debe iniciarse dentro de los tres minutos siguientes. Si la
preparación caduca, el propio script la repetirá. Alcanzar exactamente un minuto
depende además del tiempo de las trayectorias oficiales de brazos y de la
navegación hasta `MESA2_PRE`; las líneas `TIMING_*` permiten medir el límite
real sin eliminar controles críticos.

El alineador también puede comprobarse de forma independiente:

```bash
# Infraestructura y referencia; no mueve.
./scripts/cruzr_apriltag_mesa2_align.sh --check

# Pose actual y error respecto al objetivo; no mueve.
./scripts/cruzr_apriltag_mesa2_align.sh --measure

# Correcciones del chasis sin caja.
./scripts/cruzr_apriltag_mesa2_align.sh --align-empty

# Correcciones del chasis exigiendo un agarre vigente.
./scripts/cruzr_apriltag_mesa2_align.sh --align-held
```

Los componentes de bajo nivel que reutiliza el orquestador son:

```bash
# Centrar, sujetar y elevar la caja.
./scripts/cruzr_blue_workbin_carry_back.sh \
  --grasp-only --yes --fast

# Separarse 0,50 m de la mesa 1.
./scripts/cruzr_blue_workbin_carry_back.sh \
  --retreat-only --yes --fast

# Navegar de forma autónoma hasta la premesa de destino.
./scripts/cruzr_blue_workbin_map_route.sh \
  --navigate-waypoint MESA2_PRE --yes --fast

# Depositar cuando la alineación con la mesa 2 ya esté validada.
./scripts/cruzr_blue_workbin_cycle.sh \
  --deposit-held --yes

# Separarse y terminar en home.
./scripts/cruzr_recover_to_home.sh \
  --run --yes --fast
```

Si la alineación falla antes del depósito, el orquestador no abre los cogedores.
Debe conservarse la zona despejada y diagnosticarse el estado antes de
reanudar. No se debe lanzar de nuevo el ciclo completo con una caja ya sujeta.

## 9. Validación progresiva

La puesta en servicio debe realizarse en este orden:

1. Detectar el tag con el robot inmóvil: completado.
2. Navegar sin caja hasta `MESA2_PRE`: completado.
3. Calibrar y repetir tres veces la pose final: completado.
4. Validar el cálculo `PLAN=READY` en la pose objetivo: completado.
5. Probar `--align-empty` desde un desplazamiento inicial pequeño y controlado:
   pendiente de completar como ensayo independiente.
6. Ejecutar `--stage-held` y confirmar que el tag sigue visible con la caja:
   completado.
7. Calibrar `MESA2_DROP_TARGET_HELD` en la pose física de depósito: completado.
8. Ejecutar `--resume-held` con la caja vacía: completado; el depósito, el
   retroceso de 0,484 m y `cruzr/home` terminaron correctamente.
9. Ejecutar y repetir el ciclo completo `--run` únicamente después de obtener
   resultados
   consistentes.

Durante todas las pruebas de movimiento deben permanecer desconectados el
cargador y Ethernet, debe haber espacio libre para robot y caja, y una segunda
persona debe mantener preparado el paro físico. El detector, ROS 2 y estos
scripts no sustituyen una función de seguridad certificada.
