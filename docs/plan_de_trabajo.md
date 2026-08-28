# Plan de trabajo: recoger, transportar, vaciar y depositar una caja

**Fecha:** 2026-08-28

**Estado:** `PLANIFICADO`; este documento no autoriza movimiento físico

**Unidad:** Cruzr S2 `WAE001UBT60000669`, abrazaderas, `HW_TYPE=cruzr_s2_v1`

## Manual secuencial del experimentador

Ésta es la entrada operativa al plan. Los apartados posteriores explican el
porqué técnico; los experimentos siguientes indican exactamente qué preparar,
qué ejecutar y qué registrar. Se realizan en orden. Un experimento `FAIL` o
`BLOCKED` impide continuar a su sucesor, salvo que éste diga expresamente que
es independiente.

### Estados de los experimentos

- `EJECUTABLE_SHADOW`: usa herramientas existentes, produce inferencia pero
  mantiene cero publicadores físicos y no mueve el robot.
- `EJECUTABLE_LECTURA`: sólo inspección, medida o cálculo.
- `PENDIENTE_CODIGO`: la interfaz está especificada, pero el script todavía no
  existe; copiar la orden debe fallar y no se sustituye por una orden manual.
- `PENDIENTE_DATOS_Y_CODIGO`: faltan tanto el dataset conforme al contrato como
  su wrapper reproducible.
- `PENDIENTE_DISENO`: todavía debe definirse el contrato de entradas/salidas;
  no se elige una implementación antes de cerrarlo.
- `BLOQUEADO_FISICO`: implicaría movimiento; requiere herramientas terminadas,
  gates previos aprobados, preflight físico fresco y autorización en esa sesión.

### Convención física confirmada y magnitudes todavía desconocidas

Para eliminar “aproximadamente” y “frente al robot” se define:

1. **Confirmado por el SDK, sección 7.3:** para alinear el demo Cruzr S2 con
   sus datos de entrenamiento, la caja mide `0,60 × 0,40 × 0,22 m` y se coloca
   sobre una plataforma de **`1,00 m de altura`**. La B0 real
   `0,603 × 0,397 × 0,217 m` satisface esa geometría dentro de 3 mm.
2. Ese `1,00 m` es la altura de la superficie desde el suelo, **no** la
   distancia horizontal entre robot y plataforma. El SDK sólo indica que el
   robot debe moverse con el mando a una “posición adecuada”; no aporta la
   cota.
3. `BUMPER_FRONT`: punto más adelantado del bumper inferior del chasis, medido
   sobre la línea central del robot y proyectado verticalmente al suelo.
4. `PLATFORM_FRONT`: línea del borde frontal de la plataforma proyectada al
   suelo. `D_BUMPER_PLATFORM` será la distancia perpendicular entre ambas.
5. `D_BUMPER_PLATFORM=UNRESOLVED`. No se coloca la plataforma delante del
   robot ni se ejecuta una inferencia nominal hasta resolverla en E4.1 mediante
   pose oficial, cinemática/alcance y encuadre del dataset.
6. Los XML `55/70/85/100/115` están en el árbol alternativo `codes` para Cruzr,
   no en el árbol S2 canónico `codes-S2`; por ello `0,55/1,15 m` no son el
   baseline inicial del S2. Sólo podrán añadirse después como variantes si se
   demuestra su mapeo con los tasks low/middle.
7. La plataforma S2 inicial tiene una única superficie a
   `H_VENDOR_PLATFORM=1,000 ± 0,010 m`, está nivelada y es rígida. El SDK no
   fija su ancho ni su fondo: `0,80 × 0,75 m` es un **mínimo provisional del
   proyecto, no un máximo ni una dimensión del proveedor**. Puede ser mayor,
   pero se medirán y registrarán sus dimensiones exteriores reales para que E4.1
   compruebe toda la plataforma en el modelo de colisiones. El baseline no lleva
   compartimientos, laterales, fondo ni divisores: cualquiera de esos elementos
   cambiaría la imagen y el volumen barrido. No se permiten mesas apiladas ni
   calzos.
8. Para seguridad se usa `B0_SAFE`, vacía. Los frames del dataset muestran un
   tote rígido gris abierto de paredes altas, con borde gris, tiras/marcas negras
   estrechas en algunos frames y un pequeño elemento con lazo dentro; una caja
   de cartón o un tote de otro aspecto es OOD aunque mida lo mismo. El lado de
   `0,603 m` queda paralelo a los hombros. Su cara frontal queda a
   `0,050 ± 0,010 m` detrás del borde; el centro es `x=0`, `y=0,2485 m`,
   `yaw=0°` en `PLATFORM_FRAME`.
9. En Experimentos 1–3, plataforma y B0 permanecen fuera de la envolvente del
   robot: separación mínima de `1,5 m` respecto de cualquier parte del robot.
   E2 sólo es un smoke test OOD de runtime, no una prueba de pick/place.
10. Nadie coloca o corrige caja/plataforma mientras shadow o inferencia estén
    activos. Primero se ejecuta `--stop`, luego se modifica el escenario y se
    fotografía, y sólo después se reinicia shadow.

**Fixture disponible declarado por el propietario:** `MESA_T1`, dimensiones
nominales `1,85 m` de ancho × `0,80 m` de fondo × `1,00 m` de altura. Es
`PENDIENTE` hasta ejecutar E1.0: medir tablero y cuatro esquinas, comprobar
nivelación, rigidez, estabilidad y registrar patas/travesaños. Su disponibilidad
no resuelve `D_BUMPER_PLATFORM` ni autoriza acercarla al robot.

#### Inventario mínimo de superficies

| Elemento | Para qué se usa | Estado y decisión |
|---|---|---|
| `MESA_T1` | Reproducir el fixture del SDK a 1 m; PICK/PLACE del escenario que E4.2 consiga mapear a esa altura | Disponible, pendiente de E1.0 |
| `PLATAFORMA_TASK_AJUSTABLE` | Reproducir `H_TASK_0_1` y `H_TASK_2_3` si resultan diferentes de 1 m | No adquirir/fabricar hasta E4.2. Puede ser una sola mesa elevadora rígida, bloqueable y estable, recalibrada para cada altura; no se usan mesas apiladas ni calzos |
| `RECEPTOR_VOLCADO` | Recibir el contenido de B0 durante `TIP/POUR` | No pertenece a los tasks 0–3 ni al checkpoint actual; dimensiones, borde y altura se definirán con la primitiva y los datos propios de volcado |
| `MESA_DESTINO_VACIA` | Recibir B0 después de vaciarla a otra altura | Sólo para la misión ampliada. Será una estación separada o una superficie existente cuya altura/pose entren en el nuevo dataset |

No hace falta una repisa con compartimientos para caracterizar el checkpoint
actual. Tampoco hacen falta simultáneamente dos plataformas low/middle: las
pruebas 0–3 se ejecutan una por una y una plataforma regulable validada puede
reutilizarse. Para ensayar posteriormente la misión completa en una sola
ejecución sí deberán coexistir origen, receptor de volcado y destino de la caja
vacía, cada uno con pose y geometría versionadas.

Antes de E1.1 el robot, si está encendido, debe estar estable y sin movimiento,
la teleoperación/PICO/UI cerradas y VLA detenido. Ningún experimento 1–5
autoriza liberar un paro, cambiar de postura ni mover una articulación.

### Formulario obligatorio del resultado real

Cada experimento crea un directorio independiente y termina con un
`actual_result.yaml`. No se escribe “funcionó” sin datos. Éste es el patrón,
no una orden adicional a ejecutar antes de cada tarjeta:

```bash
VLA_RUN_DIR="$(./scripts/vla/new_vla_evidence_run.sh --experiment ID_DE_LA_TARJETA)"
printf 'VLA_RUN_DIR=%s\n' "$VLA_RUN_DIR"
```

Cada sección manual sustituye `ID_DE_LA_TARJETA` una sola vez; los wrappers
crean el run internamente y no requieren ejecutar este patrón.

```yaml
experiment_id: E1.0
run_id: null
operator: null
start_time: null
end_time: null
status: PASS_OR_FAIL_OR_BLOCKED
scenario_id: null
fixture_measured:
  platform_height_m: null
  bumper_to_platform_m: null
  bumper_to_platform_source: UNRESOLVED_OR_COMPUTED_OR_VENDOR
  box_lwh_m: null
  box_pose_platform_frame: null
initial_robot_state: null
commands_executed: []
expected_result: null
actual_observations: []
files: []
failure_reason: null
final_robot_state: null
recovery_or_stop: null
next_experiment_authorized: false
```

Para shadow se añaden checkpoint/hash, task ID/texto, estado 20D, frame RGB,
chunk bruto, verdict, latencia y publicadores antes/después. Para futuros
experimentos físicos se añaden paros, cargador, velocidades, fuerzas, vídeo
externo, pose final y latencia de STOP.

### Serie 1 — Construir el escenario y congelar el baseline

#### Experimento 1.0 — Montar y medir la plataforma S2 sin acercarla

**Estado:** `EJECUTABLE_LECTURA`; no requiere encender ni mover el robot.

**Objetivo:** construir el fixture confirmado por el SDK sin inventar todavía
la distancia horizontal al robot.

**Pasos:**

1. Crear el run E1.0 en el mismo terminal y conservar la ruta mostrada:

   ```bash
   VLA_RUN_DIR="$(./scripts/vla/new_vla_evidence_run.sh --experiment E1.0)"
   printf 'VLA_RUN_DIR=%s\n' "$VLA_RUN_DIR"
   ```

2. Mantener el robot inmóvil; si existe una sesión VLA anterior, ejecutar:

   ```bash
   ./scripts/vla/run_ubtech_vla_shadow.sh --stop
   ```

3. Colocar la plataforma a más de `1,5 m` de cualquier parte del robot; esta
   separación sólo mantiene el fixture fuera de la envolvente y no se registra
   como distancia de trabajo.
4. Medir desde el mismo suelo la superficie a `1,000 m` en sus cuatro esquinas.
   Cada medida debe quedar en `0,990…1,010 m` y la diferencia máxima entre
   esquinas no debe superar `0,010 m`.
5. Medir y registrar el ancho/fondo reales. Verificar el mínimo provisional del
   proyecto `0,80 × 0,75 m`; se admite una superficie mayor y no se recorta su
   geometría al modelar colisiones en E4.1.
6. Con B0 aún fuera, verificar estabilidad de la plataforma manualmente.
7. Pegar marcas de cinta para plataforma, centro de B0, cara frontal de B0 y
   orientación `yaw=0°`.
8. Fotografiar vista frontal/lateral con cinta métrica y la altura de las
   cuatro esquinas.

**Resultado esperado:** todas las cotas dentro de tolerancia, plataforma estable,
zona despejada y robot sin movimiento.

**PASS:** las medidas y fotografías existen. **FAIL:** plataforma inestable,
superficie fuera de tolerancia o falta una referencia medible. No continuar
ajustando el robot para “compensar”.

**Resultado real:** completar `actual_result.yaml` y guardar
`front.jpg`, `side.jpg`, `height_corners.jpg` y un croquis. Registrar
`bumper_to_platform_m: null`: E1.0 no calcula esa distancia.

**Resultado real 2026-08-28:** `PASS` para progresar en lectura/shadow. El
propietario midió `1,80 × 0,80 m`, las cuatro esquinas a `1,00 m`, confirmó
rigidez, estabilidad y más de `1,5 m` respecto de toda parte del robot. Para
reducir carga operativa, fotos y marcas se aplazan explícitamente a E4, antes
de acercar el fixture o permitir movimiento; esta dispensa no autoriza una
prueba física. Evidencia: `20260828T104622_E1.0`.

#### Experimento 1.1 — Baseline PC/VLA sin inferencia

**Estado:** `EJECUTABLE_LECTURA`.

**Escenario:** plataforma fuera de la envolvente; B0 retirada; robot inmóvil. La
red Motion/Vision debe estar disponible.

**Comandos, en este orden:**

```bash
./scripts/vla/audit_vla_experiment_e1_1.sh
```

El wrapper crea un run exclusivo, rechaza contenedores activos, conserva los
cinco logs y genera `actual_result.yaml` más hashes relativos. No reutiliza
`VLA_RUN_DIR` del terminal.

**Resultado esperado:** checkpoint/config/runtime presentes, contenedores
instalados, final detenidos, `restart=no` y cero publicadores en
`/mc/sdk/robot_command`. No debe aparecer ninguna orden de movimiento.

**PASS:** todas las órdenes terminan correctamente y el último check demuestra
cero publishers. **FAIL:** hash inesperado, contenedor ausente/auto-restart,
Motion/Vision no accesible o publisher físico presente.

**Resultado real:** copiar al YAML versiones, hashes, hosts, estados de los dos
contenedores, contador de publishers y el error completo si falla.

**Primer intento observado el 2026-08-27:** los cinco comandos reportaron hosts,
paquete, instalación deshabilitada, contenedores `exited`, cero publishers y
STOP; sin embargo, `VLA_RUN_DIR` no estaba definido y `tee` intentó escribir en
`/`, por lo que no conservó los cinco logs. Estado:
`INCOMPLETE_EVIDENCE_EMPTY_VLA_RUN_DIR`; repetir este mismo bloque no mueve el
robot y es obligatorio antes de marcar E1.1 como `PASS`.

**Repetición verificada:** `20260827T141244_E1.1`, estado `PASS`. Existen cinco
logs no vacíos y `sha256sum -c logs.sha256` valida los cinco. Vision y Motion
respondieron; paquete `codes-S2`/`checkpoint-40000`/abrazaderas correcto; ambos
contenedores terminaron `exited`; `verify_installation` comprobó además
`restart=no`; publicadores físicos `0` y `SHADOW_SESSION_STOPPED=yes`. Resultado
estructurado en
`Humanoide-vla-evidence/20260827T141244_E1.1/actual_result.yaml`. E1.2 queda
autorizado como inspección de sólo lectura; no se autoriza inferencia ni
movimiento por este PASS.

#### Experimento 1.2 — Auditar el fixture, el dataset y la pose S2 suministrada

**Estado:** `EJECUTABLE_LECTURA`; usa `jq`, `sha256sum` y VLC instalados. No
reutiliza `VLA_RUN_DIR` de E1.1: aquella variable vivía en un subshell y ya no
existe al volver al prompt.

**Comando único recomendado:**

```bash
./scripts/vla/audit_vla_experiment_e1_2.sh
```

El script crea su propio directorio `<timestamp>_E1.2`, valida antes de escribir,
comprueba el hash XML y los cuatro task IDs, y extrae muestras próximas a
inicio/medio/final. Los tiempos proceden de la longitud de cada episodio
dividida por 120 FPS. El seek temporal de VLC puede escoger frames adyacentes
entre ejecuciones: los hashes prueban integridad dentro de cada run, no una
identidad canónica entre runs. Al terminar debe mostrar:

```text
E1.2_ARTIFACTS_OK=/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/...
E1.2_STATUS=ARTIFACTS_EXTRACTED_PENDING_VISUAL_REVIEW
```

Ese estado exige inspeccionar los doce PNG antes de convertir el resultado a
`PASS`; el script no declara por sí solo qué objeto aparece en las imágenes.

**Intento fallido observado el 2026-08-27:** se ejecutaron las órdenes manuales
después del subshell E1.1. `VLA_RUN_DIR` estaba vacío y las redirecciones
intentaron crear `/s2_ready.sha256`, `/s2_ready.xml.txt` y `/tasks.tsv`, que el
sistema rechazó. No se alteraron los artefactos originales ni el robot.

**Repetición verificada:** `20260827T141837_E1.2`, estado `PASS`. El wrapper
validó hash XML, preposiciones, catálogo exacto de tasks y doce PNG con hashes.
La hoja de contacto confirma un tote rígido gris abierto de paredes altas y
borde gris, con tiras/marcas negras estrechas en algunos frames y un pequeño
elemento con lazo dentro; no es cartón. Permanecen `UNRESOLVED` la definición de
`clamp_s2_joints_trajectory`, task ready instalado, alturas low/middle y pose
horizontal del fixture. No hubo conexión al robot, inferencia ni publicadores.

**Repetición del operador:** `20260827T142214_E1.2`, estado `PASS` tras revisión
visual. Todos sus artefactos validan contra sus hashes; varios PNG no son
bit-idénticos al run anterior porque VLC escogió frames adyacentes, pero la hoja
de contacto conserva el mismo tote, escenario y significado visual. No se usan
los hashes PNG como patrón canónico. Sin conexión al robot ni inferencia.

**Resultado esperado:** hash S2
`f4025124491eba995ec824db3e3be91875f781a4b4e98928654bde9a021d8323`;
el XML preposiciona cintura/cabeza/brazos y termina invocando
`clamp_s2_joints_trajectory`; tasks 0/1 son low y 2/3 middle. El SDK confirma
plataforma a 1 m de altura, pero no mapea low/middle a cotas ni da distancia
horizontal.

**PASS:** XML/hash/catalog, 12 frames con índice/hash y lista
`CONFIRMED/UNRESOLVED`. La inspección debe registrar que el objeto visual de
referencia es un tote gris abierto con detalles negros y no asumir equivalencia
con cartón/B0 vacía. **FAIL:** falta un artefacto o el hash cambió.

#### Experimento 1.3 — Medir B0 sobre la plataforma fuera de la envolvente

**Estado:** `EJECUTABLE_LECTURA`; robot inmóvil y sin usar su detector.

1. Crear un run nuevo; no reutilizar el directorio E1.0:

   ```bash
   VLA_RUN_DIR="$(./scripts/vla/new_vla_evidence_run.sh --experiment E1.3)"
   printf 'VLA_RUN_DIR=%s\n' "$VLA_RUN_DIR"
   ```

2. Pesar B0 vacía.
3. Colocarla sobre la plataforma a `x=0`, cara frontal `0,050 m` detrás del
   borde, lado de 0,603 m paralelo al borde y `yaw=0°`.
4. Medir L/W/H, centro y altura superior esperada
   `1,000 + 0,217 = 1,217 m`.
5. Fotografiar frontal/lateral/superior y retirar de nuevo plataforma+B0 fuera
   de la envolvente.

**PASS:** dimensiones dentro de `±0,010 m`, superficie a `1,000 ±0,010 m`,
pose marcada y masa registrada. `D_BUMPER_PLATFORM` continúa `null`.

**Resultado real 2026-08-28:** `PASS_FOR_OOD_SHADOW_ONLY`. Se reutilizan las
dimensiones ya registradas de B0 `0,603 × 0,397 × 0,217 m` y se congela la pose
nominal sólo como metadato. Masa, fotos y validación de la colocación real se
aplazan hasta E4/E6 y siguen siendo obligatorias antes de cualquier canary
físico. Evidencia: `20260828T105453_E1.3`. Esto sólo libera E2.1 como smoke OOD
sin publicador; no valida semántica PICK/PLACE ni autoriza movimiento.

### Serie 2 — Primera inferencia shadow con las herramientas actuales

#### Experimento 2.0 — Task 0, PICK bajo, una inferencia sin movimiento

**Estado:** `PASS_SHADOW_SAFETY_ONLY` observado fuera de secuencia el
2026-08-28. E1.0 y E1.3 continúan pendientes; por ello este resultado no
autoriza E2.1 ni valida `PICK`.

**Escenario:** plataforma y B0 fuera de la envolvente; robot inmóvil en su
postura actual. Es un smoke test OOD: no representa `SUPPORTED_LOW`.

**Comando canónico:** el wrapper crea y valida su propio directorio de
evidencia, solicita STOP ante error/señal y exporta los logs de los contenedores
después de detenerlos:

```bash
./scripts/vla/run_vla_shadow_smoke.sh --task-id 0
```

No reconstruir manualmente esa secuencia. Si los contenedores ya están
detenidos y sólo faltan logs, crear una ruta exclusiva y recuperarlos sin
arrancarlos con:

```bash
VLA_RUN_DIR="$(./scripts/vla/new_vla_evidence_run.sh \
  --experiment RECOVERED-SHADOW)"
./scripts/vla/run_ubtech_vla_shadow.sh --export-evidence "$VLA_RUN_DIR"
```

**Resultado esperado:** goal task 0 aceptado por el action server, uno o más
chunks 10×20 finitos y verdict shadow `ACCEPT` o `REJECT` con causa. Desde
`home` es esperable `REJECT` por primer salto; eso es un PASS de seguridad, no
un PASS de la tarea. Siempre debe haber cero publishers físicos y cero
movimiento observado.

**PASS:** la inferencia termina, existe verdict explicable, `--stop` detiene
ambos contenedores y no aparece publisher. **FAIL:** timeout sin diagnóstico,
chunk inválido sin rechazo, publisher o movimiento.

**Resultado real:** registrar `ACCEPT/REJECT`, razón, máximo primer delta,
ejes implicados, latencia, chunk IDs, `flag_pred` y publishers.

**Ejecución observada y recuperada:** el intento manual comenzó el
2026-08-28 08:02 CEST. Como `$VLA_RUN_DIR` estaba vacío, los seis `tee`
fallaron contra `/`; no obstante, STOP dejó inferencia/control `exited` y
`COMMAND_PATH_SAFE=publishers:0`. Los logs persistentes se recuperaron, sin
arrancar contenedores, en
`Humanoide-vla-evidence/20260828T080202_E2.0_recovered/` y validan contra
SHA-256. Task 0 produjo dos chunks: `0 ACCEPT / 2 REJECT`, ambos por
`first_point_delta_violations:7`. El máximo fue
`R_shoulder_yaw_joint=1,339886 rad` frente al límite `0,35 rad`. La petición de
8 s terminó en `10,063076 s` —sobrepaso `2,063076 s` al completarse el ciclo en
curso—. La escena, dimensiones y postura inicial no quedaron documentadas, por
lo que se etiqueta `LIVE_CURRENT_SCENE_UNDOCUMENTED_OOD`. Resultado:
`PASS_SHADOW_SAFETY_ONLY`, nunca éxito físico de PICK. No se publicaron
comandos ni se movió el robot.

#### Experimento 2.1 — Task 2, smoke test medio sin fixture nominal

**Estado:** `PASS_SHADOW_SAFETY_ONLY`; ejecutado después de cerrar E1.0/E1.3
para progresión shadow y revisar E2.0.

**Escenario:** idéntico a E2.0; plataforma y B0 fuera de la envolvente. Sólo
cambia el task ID para verificar el catálogo y runtime.

**Comando:** cuando se libere el gate, usar el mismo wrapper con task 2:

```bash
./scripts/vla/run_vla_shadow_smoke.sh --task-id 2
```

**Resultado esperado/PASS:** iguales a E2.0, pero task/texto deben ser
`Pick up the large box from the middle level of shelf`. Comparar low y middle
sin afirmar que la diferencia sea correcta físicamente.

**Resultado real 2026-08-28:** run `20260828T105547_E2.1`. Task 2 terminó
`SUCCEEDED` como servicio de inferencia en `10,065012 s` para 8 s solicitados y
produjo dos chunks 10×20. El validador rechazó ambos por siete discontinuidades
del primer punto: `0 ACCEPT / 2 REJECT`; el máximo fue
`R_shoulder_yaw_joint=1,376502 rad` frente a `0,35 rad`. Los dos contenedores
terminaron `exited`, `COMMAND_PATH_SAFE=publishers:0`, hashes correctos y no se
ordenó movimiento. Resultado `PASS_SHADOW_SAFETY_ONLY`, no éxito de PICK medio.

#### Experimento 2.2 — Tasks 1 y 3, PLACE, con entrada reproducible

**Estado:** `PASS_OFFLINE_INFERENCE_ONLY` el 2026-08-28. No demuestra PLACE
físico ni generalización.

**Razón:** un PLACE necesita `HELD_LOW` o `HELD_MIDDLE`. No se pondrá al robot a
sujetar B0 sólo para crear una entrada shadow. Primero se implementa replay
offline de un episodio de place o un mock 20D+RGB documentado.

**Orden implementada:**

```bash
./scripts/vla/run_vla_offline_place_e2_2.sh --check
./scripts/vla/run_vla_offline_place_e2_2.sh --run --seed 0
```

El wrapper selecciona de forma determinista el último 15 % de episodios de
cada task como holdout **del proyecto**. El dataset sólo declara `train`, por
lo que no es un split test del proveedor ni demuestra que el checkpoint no
haya visto esos episodios. Staging e inferencia ocurren en un contenedor nuevo
de Vision con `--network none`, sin ROS, estado vivo ni `RobotCommand`; los
contenedores VLA persistentes permanecen detenidos.

**Resultado real:** run `20260828T112730_E2.2`. Task 1 seleccionó episodio 465
y task 3 episodio 265, ambos en frame 0 con semántica
`HELD_FROM_PLACE_EPISODE_TASK_AND_FRAME_0`. Los parquets reales omiten
`frame_index` aunque `meta/info.json` lo anuncia; el evaluador aceptó el índice
de fila sólo después de comprobar `timestamp=frame/120` y task/episodio
exclusivos. El checkpoint cargó en `27,296552 s`; inferencia task 1 tardó
`1,586348 s`, MAE `0,007283609`, y task 3 `0,401792 s`, MAE `0,011394879`.
Ambas salidas fueron 10×20 finitas, sin violaciones de rango ni del salto
conservador desde el estado replay. Al cierre:
`exited/exited/publishers:0`, hashes válidos, sin leer ni mover el robot.

Los runs `20260828T112327_E2.2` y `20260828T112419_E2.2` documentan fallos
previos antes de inferencia: incompatibilidad de `setup.bash` con `nounset` y
la contradicción de esquema citada. El run válido dejó inicialmente tres JSON
temporales propiedad de root; se eliminaron con otro contenedor sin red y el
wrapper quedó corregido para hacer esa limpieza también ante fallo.

**Interpretación:** PASS valida carga, replay RGB+20D, contrato de salida y
comparación contra diez acciones registradas. No evalúa que el robot deposite
una caja, altura low/middle, contacto, colisiones ni generalización fuera del
dataset; no libera publicación física.

#### Experimento 2.3 — Repetibilidad P20 OOD de tasks 0 y 2

**Estado:** `PASS_PILOT_2X2_SHADOW_ONLY`; se ejecutó el piloto reducido acordado
por el propietario después de E1.0/E1.3/E2.1. Mide runtime P20, no máscaras
14–19 ni éxito físico de las tareas.

**Escenario:** plataforma/B0 fuera de la envolvente. Ejecutar cinco repeticiones
task 0 y cinco task 2 sin cambiar escena, robot ni cámara. Esto mide
repetibilidad del runtime en una entrada OOD, no fidelidad de pick low/middle.

**Secuencia por bloque:**

```bash
./scripts/vla/run_vla_shadow_repetitions.sh --task-id 0 --repetitions 5
./scripts/vla/run_vla_shadow_repetitions.sh --task-id 2 --repetitions 5
```

Cada repetición usa un sub-run independiente y confirma STOP antes de iniciar la
siguiente; así no mezcla chunks, logs ni estado de inferencia. **PASS:** 5/5
ejecuciones por task terminan con verdict y cero publishers; se reporta
variación de latencia, endpoint, primer delta y `flag_pred`.

**Resultado real 2026-08-28:** dos repeticiones independientes por task, con
STOP entre runs. Task 0 (`20260828T110217_E2.3-task0`) produjo cuatro chunks:
`0 ACCEPT / 4 REJECT`; duración `10,006055…10,039981 s` y máximo delta por
chunk `1,361919…1,367893 rad`, siempre en `R_shoulder_yaw_joint`. Task 2
(`20260828T110617_E2.3-task2`) produjo cuatro chunks: `0 ACCEPT / 4 REJECT`;
duración `10,005578…10,006689 s` y máximo `1,372170…1,379845 rad`, también en
`R_shoulder_yaw_joint`. Todos los chunks repitieron siete violaciones del
primer punto. Los dos manifiestos SHA-256 validan; cada repetición y ambos
parents terminaron `exited/exited/publishers:0`. Resultado: runtime y rechazo
reproducibles en esta escena OOD; no se valida PICK ni se autoriza movimiento.
Las cinco repeticiones originales quedan como ampliación opcional, no como
requisito para continuar el trabajo offline.

### Serie 3 — Dataset, OOD y contrato temporal

#### Experimento 3.0 — Evaluación offline tasks 0–3

**Estado:** `PENDIENTE_CODIGO`. El evaluador E2.2 ya cubre un frame de tasks 1
y 3; falta ampliarlo a tasks 0–3, varios frames/seeds y agregación por episodio
sin reutilizar una muestra entre particiones.

**Escenario:** sin robot ni plataforma. Crear split por episodio/sesión, no por frame.
Para cada task ejecutar seeds `0,1,2,3,4`; repetir seed 0 cinco veces.

**Comando:** todavía no existe. El wrapper E2.2 ejecuta conjuntamente sólo
tasks 1/3 y rechaza 0/2; no se altera manualmente para simular E3.0. **PASS:**
salida 10×20 finita, métricas por eje/horizonte/task, ningún episodio compartido
entre train/test y C0 inmutable. **Resultado actual:**
`BLOCKED_MISSING_FOUR_TASK_MULTI_SAMPLE_EVALUATOR`.

#### Experimento 3.1 — OOD geométrico offline, una variable cada vez

**Estado:** `PENDIENTE_CODIGO`. Ya existe replay nominal para E2.2; falta la
transformación OOD versionada de imagen/geometría y su verificación.

**Escenario base:** frames de dataset task 0/2. Variantes sintéticas exactas:

```text
x = -0,100; -0,050; 0; +0,050; +0,100 m
cara frontal detrás del borde = 0,050; 0,100; 0,150 m
yaw = -15; -5; 0; +5; +15 grados
```

Se cambia una sola variable por transformación reproducible del frame/metadata.
No se aproxima físicamente plataforma o caja al robot para generar OOD.

**Resultado esperado:** un verdict por punto y mapa de sensibilidad. `ACCEPT`
significa sólo chunk estructuralmente aceptable, no capacidad de agarre.
**FAIL metodológico:** cambiar dos variables, recolocar mientras VLA está
activo o perder la foto/medida.

#### Experimento 3.2 — Mensajes inválidos y fault injection

**Estado:** `PENDIENTE_CODIGO`; sólo sink, nunca robot.

**Comando previsto:**

```bash
VLA_RUN_DIR="$(./scripts/vla/new_vla_evidence_run.sh --experiment E3.2)"
python3 scripts/vla/test_vla_executor_sink.py \
  --axis-profile P20_AHLW --fixture low --fault-suite all \
  --output "$VLA_RUN_DIR"
```

**Entradas:** NaN, Inf, dimensión distinta, orden permutado, estado >1 s,
chunk duplicado/regresivo, tiempo no monótono, rango/salto/velocidad excedidos,
cancel y doble cliente. **PASS:** 100 % rechazadas y cero publishers.

#### Experimento 3.3 — Tiempo, huecos, cancelación y end flag

**Estado:** parte `EJECUTABLE_SHADOW`, cancel/fault completo
`PENDIENTE_CODIGO`.

**Escenario:** para runtime vivo, plataforma/B0 fuera de la envolvente y robot
inmóvil; para semántica nominal, replay del dataset. Ejecutar E2.0 guardando
goal, feedback, timestamps de los diez puntos, siguiente chunk y STOP.

**Resultado esperado:** medir `Δt=0,08 s`, horizonte `0,72 s`, frecuencia real
de inferencia y hueco hasta el siguiente chunk. **PASS final:** existe una sola
semántica demostrada para hold, chunk viejo, `continuous_end_chunk_num`, timeout
y cancel. Mientras no se resuelva, no avanzar a ejecución física.

### Serie 4 — Obtener y validar las posturas `VLA_READY`

#### Experimento 4.0 — Completar la pose S2 suministrada

**Estado:** inspección `EJECUTABLE_LECTURA`; uso físico `BLOQUEADO_FISICO`.

**Evidencia disponible:**

- `codes-S2/.../s2_vla_pick_large_teleop_ready.xml`, hash
  `f4025124…d8323`, preposiciona waist `0`, cabeza `-0,65` y ambos brazos con
  segundo ángulo `-0,6`;
- después llama a `MetaMove name="clamp_s2_joints_trajectory"`, cuya
  trayectoria/semántica no está definida en ese XML;
- el SDK muestra otro nombre de task (`cruzr_bio_vla/...`) y exige mover el
  robot con el mando a una posición adecuada, pero no da la distancia.

**Trabajo exacto:** localizar en la instalación real, sólo lectura, qué task
S2 está cargado; resolver `clamp_s2_joints_trajectory`; obtener sus 20 estados,
duración, límites, swept volume, trayectoria inversa y precondición. Separar
ready de PICK/PLACE si son distintos. No aceptar el primer chunk como ready.

**PASS:** task canónico, hash, trayectoria completa, inverse/recovery y
dependencias demostradas. **Resultado actual:**
`BLOCKED_INCOMPLETE_S2_READY_AND_CLAMP_TRAJECTORY`.

#### Experimento 4.1 — Derivar offline la pose completa del fixture

**Estado:** `PENDIENTE_CODIGO` hasta PASS en E4.0; no usa el robot.

**No se ensaya una parrilla de distancias a ojo.** Se calcula la pose de
plataforma que satisface simultáneamente:

1. TCP izquierdo/derecho y caras laterales de B0 según la trayectoria S2;
2. superficie `z=1,000 m` y caja superior `z=1,217 m`;
3. ausencia de colisión en todo el swept volume;
4. caja completa y ubicación/escala visual compatibles con los frames iniciales
   de episodios 0/1/90/91;
5. margen de alcance y no una solución en singularidad/límite.

Se implementará `scripts/vla/derive_vla_fixture_pose.py` con inputs XML/task,
URDF/TF, B0, cámara/intrínsecos y frames de referencia. Su salida será una pose
completa `platform_in_base={x,y,z,roll,pitch,yaw}`, más
`D_BUMPER_PLATFORM`, error de reproyección y margen cinemático.

```bash
VLA_RUN_DIR="$(./scripts/vla/new_vla_evidence_run.sh --experiment E4.1)"
test -n "$VLA_READY_TASK"
test -s "$VLA_S2_URDF"
test -d "$VLA_E1_2_RUN_DIR/reference_frames"
python3 scripts/vla/derive_vla_fixture_pose.py \
  --ready-task "$VLA_READY_TASK" --urdf "$VLA_S2_URDF" \
  --box-lwh 0.603,0.397,0.217 --platform-height 1.000 \
  --reference-frames "$VLA_E1_2_RUN_DIR/reference_frames" \
  --output "$VLA_RUN_DIR/fixture_pose.yaml"
```

**PASS:** una única pose candidata versionada, sin colisión y reproducible. Si
no hay solución o los criterios discrepan, `FAIL_NO_COMPATIBLE_FIXTURE_POSE`.
Todavía no se mueve el robot ni se coloca la plataforma delante.

#### Experimento 4.2 — Resolver qué alturas corresponden a low/middle

**Estado:** análisis `PENDIENTE_CODIGO`; físico `BLOQUEADO_FISICO`.

El SDK S2 confirma 1 m, mientras los task texts dicen low/middle y el árbol
no-S2 incluye alturas 55/70/85/100/115. Se reconstruye cada task a partir de
frames, estados iniciales/finales, lifter y FK, y se solicita confirmación de
UBTECH. La salida debe ser `H_TASK_0_1` y `H_TASK_2_3` con fuente e
incertidumbre. No se asigna automáticamente `0,55/1,15 m`.

**PASS:** cada task tiene una altura y pose de soporte demostradas. Si sólo se
confirma la plataforma de 1 m, se valida primero únicamente el task/escenario
que corresponda y los demás quedan bloqueados.

#### Experimento 4.3 — Validar la pose S2 en vacío

**Estado:** `BLOQUEADO_FISICO` hasta PASS en E4.0/E4.1 e implementación de
`scripts/vla/cruzr_vla_ready_pose.sh`.

**Escenario futuro:** plataforma/B0 retiradas más de 1,5 m; zona completa
vacía; abrazaderas vacías; robot estable; cargador fuera; ambos paros
comprobados; persona junto al paro.

**Órdenes futuras, en una sesión autorizada:**

```bash
test -n "$VLA_READY_TASK"  # valor canónico producido y registrado por E4.0
./scripts/vla/cruzr_vla_ready_pose.sh --check --task "$VLA_READY_TASK"
./scripts/vla/cruzr_vla_ready_pose.sh --run --task "$VLA_READY_TASK"
```

**PASS:** completa la trayectoria suministrada sin contacto/oscilación, termina
a velocidad cero y tiene trayectoria inversa comprobable. **Aborto:** movimiento
no previsto, FT, salto o discrepancia. STOP y mantener postura; no home
automático.

#### Experimento 4.4 — Validar y congelar el fixture calculado

**Estado:** `BLOQUEADO_FISICO`.

Con el robot parado, colocar primero un target visual ligero en la pose
calculada de E4.1 y ejecutar sólo shadow; validar encuadre. Retirarlo. En una
sesión posterior, y sólo si el swept volume validado no intersecta el fixture,
colocar la plataforma vacía; repetir ready determinista y shadow. Finalmente
repetir con `B0_SAFE` vacía. Cada transición requiere STOP, personas fuera y
foto/medida nueva. Publicar exactamente
`H_TASK_*`, `platform_in_base`, `D_BUMPER_PLATFORM` y tolerancias. Si cualquier
campo queda `null`, toda la Serie 7 permanece bloqueada.

### Serie 5 — Máscaras 14–20 y ejecutor sink

#### Experimento 5.0 — Tests de los ocho perfiles

**Estado:** `PENDIENTE_CODIGO`.

**Escenario:** sin robot. Chunks guardados y poses hold low/middle. Ejecutar
`test_vla_executor_sink.py` para `P14_A`, `P15_AW`, `P16_AH`, `P17_AL`,
`P17_AHW`, `P18_ALW`, `P19_AHL`, `P20_AHLW`.

**PASS:** ejes habilitados copian el chunk; bloqueados mantienen la pose real,
no cero; fault suite aprobada y cero import/publicación de `RobotCommand`.

#### Experimento 5.1 — Matriz shadow 4 tasks × 8 perfiles × 5

**Estado:** `PENDIENTE_CODIGO` hasta implementar
`scripts/vla/run_vla_shadow_matrix.sh`.

**Comando de cada celda:**

```bash
VLA_RUN_DIR="$(./scripts/vla/new_vla_evidence_run.sh --experiment E5.1)"
./scripts/vla/run_vla_shadow_matrix.sh \
  --scenario SUPPORTED_LOW --task-id 0 --axis-profile P14_A \
  --repetitions 5 --output "$VLA_RUN_DIR"
```

Cambiar escenario/task/perfil según la tabla 0.3; tasks 1/3 usan replay HELD,
no un agarre físico. **PASS:** 160 bundles y cero publishers.

#### Experimento 5.2 — Selección shadow preliminar

**Estado:** `PENDIENTE_CODIGO`.

```bash
VLA_RUN_DIR="$(./scripts/vla/new_vla_evidence_run.sh --experiment E5.2)"
python3 scripts/vla/analyze_vla_campaign.py \
  --input /home/lacuna/proyectos/Robots/Humanoide-vla-evidence \
  --select-minimal-profile \
  --output "$VLA_RUN_DIR/shadow-profile-selection.json"
```

**PASS:** perfil candidato por task y razón cuantitativa para H/L/W. No autoriza
movimiento.

### Serie 6 — Canary físico sin caja

Toda esta serie está `BLOQUEADO_FISICO` hasta PASS en E4.4/E5.2, ejecutor
revisado y primitiva `clamp_s2_joints_trajectory` demostrada.

#### Experimento 6.0 — Un punto P14 sin caja

**Escenario futuro:** plataforma y B0 retiradas >1,5 m; ready S2 validado; ruedas
bloqueadas; cargador fuera; persona en paro; un cliente.

```bash
./scripts/vla/run_cruzr_vla_canary.sh --check \
  --task-id 0 --axis-profile P14_A --scenario NO_BOX_READY
./scripts/vla/run_cruzr_vla_canary.sh --one-point \
  --task-id 0 --axis-profile P14_A --scenario NO_BOX_READY
./scripts/vla/run_cruzr_vla_canary.sh --stop
```

**PASS:** sólo brazos, delta pequeño autorizado, velocidad/fuerza dentro de
gate, STOP y velocidad cero. Repetir tres veces.

#### Experimento 6.1 — Un chunk y dos chunks P14

Después de E6.0, ejecutar `--one-chunk`; STOP/revisión; luego `--window` limitado
a dos chunks; STOP/revisión. **FAIL:** continuidad incorrecta, salto, oscilación
o postura no clasificable.

#### Experimento 6.2 — Añadir H, W y L aisladamente

Probar en sesiones separadas P16_AH, P15_AW y P17_AL; después combinaciones
P17_AHW/P18_ALW/P19_AHL/P20. Cada perfil comienza de nuevo en un punto y exige
tres repeticiones limpias. No se habilita un grupo porque el anterior funcionó.

#### Experimento 6.3 — Timeout, cancel y STOP físico

Ejecutar ventanas cortas primero terminadas por timeout y después por cancel.
Medir latencia hasta velocidad cero. **PASS:** no se ejecuta ningún chunk tras
STOP/cancel y recovery deja estado conocido.

### Serie 7 — Las cuatro tareas físicas con B0 vacía

Toda esta serie está `BLOQUEADO_FISICO`; necesita autorización por experimento.
Usa altura y pose completa congeladas en E4.4. El único `1,000 m` confirmado
es altura de plataforma; no existe distancia horizontal por defecto.

#### Experimento 7.0 — PICK bajo, task 0

**Inicio:** B0 `SUPPORTED_LOW`, pose nominal; robot `VLA_READY_LOW`; plataforma
en `platform_in_base` y `H_TASK_0_1` resueltos por E4; B0 pesada/vacía;
abrazaderas vacías.

```bash
./scripts/vla/run_cruzr_vla_canary.sh --check \
  --task-id 0 --axis-profile PROFILE_APROBADO --scenario SUPPORTED_LOW
./scripts/vla/run_cruzr_vla_canary.sh --one-chunk \
  --task-id 0 --axis-profile PROFILE_APROBADO --scenario SUPPORTED_LOW
./scripts/vla/run_cruzr_vla_canary.sh --stop
```

**Esperado:** `HELD_LOW`, suspendida estable, fuerza dentro de gate, sin apoyo.
Primero 1 intento; si PASS, 3; si todos PASS, 10. Si queda `UNKNOWN`, STOP y no
home.

#### Experimento 7.1 — PLACE bajo, task 1

**Inicio:** `HELD_LOW` demostrado y superficie low vacía. Mismo patrón de
comandos con task 1/scenario `HELD_LOW`. **Esperado:** `SUPPORTED_LOW`,
abrazaderas libres y brazos retirados. No crear HELD improvisando.

#### Experimento 7.2 — PICK medio, task 2

**Inicio:** B0 `SUPPORTED_MIDDLE`, `VLA_READY_MIDDLE`, plataforma en la pose y
`H_TASK_2_3` resueltas por E4. Mismo patrón con task 2. **Esperado:**
`HELD_MIDDLE`.

#### Experimento 7.3 — PLACE medio, task 3

**Inicio:** `HELD_MIDDLE` demostrado. Mismo patrón con task 3. **Esperado:**
`SUPPORTED_MIDDLE`, abrazaderas libres y retirada limpia.

#### Experimento 7.4 — Repetibilidad y decisión física

Completar `1+3+10` por task/perfil sin contenido, navegación ni volcado.
Registrar éxito, fuerza máxima, tiempo, STOP y recovery. Cualquier incidente
peligroso invalida esa celda; no se promedia como un fallo ordinario.

### Serie 8 — Elegir o evolucionar el checkpoint

#### Experimento 8.0 — Selección final de dimensiones

**Estado:** `PENDIENTE_CODIGO`; análisis sin robot.

Comparar E5/E7 y elegir el menor perfil que iguale al completo por task. La
salida es `task→profile`, dominio físico aprobado y holds H/L/W.

#### Experimento 8.1 — Candidato C1 continuando checkpoint-40000

**Estado:** `PENDIENTE_DATOS_Y_CODIGO`; sin salida al robot.

Recopilar/curar nuevos datos manteniendo 1 RGB, abrazaderas y acción 20D;
incluir cajas/tamaños/poses/alturas y futuros `TIP/POUR`, mezclando tareas 0–3.

```bash
./scripts/vla/train_cruzr_vla_candidate.sh \
  --base C1_CONTINUE_40000 --dataset-manifest DATASET_MANIFEST \
  --data-config utars1 --output CHECKPOINT_OUTPUT
```

Repetir Series 3–7 desde cero para cada candidato. Nunca sobrescribir C0.

#### Experimento 8.2 — Candidato C2 con contrato nuevo

**Estado:** `PENDIENTE_DISENO`; sin salida al robot.

Sólo si se añaden dedos, pinza activa, fuerza como input, profundidad, cámaras o
chasis: partir de GR00T N1.5 base, crear DataConfig/estado/acción nuevos y
datasets nuevos. No conectar `checkpoint-40000` a una salida de distinta
dimensión. El experimento termina con una model card y vuelve a Serie 3; no
pasa directamente al robot.

### Punto exacto de comienzo

E1.0 y E1.3 quedaron cerrados para progresión shadow; fotos, marcas, masa y
colocación real siguen diferidas a E4/E6 antes de cualquier movimiento. E1.1 y
E1.2 ya están aprobados y no se repiten. E2.0 quedó registrado sólo como smoke
OOD seguro; el próximo experimento es **E2.1**, también OOD y sin publicador. El primer
experimento con movimiento determinista sería E4.3 y el primer canary VLA sería
E6.0; ambos siguen bloqueados por dependencias explícitas y requieren
autorización física futura independiente.

## 0. Próximo bloque prioritario: caracterización integral del VLA

Éste es el trabajo que se realizará **antes** de ampliar la misión de cajas. Su
objetivo es determinar, con evidencia reproducible, qué puede ejecutar el
`checkpoint-40000` intacto, qué subconjunto de sus 20 salidas debe gobernar el
robot y qué capacidades requieren continuar el entrenamiento.

La campaña no presupone que 20 ejes sean mejores que 14. Probará todas las
combinaciones funcionales razonables y conservará el menor espacio de mando que
complete la tarea de forma segura y repetible.

Este apartado es planificación. No habilita el publicador físico, no arranca
los contenedores VLA y no autoriza una postura `VLA-ready` ni movimiento.

### 0.1 Capacidad que se somete a prueba

El checkpoint actual está entrenado, no simplemente propuesto, para:

| Task ID canónico | Instrucción exacta | Episodios |
|---:|---|---:|
| 0 | `Pick up the large box from the lowest level of shelf` | 150 |
| 1 | `Place the large box on the lowest level of shelf` | 150 |
| 2 | `Pick up the large box from the middle level of shelf` | 100 |
| 3 | `Place the large box on the middle level of shelf` | 100 |

Su contrato verificado es:

- una RGB de la cámara estéreo principal; fuente `960 × 576`, recorte 0,95 y
  entrada de modelo `224 × 224`;
- una de las cuatro instrucciones anteriores;
- una muestra de 20 posiciones articulares como estado;
- salida de 10 posiciones absolutas por 20 articulaciones;
- orden: 7 brazo izquierdo, 7 derecho, 2 cabeza, 3 elevador y 1 cintura;
- normalización `min_max`, cuatro pasos de denoising y cómputo `bfloat16`;
- 500 episodios, 105 207 frames, checkpoint en step 40 000, batch 16 y
  aproximadamente 6,08 épocas;
- 12 valores FT guardados en los datos pero **no consumidos por el modelo**;
- ninguna acción para chasis, dedos ni pinza eléctrica.

El SDK S2 sección 7.3 sí confirma una caja `60 × 40 × 22 cm` sobre una
plataforma de `1 m de altura` para reproducir el demo. No especifica la
distancia horizontal ni mapea los textos low/middle del dataset a alturas. Los
XML 55/70/85/100/115 pertenecen al árbol alternativo `codes` no-S2 y no se
usarán como rango S2 sin demostrar su compatibilidad.

El comentario de `InferenceTask.action` contiene un orden antiguo de tareas que
no coincide con `tasks.jsonl` ni con el YAML vivo. Antes de probar se fijará un
único catálogo canónico con los IDs de la tabla anterior.

### 0.2 Qué significa probar de 14 a 20

El modelo siempre calcula 20 valores. Lo que varía es qué grupos puede publicar
un ejecutor independiente. Los ejes bloqueados se mantienen en su posición
real/preposición validada; nunca se sustituyen por cero.

Se consideran atómicos los grupos funcionales:

- `A`: ambos brazos, 14 ejes;
- `H`: cabeza, 2 ejes;
- `L`: elevador, 3 ejes;
- `W`: cintura, 1 eje.

El conjunto exhaustivo de combinaciones por grupos es:

| Perfil | Dimensiones habilitadas | Grupos | Pregunta que responde |
|---|---:|---|---|
| `P14_A` | 14 | A | ¿Basta preposicionar cuerpo/cámara y dejar al VLA sólo la manipulación? |
| `P15_AW` | 15 | A+W | ¿La pequeña corrección de cintura mejora alcance sin mover elevador/cámara? |
| `P16_AH` | 16 | A+H | ¿El movimiento de cabeza aporta observación o desestabiliza el encuadre? |
| `P17_AL` | 17 | A+L | ¿El elevador aprendido es necesario para distinguir alturas? |
| `P17_AHW` | 17 | A+H+W | ¿Cabeza+cintura ayudan cuando la altura está preposicionada? |
| `P18_ALW` | 18 | A+L+W | ¿Elevador+cintura bastan manteniendo fija la cámara? |
| `P19_AHL` | 19 | A+H+L | ¿Cabeza+elevador bastan manteniendo fija la cintura? |
| `P20_AHLW` | 20 | A+H+L+W | ¿La política completa supera de forma demostrable a un perfil reducido? |

Hay dos perfiles de 17 dimensiones porque son combinaciones funcionalmente
distintas. No se probarán los 64 subconjuntos arbitrarios de seis ejes: romper
un grupo cinemático —por ejemplo mandar sólo una articulación del elevador— no
representa una capacidad prevista y puede ser físicamente inválido.

### 0.3 Matriz mínima de cobertura

La matriz shadow base tiene `4 tareas × 8 perfiles = 32 celdas`. Cada tarea se
ejecuta desde su postura baja o media correspondiente y con cinco repeticiones
controladas, para un mínimo de 160 inferencias aceptadas o rechazadas con causa.

Por cada celda se registran además:

- checkpoint/hash, configuración, seed y task ID;
- imagen, estado 20D y postura inicial;
- chunk bruto 10×20 antes de máscara y chunk efectivo después de máscara;
- latencia, uso de GPU/VRAM y frecuencia real;
- clipping por eje, rango, velocidad, primer salto y continuidad entre chunks;
- `flag_pred`, criterio de fin, cancelación y timeout;
- veredicto `ACCEPT`, `REJECT_SAFE`, `OOD` o `INVALID_RUNTIME`.

Las pruebas físicas no heredan automáticamente las 32 celdas. Sólo una celda
aprobada offline y shadow puede pasar, una por una, al canary físico.

### 0.4 Gate VLA-0 — Congelar artefactos y corregir contradicciones

**Sólo lectura y cambios en repositorio; ningún movimiento.**

1. Calcular y guardar SHA-256 de pesos, `config.json`, metadatos, DataConfig,
   YAML vivo, runtime y dataset.
2. Confirmar que sólo existe `checkpoint-40000`; no llamar “alternativa” a un
   checkpoint que no esté físicamente disponible.
3. Fijar el catálogo task ID 0–3 de `tasks.jsonl` y hacer que scripts, action y
   logs lo validen antes de inferir.
4. Inventariar exactamente los 20 nombres, unidades, límites min/max y orden.
5. Separar límites del dataset, límites mecánicos del robot y límites
   conservadores del canary; ninguno sustituye a los otros.
6. Resolver documentalmente estas inconsistencias antes de movimiento:
   - dataset declarado a 120 FPS frente a puntos runtime cada 0,08 s;
   - inferencia a 0,2 Hz frente a un chunk que termina en 0,72 s;
   - `continuous_end_chunk_num=5` declarado pero no aplicado por el código;
   - `/mc/sdk/robot_state` sin muestras frente al fallback
     `/mc/whole_joint_states`;
   - definición/ausencia de `clamp_s2_joints_trajectory`.
7. Demostrar que ambos contenedores continúan con `restart=no` y que shadow
   crea cero publicadores en `/mc/sdk/robot_command`.

**Salida del gate:** manifiesto inmutable de la campaña y lista cerrada de
deudas. Cualquier cambio posterior genera un nuevo `runtime_id`.

### 0.5 Gate VLA-1 — Evaluación offline del checkpoint intacto

**Sin conexión de salida al robot.**

1. Crear splits retenidos por episodio y sesión. El dataset suministrado sólo
   declara `train=0:500`, por lo que no existe evaluación independiente.
2. Ejecutar las cuatro tareas sobre episodios no usados para seleccionar
   parámetros de evaluación.
3. Comparar cada predicción con la trayectoria 20D registrada:
   - error por articulación y por horizonte;
   - error de primer punto y endpoint;
   - continuidad entre ventanas;
   - porcentaje recortado a min/max;
   - precisión y anticipación del `flag_pred`.
4. Ejecutar cinco inferencias idénticas con seed fijo y cinco con seeds
   distintos para medir variabilidad de la difusión.
5. Auditar separadamente recogida, depósito, nivel bajo y nivel medio; una media
   global no puede ocultar el fallo de una tarea.
6. Revisar muestras visuales y medir, si es posible, caja, estantes, encuadre,
   iluminación, offsets y yaw observados. Lo que no se pueda medir queda
   `UNKNOWN`, no se atribuye al modelo.
7. Probar replay puramente cinemático de los chunks; no publicar comandos.

**Criterio de avance:** chunks finitos 10×20, catálogo correcto, métricas por
tarea y ningún supuesto pendiente sobre el orden de ejes.

### 0.6 Gate VLA-2 — Robustez, límites y fuera de distribución

**Offline o shadow sin publicador.**

Probar sistemáticamente:

| Familia | Casos |
|---|---|
| Entrada nominal | caja/estante del dataset, postura baja y media |
| Caja | ausente, parcialmente ocluida, desplazada lateral/profundidad, yaw distinto, otro tamaño/color |
| Escena | luz baja/alta, fondo cambiado, persona fuera de envolvente pero visible, receptor añadido |
| Cámara | frame congelado, timestamp viejo, pérdida, oclusión y resolución incorrecta |
| Estado | articulación ausente, orden cambiado, NaN/Inf, timestamp viejo y valores cerca/fuera de rango |
| Lenguaje | IDs 0–3 correctos, ID inválido y contradicción ID/instrucción |
| Runtime | pérdida de Vision/Motion, chunk duplicado, ID regresivo, timeout y cancelación |

El resultado esperado para entradas inválidas no es “algún movimiento
razonable”, sino rechazo antes del ejecutor. Los casos válidos pero fuera de la
distribución delimitan el dominio que requerirá nuevos datos.

**Criterio de avance:** 100 % de entradas estructuralmente inválidas rechazadas
y mapa OOD por tarea publicado.

### 0.7 Gate VLA-3 — Resolver el contrato temporal y el fin de tarea

Antes de movimiento se debe elegir y demostrar una sola semántica temporal:

1. determinar si los 120 FPS representan muestras físicas, interpolación o
   sólo timestamps de exportación;
2. determinar por qué el runtime expande 10 filas a puntos de 80 ms;
3. fijar la frecuencia de inferencia y qué mantiene el robot entre chunks;
4. prohibir huecos sin comando vigente, repetición silenciosa de un chunk viejo
   o colas que ejecuten después de STOP;
5. implementar y probar `N` flags consecutivos si ésa es la condición de fin,
   o eliminar el parámetro engañoso;
6. probar cancelación antes, durante y después de inferencia;
7. probar pérdida de imagen/estado y expiración del último chunk.

**Criterio de avance:** timeline documentada extremo a extremo —sensor,
inferencia, chunk, ejecutor y feedback— y STOP con latencia medida.

### 0.8 Gate VLA-4 — Posturas `VLA-ready` baja y media

El checkpoint ya demostró que `home` no es una postura inicial compatible:
ocho ejes de brazo superaron el límite conservador y el máximo rondó 1,35 rad.

1. Auditar la definición suministrada
   `codes-S2/.../s2_vla_pick_large_teleop_ready.xml` (hash `f4025124…d8323`),
   resolver su llamada `clamp_s2_joints_trajectory` y comprobar cuál es el task
   realmente instalado; no reconstruirlo a partir del primer chunk.
2. Derivar, o conseguir de UBTECH, los ready específicos low/middle y la pose
   completa de plataforma, incluyendo altura, distancia horizontal, cabeza,
   elevador, cintura, caja y encuadre. El SDK sólo confirma plataforma a 1 m.
3. Validar cada postura primero como trayectoria determinista independiente,
   con preflight físico fresco y autorización específica en otra intervención.
4. Repetir shadow de los cuatro tasks desde su postura correcta.
5. Rechazar todo chunk cuyo primer punto exceda los límites por eje; no ocultar
   el salto con clipping o smoothing.
6. Registrar cuánto cambiarían H/L/W. Esto decide si `P14_A` puede ser fiel o si
   ignoraría una parte esencial de la política.

**Criterio de avance:** cinco primeros chunks consecutivos aceptados por task y
postura, sin mover el robot durante esta evaluación.

### 0.9 Gate VLA-5 — Ejecutor independiente, en sink/simulación

El ejecutor no será una modificación rápida del nodo de inferencia. Debe:

1. aceptar únicamente `runtime_id`, checkpoint, task y perfil de ejes
   autorizados;
2. validar 10×20, finitud, orden, rango, timestamps, monotonía de `chunk_id`,
   estado fresco y primer salto;
3. publicar sólo los nombres habilitados; los grupos bloqueados permanecen bajo
   hold determinista en su postura validada;
4. tener deadman, timeout de estado/imagen/chunk, cancelación, STOP externo y
   límite de duración;
5. no importar ni publicar al topic físico en modo `sink`, `offline` o
   `shadow`;
6. impedir dos clientes, replays tardíos y ejecución después de cancelación;
7. conservar protecciones FT, límites, anticolisión y paros del robot;
8. registrar comando solicitado, aceptado, rechazado y estado observado;
9. verificar velocidad y aceleración con una primitiva oficial de trayectoria;
10. fallar cerrado si la primitiva `clamp_s2_joints_trajectory` no existe o su
    contrato no está demostrado.

Los límites actuales del validador —no certificados como límites mecánicos—
son: estado ≤1 s; tolerancia de rango 0,05; velocidad entre puntos de brazos
1,25 rad/s, cabeza 0,50, elevador 0,25 y cintura 0,35; salto inicial máximo de
brazos 0,35 rad, cabeza 0,20, elevador 0,25 y cintura 0,15. El canary físico
puede imponer valores más estrictos, nunca más laxos sin evidencia.

**Criterio de avance:** tests automatizados de aceptación/rechazo, STOP y
máscaras para los ocho perfiles, sin publicador físico.

### 0.10 Gate VLA-6 — Matriz shadow de los ocho perfiles

Para cada una de las 32 celdas task/perfil:

1. colocar lógicamente el estado correspondiente a `VLA_READY_LOW` o
   `VLA_READY_MIDDLE`;
2. generar cinco rollouts shadow;
3. validar primero la salida completa P20 sin máscara;
4. construir el chunk efectivo del perfil conservando en los ejes bloqueados
   la postura de hold;
5. comparar endpoint, continuidad y geometría con P20;
6. medir si H, L o W tienen movimiento significativo o sólo ruido;
7. simular la trayectoria y revisar autocolisión, alcance y encuadre;
8. rechazar perfiles que eliminen un grupo necesario para completar la tarea.

Resultados esperados que deben demostrarse, no suponerse:

- `P14_A` puede funcionar si cuerpo/cámara se preposicionan y H/L/W permanecen
  prácticamente constantes durante el task;
- `P17_AL` puede reproducir mejor el cambio bajo/medio si el elevador forma
  parte esencial de la demostración;
- cabeza o cintura pueden permanecer bloqueadas si no mejoran la tarea;
- `P20_AHLW` sólo se justifica si supera perfiles reducidos y conserva margen
  de seguridad.

**Criterio de avance:** tabla 32×métricas completa y recomendación de perfil por
task. Shadow debe seguir mostrando cero publicadores físicos.

### 0.11 Gate VLA-7 — Canary físico sin caja

Este gate requiere una futura autorización explícita y un preflight físico
nuevo. Se ejecuta en una sesión distinta; este documento no la concede.

Orden de escalado por cada perfil aprobado:

1. robot en postura `VLA-ready`, caja retirada y envolvente completa despejada;
2. ejecutar una única consigna aceptada y de delta muy pequeño mediante la
   primitiva segura;
3. STOP, velocidad cero y revisión de logs;
4. ejecutar un chunk aceptado;
5. STOP y revisión;
6. ejecutar dos chunks con continuidad demostrada;
7. ejecutar una ventana corta cerrada por timeout y después por cancelación;
8. repetir tres veces sin anomalía antes de añadir otro grupo.

Orden recomendado de grupos, manteniendo siempre A como base:

```text
P14_A -> aislar P16_AH -> aislar P15_AW -> aislar P17_AL
      -> P17_AHW / P18_ALW / P19_AHL -> P20_AHLW
```

“Aislar” significa que cada subsistema nuevo se prueba primero sin combinarlo
con los otros. El elevador se prueba después de cabeza/cintura por su impacto en
altura, alcance y centro de masa.

**Aborta:** primer salto, movimiento de grupo bloqueado, contacto, trip FT,
oscilación, pérdida de imagen/estado, latencia fuera del contrato, end flag
prematuro, STOP tardío o postura final no clasificable.

### 0.12 Gate VLA-8 — Las cuatro tareas físicas del checkpoint

Sólo después del canary sin caja:

1. usar una caja vacía cuya geometría y escena se hayan comparado con el
   dataset; una caja “parecida” no se considera automáticamente equivalente;
2. probar task 0 con `P14_A` desde `VLA_READY_LOW`;
3. probar task 1 sólo cuando la caja esté `HELD` de forma demostrada y exista
   una recuperación específica;
4. repetir tasks 2 y 3 desde `VLA_READY_MIDDLE`;
5. repetir cada task con los perfiles adicionales aprobados en shadow;
6. ejecutar una sola caja y una sola tarea por ensayo;
7. realizar 1 canary, después 3 repeticiones y finalmente 10 para declarar una
   celda validada;
8. no probar todavía contenido, navegación ni volcado.

Éxito de `PICK`: caja suspendida estable, sin contacto externo, fuerza dentro
de protección y estado `HELD` demostrado. Éxito de `PLACE`: apoyo estable,
abrazaderas libres, brazos retirados y caja `SUPPORTED`. El `flag_pred` no
sustituye estas verificaciones.

**Criterio de avance:** matriz task/perfil con tasa de éxito, fuerza máxima,
tiempo, STOP y recovery; cero fallos peligrosos.

### 0.13 Gate VLA-9 — Seleccionar 14, 15, 16, 17, 18, 19 o 20

La decisión se toma por tarea, no para todo el robot:

| Evidencia | Decisión |
|---|---|
| P14 iguala P20 | Mantener cabeza/elevador/cintura deterministas |
| Sólo L mejora bajo/medio | Usar P17_AL o preposicionar L determinísticamente, comparando ambos |
| H mejora visibilidad sin inestabilidad | Considerar P16/P19/P20 |
| W mejora alcance de forma repetible | Considerar P15/P18/P20 |
| Un grupo no mejora éxito o aumenta riesgo | Mantenerlo bloqueado |
| P20 supera significativamente y pasa todos los gates | Autorizarlo sólo para ese task/escena |

La métrica prioriza: cero incidentes, STOP/recovery, éxito físico, continuidad,
fuerza/contacto, repetibilidad y finalmente tiempo. No se habilita un eje sólo
porque el checkpoint produzca un valor para él.

### 0.14 Gate VLA-10 — Probar las posibilidades de evolución del checkpoint

Después de establecer el baseline intacto se comparan tres ramas:

| Rama | Punto de partida | Qué puede cubrir |
|---|---|---|
| `C0_VENDOR_40000` | checkpoint intacto | Las cuatro tareas originales dentro de su distribución |
| `C1_CONTINUE_40000` | copia del checkpoint + mezcla de datos viejos/nuevos | Nuevos tamaños, poses, yaw, alturas y `TIP/POUR` con 1 RGB, abrazaderas y 20D |
| `C2_GROOT_BASE` | `nvidia/GR00T-N1.5-3B` + DataConfig nuevo | Dedos, pinza activa, fuerza aprendida, más cámaras, profundidad o chasis |

Para `C1`:

1. conservar inmutable `C0`;
2. capturar episodios nuevos con exactamente 1 RGB y estado/acción 20D;
3. separar instrucciones `PICK`, `PLACE`, `TIP/POUR` y `RETURN_UPRIGHT`;
4. mezclar tareas antiguas para evitar olvido;
5. evaluar tareas antiguas y nuevas en splits por sesión/caja/altura;
6. repetir desde Gate VLA-1 hasta VLA-9 para cada candidato.

Para `C2` se define primero un contrato distinto; no se conectan pesos C0 a una
salida que incluya dedos, base o fuerza.

### 0.15 Campaña de generalización después del baseline VLA

Sólo para el perfil/checkpoint ganador y mediante OFAT:

1. posición lateral;
2. profundidad;
3. yaw;
4. altura baja/media adicional;
5. tamaño y color de caja;
6. iluminación/fondo;
7. caja vacía frente a carga ligera;
8. receptor y volcado, tras entrenar `C1`.

Cada variación se prueba offline, shadow, canary sin caja y caja vacía antes de
carga ligera. Una combinación fuera del dataset no se convierte en capacidad
por completar una sola vez.

### 0.16 Entregables antes de continuar la misión de cajas

- manifiesto de artefactos y catálogo task ID canónico;
- informe de dataset, splits y geometría conocida/desconocida;
- contrato temporal corregido;
- ejecutor sink/simulación con ocho máscaras y tests;
- reporte de 32 celdas shadow;
- definición validada de posturas `VLA_READY_LOW/MIDDLE`;
- reporte canary y físico por task/perfil, si se autoriza posteriormente;
- decisión documentada de perfil mínimo por task;
- decisión `C0`, `C1` o `C2` para recogida, depósito y futuro volcado;
- rollback que detenga contenedores y deje cero publicadores físicos.

Los stages 10–13 posteriores de este documento resumen captura, entrenamiento y
despliegue dentro de la misión completa. En caso de discrepancia, esta campaña
VLA prioritaria impone los gates más estrictos.

### 0.17 Fixture físico común y sistema de coordenadas

Las pruebas no comenzarán con una caja, mesa o distancia elegidas a ojo. Cada
ejecución usará un `scenario_id` versionado y fotografías de las marcas antes
de arrancar inferencia.

#### Caja segura inicial `B0_SAFE` y referencia visual del dataset

| Propiedad | Valor inicial |
|---|---|
| Geometría exterior | `0,603 × 0,397 × 0,217 m` (`L × W × H`) |
| Estado de canary | vacía, seca y sin piezas sueltas; confirmar si es tote abierto o caja |
| Masa | `PENDIENTE_DE_MEDIR`; se pesa y registra antes de cualquier canary físico |
| Orientación nominal | lado de 0,603 m paralelo a los hombros (`+x/-x`); fondo de 0,397 m en `+y` |
| Efectores | abrazaderas vacías al inicio; apertura y fuerza no son acciones del VLA 20D |
| Uso | una sola caja por ensayo; sin contenido durante Gates VLA-0…VLA-9 |

`B0_SAFE` es la caja de trabajo conocida por el detector `workbin`, no una
demostración de que coincida con la “large box” del dataset. Los frames de los
episodios 0/1/90/91 muestran un tote rígido gris abierto de paredes altas, borde
gris, tiras/marcas negras estrechas en algunos frames y un pequeño elemento con
lazo en el interior. Antes de una prueba
física se compara material, color, abertura, borde, asas y contenido además de
la geometría. Una B0 vacía distinta sigue siendo el canary seguro, pero se
etiqueta OOD hasta recopilar datos propios; no se convierte en “nominal” por
medir 60×40×22 cm.

#### Plataforma inicial y alturas de task

El fixture suministrado para Cruzr S2 es:

| ID | Superficie `z` desde suelo | Centro de B0 | Parte superior de B0 | Estado |
|---|---:|---:|---:|---|
| `S_VENDOR_1M` | `1,000 ± 0,010 m` | `1,1085 m` | `1,217 m` | confirmado por SDK 7.3 |
| `S_TASK_LOW` | `H_TASK_0_1=UNRESOLVED` | derivado | derivado | pendiente de mapear dataset/task |
| `S_TASK_MIDDLE` | `H_TASK_2_3=UNRESOLVED` | derivado | derivado | pendiente de mapear dataset/task |

Los XML 55/70/85/100/115 existen sólo en el árbol alternativo no-S2 y no fijan
estas dos alturas. Primero se reproduce `S_VENDOR_1M`; los tasks low/middle no
pasan a prueba física hasta resolver su altura con frames, estado/FK y
confirmación del proveedor.

La superficie será horizontal, rígida e inmóvil. El SDK no especifica ancho ni
fondo: `0,80 × 0,75 m` es el mínimo provisional adoptado por el proyecto, no un
máximo. Puede utilizarse una plataforma mayor si se registran sus dimensiones
exteriores completas y E4.1 demuestra que no invade el volumen barrido. El
fixture inicial es una superficie abierta, sin compartimientos, laterales,
respaldo ni divisores. Esos elementos sólo se introducirán como otro escenario
después de modelar sus colisiones y validar o recopilar datos que los incluyan.
No se apilarán mesas ni se improvisarán calzos. La zona debajo, encima y
alrededor de brazos/caja estará despejada; para gates físicos se mantendrá una
envolvente mínima de 1,5 m y una persona junto al paro.

Se define `PLATFORM_FRAME` con origen en el centro del borde frontal de la
superficie, `x` hacia la derecha del robot, `y` alejándose del robot y `z`
hacia arriba. La pose nominal de B0 apoyada será:

```yaml
box_pose_in_shelf_frame:
  x: 0.000       # centrada lateralmente
  y: 0.2485      # cara frontal a 0.050 m del borde + W/2
  z_vendor_1m: 1.1085
  z_task_low: UNRESOLVED
  z_task_middle: UNRESOLVED
  roll_deg: 0
  pitch_deg: 0
  yaw_deg: 0     # eje largo paralelo a los hombros / eje x
tolerances:
  x_y_m: 0.010
  surface_height_m: 0.010
  yaw_deg: 1
```

La base se centra con `x=0` y `yaw=0°` respecto de `PLATFORM_FRAME`. **No se fija
todavía una distancia longitudinal base–borde**: `D_BUMPER_PLATFORM` y la pose
`platform_in_base` permanecen `UNRESOLVED` hasta resolver
`clamp_s2_joints_trajectory`, cinemática, alcance y encuadre del dataset. Esa
pose se marcará en el suelo y no se alterará dentro de una celda. Inventar una
distancia podría colocar caja o plataforma dentro de una trayectoria
desconocida.

#### Estados iniciales físicos permitidos

| Estado | Caja | Abrazaderas | Robot | Uso |
|---|---|---|---|---|
| `NO_BOX_READY` | retirada de toda la envolvente | vacías | ready S2 validado, velocidad cero | canary sin caja |
| `SUPPORTED_VENDOR_1M` | B0 apoyada en `S_VENDOR_1M` | vacías | ready S2/pose fixture validados | reproducción inicial SDK |
| `SUPPORTED_LOW` | B0 apoyada en `S_TASK_LOW` ya resuelta | vacías | `VLA_READY_LOW`, velocidad cero | task 0 |
| `HELD_LOW` | B0 suspendida y estable | sujetando B0 | postura de place baja validada | task 1 |
| `SUPPORTED_MIDDLE` | B0 apoyada en `S_TASK_MIDDLE` ya resuelta | vacías | `VLA_READY_MIDDLE`, velocidad cero | task 2 |
| `HELD_MIDDLE` | B0 suspendida y estable | sujetando B0 | postura de place media validada | task 3 |

`HELD_LOW/MIDDLE` no se obtienen iniciando el task de place desde home. Deben
provenir de un PICK anterior declarado correcto o de una puesta en escena
determinista aprobada, y han de demostrar caja suspendida, fuerza estable y
ausencia de apoyo. Si el estado es desconocido, el task de place no empieza.

En todas las poses `VLA_READY`, la cámara principal debe contener la caja
completa y margen visible a izquierda, derecha y por encima. Los metadatos
muestran cabeza casi fija alrededor de `head_pitch≈-0,431 rad` y
`head_yaw≈0`, pero esos valores son una referencia observada del dataset, no
un comando ni una postura validada. Los 14 ángulos de brazos y las posiciones
del elevador deben obtenerse de la tarea oficial; no se inferirán del primer
chunk.

### 0.18 Interfaces PC, mensajes y herramientas necesarias

#### Scripts que existen hoy

| Orden en el PC | Efecto | Movimiento |
|---|---|---|
| `./scripts/vla/new_vla_evidence_run.sh --experiment ID` | crea un directorio exclusivo y muestra su ruta; rechaza `/` y runs existentes | no |
| `./scripts/vla/audit_vla_experiment_e1_1.sh` | ejecuta E1.1 con logs/hashes autocontenidos | no |
| `./scripts/vla/audit_vla_experiment_e1_2.sh` | ejecuta E1.2 local y rechaza sobrescritura | no |
| `./scripts/vla/install_ubtech_vla.sh --check` | valida paquete local y prerequisitos | no |
| `./scripts/vla/install_ubtech_vla.sh --verify` | comprueba instalación/contenedores | no |
| `./scripts/vla/run_ubtech_vla_shadow.sh --deploy` | sincroniza runtime seguro; cambia archivos remotos | no |
| `./scripts/vla/run_ubtech_vla_shadow.sh --check` | preflight de Motion/Vision, hashes, estado y cero publicadores | no |
| `./scripts/vla/run_ubtech_vla_shadow.sh --start-shadow --shadow-duration 180` | arranca validador que sólo registra/rechaza chunks | no |
| `./scripts/vla/run_ubtech_vla_shadow.sh --start-inference` | arranca contenedor de inferencia | no |
| `./scripts/vla/run_ubtech_vla_shadow.sh --trigger --task-id N --inference-duration 8` | solicita inferencia para task `N`; exige shadow activo | no |
| `./scripts/vla/run_ubtech_vla_shadow.sh --status` | muestra contenedores, logs y publicadores | no |
| `./scripts/vla/run_ubtech_vla_shadow.sh --stop` | detiene VLA y verifica cero publicadores físicos | no |
| `./scripts/vla/run_ubtech_vla_shadow.sh --export-evidence DIR` | recupera logs incluso desde contenedores detenidos sin arrancarlos | no |
| `./scripts/vla/run_vla_shadow_smoke.sh --task-id 0\|2` | ejecuta una secuencia shadow autocontenida, detiene y conserva evidencia | no |
| `./scripts/vla/run_vla_shadow_repetitions.sh --task-id 0\|2 --repetitions 5` | ejecuta E2.3 en sub-runs independientes con STOP entre ellos | no |
| `./scripts/cruzr_blue_workbin_cycle.sh --measure-box-fast` | mide/detecta B0 para registrar geometría | no debe mover; confirmar `--help` antes |
| `./scripts/cruzr_recover_to_home.sh --check` | diagnóstico de estado para recuperación | no |

No se combina este flujo con PICO, UI web, joystick ni otro cliente de control.
`--deploy` se usa sólo al cambiar runtime; no se repite como parte de cada
inferencia.

La secuencia shadow canónica para un único smoke es:

```bash
./scripts/vla/run_vla_shadow_smoke.sh --task-id 0
```

El wrapper encadena internamente `--check`, `--start-shadow`,
`--start-inference`, `--trigger`, `--status`, `--stop` y
`--export-evidence`; no debe ejecutarse en paralelo con la secuencia manual.

El script envía internamente el goal ROS 2 siguiente; se documenta para auditar
el contrato, **no para abrir un segundo cliente en paralelo**:

```yaml
action: /gr00t/trigger_inference
type: mc_task_msgs/action/InferenceTask
goal:
  task_id: 0                 # 0, 1, 2 o 3 según la tarjeta
  max_inference_duration: 8.0
  end_threshold: 0.1
```

El resultado esperado aparece en `/vla_inference_result` como
`vla_msgs/msg/Gr00tMotionChunk`: `chunk_id`, latencia, estado y 10 puntos con
20 posiciones absolutas. `/mc/sdk/robot_command` debe tener **cero
publicadores**. `--status`, `shadow.jsonl` y el resultado de cada `--trigger`
son la vía primaria para observarlos; no se mantiene un segundo WebSocket/ROS
client después de STOP.

#### Herramientas que deben existir antes de completar la campaña

Los nombres siguientes son especificaciones de trabajo; **aún no existen** y
no deben copiarse al terminal como si estuvieran implementados:

| Herramienta requerida | Interfaz mínima | Gate que desbloquea |
|---|---|---|
| `scripts/vla/build_vla_manifest.sh` | `--output DIR` | VLA-0 |
| `scripts/vla/evaluate_checkpoint_offline.py` | `--checkpoint`, `--dataset`, `--split`, `--task-id`, `--seed`, `--output` | VLA-1/2/3 |
| `scripts/vla/run_vla_shadow_matrix.sh` | `--scenario`, `--task-id`, `--axis-profile`, `--repetitions`, `--output` | VLA-6 |
| `scripts/vla/cruzr_vla_ready_pose.sh` | primero `--check --task TASK`; `--run` sólo con autorización futura | VLA-4 |
| `scripts/vla/derive_vla_fixture_pose.py` | `--ready-task`, `--urdf`, `--box-lwh`, `--platform-height`, `--reference-frames`, `--output` | VLA-4/geometría |
| `scripts/vla/test_vla_executor_sink.py` | `--axis-profile`, `--fixture`, `--fault-suite`, `--output` | VLA-5 |
| `scripts/vla/run_cruzr_vla_canary.sh` | `--check`, `--one-point`, `--one-chunk`, `--window`, `--stop`; siempre `--task-id`, `--axis-profile` y `--scenario` | VLA-7/8 |
| `scripts/vla/analyze_vla_campaign.py` | `--input`, `--select-minimal-profile`, `--output` | VLA-9 |
| `scripts/vla/train_cruzr_vla_candidate.sh` | `--base`, `--dataset-manifest`, `--data-config`, `--output` | VLA-10 |

El canary no publicará un `RobotCommand` escrito a mano desde la shell. Sólo un
ejecutor revisado podrá convertir chunks a la primitiva oficial, tras demostrar
tipo, QoS, unidades, límites, cancelación y ausencia de conflicto. Mientras
la trayectoria/instalación de `clamp_s2_joints_trajectory` siga sin demostrarse,
VLA-7 y VLA-8 permanecen
`BLOCKED` incluso si shadow da `ACCEPT`.

### 0.19 Registro mínimo por ejecución

Antes de cada tarjeta se crea un directorio fuera de Git y se completa un
manifiesto. En este PC se propone:

```bash
VLA_RUN_DIR="$(./scripts/vla/new_vla_evidence_run.sh \
  --experiment gate-task-profile-rep)"
printf 'VLA_RUN_DIR=%s\n' "$VLA_RUN_DIR"
```

No se reutilizan `VLA_RUN_DIR`, `VLA_RUN_ID` ni `VLA_EVIDENCE_ROOT` de otra
orden, subshell o sesión. Cada bloque que necesite una ruta la crea en ese mismo
bloque; los wrappers ejecutables la crean internamente. Un directorio ya
existente se rechaza aunque esté vacío.

El manifiesto debe contener como mínimo:

```yaml
run_id: null
gate: null
task_id: null
task_text: null
axis_profile: null
checkpoint_sha256: null
runtime_id: null
scenario_id: null
box_id: B0_SAFE
box_mass_kg: null
box_state: RETIRED_OR_SUPPORTED_OR_HELD
station_id: null
station_height_m: null
box_pose_shelf_frame: null
base_to_edge_m: null
robot_pose: HOME_OR_VLA_READY_LOW_OR_VLA_READY_MIDDLE
estops: null
charger: null
joint_velocity: null
command_publishers_before: null
command_publishers_after: null
result: PASS_OR_FAIL_OR_BLOCKED
failure_reason: null
recovery_state: null
```

Guardar: foto frontal/lateral del fixture, medida de altura/distancia, frame RGB
exacto, estado 20D, goal, chunk bruto, chunk enmascarado, `shadow.jsonl`, logs,
latencias, verdict y `--status` antes/después. Un `PASS` sin esos artefactos no
cuenta.

### 0.20 Tarjetas de prueba completas por gate

#### `VLA-T00` — Baseline y manifiesto de artefactos (Gate VLA-0)

- **Escenario:** robot apagado o detenido en `operation_type=1`, sin cliente de
  control; B0/plataforma retiradas. No se necesita pose relativa de fixture.
- **Preparación PC:** red Motion/Vision disponible sólo para `--check`; no
  arrancar inferencia.
- **Comandos existentes:** ejecutar `install_ubtech_vla.sh --check`,
  `install_ubtech_vla.sh --verify`, `run_ubtech_vla_shadow.sh --check` y
  `run_ubtech_vla_shadow.sh --status`. Construir hashes con la futura
  `build_vla_manifest.sh`; hasta entonces registrar manualmente `sha256sum` de
  checkpoint, metadata, DataConfig, YAML y runtime.

  ```bash
  ./scripts/vla/audit_vla_experiment_e1_1.sh
  VLA_RUN_DIR="$(./scripts/vla/new_vla_evidence_run.sh \
    --experiment VLA-T00-manifest)"
  find cruzrss2_vla_pack-002/weight/checkpoint-40000 \
    -type f -print0 | sort -z | xargs -0 sha256sum \
    > "$VLA_RUN_DIR/checkpoint.sha256"
  ```
- **Prueba:** comparar catálogo 0–3 de `tasks.jsonl` con goal/action, comprobar
  orden 20D y registrar las cinco contradicciones de 0.4.
- **PASS:** hashes completos, `restart=no`, contenedores detenidos al final y
  `/mc/sdk/robot_command` con cero publicadores.
- **FAIL/STOP:** artefacto cambia, task mapping ambiguo, contenedor con restart
  automático o aparece un publicador.
- **Evidencia:** `artifact-manifest.sha256`, `task-catalog.json`, salida de
  `--check/--status` y lista de deudas.
- **Recuperación:** `run_ubtech_vla_shadow.sh --stop`; no hay recuperación
  mecánica porque no hubo movimiento.

#### `VLA-T01` — Replay offline nominal (Gate VLA-1)

- **Escenario:** sin robot; se usan episodios del dataset, no cámara viva ni
  estaciones reales.
- **Casos:** tasks 0–3; cinco seeds iguales y cinco diferentes por task;
  splits separados por episodio/sesión.
- **PC:** futura `evaluate_checkpoint_offline.py` con checkpoint
  `cruzrss2_vla_pack-002/weight/checkpoint-40000`, dataset
  `utars_clamp_and_place_large_box_full_data_bio_lerobot_0319`, task y seed.
  `gr00t_finetune.py` **no** se usa para evaluar ni se reentrena C0.

  Invocación especificada, disponible sólo después de implementar el script:

  ```bash
  VLA_RUN_DIR="$(./scripts/vla/new_vla_evidence_run.sh \
    --experiment VLA-T01)"
  python3 scripts/vla/evaluate_checkpoint_offline.py \
    --checkpoint cruzrss2_vla_pack-002/weight/checkpoint-40000 \
    --dataset cruzrss2_vla_pack-002/data/utars_clamp_and_place_large_box_full_data_bio_lerobot_0319 \
    --split test --task-id 0 --seed 0 \
    --output "$VLA_RUN_DIR"
  ```
- **Mensaje:** misma instrucción textual exacta del catálogo más un estado 20D
  y una RGB del episodio; salida esperada 10×20 finita.
- **PASS:** métricas por eje/horizonte/task, error de primer punto/endpoint,
  continuidad, clipping y `flag_pred`, sin fuga entre splits.
- **FAIL:** cualquier NaN/Inf, orden distinto, resultado no reproducible sin
  explicación o promedio global que oculte una tarea.
- **Evidencia:** split manifest, seeds, predicciones, métricas y mosaico de
  frames representativos.
- **Recuperación:** ninguna; proceso offline se cancela y los pesos C0 quedan
  inmutables.

#### `VLA-T02` — OOD visual/estado/runtime (Gate VLA-2)

- **Escenario offline nominal:** frame retenido cuya caja/plataforma se parezcan
  al dataset. Una escena física task-valid sólo existe después de E4.4; antes,
  live-shadow con fixture retirado se etiqueta `OOD_RUNTIME_SMOKE`.
- **Variantes OFAT:** x de caja `0, ±0,05, ±0,10 m`; y de cara frontal
  `0,05, 0,10, 0,15 m`; yaw `0°, ±5°, ±15°`; después caja ausente, oclusión,
  otro color/tamaño y distractor. Esas cifras son estímulos OOD, no posiciones
  físicas autorizadas para PICK.
- **Estado inválido:** NaN/Inf, eje ausente, permutación, timestamp >1 s y valor
  fuera de rango. **Se inyecta sólo al sink/offline**, nunca al robot.
- **PC:** `evaluate_checkpoint_offline.py --fault-suite ...` cuando exista. Para
  una escena viva válida usar la secuencia shadow de 0.18 y el task correcto.

  ```bash
  # Especificación futura; hoy este archivo no existe.
  VLA_RUN_DIR="$(./scripts/vla/new_vla_evidence_run.sh \
    --experiment VLA-T02)"
  python3 scripts/vla/evaluate_checkpoint_offline.py \
    --checkpoint cruzrss2_vla_pack-002/weight/checkpoint-40000 \
    --dataset cruzrss2_vla_pack-002/data/utars_clamp_and_place_large_box_full_data_bio_lerobot_0319 \
    --split test --task-id 0 --seed 0 --fault-suite all \
    --output "$VLA_RUN_DIR"
  ```
- **PASS:** 100 % de mensajes estructuralmente inválidos rechazados; cada
  variante válida queda etiquetada `NOMINAL`, `OOD_ACCEPTED` o `OOD_REJECTED`.
- **FAIL:** un inválido llega al ejecutor, cambio simultáneo de dos factores o
  el modelo se declara capaz por generar un chunk.
- **Evidencia:** tabla factor/valor/task, RGB de entrada, estado, chunk, razón de
  rechazo y cero publicadores antes/después.
- **Recuperación:** `--stop`; devolver físicamente B0 a pose nominal sólo a
  mano con robot parado y fuera de control, nunca mientras shadow/inferencia
  estén activos.

#### `VLA-T03` — Timeline, timeout y end flag (Gate VLA-3)

- **Escenario:** robot inmóvil con plataforma/B0 fuera de la envolvente para el
  timeline de runtime; o replay de dataset para timeline nominal. No atribuir
  semántica low/middle a la escena viva hasta E4.4.
- **PC:** iniciar shadow 180 s, inferencia y disparar task 0 por 8 s. Repetir
  task 2. La futura herramienta offline prueba cancelación en `t=0`, durante
  inferencia, entre chunks y tras timeout.

  ```bash
  ./scripts/vla/run_vla_shadow_smoke.sh --task-id 0
  ./scripts/vla/run_vla_shadow_smoke.sh --task-id 2
  ```
- **Mensaje:** `InferenceTask{task_id, max_inference_duration:8.0,
  end_threshold:0.1}`; observar `chunk_id`, diez `time_from_start`, feedback,
  `flag_pred`, cancelación y fin.
- **PASS:** se explica 120 FPS frente a `Δt=0,08 s`, se fija qué ocurre en el
  hueco `0,72–5 s`, no se reutiliza chunk viejo y STOP/cancel tienen latencia
  medida.
- **FAIL:** cola ejecutable después de STOP, chunk duplicado/regresivo aceptado,
  end con un criterio diferente al documentado o hueco de mando indefinido.
- **Evidencia:** timeline monotónica sensor→goal→chunk→end y logs de cuatro
  puntos de cancelación.
- **Recuperación:** `--stop`; este test no debe haber movido el robot.

#### `VLA-T04` — Completar ready S2 y geometría del fixture (Gate VLA-4)

- **Escenario A, rechazo de control:** robot inmóvil en `home`, sin caja.
  Ejecutar sólo shadow y conservar como evidencia el salto inicial ya observado
  (~1,35 rad máximo); no repetir físicamente ese chunk.
- **Escenario B, ready S2 vacío:** plataforma/B0 retiradas; validar el XML
  `s2_vla_pick_large_teleop_ready` sólo tras resolver
  `clamp_s2_joints_trajectory`.
- **Escenario C, fixture calculado:** plataforma a `z=1,000 m` y pose horizontal
  producida por `derive_vla_fixture_pose.py`; primero target visual, luego
  plataforma vacía y finalmente B0. Low/middle adicionales sólo si E4.3 les
  asigna alturas verificadas.
- **PC hoy:** sólo `--check`, secuencia shadow y `--trigger` para los tasks
  correspondientes. La entrada física a ready está bloqueada hasta implementar
  `cruzr_vla_ready_pose.sh --check --task ...`, completar la trayectoria S2
  y autorizar su `--run` en otra sesión.

  ```bash
  # Existe y es shadow:
  ./scripts/vla/run_vla_shadow_smoke.sh --task-id 0

  # Especificación futura; --run no queda autorizado por este documento:
  test -n "$VLA_READY_TASK"  # salida canónica de E4.0
  ./scripts/vla/cruzr_vla_ready_pose.sh --check --task "$VLA_READY_TASK"
  ```
- **PASS:** ready S2 completo, `platform_in_base` y `D_BUMPER_PLATFORM`
  versionados; después cinco primeros chunks aceptados por cada task cuya
  altura low/middle esté resuelta.
- **FAIL:** se deduce ready del primer chunk, se suaviza el salto, caja/cámara
  quedan fuera del encuadre o cualquier primer delta excede límites.
- **Evidencia:** trayectoria oficial, hash, pose 20D, distancias, fotografías,
  frames y cinco verdicts por task.
- **Recuperación:** sólo la trayectoria determinista inversa aprobada; no usar
  `home` si una caja/estante está dentro de la trayectoria.

#### `VLA-T05` — Ejecutor sink y fallos (Gate VLA-5)

- **Escenario:** sin robot y sin caja; chunks guardados de T01/T03 alimentan un
  sink. Un mock representa la pose inicial de low/middle.
- **Perfiles:** los ocho `P14_A…P20_AHLW`; para cada uno, un chunk válido y
  fallos de dimensión, NaN, rango, velocidad, primer salto, timestamp, ID,
  duplicado, timeout, estado viejo, cancel y doble cliente.
- **PC:** futura `test_vla_executor_sink.py --axis-profile PROFILE
  --fixture low|middle --fault-suite all --output DIR`.

  ```bash
  # Especificación futura; no publica al robot.
  VLA_RUN_DIR="$(./scripts/vla/new_vla_evidence_run.sh \
    --experiment VLA-T05)"
  python3 scripts/vla/test_vla_executor_sink.py \
    --axis-profile P14_A --fixture low --fault-suite all \
    --output "$VLA_RUN_DIR"
  ```
- **Mensajes:** entrada `Gr00tMotionChunk`; salida sólo un comando serializado al
  sink. Los ejes bloqueados deben conservar exactamente el hold inicial.
- **PASS:** todos los válidos aceptados, todos los inválidos rechazados,
  deadman/STOP idempotentes y ninguna importación/publicación al topic físico.
- **FAIL:** cero usado como hold, clipping oculta salto, ejecución continúa tras
  timeout/cancel o aparece publisher en `/mc/sdk/robot_command`.
- **Evidencia:** tests, cobertura, input/output por caso y conteo de publishers.
- **Recuperación:** terminar procesos y demostrar cero publishers; no hay estado
  físico que recuperar.

#### `VLA-T06` — Matriz shadow 4×8×5 (Gate VLA-6)

- **Escenarios task:** 0=`SUPPORTED_LOW`; 1=`HELD_LOW`; 2=`SUPPORTED_MIDDLE`;
  3=`HELD_MIDDLE`. Para shadow inicial se permite un replay de imagen/estado;
  una puesta en escena viva `HELD` sólo se hará después de contar con un método
  seguro para establecerla.
- **Posición:** B0 nominal `x=0`, `y=0,2485`, `yaw=0`; alturas y ready del
  fixture. Sin variaciones OOD dentro de esta matriz.
- **PC:** hoy sólo puede obtenerse P20 con `run_ubtech_vla_shadow.sh`. Antes de
  declarar completa la matriz se implementará `run_vla_shadow_matrix.sh` para
  aplicar las máscaras/holds P14–P20 y guardar cinco repeticiones por celda.

  ```bash
  # Especificación de una celda futura; repetir task/perfil según la matriz.
  VLA_RUN_DIR="$(./scripts/vla/new_vla_evidence_run.sh \
    --experiment VLA-T06-task0-P14-A)"
  ./scripts/vla/run_vla_shadow_matrix.sh \
    --scenario SUPPORTED_LOW --task-id 0 --axis-profile P14_A \
    --repetitions 5 --output "$VLA_RUN_DIR"
  ```
- **Orden:** task 0 perfiles 14→20, task 1 sólo tras establecer HELD; después 2
  y 3. Un perfil no avanza si la celda anterior falla por seguridad.
- **PASS de celda:** 5/5 outputs estructuralmente válidos, primer salto y
  continuidad aceptados, sin movimiento significativo requerido en un grupo
  bloqueado y cero publishers.
- **FAIL:** un perfil elimina un grupo necesario, cambia el fixture entre
  repeticiones o no conserva el output P20 bruto para comparación.
- **Evidencia:** 160 bundles completos y tabla 32×métricas.
- **Recuperación:** `--stop` después de cada bloque task; verificar
  `operation_type=1` y cero publishers.

#### `VLA-T07` — Canary físico sin caja (Gate VLA-7, bloqueado hoy)

- **Autorización:** nueva confirmación física el día de la prueba; el plan no
  la concede.
- **Escenario:** `NO_BOX_READY`, plataforma y B0 retiradas >1,5 m, envolvente
  completamente vacía, base en marca calibrada, ruedas bloqueadas,
  cargador desconectado, ambos paros liberados sólo tras preflight, persona en
  el paro y un único cliente.
- **PC preflight:** `run_ubtech_vla_shadow.sh --check`,
  `cruzr_vla_ready_pose.sh --check --task TASK` y futuro
  `run_cruzr_vla_canary.sh --check --task-id N --axis-profile PROFILE`.

  Secuencia especificada para cuando ambas herramientas y la primitiva estén
  revisadas; hoy los comandos marcados como futuros deben fallar por ausencia:

  ```bash
  ./scripts/vla/run_ubtech_vla_shadow.sh --check
  test -n "$VLA_READY_TASK"  # salida canónica de E4.0
  ./scripts/vla/cruzr_vla_ready_pose.sh --check --task "$VLA_READY_TASK"
  ./scripts/vla/run_cruzr_vla_canary.sh --check \
    --task-id 0 --axis-profile P14_A --scenario NO_BOX_READY
  ./scripts/vla/run_cruzr_vla_canary.sh --one-point \
    --task-id 0 --axis-profile P14_A --scenario NO_BOX_READY
  ./scripts/vla/run_cruzr_vla_canary.sh --stop
  ```
- **Escalado:** una consigna/punto de delta pequeño → STOP/revisión; un chunk →
  STOP; dos chunks → STOP; ventana corta por timeout; ventana corta por cancel.
  Tres repeticiones limpias antes de añadir H, W o L.
- **Mensaje:** nunca shell→`RobotCommand`; el canary toma un chunk ya aceptado,
  aplica máscara/hold y usa la primitiva oficial todavía no demostrada.
- **PASS:** movimiento sólo en grupos autorizados, velocidad/fuerza/latencia
  dentro de contrato, STOP y cero velocidad demostrados, postura final
  clasificable.
- **FAIL inmediato:** cualquier contacto, oscilación, primer salto, grupo
  bloqueado que se mueve, trip FT, imagen/estado viejo, STOP tardío o executor
  ambiguo.
- **Evidencia:** vídeo externo, logs sincronizados, estado/órdenes, fuerza,
  latencia STOP y pose final.
- **Recuperación:** STOP del executor; mantener postura. Recovery determinista
  específico sólo tras clasificarla; no enviar home automáticamente.

#### `VLA-T08-0` — PICK bajo físico, caja vacía (task 0)

- **Inicio:** `SUPPORTED_LOW`; B0 en `S_TASK_LOW` cuya altura y
  `platform_in_base` fueron resueltas en E4, pose nominal, masa medida,
  abrazaderas vacías, `VLA_READY_LOW`, velocidad cero.
- **PC:** preflights de T07 y futuro canary con `--task-id 0`. Primero perfil
  ganador shadow de menor dimensión; no asumir P14 si la matriz requiere L/W/H.

  ```bash
  # Especificación futura, bloqueada hoy:
  ./scripts/vla/run_cruzr_vla_canary.sh --check \
    --task-id 0 --axis-profile PROFILE_APROBADO --scenario SUPPORTED_LOW
  ./scripts/vla/run_cruzr_vla_canary.sh --one-chunk \
    --task-id 0 --axis-profile PROFILE_APROBADO --scenario SUPPORTED_LOW
  ./scripts/vla/run_cruzr_vla_canary.sh --stop
  ```
- **Ejercicio:** un canary, después tres y finalmente diez repeticiones. Cada
  repetición termina al demostrar `HELD_LOW` o al primer fallo.
- **PASS:** B0 suspendida estable, sin apoyo ni contacto externo, fuerza dentro
  de protección; fin de tarea y estado físico concuerdan.
- **Recuperación:** si `SUPPORTED`, retirar brazos con trayectoria específica;
  si `HELD`, depositar mediante recovery dedicado; si `UNKNOWN`, STOP y no home.

#### `VLA-T08-1` — PLACE bajo físico, caja vacía (task 1)

- **Inicio:** `HELD_LOW` demostrado, B0 centrada respecto de la estación,
  `S_TASK_LOW` vacía y `VLA_READY_PLACE_LOW` validada.
- **PC:** futuro canary con `--task-id 1`; no iniciar desde home ni improvisar
  el agarre para crear el estado inicial.

  ```bash
  # Especificación futura, bloqueada hoy:
  ./scripts/vla/run_cruzr_vla_canary.sh --check \
    --task-id 1 --axis-profile PROFILE_APROBADO --scenario HELD_LOW
  ./scripts/vla/run_cruzr_vla_canary.sh --one-chunk \
    --task-id 1 --axis-profile PROFILE_APROBADO --scenario HELD_LOW
  ./scripts/vla/run_cruzr_vla_canary.sh --stop
  ```
- **Ejercicio:** una sola colocación por ensayo; STOP tras apoyo y retirada.
- **PASS:** `SUPPORTED_LOW`, B0 estable dentro de tolerancias, abrazaderas
  libres, brazos retirados y fuerza descargada.
- **Recuperación:** si sigue `HELD`, volver a ready-place; si queda `PARTIAL`,
  STOP y retirar obstáculo sólo con procedimiento específico.

#### `VLA-T08-2` — PICK medio físico, caja vacía (task 2)

- **Inicio:** `SUPPORTED_MIDDLE`; B0 nominal en `S_TASK_MIDDLE` cuya altura y
  pose fueron resueltas en E4, abrazaderas vacías, `VLA_READY_MIDDLE`, cámara
  con caja completa.
- **PC:** igual a T08-0 con `--task-id 2`.

  ```bash
  # Especificación futura, bloqueada hoy:
  ./scripts/vla/run_cruzr_vla_canary.sh --check \
    --task-id 2 --axis-profile PROFILE_APROBADO --scenario SUPPORTED_MIDDLE
  ./scripts/vla/run_cruzr_vla_canary.sh --one-chunk \
    --task-id 2 --axis-profile PROFILE_APROBADO --scenario SUPPORTED_MIDDLE
  ./scripts/vla/run_cruzr_vla_canary.sh --stop
  ```
- **PASS:** `HELD_MIDDLE` estable y mismos límites de seguridad; se reporta por
  separado de low.
- **Recuperación:** depósito dedicado en `S_TASK_MIDDLE`; nunca home con B0
  sujeta.

#### `VLA-T08-3` — PLACE medio físico, caja vacía (task 3)

- **Inicio:** `HELD_MIDDLE` demostrado y `VLA_READY_PLACE_MIDDLE`; superficie
  media vacía.
- **PC:** igual a T08-1 con `--task-id 3`.

  ```bash
  # Especificación futura, bloqueada hoy:
  ./scripts/vla/run_cruzr_vla_canary.sh --check \
    --task-id 3 --axis-profile PROFILE_APROBADO --scenario HELD_MIDDLE
  ./scripts/vla/run_cruzr_vla_canary.sh --one-chunk \
    --task-id 3 --axis-profile PROFILE_APROBADO --scenario HELD_MIDDLE
  ./scripts/vla/run_cruzr_vla_canary.sh --stop
  ```
- **PASS:** `SUPPORTED_MIDDLE`, B0 estable, abrazaderas libres y retirada limpia.
- **Recuperación:** específica según `HELD/SUPPORTED/PARTIAL/UNKNOWN`.

Para cada T08 la progresión es `1 + 3 + 10` sólo si no ocurre ningún fallo
peligroso. Contenido, chasis, navegación, otra caja y volcado quedan fuera.

#### `VLA-T09` — Selección del perfil mínimo (Gate VLA-9)

- **Escenario:** no añade movimiento; analiza T01–T08 preservando cada fixture.
- **PC:** futura `analyze_vla_campaign.py --input EVIDENCE_ROOT
  --select-minimal-profile --output REPORT`.

  ```bash
  # Especificación futura; sólo analiza evidencia.
  VLA_RUN_DIR="$(./scripts/vla/new_vla_evidence_run.sh \
    --experiment VLA-T09)"
  python3 scripts/vla/analyze_vla_campaign.py \
    --input /home/lacuna/proyectos/Robots/Humanoide-vla-evidence \
    --select-minimal-profile \
    --output "$VLA_RUN_DIR/profile-selection.json"
  ```
- **Comparación:** por task, P14 frente a todos los superconjuntos; seguridad,
  recovery, éxito, continuidad/fuerza y sólo después tiempo.
- **PASS:** una decisión independiente por task con intervalo de confianza y
  razón para cada grupo H/L/W habilitado o bloqueado.
- **FAIL:** elegir P20 por ser “completo”, mezclar low/middle o concluir con una
  sola repetición.
- **Salida:** tabla `task→profile`, pose hold de grupos bloqueados y dominio
  físico exacto aprobado.

#### `VLA-T10` — Checkpoint C1/C2 y regresión (Gate VLA-10)

- **Escenario de entrenamiento:** sin conexión de salida al robot. C0 permanece
  inmutable. Las demostraciones nuevas conservan el `scenario_id`, geometría,
  alturas, pose, task text y fronteras de episodio.
- **C1:** B0 y nuevas cajas, alturas/poses/yaw y futuros `TIP/POUR`, manteniendo
  1 RGB, abrazaderas y acción 20D. Mezclar tareas 0–3 para evitar olvido.
- **C2:** sólo si cambian entradas/salidas —dedos, pinza activa, fuerza como
  entrada, profundidad, otra cámara o chasis—; partir de GR00T N1.5 base con un
  DataConfig nuevo.
- **PC:** `cruzrss2_vla_pack-002/gr00t_finetune.py` es el entrenador proveedor,
  pero la invocación reproducible se encapsulará en
  `train_cruzr_vla_candidate.sh`; no se lanza directamente hasta congelar
  manifest/splits/config/receta y disponer de rollback.

  ```bash
  # Especificación futura; sólo entrenamiento, sin salida al robot.
  ./scripts/vla/train_cruzr_vla_candidate.sh \
    --base C1_CONTINUE_40000 --dataset-manifest DATASET_MANIFEST \
    --data-config utars1 --output CHECKPOINT_OUTPUT
  ```
- **Validación:** cada checkpoint candidato repite T01–T09. Primero offline,
  después shadow; ningún peso entrenado entra directamente a canary.
- **PASS:** mejora demostrada en tarea nueva sin regresión inaceptable de 0–3,
  hashes/receta/datos reproducibles y dominio explícito.
- **FAIL:** training/test comparten sesión o caja, C0 se sobrescribe, cambia el
  contrato sin DataConfig nuevo o se prueba físicamente antes de shadow.
- **Evidencia:** dataset manifest, splits, licencia/procedencia, configuración,
  logs, checkpoints, métricas y model card.

### 0.21 Orden operativo para comenzar

El trabajo ejecutable ahora, sin movimiento, es:

```text
VLA-T00 -> implementar herramientas offline -> VLA-T01 -> VLA-T02 -> VLA-T03
        -> obtener/validar VLA_READY -> VLA-T04 -> VLA-T05 -> VLA-T06
```

VLA-T07 y VLA-T08 están bloqueados por tres condiciones independientes:

1. no está completa/demostrada la trayectoria S2 ready ni el mapeo de alturas
   low/middle;
2. no existe todavía el ejecutor canary revisado con STOP/deadman;
3. no está demostrada la primitiva física `clamp_s2_joints_trajectory`.

Por tanto, la primera sesión práctica debe medir `B0_SAFE` y la
plataforma `S_VENDOR_1M` fuera de la envolvente, fotografiar el fixture y
ejecutar **T00**. La pose horizontal se deriva posteriormente en E4.1 y se
valida físicamente en E4.4. El
primer goal permitido después será un goal shadow; no un mensaje de movimiento.

## 1. Resultado buscado

Construir y validar un flujo recuperable que, con **una sola caja manipulada por
ensayo**, permita:

1. localizar una caja cargada situada a baja altura;
2. alinearse y sujetarla sin contacto no previsto;
3. levantarla y retirarse de la estación de origen;
4. navegar hasta una estación receptora;
5. elevarla a una altura configurada y volcar su contenido dentro de un
   recipiente mayor;
6. comprobar que la caja manipulada quedó vacía y volverla a una orientación
   estable;
7. navegar hasta una tercera estación, de otra altura;
8. depositar allí la caja vacía;
9. retirarse y terminar en una postura segura conocida.

El plan debe generalizar progresivamente a varios tamaños, posiciones y
orientaciones de caja. La generalización no se presume: cada perfil se calibra
y valida por separado antes de combinar variaciones.

La misión nominal será:

```text
SAFE_READY
  -> NAV_PICK_PRE -> ALIGN_PICK -> PICK_LOW -> VERIFY_HELD
  -> RETREAT_PICK -> NAV_POUR_PRE -> ALIGN_POUR -> PREPARE_POUR_HEIGHT
  -> TIP -> VERIFY_EMPTY -> RETURN_UPRIGHT -> RETREAT_POUR
  -> NAV_EMPTY_DROP_PRE -> ALIGN_EMPTY_DROP -> PLACE_EMPTY
  -> RETREAT_DROP -> SAFE_HOME
```

## 2. Alcance y límites

### 2.1 Incluido

- cajas rígidas o semirrígidas compatibles con la apertura, geometría, carga y
  fuerza admisibles de las abrazaderas;
- una caja manipulada cada vez;
- origen bajo, receptor a altura configurable y mesa final a otra altura;
- navegación, percepción, manipulación, teleoperación para demostraciones,
  reproducción parametrizada y VLA como alternativas que deben compararse;
- episodios separados de recogida, volcado y depósito, con navegación y
  alineación registradas como contexto de misión;
- reanudación desde el último estado seguro, incluida la situación de caja
  todavía sujeta.

### 2.2 No incluido inicialmente

- líquidos, vidrio, arena, carga densa, peligrosa o cortante;
- más de una caja manipulada a la vez;
- abrir cajas cerradas o extraer contenido atascado;
- movimiento aprendido del chasis;
- inferencia VLA conectada directamente a actuadores;
- manos con dedos como parte del espacio de acción actual de 20 dimensiones;
- modificar o puentear fuerza, anticolisión, límites, bumpers, watchdogs o
  paros.

El primer contenido vertible serán piezas grandes, secas, blandas, ligeras y
contables. Esto permite detectar cada pieza fuera del receptor y evita repetir
el contacto de aproximadamente 306 N observado el 2026-08-27.

## 3. Punto de partida demostrado

| Elemento | Estado actual | Consecuencia para este plan |
|---|---|---|
| Robot v0.2.0 + controller 4.7.0 + UI 4.1.0 | Baseline oficial observado | Mantener como baseline de teleoperación hasta registrar otra combinación |
| Efector | Abrazaderas; `clamp` requerido | Todo perfil debe declarar agarre, apertura y caras de contacto |
| Motion después del último reinicio | Self-check aprobado, actuadores habilitados y `AutoTaskMode` observado | Salud lógica recuperada, pero debe repetirse el preflight el día de cada prueba |
| Postura física | No clasificada automáticamente por el log nuevo | Ningún ensayo comienza hasta demostrar `home` o una `SAFE_READY` aprobada |
| Transferencia BYD entre mesas | Recogida, navegación, alineación y depósito existen parcialmente y se probaron por etapas | Reutilizar como baseline determinista; no reescribirla desde cero |
| Volcado | No existe una primitiva validada | Desarrollarla primero sin contenido y sin navegación |
| PICO | Teleoperación de brazos demostrada; se pausó tras un trip de fuerza | Sólo para sesiones supervisadas y captura piloto después de cerrar los gates |
| VLA `checkpoint-40000` | Shadow produce chunks, pero fueron discontinuos desde `home` | No puede mover; sirve para evaluación offline y como punto de partida condicionado |

Antes de cualquier movimiento prevalece el estado fresco sobre esta tabla.

## 4. Reglas operativas no negociables

1. Se manipula **una sola caja por ensayo**. El recipiente receptor grande es
   una estación fija, no una segunda caja que el robot deba coger.
2. Cada fase termina en un checkpoint reanudable. Si la caja sigue sujeta, no
   se reinicia la misión completa ni se ordena `home`.
3. El estado de la caja se registra siempre como uno de:
   `LOADED_SUPPORTED`, `LOADED_HELD`, `EMPTY_HELD`, `EMPTY_SUPPORTED` o
   `REMOVED`. `unknown` bloquea movimiento automático.
4. Antes de mover: efector, caja, postura, carga, batería, cargador, ambos
   paros, modo, ruedas, clientes de control, zona y persona junto al paro se
   comprueban de nuevo.
5. Sólo un cliente manda: tarea determinista, PICO, UI, replay o VLA. Nunca dos
   simultáneamente.
6. Toda rama con movimiento debe tener `--check`, confirmación específica,
   timeout, STOP y verificación final de velocidad cero.
7. No se ejecuta una trayectoria vertical o de volcado de una altura en otra
   estación sin recalibrarla.
8. Ethernet directo es adecuado para diagnóstico y captura estacionaria. Antes
   de mover el chasis se retira cualquier cable de arrastre y se usa ejecución
   local/Wi-Fi Cruzr; `DSA CORPORATE` conserva Internet y no transporta control
   del robot.
9. Al transportar una caja se pueden retirar temporalmente del costmap las
   entradas RGB-D que vean la propia carga, pero se conservan LiDAR, mapa,
   localización, odometría, bumpers y paros. La configuración se restaura al
   finalizar o fallar.
10. Un trip de fuerza, servo, EtherCAT, acción abortada, pérdida de pose o caja
    que resbala termina el ensayo. Se aplica la guía de recuperación; no se
    insiste aumentando fuerza.

## 5. Parámetros que deben sustituir constantes embebidas

### 5.1 Perfil de caja

Cada caja física recibirá un identificador único y un perfil versionado. Se
propone `config/box_profiles.yaml` con, como mínimo:

```yaml
boxes:
  box_b0_blue:
    dimensions_m: [0.603, 0.397, 0.217]
    empty_mass_kg: null
    loaded_mass_kg: null
    rigidity: semirigid
    contents_profile: foam_blocks_v1
    detector_profile: workbin
    grasp_faces: [long_sides]
    grasp_height_fraction: null
    clamp_opening_m: null
    nominal_pick_yaw_deg: 0
    maximum_tested_tip_deg: null
    maximum_observed_wrist_force_n: null
    status: perception_verified_manipulation_requires_fresh_validation
```

Campos obligatorios adicionales:

- dimensiones exteriores y masa vacía/cargada medidas;
- rigidez y deformación aceptable;
- posición estimada del centro de masa;
- caras permitidas y prohibidas de agarre;
- apertura y punto vertical de las abrazaderas;
- contenido, cantidad, masa y facilidad de deslizamiento;
- detector/tag/configuración utilizados;
- ángulo de volcado probado, fuerza máxima observada y resultado;
- fotos RGB/depth de referencia y versión de la calibración.

Perfiles que aparecen en el software y que sólo son **candidatos**, no cajas ya
validadas:

| Candidato | Dimensiones aproximadas | Tecnología local | Estado inicial |
|---|---:|---|---|
| B0 azul/BYD | 603 × 397 × 217 mm | `workbin` | Detector 6D probado; nueva misión pendiente |
| B1 | 410 × 308 × 140 mm | perfil `putbox` | Presente, no validado en esta unidad |
| B2 | 400 × 300 × 160 mm | perfil `putbox` | Presente, no validado |
| B3 | 600 × 400 × 250 mm | perfil `putbox` | Presente, no validado |
| B4 alta | 600 × 430 × 410 mm | perfil `putcarton` | Presente; alcance y estabilidad por demostrar |
| Bandeja F | 380 × 360 × 220 mm | `foxconn_tray` | Clase alternativa, no equivalente a caja |
| Bandeja J | 410 × 260 × 240 mm | `jiepu_tray` | Clase alternativa, no equivalente a caja |
| Perfil O | no documentadas | `om` | Modelo presente; clase y dimensiones por aclarar |
| Perfil T | no documentadas | `thor` | Modelo presente; clase y dimensiones por aclarar |

Se prueba B0 primero. Después se incorpora **un único perfil nuevo por vez**,
empezando por percepción en estático y terminando con la misión integrada.

### 5.2 Perfil de estación

Se propone `config/station_profiles.yaml`:

```yaml
stations:
  pick_low_01:
    role: pick
    surface_height_m: null
    waypoint: PICK_LOW_PRE
    apriltag: {id: 112, family: tag36h11, measured_size_m: 0.075}
    lateral_target_m: null
    depth_target_m: null
    approach_yaw_deg: 0
    lifter_prepose_m: null
    waist_prepose_deg: null
  pour_01:
    role: pour
    surface_height_m: null
    rim_height_m: null
    waypoint: POUR_PRE
    apriltag: {id: 113, family: tag36h11, measured_size_m: 0.0735}
    receiver_inner_dimensions_m: null
    safe_tip_axis: null
  empty_drop_01:
    role: empty_drop
    surface_height_m: null
    waypoint: EMPTY_DROP_PRE
    apriltag: {id: 114, family: tag36h11, measured_size_m: null}
```

Para cada estación se medirán altura desde el suelo, geometría útil, borde,
obstáculos, espacio de retirada, waypoint, pose final, tag y tolerancias. No se
copiará una altura de una mesa a otra.

### 5.3 Convención de pose

Para que cámaras y control no mezclen ejes, la matriz de pruebas usa nombres
físicos en el marco local de la estación:

- `lateral`: izquierda/derecha respecto al centro nominal;
- `depth`: más cerca/más lejos del borde de trabajo;
- `height`: altura de la superficie o del punto de agarre desde el suelo;
- `yaw`: giro de la caja sobre la vertical;
- `roll` y `pitch`: inclinación de la caja.

La transformación concreta a cámara, tag, mapa y base se guarda con su
`frame_id` y timestamp. Nunca se interpreta un `x/y/z` sin marco.

## 6. Matriz de variación OFAT

OFAT significa cambiar un factor por vez. La cuadrícula siguiente es una
propuesta conservadora, no una tolerancia ya certificada.

### 6.1 Orden de expansión

1. B0, posición central, `yaw=0°`, caja erguida, alturas nominales.
2. B0, variar sólo posición lateral.
3. B0, variar sólo profundidad.
4. B0, variar sólo `yaw`.
5. B0, variar sólo altura de origen.
6. B0, variar sólo altura de volcado.
7. B0, variar sólo altura de depósito vacío.
8. B0, combinaciones limitadas ya cubiertas por los rangos individuales.
9. Repetir desde el paso 1 con B1; después B2, B3 y sólo entonces B4.

### 6.2 Niveles piloto

| Factor | Piloto | Expansión posterior | Regla |
|---|---|---|---|
| `lateral` | `-0,08 / 0 / +0,08 m` | hasta el rango visible y alcanzable calibrado | Un nivel por bloque |
| `depth` | `-0,05 / 0 / +0,05 m` | límites medidos sin acercar el chasis a contacto | Un nivel por bloque |
| `yaw` de recogida | `-10 / 0 / +10°` | `-15 / +15°` sólo tras éxito | `roll=pitch=0°` inicialmente |
| altura de origen | `H_PICK_LOW_NOM` | `LOW_1`, `LOW_2` medidas | Recalibrar prepose/alcance |
| altura de volcado | `H_POUR_NOM` | `POUR_LOW/MID/HIGH` medidas | Recalibrar borde y trayectoria vertical |
| altura de depósito | `H_DROP_NOM` | `DROP_LOW/MID/HIGH` medidas | Nueva trayectoria por altura |
| orientación de receptor | `0°` | `-10 / +10°` | Mantener libre el lado de volcado |
| orientación final vacía | `0°` | `-15 / +15°` | Validar apoyo antes de abrir |
| carga | caja vacía | 1, 2… piezas de espuma contables | Masa medida y un nivel por vez |

`H_*` no se sustituye por un número hasta medir la estación real y verificar el
alcance sin carga. No se ensayan inicialmente cajas apoyadas con `roll` o
`pitch` distintos de cero.

### 6.3 Evitar la explosión combinatoria

No se ejecuta el producto cartesiano completo. Después de OFAT se seleccionan
casos de borde mediante cobertura por pares:

- lateral extremo + `yaw` extremo opuesto;
- origen más bajo + caja de mayor altura ya validada;
- volcado más alto + carga máxima ya validada;
- depósito más bajo + orientación final extrema;
- ruta más larga + caja más voluminosa ya validada.

Cada celda comienza con simulación geométrica/offline, continúa sin carga y
sólo pasa a contenido ligero si no hubo contacto ni anomalía.

## 7. Tecnologías disponibles y decisión por etapa

Estados usados:

- **VERIFICADO:** hubo evidencia en esta unidad;
- **PRESENTE:** existe en robot/repositorio, falta validar para este uso;
- **PROPUESTO:** integración que debe implementarse;
- **EXTERNO OPCIONAL:** sensor o herramienta no instalada.

| Etapa | Alternativas | Estado | Primera elección y criterio de cambio |
|---|---|---|---|
| Localización global | Waypoints/vnav + mapa + LiDAR; odometría relativa; PICO/manual | vnav y odometría verificadas parcialmente; PICO verificado para brazos | vnav hasta `*_PRE`; odometría sólo para retiradas cortas; manual sólo desarrollo |
| Detección de B0 | detector 6D `workbin`; cámara estéreo o cámara de cintura; AprilTag en caja; RGB-D/ROI/point cloud; VLA visual | `workbin` verificado; transporte por cámara de cintura, ROI y nubes presentes; demás propuesto | `workbin`; cambiar si la pose no es repetible en el rango objetivo |
| Detección de otro tamaño | `putbox`, `putcarton`, `foxconn_tray`, `jiepu_tray`, `om`, `thor`; tag; detector RGB-D propio | Perfiles presentes, no validados | Probar perfil existente en sólo lectura; tag como referencia; entrenar detector si no generaliza |
| Alineación de recogida | pose `workbin`; AprilTag 112; servo visual RGB-D; ajuste manual | `workbin` y tag disponibles | pose del detector con tag como auditor independiente |
| Seguimiento durante aproximación | detecciones 6D repetidas; servicios de tracking 6D estéreo/cintura; tag único; bundle AprilTag | Detección repetida disponible; tracking y bundle presentes sin contrato validado | Repetir detección para el MVP; probar tracking aislado; bundle si un tag se ocluye |
| Recogida | XML/tarea determinista; replay parametrizado; PICO; VLA | determinista y PICO disponibles; replay/VLA restringidos | determinista para MVP; PICO para demostrar casos no cubiertos; VLA sólo tras gates |
| Elevación | trayectoria determinista por perfil/altura; replay; VLA 20D | determinista disponible; VLA shadow | determinista con límites por estación |
| Transporte | vnav/LiDAR/localización; odometría; PICO/chasis manual | navegación instalada; PICO móvil no aceptado como producción | vnav conservando LiDAR/bumper/estop; sin base aprendida |
| Alineación en receptor | AprilTag de estación; detector del recipiente; RGB-D/ROI; teleop | AprilTag verificado para mesa 2; otros por validar | AprilTag + distancia RGB-D; cambiar si el tag se ocluye |
| Volcado | primitiva articular determinista; replay parametrizado; PICO; VLA específico | No existe primitiva validada | Determinista y lenta sin contenido; replay sólo como referencia; VLA si la variedad lo exige |
| Verificación de vaciado | conteo visual RGB/depth; cambio de masa; inferencia FT; temporización | Cámaras/FT presentes; solución no integrada | Piezas contables + cámara; báscula externa para evidencia; FT sólo señal auxiliar |
| Retorno erguido | inversa determinista del volcado; replay; VLA | Propuesto | Inversa determinista con verificación de pose |
| Alineación depósito vacío | AprilTag 114/waypoint; RGB-D; geometría de mesa | Propuesto sobre infraestructura existente | Tag + profundidad; calibración independiente por altura |
| Depósito | contacto y apertura deterministas; PICO; VLA | Depósito BYD verificado por etapas | Determinista por perfil/altura |
| Registro | log de misión/fases; ROS bags/streams; exportador 20D; vídeo | Plantillas y señales presentes; contrato de action aún pendiente | Sidecar de misión siempre; dataset sólo tras probar sincronización |
| Política aprendida | continuar `checkpoint-40000`; fine-tune desde GR00T N1.5 base; política separada por fase | Checkpoint instalado en shadow | Continuar checkpoint sólo si permanece 1 RGB + clamps + 20D; si cambia espacio, partir del modelo base |
| Fuerza adicional | FT de muñeca; báscula/load-cell bajo estación | FT instalada; báscula externa opcional | FT para protección/tendencia, nunca como prueba única de caja vacía |

### 7.1 Regla de selección

Para cada etapa se puntúa cada alternativa de 0 a 3 en:

1. seguridad y capacidad de STOP/recovery;
2. repetibilidad entre días;
3. cobertura de tamaños/poses;
4. evidencia observable;
5. esfuerzo de calibración y mantenimiento;
6. necesidad de datos nuevos.

La solución nominal favorece percepción geométrica + navegación + primitivas
deterministas. Teleoperación genera demostraciones y resuelve exploración. VLA
se incorpora donde la variabilidad residual justifique el coste y sólo después
de superar offline, replay, shadow y canary físico.

## 8. Plan por etapas y gates

Cada etapa produce evidencia versionada. Fallar un gate devuelve a esa etapa;
no autoriza saltar a la siguiente.

### Etapa 0 — Congelar baseline y recuperar una postura conocida

**Acciones**

1. Ejecutar únicamente los `--check` pertinentes.
2. Descubrir de nuevo contenedores, tareas, endpoints, `HW_TYPE`, efector,
   versión, modo y clientes activos.
3. Demostrar `home` o aprobar y registrar una postura `SAFE_READY` sin caja.
4. Resolver o adaptar el parser que actualmente no clasifica el log nuevo en
   `AutoTaskMode` antes de depender de recuperación automática.
5. Guardar hashes de XML, scripts y configuraciones de la campaña.

**Gate 0**

- postura conocida, velocidad cero, caja `REMOVED`, paros y cargador
  comprobados, acciones listas y recovery ensayado en seco;
- rollback y STOP identificados;
- ningún cable dentro de la trayectoria futura.

### Etapa 1 — Medir cajas, estaciones y marcos

**Acciones**

1. Crear los perfiles de B0 y de las tres estaciones.
2. Medir dimensiones, masas, alturas, bordes y espacios libres.
3. Fijar y medir tags 112/113/114; registrar familia, tamaño real y marco.
4. Capturar RGB, depth, point cloud y poses desde tres aproximaciones.
5. Verificar cada detector alternativo en modo lectura y documentar falsos
   positivos/negativos; no cargar un perfil de otra forma sólo por tamaño
   parecido.
6. Medir apertura y zona de contacto necesaria para B0 sin aplicar fuerza.

**Gate 1**

- desvío de alineación repetible dentro de la tolerancia calibrada; como
  referencia inicial, no peor que 20 mm y 2° en tres aproximaciones;
- tres perfiles de estación completos y transformación trazable;
- B0 reconocido en las tres poses piloto centrales sin mover el robot.

### Etapa 2 — Baseline determinista: recoger B0 abajo sin navegar

**Acciones**

1. Ejecutar el `--check` de `cruzr_blue_workbin_cycle.sh` y de la tarea de
   transferencia.
2. Ensayar aproximación y retirada con caja ausente.
3. Ensayar agarre de B0 vacía, elevación mínima, STOP controlado y depósito en
   la misma estación.
4. Repetir con lateral, depth y yaw nominales; registrar FT, pose, acciones y
   vídeo.
5. Separar `PICK_LOW` en pasos `prepare`, `detect`, `clamp`, `verify`, `lift` y
   `retreat` para poder reanudar.

**Gate 2**

- 3 ciclos consecutivos sin contacto externo, trip, resbalamiento ni acción
  abortada;
- `VERIFY_HELD` distingue caja apoyada de caja realmente sujeta;
- existe un procedimiento probado para soltar en la misma estación si falla la
  elevación.

### Etapa 3 — Variar la recogida a baja altura

**Acciones**

1. Ejecutar OFAT lateral, depth y yaw con B0 vacía.
2. Cambiar a cada `H_PICK_LOW_*` sólo después de calibrar lifter, cintura,
   cabeza y punto de agarre.
3. Comparar `workbin`, tag y RGB-D como estimadores independientes.
4. Marcar las celdas como `PASS`, `FAIL_SAFE`, `UNREACHABLE` o `RECALIBRATE`.

**Gate 3**

- al menos 3 repeticiones por nivel piloto y ninguna salida de límites;
- mapa de alcance explícito, incluida la zona que no se intentará;
- errores de percepción separados de errores de manipulación.

### Etapa 4 — Transporte hasta el receptor, sin volcar

**Acciones**

1. Con B0 vacía, validar por separado `RETREAT_PICK`, `NAV_POUR_PRE` y
   `ALIGN_POUR`.
2. Reutilizar el patrón de `MESA2_PRE` y AprilTag 113.
3. Validar primero `--align-empty`; después navegar con caja vacía sujeta.
4. Registrar localización, odometría, clearance, costmap y restauración del
   perfil de carga.
5. Terminar sujeto y estacionario en `ALIGNED_POUR`; todavía no volcar.

**Gate 4**

- 3 llegadas consecutivas dentro de tolerancia, sin cable, contacto ni pérdida
  de localización;
- parada segura y reanudación probadas desde `LOADED_HELD`/`EMPTY_HELD`;
- LiDAR, bumpers y paros demostrados activos.

### Etapa 5 — Crear la primitiva de volcado sin contenido

Se propone `scripts/cruzr_box_tip.sh` con `--check`, `--dry-plan`,
`--tip-empty`, `--return-upright` y estados reanudables.

**Acciones**

1. Calcular offline alcance, autocolisión, borde, punto de giro y envolvente.
2. Elegir el eje de volcado que mantenga la caja dentro del receptor y alejada
   del torso.
3. Ejecutar primero un movimiento parcial con caja ausente.
4. Sujetar B0 vacía y aumentar el ángulo por escalones conservadores; detenerse
   entre escalones para verificar pose, fuerza y margen.
5. Validar la trayectoria inversa hasta `RETURN_UPRIGHT`.
6. Repetir por separado cada altura de receptor.

**Gate 5**

- 3 ciclos vacíos `upright -> tip -> upright` sin contacto, deslizamiento,
  trip ni discontinuidad;
- ángulo y altura máximos quedan en el perfil, no hardcodeados globalmente;
- STOP puede dejar la caja en un estado identificado y recuperable.

### Etapa 6 — Volcar contenido ligero y comprobar vaciado

Se propone `scripts/cruzr_verify_box_empty.sh`.

**Acciones**

1. Introducir una sola pieza de espuma contable; después 2, 3… sin cambiar
   tamaño, pose o altura.
2. Registrar masa antes/después mediante báscula externa si está disponible.
3. Capturar cámara del receptor y, si la geometría lo permite, interior de la
   caja antes/después.
4. Comparar tres señales: piezas detectadas en receptor, masa residual y
   tendencia FT. La temporización por sí sola no confirma vaciado.
5. Si queda contenido, terminar seguro y etiquetar `PARTIAL_EMPTY`; no sacudir
   ni aumentar fuerza automáticamente.

**Gate 6**

- `N_out=N_in`, cero piezas fuera del receptor y caja de nuevo erguida;
- 10 éxitos del caso nominal, sin trip ni contacto;
- criterio de `VERIFY_EMPTY` documentado con falsos positivos y negativos.

### Etapa 7 — Transportar y depositar la caja vacía a otra altura

**Acciones**

1. Validar sin caja `NAV_EMPTY_DROP_PRE` y alineación con tag 114.
2. Repetir con B0 vacía sujeta desde `RETURN_UPRIGHT`.
3. Crear una trayectoria de depósito independiente para cada `H_DROP_*`.
4. Confirmar apoyo antes de abrir; confirmar separación antes de retirar brazos.
5. Volver a `SAFE_HOME` sólo después de `EMPTY_SUPPORTED` y envolvente libre.

**Gate 7**

- 3 depósitos consecutivos por altura nominal sin caída, arrastre ni contacto;
- `VERIFY_RELEASED` demuestra abrazaderas libres y caja apoyada;
- recovery desde `EMPTY_HELD` y desde `EMPTY_SUPPORTED` documentado.

### Etapa 8 — Integrar la misión nominal completa

**Acciones**

1. Encadenar los checkpoints sin eliminar sus verificaciones.
2. Ejecutar primero B0 vacía; luego una pieza de espuma; después la carga ligera
   nominal ya validada.
3. Guardar un manifiesto único de misión y un registro por fase.
4. Fallar deliberadamente en seco entre fases para verificar cada `--resume-*`.

**Gate 8**

- 10 misiones nominales completas, con 100 % de contenido dentro del receptor;
- cero STOP no explicado, trips, objetos caídos fuera de zona o estados
  `unknown`;
- retorno final seguro comprobado, no inferido.

### Etapa 9 — Generalizar posición, orientación y tamaño

**Acciones**

1. Aplicar la matriz OFAT completa a B0.
2. Ejecutar sólo las combinaciones por pares de borde seleccionadas.
3. Incorporar B1 desde Etapa 1, después B2, B3 y finalmente B4 si alcance,
   rigidez y carga lo permiten.
4. Para cada caja elegir de nuevo detector, agarre, altura, ángulo y tolerancias;
   no escalar una trayectoria sólo por las dimensiones.

**Gate 9**

- 10 éxitos por celda aceptada y 0 fallos peligrosos;
- caja, pose o altura fuera del mapa aprobado se rechaza antes de mover;
- matriz de compatibilidad caja × estación publicada.

### Etapa 10 — Captura piloto de demostraciones

La captura se inicia sólo cuando la misión determinista puede dejar el robot y
la caja en estados recuperables.

**Acciones**

1. Demostrar que el exportador contiene RGB sincronizado, `state[20]`,
   `action[20]`, timestamps y tarea; registrar FT de 12 valores como QC/sidecar.
2. Grabar tareas separadas:
   - `PICK_LOW`: detectar, sujetar y levantar;
   - `TIP_INTO_RECEIVER`: preparar, volcar y volver erguido;
   - `PLACE_EMPTY`: apoyar, abrir y retirar.
3. Registrar navegación, tags, detector, odometría, safety y recovery en el
   sidecar de misión, no fingir que son acciones del VLA actual.
4. Capturar al menos 10 episodios aceptados por celda piloto antes de ampliar.
5. Separar train/validation/test por sesión, caja, altura y layout, nunca por
   frames del mismo episodio.

**Gate 10**

- reproducción visual/articular coherente en 10 episodios piloto;
- origen exacto de `action[20]` demostrado, no inferido de `state`;
- frecuencias y sincronización medidas; episodios con contacto o recovery
  excluidos del entrenamiento y conservados para análisis.

### Etapa 11 — Elegir determinista, replay o VLA por fase

**Comparación**

| Opción | Prueba | Se elige si… | Se descarta si… |
|---|---|---|---|
| Determinista parametrizada | Repetición en toda la matriz aprobada | Cubre la variación con baja tasa de fallo | Requiere demasiadas reglas frágiles o no adapta la aproximación |
| Replay parametrizado | Replay offline y luego sin carga | Sirve como primitiva calibrable y continua | Sólo funciona en una pose exacta o introduce discontinuidades |
| VLA por fase | Offline, replay, shadow | Mejora cobertura con límites y confianza observables | Sale de distribución, salta respecto al estado actual o no permite gate |

No es necesario que una sola tecnología controle la misión completa. La
arquitectura objetivo puede ser navegación y seguridad deterministas con VLA
sólo para una fase de manipulación.

### Etapa 12 — Decidir checkpoint y entrenar

El `checkpoint-40000` suministrado vio 500 episodios de pick/place de una caja
grande a alturas baja/media. No contiene evidencia de volcado, base móvil,
fuerza como entrada ni dedos.

**Continuar `checkpoint-40000`** si se conserva:

- una cámara RGB 224 × 224;
- estado y acción de 20 dimensiones en el mismo orden;
- abrazaderas, sin dedos;
- brazos/cabeza/elevador/cintura compatibles;
- tarea cercana a cajas, mezclando episodios antiguos y nuevos para evitar
  olvido.

**Partir de `nvidia/GR00T-N1.5-3B` con un DataConfig nuevo** si se incorpora:

- base/chasis al espacio de acción;
- manos con dedos;
- fuerza como entrada de política;
- profundidad o varias cámaras;
- otra dimensionalidad u orden de estado/acción.

Para el primer VLA físico, cabeza, elevador y cintura se preposicionan de forma
determinista y se bloquean; sólo se consideran las 14 articulaciones de brazos
tras superar los gates de la guía de activación segura.

**Gate 12**

- mejora en test no visto por caja/altura/layout;
- límites, latencia, confianza y detección fuera de distribución definidos;
- ninguna selección se basa sólo en pérdida de entrenamiento.

### Etapa 13 — Validación VLA gradual

1. Inferencia offline sobre test congelado.
2. Replay cinemático sin actuadores.
3. Shadow junto a una ejecución determinista/teleoperada.
4. Comprobar continuidad del primer chunk respecto al estado real.
5. Canary físico sin caja, un brazo y horizonte corto.
6. Caja vacía, fase aislada y STOP inmediato.
7. Contenido ligero sólo después de igualar el baseline determinista.

**Gate 13**

- cero discontinuidades fuera de umbral;
- shadow y canary cumplen los mismos límites de fuerza/pose/tiempo;
- rollback a política determinista disponible en estado seguro, nunca a mitad
  de una trayectoria no clasificada.

## 9. Máquina de estados y recuperación

| Estado | Caja | Movimiento permitido siguiente | Reanudación que debe existir |
|---|---|---|---|
| `SAFE_READY` | retirada o apoyada fuera de trayectoria | `NAV_PICK_PRE` | inicio nominal |
| `AT_PICK_PRE` | cargada y apoyada | `ALIGN_PICK` | `--resume-at-pick-pre` |
| `ALIGNED_PICK` | cargada y apoyada | `PICK_LOW` | `--resume-aligned-pick` |
| `LOADED_HELD` | cargada y sujeta | elevar/retirarse o soltar en origen | `--resume-held-after-pick` |
| `CLEAR_PICK` | cargada y sujeta | `NAV_POUR_PRE` | `--resume-held-navigation` |
| `ALIGNED_POUR` | cargada y sujeta | preparar/volcar | `--resume-held-at-pour` |
| `PARTIAL_TIP_HELD` | contenido desconocido y caja sujeta | STOP y recuperación específica | `--recover-partial-tip` |
| `EMPTY_HELD_UPRIGHT` | vacía y sujeta | retirar/navegar a depósito | `--resume-empty-held-after-pour` |
| `AT_EMPTY_DROP_PRE` | vacía y sujeta | alinear/depositar | `--resume-empty-held-at-drop` |
| `EMPTY_SUPPORTED` | vacía, apoyada, quizá aún entre abrazaderas | verificar y abrir | `--resume-supported-release` |
| `RELEASED_CLEAR` | vacía y apoyada; abrazaderas libres | retirada y `SAFE_HOME` | `--resume-retreat-home` |
| `FAULT_*` | estado explícito | sólo diagnóstico/STOP/recovery | guía específica, nunca ciclo completo |

El orquestador futuro debe persistir de forma atómica: `mission_id`, estado,
caja, carga, estación, pose, modo, acción activa, cliente, hashes y evidencia.
Tras reinicio, `unknown` no se convierte en `SAFE_READY` automáticamente.

## 10. Componentes existentes que se reutilizan

- `scripts/cruzr_blue_workbin_cycle.sh`: preflight y primitivas BYD/workbin;
- `scripts/cruzr_blue_workbin_table_transfer.sh`: etapas de recogida,
  retirada, navegación, alineación, depósito y reanudación;
- `scripts/cruzr_blue_workbin_carry_back.sh`: movimiento relativo corto con
  caja sujeta;
- `scripts/cruzr_apriltag_mesa2_align.sh`: diagnóstico, calibración y alineación
  respecto al AprilTag de mesa 2;
- `scripts/cruzr_recover_to_home.sh`: recuperación, siempre condicionada al
  estado físico y lógico demostrado;
- `scripts/teleoperation/probar_pico.sh`: preflight, START/STOP y sesiones PICO;
- plantillas de `docs/vla/templates/`: manifiesto y logs de episodios/misiones;
- `checkpoint-40000`: únicamente offline/shadow mientras continúe bloqueado.

Los nombres deben confirmarse con `rg --files scripts` y `--help` antes de
implementar; una referencia en este plan no garantiza que una rama de
movimiento siga instalada después de una actualización.

## 11. Componentes propuestos

No se crean ni se ejecutan como parte de este documento:

| Componente | Responsabilidad |
|---|---|
| `config/box_profiles.yaml` | Geometría, carga, agarre, percepción y límites por caja |
| `config/station_profiles.yaml` | Alturas, tags, waypoints, poses y tolerancias por estación |
| `scripts/cruzr_box_pick_pour_place.sh` | Orquestador de estados, checkpoints y `--resume-*` |
| `scripts/cruzr_box_tip.sh` | Volcado gradual y retorno erguido parametrizados |
| `scripts/cruzr_verify_box_empty.sh` | Fusión de conteo visual, masa y QC FT |
| `scripts/cruzr_box_mission_check.sh` | Preflight global de sólo lectura |
| `docs/vla/templates/box_profile.example.yaml` | Plantilla auditable de caja |
| `docs/vla/templates/station_profile.example.yaml` | Plantilla auditable de estación |
| `docs/vla/templates/pick_pour_place_matrix.csv` | Matriz OFAT, resultados y exclusiones |

Cada script físico deberá implementar `--help`, `--check`, logs vivos,
confirmación inequívoca, STOP por señal/fallo/timeout y pruebas de sintaxis.

## 12. Evidencia mínima por ensayo

Registrar:

- `mission_id`, fecha, operador y observador de paro;
- serial/versiones/hashes y configuración de red;
- caja, dimensiones, masa, contenido y cantidad;
- las tres estaciones, alturas, tags y waypoints;
- pose objetivo y observada en cada checkpoint;
- alternativa tecnológica usada en cada fase;
- estado/acción 20D si existe captura, FT de ambas muñecas y timestamps;
- estados de navegación, localización, detector, acciones y STOP;
- vídeo RGB y, cuando proceda, depth/point cloud;
- fuerza máxima, velocidad máxima, tiempo por fase y clearance mínimo;
- resultado `PASS`, `FAIL_SAFE`, `ABORTED`, `RECOVERY` o `INVALID_DATA`;
- estado físico y lógico final demostrado.

## 13. Criterios de aceptación finales

La funcionalidad se considera lograda sólo cuando:

1. cada caja declarada compatible completa 10 misiones por celda nominal
   aceptada y los casos de borde seleccionados;
2. se recogen cajas en todas las alturas bajas aprobadas, posiciones y yaw del
   mapa publicado;
3. todo el contenido ligero de prueba cae dentro del receptor, sin residuo
   según el método de verificación aprobado;
4. la caja vuelve erguida y se deposita estable en cada altura final aprobada;
5. no hay trips, contacto no previsto, caída fuera de zona, pérdida de
   localización ni estado `unknown` oculto;
6. cada fallo ensayado termina en STOP y puede reanudarse desde la fase correcta;
7. ninguna tecnología aprendida empeora el baseline determinista en seguridad
   o tasa de éxito;
8. el sistema rechaza antes de mover cualquier tamaño, masa, pose, estación o
   carga fuera del perfil validado.

## 14. Orden inmediato de trabajo

1. Corregir la clasificación segura de postura/modo tras el último arranque.
2. Crear y medir el perfil de B0 y de `PICK_LOW`, `POUR` y `EMPTY_DROP`.
3. Auditar `cruzr_blue_workbin_table_transfer.sh --check` contra el baseline
   actual y ejecutar únicamente pruebas estáticas de percepción.
4. Validar recogida baja y depósito local con B0 vacía.
5. Validar navegación/alineación a las dos estaciones sin caja.
6. Diseñar y revisar offline la primitiva de volcado.
7. Ejecutar el volcado incremental sin contenido.
8. Añadir piezas de espuma contables y validar `VERIFY_EMPTY`.
9. Integrar el depósito vacío a distinta altura.
10. Completar OFAT con B0 y sólo después introducir el siguiente tamaño.
11. Capturar un piloto 20D y auditarlo extremo a extremo.
12. Decidir por fase si permanece determinista, usa replay o justifica VLA.

## 15. Documentación relacionada

- [Fuente de verdad global](PROJECT_SOURCE_OF_TRUTH.md)
- [Transferencia de caja entre mesas con AprilTag](guides/TRANSFERENCIA_CAJA_ENTRE_MESAS_CON_APRILTAG.md)
- [Catálogo de funcionalidades instaladas](guides/CATALOGO_FUNCIONALIDADES_CRUZR_S2.md)
- [Guía de teleoperación, datos y entrenamiento VLA](vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md)
- [Activación segura del VLA suministrado](guides/CRUZR_S2_VLA_SAFE_ENABLEMENT.md)
- [Recuperación tras contacto o fallo durante teleoperación](guides/CRUZR_S2_RECUPERACION_TRAS_CONTACTO_TELEOP.md)
- [Fuente de verdad PICO/PC/robot](teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md)
