# Plan de trabajo: recoger, transportar, vaciar y depositar una caja

**Fecha:** 2026-08-27

**Estado:** `PLANIFICADO`; este documento no autoriza movimiento físico

**Unidad:** Cruzr S2 `WAE001UBT60000669`, abrazaderas, `HW_TYPE=cruzr_s2_v1`

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
