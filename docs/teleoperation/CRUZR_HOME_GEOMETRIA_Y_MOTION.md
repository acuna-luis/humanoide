# HOME general: geometría y contrato de Motion

## Resultado de la revisión de interfaces, 11-09-2026

**Punto 1 todavía NO CERRADO. Diagnóstico corregido y contraste nativo
VERIFICADOS offline; no se han habilitado exclusiones ni ejecución general.**
No basta aceptar los solapamientos de HOME/PICO para omitir esas mismas parejas
en todo su recorrido. La información pendiente es una representación mecánica
de las interfaces: zonas de contacto/solapamiento admitidas y dominio articular
al que se aplican, o un modelo de colisión equivalente y validado. Una lista
de pares que fallan en reposo no sustituye esa definición. No se requieren más
medidas de la almohadilla para resolver esta cuestión de las uniones internas.

### Corrección de los puntos de contacto

Una prueba con dos cajas demostró que `FCL contact.pos` puede estar sobre una
sola de las caras y fuera de la intersección, especialmente con caras coplanares.
Los radios/zonas calculados antes a partir de esos puntos no son una descripción
válida de todo el contacto y **no deben usarse para construir exclusiones**.
Los recuentos de colisión/distancia del planificador no dependían de esas
coordenadas y no cambian por esta corrección.

`general_home/contact_witnesses.py` reconstruye candidatos mediante cruces de
aristas con planos y de aristas proyectadas. Verifica cada punto contra **ambos
triángulos originales**, con tolerancia numérica de 10 nm. Rechaza caras
degeneradas y resultados no finitos. `audit_home_interfaces.py` usa ahora esos
testigos en el marco base; las llamadas sin mallas originales marcan sus puntos
FCL como no verificados. Ni los testigos reconstruidos ni una lista limitada
a 256 contactos describen el volumen completo de una interfaz.

### Prueba de las exclusiones completas

`audit_home_interface_sweeps.py` mantiene HOME y ambos PICO como referencias.
Para cada una de las 24 parejas móviles forma, en el marco de la primera pieza,
una caja que encierra toda posible intersección de las envolventes AABB de las
dos superficies. Amplía ambas AABB 2 mm. Busca después puntos de contacto
reconstruidos fuera de **todas** esas cajas, dejando además una banda numérica
de 20 nm. Un punto así queda fuera incluso de esa aproximación amplia de las
zonas iniciales; una exención de la pareja completa también lo ocultaría.

| Barrido sintético | Configuraciones de parejas examinadas | Parejas con testigo nuevo validado |
|---|---:|---:|
| Límites del URDF, nueve muestras por eje y cero si falta | 228 | 8 |
| Mismo barrido restringido a ±0,5 rad | 261 | 4 |

El barrido se detiene en el primer testigo nuevo de cada pareja. **Es una
búsqueda de contraejemplos, no una prueba continua de ausencia de colisiones.**
Las otras parejas no quedan aprobadas. Son resultados del CAD; no demuestran
contactos físicos. Los límites del URDF tampoco equivalen a los límites activos
de Motion: el YAML archivado del elevador/cabeza contiene límites más estrechos.
El segundo barrido reduce la dependencia de esos extremos, pero no constituye
verificación de los límites activos, calibración ni autorización de movimiento.

Los cuatro ejemplos cercanos a HOME son:

| Pareja del CAD | Ejes distintos de cero en el ejemplo, radianes |
|---|---|
| `lifter_pitch_2_link` / `waist_yaw_link` | `lifter_pitch_3_joint=-0.5`, `waist_yaw_joint=-0.5` |
| `torso_link` / `head_pitch_link` | `head_pitch_joint=-0.5`, `head_yaw_joint=-0.375` |
| `L_wrist_pitch_link` / `L_wrist_roll_link` | `L_wrist_roll_joint=-0.5` |
| `R_wrist_pitch_link` / `R_wrist_roll_link` | `R_wrist_roll_joint=-0.5` |

Son datos para revisar geometría, **no consignas que ejecutar**. Los informes
privados conservan los veinte ángulos, marcos, puntos, cajas y hashes. Las cifras
preliminares 13/9 obtenidas con posiciones FCL sin verificar quedan **DESCARTADAS**.
El intento intermedio que filtraba sólo `contact.pos` tampoco sustituye al
resultado final: no reconstruía la intersección cuando FCL elegía otro punto.

### Qué aporta el código nativo

Se descubrieron contenedores y copiaron bibliotecas mediante consultas de
lectura. Se localizaron `CollisionHelper::CheckCollisionWithSelfAndEnv`,
`CheckSelfCollisionWithTorsoAndHead` y `GetPrimitiveSetOfBodyAndHead` en
`/opt/walker/manipulation_platforms/lib/librobot.so`, SHA-256
`7322b075badd43ad6f20f87fe9ff6b4b1cd6fc95bcd44d8c5048df26486432de`.
También se archivaron las bibliotecas específicas `cruzr_s2_lifter` y
`cruzr_s2_waist`; la biblioteca anterior `s2_leg` no corresponde a este elevador.

El nuevo auditor nativo interpreta **sólo** el bucle revisado de selección de
parejas, direcciones `0xe2750` a `0xe229f`, con grupos sintéticos y la llamada de
distancia sustituida por un resultado ficticio. Para 1, 2, 3, 4, 8 y 16 grupos,
comprueba que consulta cada combinación de grupos distintos una vez. No mide
distancias reales, no lee los grupos activos y no demuestra qué comprobaciones
realizan otras ramas. No hay carga nativa del ELF, llamadas ROS o movimiento;
hash, memoria, instrucciones, destinos de llamada y tiempo están limitados.

**Conclusión:** ese bucle no proporciona una matriz de exclusiones entre los
links del CAD. Trasladar directamente la agrupación de primitivas nativas al
modelo completo no tiene justificación con la evidencia disponible. La
cobertura adicional de abrazaderas ya calculada sigue siendo necesaria y no
resuelve por sí sola la definición mecánica de las otras interfaces.

### Reproducción y punto de reanudación

Con el venv ANL-01 existente, sin instalar dependencias ni archivos en el robot:

```bash
.venv/general-home/bin/python scripts/teleoperation/audit_home_interfaces.py \
  --output /ruta/privada/interfaces-corregidas.json
.venv/general-home/bin/python scripts/teleoperation/audit_home_interface_sweeps.py \
  --output /ruta/privada/barrido-urdf.json
.venv/general-home/bin/python scripts/teleoperation/audit_home_interface_sweeps.py \
  --maximum-absolute-angle 0.5 --output /ruta/privada/barrido-cerca-home.json
.venv/general-home/bin/python scripts/teleoperation/audit_native_collision_policy.py \
  --library /ruta/privada/runtime/opt/walker/manipulation_platforms/lib/librobot.so \
  --output /ruta/privada/politica-nativa.json
```

Las salidas deben ser nuevas. Pruebas: `test_general_home.py`,
`test_prism_enclosure.py`, `test_home_interfaces.py`, `test_interface_sweeps.py`
y `test_native_collision_policy.py`, con `unittest discover -s scripts/teleoperation
-p NOMBRE -v`. La última suite requiere `CRUZR_POLICY_LIBRARY` apuntando a la
copia privada fijada por hash para no omitir sus pruebas del binario real.

Reanudar cuando exista una definición revisable de las interfaces y sus
dominios, o acotar explícitamente el producto a trayectorias/posturas ya
validadas. Entonces integrar esas regiones, comprobar cobertura frente a
terceras piezas y repetir la prueba continua. No repetir indefinidamente el
recuento de 54 avisos ni convertir un barrido sin hallazgos en aprobación.
La estimación previa de 4–8 horas estaba condicionada a que la información
mecánica bastase; esta revisión no permite comprometer ese plazo de cierre.

Evidencia vigente: `../Humanoide-vla-evidence/20260911T075508Z_HOME-INTERFACE-CLOSURE/`,
`interfaces-corrected.json`, `interface-sweeps-final.json`,
`interface-sweeps-near-home-final.json`, `native-policy.json`, manifiesto de
bibliotecas, pruebas, `before/`, `after/` y `result.json`. Los borradores sin
verificación de testigos se conservan como intentos descartados.
Sólo fuentes PC y copias privadas de lectura; sin instalaciones, recargas,
cambios de modo, reinicios o movimientos remotos. Registro y reversión: ANL-01.

## Avance anterior: refinamiento de prismas

**Último avance 11-09-2026:** refinamiento del elevador integrado en el modelo
offline y auditoría de las interfaces con superficies originales. Pasan52pruebas.
Las envolventes generales bajan de11a10; continúan54avisos por referencia y no
se ha habilitado ejecución general. El complemento local de muñeca de la sección
siguiente sigue siendo un artefacto separado, no integrado en el planificador.
Los resultados anteriores conservan su fecha y alcance.

## Refinamiento del elevador y diagnóstico de interfaces, 11-09-2026

**VERIFICADO en el CAD y pruebas offline; ejecución física PENDIENTE.**
La revisión examinó las once mallas abiertas: ampliar la soldadura de vértices
no resolvía su topología y llegaba a empeorarla. No se aplicó esa ampliación.
En `lifter_pitch_3_link.STL` se identificaron cinco componentes con paredes
completas de prismas convexos y ambas tapas ausentes: tres de33vértices por
contorno y4mm de longitud, dos de28vértices por contorno y13mm de longitud.
Sus discrepancias geométricas numéricas máximas son6,8nm, no milímetros.

`general_home/prism_enclosure.py` exige dos contornos convexos congruentes,
planos dentro de10nm, correspondencia biunívoca de vértices y todas las bandas
laterales con exactamente sus dos triángulos. Rechaza bandas ausentes/duplicadas,
extremos cóncavos, deformados o no congruentes. Construye la envolvente completa
de cada prisma y verifica contención de los vértices originales; la convexidad
incluye sus triángulos y el interior. Conserva los otros componentes cerrados.
Si queda una sola lámina sin reconocer, mantiene el cierre conservador general.
No infiere una tapa para una abertura arbitraria ni borra superficies originales.

**Cambio efectivo del modelo PC:** `Shape.from_mesh` usa esa unión local en el
tercer tramo del elevador, en lugar de rellenar los huecos entre todas sus piezas
con una única envolvente. Los originales del proveedor no cambian. Las otras
diez mallas abiertas conservan su representación anterior. Se mantienen45formas,
982pares comprobados, los ocho pares internos rígidos anteriores y el margen
de2mm. No hay pares nuevos omitidos, tolerancias físicas reducidas ni XML cambiado.

### Qué significan los avisos restantes

`audit_home_interfaces.py` contrasta cada rechazo con las superficies originales
mediante BVH, además de la comprobación de sólidos vigente. Guarda puntos de
contacto o puntos más próximos en el marco base. Para relaciones de un solo eje
añade sus coordenadas axiales/radiales respecto a ese eje. **Son testigos, no una
envolvente de todo el contacto ni una zona de exclusión autorizada.** Una lista
de contactos se marca como potencialmente truncada al llegar a256testigos.

| Referencia sintética | Intersección de superficies CAD | Volumen derivado solapado o contención a revisar | Separación positiva inferior al margen | Total |
|---|---:|---:|---:|---:|
| HOME | 10 | 24 | 20 | 54 |
| PICO con cuerpo flexionado | 13 | 23 | 18 | 54 |
| PICO con cuerpo a cero | 12 | 24 | 18 | 54 |

En cada referencia hay30pares invariantes con base/auxiliares fijos y24relaciones
móviles. Ninguno se elimina por aparecer ya en HOME. Ejemplos en HOME:

- Base frente al primer tramo del elevador: superficies originales separadas
  20,75mm, aunque el sólido derivado solapa. Requiere interpretar volumen/huecos.
- Torso frente a cada primer componente del hombro: separación superficial
  7,70mm; no basta por sí sola para descartar contención o geometría omitida.
- Hombro roll/yaw: separación original de aproximadamente0,31mm; codo roll/yaw,
  0,64mm. Son inferiores al margen general de2mm aunque no crucen superficies.
- Elevador, hombro pitch/roll y muñecas incluyen cruces de superficies del CAD.
  No equivalen a contactos físicos demostrados ni se habilita ignorarlos.

Los recuentos de rechazo incluyen la banda numérica de1nm que ya usa el
validador junto al margen; una separación apenas superior a2mm puede caer en
esa banda. El informe conserva la distancia y el margen sin redondearlos.

**Consecuencia:** el refinamiento mejora la representación pero no cambia los54
rechazos de estas tres posturas. El cuello de botella restante exige definir
correctamente el material y las holguras de las interfaces articulares. Una
distancia entre superficies positiva no sustituye a la comprobación de sólidos:
dos sólidos anidados pueden tener sus fronteras separadas y seguir colisionando.
Tampoco los testigos muestreados bastan para definir excepciones de todo un giro.
Continúan pendientes correspondencia física, contrato de ejecución y parada.

### Reproducir esta revisión

Sin robot, con el entorno ANL-01 existente y salidas nuevas:

```bash
.venv/general-home/bin/python scripts/teleoperation/cruzr_plan_home.py \
  --audit-model --output /ruta/privada/modelo-interfaces.json
.venv/general-home/bin/python scripts/teleoperation/audit_home_interfaces.py \
  --output /ruta/privada/interfaces.json
.venv/general-home/bin/python -m unittest discover \
  -s scripts/teleoperation -p test_general_home.py -v
.venv/general-home/bin/python -m unittest discover \
  -s scripts/teleoperation -p test_prism_enclosure.py -v
.venv/general-home/bin/python -m unittest discover \
  -s scripts/teleoperation -p test_home_interfaces.py -v
```

41pruebas del planificador, ocho de cierre de prismas y tres de diagnóstico
pasan:52en total. Incluyen obstáculos finos entre extremos, desfase entre ejes,
contención de sólidos, conservación de piezas frente a otros objetos, rechazo
de una lámina residual y coordenadas transformadas de los testigos de FCL.
No se probaron trayectorias físicas ni se midió una mejora de velocidad.

Evidencia: `../Humanoide-vla-evidence/20260911T073642Z_HOME-INTERFACE-REFINEMENT/`.
`model-final.json`, `interfaces-final.json`, certificados de cada prisma,
pruebas, exploraciones descartadas, `before/`, `after/` y `result.json`.
Los informes contienen hashes del código y del CAD y rechazan cambios durante
la lectura. Sólo cambios PC; no hubo conexión, instalación, recarga o movimiento
del robot en esta intervención. Registro/reproducción/reversión: ANL-01.

## Unión muñeca y abrazadera, 11-09-2026

**VERIFICADO offline en archivos; correspondencia física/calibración activa
PENDIENTES.** `audit_wrist_clamp_union.py` comprueba la unión nativa, conservando
el CAD original. `native_arm_frames.py` emula únicamente aritmética y colocación
de cápsulas del binario de brazo con hash fijado. Intercepta `sincos` y `SetPose`,
limita memoria/instrucciones/rangos y rechaza cualquier llamada no revisada.
No usa el cargador nativo, ROS ni una interfaz de control.

La colocación nativa asocia WristRoll a la pose DH después de la articulación7;
WristPitch permanece ligado a la6 y se mueve respecto al conjunto rígido.
Se compararon 128 vectores sintéticos contra una implementación DH independiente:
error máximo2,23e-16. Es una prueba numérica, no un dominio físico autorizado.
En HOME y ambas referencias PICO, comparación nominal DH/URDF: diferencia máxima
de traslación0,02391mm y de rotación0,002454°. No mide error de montaje físico.

La rama estática del constructor genérico selecciona S2Clamp no-tray para el
`HW_TYPE=cruzr_s2_v1` observado y aplica `X_ParentBase` del YAML de cada mano:
traslación L=[0,89,94]mm, R=[0,89,−94]mm, rotación identidad. La tabla compilada
L está en0x39c80 y R en0x39b40. El YAML y el URDF nativos difieren0,38mm en Y;
para la primitiva se usa el YAML, para el CAD su propia cadena fija.
Selección y anclaje quedan respaldados por configuración/inspección estática;
**no es una lectura del modelo calibrado en memoria**. Los YAML de calibración
archivados contienen opciones/límites del calibrador, no sus resultados.

| Resultado del conjunto rígido | Izquierdo | Derecho |
|---|---:|---:|
| Triángulos originales muñeca+sensor+útil | 103.925 | 103.927 |
| Vértices únicos | 51.782 | 51.783 |
| Vértices fuera de WristRoll + S2Clamp nativas | 2.245 | 2.245 |
| Mayor exceso observado en vértices | 8,63547mm | 8,63556mm |
| Caras de la envolvente exterior del CAD | 1.464 | 1.476 |
| Caras no certificadas con las formas nativas | 1.053 | 1.055 |
| Caras sin cubrir tras añadir el complemento | **0** | **0** |

Añadir WristPitch en HOME y ambas referencias PICO reduce los vértices fuera a
1.829 por lado, pero conserva el exceso de8,64mm. No se incluye esa pieza móvil
en la cobertura rígida. Un vértice fuera prueba cobertura incompleta; la cifra
no es una cota de todo el error superficial ni demuestra una colisión real.

### Cómo se demuestra la cobertura completa

`general_home/union_coverage.py` construye la envolvente convexa de todos los
vértices originales: contiene todos sus triángulos y su volumen. Para cada cara
triangular de esa envolvente exige que **sus tres vértices estén dentro de una
misma forma convexa**, no repartidos entre formas. Todas las formas comparten el
punto [0,85,0]mm en el marco de WristRoll; su unión es estrellada respecto a ese
punto. Cubrir la frontera completa implica cubrir también el interior.

El complemento engloba todos los vértices de las caras no certificadas y el punto
común. Se añade1µm de dilatación numérica; **no sustituye el error físico de2mm
ni los márgenes de trayectoria**, que permanecen separados. La construcción
conserva la topología de Qhull sin soldar vértices próximos; el procesamiento
automático de la malla había abierto caras casi coincidentes. Una regresión
específica comprueba un sólido con dos vértices separados nanométricamente.

Es una representación conservadora amplia: volumen del complemento1,138litros
frente a1,163litros de la envolvente completa, aproximadamente en ambos lados.
**No se presenta como reducción de volumen ni mejora de velocidad.** La cobertura
local se conserva al transformar rígidamente el conjunto, pero no resuelve sus
colisiones con las otras piezas móviles. No se ha aplicado a `RobotGeometry`,
ni eliminado pares, reducido márgenes o modificado XML operativos.

### Reproducción y revisión visual sin robot

Requiere el venv ANL-01 existente y copias privadas conservando `opt/walker/`:

```bash
.venv/general-home/bin/python scripts/teleoperation/audit_wrist_clamp_union.py \
  --arm-library /ruta/geometria/runtime/opt/walker/manipulation_kinematics/lib/libs2_arm_kinematics.so \
  --runtime-root /ruta/marcos/runtime \
  --output /ruta/privada/nuevo-union-audit.json

.venv/general-home/bin/python scripts/teleoperation/render_wrist_clamp_review.py \
  --audit /ruta/privada/nuevo-union-audit.json \
  --output /ruta/privada/nuevo-wrist-clamp-review.html

CRUZR_GEOMETRY_ARCHIVE=/ruta/geometria/runtime \
  .venv/general-home/bin/python -m unittest discover \
  -s scripts/teleoperation -p test_wrist_clamp_union.py -v
```

El visor autónomo permite seleccionar brazo y comparar CAD, formas nativas,
complemento y punto testigo. Se verificaron ambos lados y controles en Chromium,
pantalla de escritorio y móvil, sin errores JavaScript/WebGL. La teselación de
curvas es sólo visual; la auditoría usa distancia matemática a cápsula y sólido
convexo dilatado. Visor e informe comprueban hashes antes/después de leer.
Ocho pruebas pasan, incluida la emulación con el binario privado; sin archivo
explícito esa prueba se omite y las otras siete no requieren bibliotecas vendor.

**Estado y reanudación:** fuentes instaladas sólo en PC, sin nuevas dependencias,
sin geometría instalada/cargada/probada físicamente en Motion. Lecturas remotas:
contenedores/HW_TYPE/hashes/configuración; el topic SDK consultado no produjo
datos dentro del timeout. No se obtuvieron poses calibradas por ese medio ni se
envió movimiento. Continúan pendientes las otras interfaces del modelo completo
(auditoría anterior:54conflictos por referencia), el elevador correcto y la cabeza;
después contrato de despacho, seguimiento/parada y ensayo del HOME general.
Los perfiles PICO y HOME de20s permanecen intactos.

Evidencia privada: `../Humanoide-vla-evidence/20260911T070352Z_WRIST-CLAMP-UNION/`.
`union-audit.json` contiene formas derivadas/certificados/hashes;
`wrist-clamp-review.html` es el visor; `viewer-check.json`, capturas y
`tests.log` guardan verificación. `runtime-manifest.json` identifica las copias
leídas; `before/`, `after/` y `result.json` conservan fuentes, backups y checksums.
Registro, aplicación y reversión: ANL-01. No distribuir CAD/binarios en Git.

## Extracción de las formas nativas, 11-09-2026

**VERIFICADO en copias del runtime, sin movimiento ni cambios remotos.**
`audit_native_collision_geometry.py` interpreta prefijos de inicialización
de datos con Unicorn. No usa `dlopen`: todas las llamadas se interceptan y
sustituyen por operaciones acotadas de strings, vectores y memoria emulada.
Se registran argumentos antes de construir las primitivas; no se ejecutan
constructores reales, transportes ni controladores. Código fuera de los rangos
revisados, hashes distintos y presupuesto agotado se rechazan. Esto extrae
defaults compilados, no el modelo activo con sus calibraciones.

| Archivo en el runtime | SHA256 |
|---|---|
| `manipulation_kinematics/lib/libs2_arm_kinematics.so` | `2a41cf5520672c9dcbd1c532eff775b4ce6d9ff1e100485d6ca7ba8174ad251c` |
| `manipulation_kinematics/lib/libs2_head_kinematics.so` | `ba3707df647ee435041de713e6dabe451fd1bb59795b783179ec529901855866` |
| `manipulation_kinematics/lib/libs2_leg_kinematics.so` | `0de5bc0bbd7469693e23eb4c58c0fbb1012fc5063ecd7a2184a4886eab6a1fe7` |
| `manipulation_common/lib/libgeometric_primitive_set.so` | `6381100d2f4b66d262145d508594d0280a616b640d4e6c8c960416e25e678803` |

La inspección estática de constructores y `SupportFunction` (`0x96c0`) distingue:
tipo3 = segmento dilatado por su radio; tipo2 = elipsoide con semiejes;
tipo5 = envolvente convexa de puntos dilatada por un radio. No se confunden
radios con diámetros ni semiejes con dimensiones completas.

- Brazo: cuatro cápsulas con segmentos de296/220/76/80mm y radios55/50/50/50mm.
  Los otros tres elementos del array usan constructor por defecto: no son
  geometrías reconstruidas del CAD y no se eliminan piezas del modelo por ello.
- Cabeza: semiejes110/130/85mm, traslación local[20,90,0]mm. Falta registrar ese
  marco y su cinemática calibrada contra la cabeza del CAD.
- **`s2_leg` no corresponde al elevador de esta unidad.** Tiene seis entradas
  con nombres HipRoll/HipPitch/Knee. El YAML de Cruzr declara
  `cruzr_s2_lifter` y `cruzr_s2_waist`; sus archivos encontrados son `.a`,
  no las bibliotecas S2 leg/waist que pueden coexistir en el runtime.
- S2Clamp izquierda/derecha: cinco puntos y radio10mm. Un extremo está a
  Z=−94mm/+94mm, con cuatro puntos en Z=0, X=±35mm, Y=±50mm. Los defaults
  repetidos en las tres bibliotecas coinciden exactamente.

### Resultado de la cobertura aislada

La comparación conserva todos los triángulos del CAD de `L_hand_link.STL` y
`R_hand_link.STL`. Usa la cadena fija muñeca→sensor→útil de los dos URDF
archivados, expresada como `p_native_tool = T @ p_CAD_tool`, **suponiendo que
la primitiva está anclada al marco útil nativo**. Ese anclaje activo y el montaje
físico no se acreditan con esta operación.

| Lado | Vértices únicos examinados | Fuera de S2Clamp aislada | Máximo exceso |
|---|---:|---:|---:|
| Izquierdo | 4.920 | 2.167 | 44,395835mm |
| Derecho | 4.919 | 2.174 | 44,394548mm |

Se mide distancia a la envolvente convexa de los cinco puntos, menos el radio;
el interior del sólido cuenta como contenido. Se guarda un vértice testigo
por lado. **No equivale a una colisión ni demuestra que Motion omita esas
piezas:** parte de ellas puede estar cubierta por cápsulas de la muñeca.
Sí impide reemplazar el CAD completo por esa única S2Clamp sin comprobar la
unión. No se recortaron esas piezas ni se aplicaron excepciones a los54pares.

### Reproducir sin robot

Con copias privadas que mantengan las rutas `opt/walker/`:

```bash
.venv/general-home/bin/python scripts/teleoperation/audit_native_collision_geometry.py \
  --geometry-root /ruta/archivo-geometria/runtime \
  --frames-root /ruta/archivo-marcos/runtime \
  --output /ruta/privada/nuevo-native-geometry-audit.json

CRUZR_GEOMETRY_ARCHIVE=/ruta/archivo-geometria/runtime \
  .venv/general-home/bin/python -m unittest discover \
  -s scripts/teleoperation -p test_native_geometry.py -v
```

Cinco pruebas pasan, incluyendo los binarios archivados, coherencia de constantes
entre builds, rechazo de hash desconocido, interior de sólidos y esquinas que
quedan fuera de una dilatación esférica aunque entren en una caja ampliada.
El informe incluye hashes de binarios, código, URDF y mallas y rechaza cambios
durante la lectura. Sin la variable de archivo privado, la prueba de extracción
real se omite explícitamente; las otras cuatro no requieren binarios del proveedor.

Evidencia: `../Humanoide-vla-evidence/20260911T063949Z_NATIVE-COLLISION-INTERFACES/`
(ruta desde la raíz del repositorio). `runtime-manifest.json` recoge procedencia
y hashes; `native-geometry-audit.json` conserva datos/testigos; `before/` y
`after/` respaldan documentos y fuentes. Registro y reversión ANL-01.
Estado: auditor instalado sólo como fuentes PC; sin geometría nueva instalada,
cargada ni probada físicamente en Motion.

**Reanudación concreta:** identificar selección y marcos activos; comprobar
cobertura de muñeca+abrazadera y representación real del elevador; después
resolver interfaces internas sin quitar protección frente al torso. Continúan
pendientes contrato de ejecución, seguimiento/parada y ensayo del HOME general.

**Ampliación 2026-09-11:** se recuperó conexión, se inspeccionaron primitivas
nativas/tarea JSON y se añadieron comprobación de progreso independiente y
captura/análisis pasivos. 90 pruebas pasan; modelo/ensayo físico siguen pendientes.
Lectura bajo E-stop: principal `1`, servo `0`, cero muestras articulares.
[Evidencia y límites actualizados](CRUZR_HOME_CAPTURA_Y_PROGRESO_INDEPENDIENTE.md).

**10-09-2026, Europe/Madrid. VERIFICADO en archivos y emulación; ejecución física
PENDIENTE.** Esta intervención avanza sobre el planificador general. No instala
trayectorias, no cambia protecciones y no modifica los perfiles operativos de 20 s.

## Resultado de la representación

Se conserva el CAD suministrado y se genera una representación derivada sólo en
memoria. De las 18 geometrías que requerían una envolvente completa, quedan 11:

| Piezas | Corrección comprobada |
|---|---|
| `lifter_pitch_1_link`, `L_elbow_roll_link` | Separar componentes cerrados que compartían aristas. Se conserva exactamente el multiconjunto de triángulos. |
| `lifter_base_link`, ambos `elbow_yaw_link` y ambos `wrist_roll_link` | Unir vértices separados por errores numéricos de 3,73–8,33 nm. Se conservan todos los triángulos y sólo se acepta el resultado si todos los componentes quedan cerrados. |

El límite del segundo método es **10 nanómetros = 0,00001 mm**, no 10 mm ni
un margen de fabricación. La desviación máxima medida se descuenta de las
distancias de cada par y se incluye en las cotas de desplazamiento. Una grieta
mayor o una pieza que siga abierta conserva su envolvente. No se rellenan
agujeros arbitrarios ni se eliminan tornillos, patitas o caras pequeñas.

La implementación utiliza la separación topológica de
[trimesh](https://trimesh.org/trimesh.html), sin reparación implícita de agujeros.
Su correspondencia con la pieza física sigue siendo una cuestión diferente de
que el archivo sea matemáticamente cerrado.

**Siguen registrados 54 conflictos de geometría/margen** en HOME y ambas
referencias PICO. La mejora sí cambia las distancias de varios pares, pero no
reduce ese recuento con el margen de 2 mm:

- 30 pares pertenecen a chasis/ruedas y su separación es invariable durante un
  movimiento de los veinte ejes si base y articulaciones auxiliares permanecen
  fijas. El informe los identifica; no los borra ni acredita el montaje físico.
- 24 pares cambian con articulaciones controladas: uniones del elevador,
  cintura, torso/cabeza, hombros, codos y muñecas. En HOME, ocho tienen distancia
  positiva pero menor o igual al margen; los otros dieciséis dan cero en la
  representación. En PICO son seis y dieciocho, respectivamente.
- Ninguno de esos 54 pares lleva `hand_link` en su etiqueta. Eso describe sólo
  estas tres posturas sintéticas; no demuestra separación de las abrazaderas
  durante cualquier camino.

Una unión mecánica diseñada con holgura inferior a 2 mm puede fallar el margen
sin estar chocando. Tampoco basta observar que un solapamiento aparece en HOME
para ignorar todo ese par durante una rotación. Para cerrar estas interfaces
necesitamos una geometría de colisión que distinga su zona interna de montaje
de la superficie exterior, o una especificación verificable de contacto permitido
y dominio articular. No se encontró esa especificación en los archivos recogidos.
La última búsqueda adicional se interrumpió por pérdida de conexión; no se afirma
que no exista en otros archivos del proveedor.

## Vista 3D revisable

```bash
.venv/general-home/bin/python scripts/teleoperation/render_home_geometry_review.py \
  --output /tmp/cruzr-home-geometry-review.html
```

El HTML es autónomo, sin CDN, sin conexión al robot y sin controles de ejecución.
Permite girar/ampliar cada par, cambiar HOME/PICO, mostrar el resto del robot y
alternar **superficies originales** con **geometría del cálculo**. Conserva las
mallas completas; los buffers de dibujo usan float32, mientras las comprobaciones
geométricas siguen usando float64. La vista no es un instrumento de medición.
El archivo contiene CAD del proveedor: guardarlo con la evidencia privada, fuera
de Git. Se comprobó su renderizado en Chrome mediante captura local.

## Qué se verificó de Motion

Se descubrieron contenedores y se copiaron archivos mediante lecturas SSH por
Wi-Fi, sin escrituras remotas. Motion seguía en v0.2.0 y la biblioteca MetaMove
conservaba SHA256 `bfeab1c7a295b58cd96fddd20916fc3f7fe16bd8c8ad1e77720f48aad34ccc69`.
En la lectura disponible, el paro principal publicó `1`. El topic de actuadores
estaba anunciado, pero la suscripción de siete segundos no recibió una muestra.
Anunciado no equivale a estar publicando ni a estar listo para moverse. Las
consultas posteriores a `192.168.11.2:22` terminaron por tiempo de conexión.

### Interpolación: comprobación del código numérico

`ComponentGroup::MoveTo` llama al interpolador cúbico, envía comandos articulares
y contiene llamadas a supervisión de seguridad. El overload examinado prepara
velocidades inicial/final cero. Se emuló únicamente su función numérica mediante
[Unicorn](https://www.unicorn-engine.org/docs/tutorial.html): memoria aislada,
hash exacto, límites de instrucciones/tiempo y rechazo de salida de la rutina.
No se cargó la biblioteca con `dlopen`, ni se ejecutaron constructores, ROS,
controladores o instrucciones de sistema.

- Archivo: `manipulation_planners/lib/libinterpolation_path_planner.so`.
- SHA256: `1267e370614d5350706caa061a24c162e3333248b9b1af74b8ea319a3d5ee329`.
- Rutina numérica en offset `0x37c0`.
- 1.312 casos, vectores de 1/2/7/20 ejes, cuatro duraciones y extremos tanto
  estacionarios como con velocidad. Error máximo frente a Hermite analítico:
  `2.6645352591003757e-15` rad.

Con extremos estacionarios, la ley es:

```text
u = t / T
q(t) = q0 + (q1 − q0) · (3u² − 2u³)
v_máxima = 1,5 · |q1 − q0| / T
a_máxima = 6 · |q1 − q0| / T²
```

Es cúbica. La quintic anterior es otra ley temporal. Ambas recorren el mismo
segmento geométrico si todos los ejes comparten exactamente el mismo progreso,
pero tienen distinta velocidad/aceleración. La cúbica tiene saltos de aceleración
al enlazar reposos: no se le atribuye un límite global finito de jerk.

El planificador permite ahora `--timing-law cubic-rest`, con caps de diseño de
0,3 rad/s y 0,35 rad/s². El valor de jerk global se informa como `null`.
La opción por defecto sigue siendo `quintic`; ninguna de las dos es ejecutable
desde esta herramienta. Un Hermite con velocidades de paso no nulas puede
salir del segmento que une los extremos; no se aplica este certificado a él.

También se encontró `FollowJointSpaceTrajectory`, OMPL y optimización en las
bibliotecas/configuraciones instaladas. Su existencia no acredita que usen el
CAD de abrazaderas ni una escena fresca. El seguidor incluye recálculo de
duraciones y otras interpolaciones. No se utiliza como sustituto automático
del `MoveTo` analizado ni se invoca un servicio que planifica y ejecuta a la vez.

**Lo que la emulación no valida:** despacho real de grupos, reloj común entre
brazos/cuerpo/cabeza, origen de la consigna inicial, seguimiento del servo,
actuación del supervisor, estabilidad y distancia de parada. No se ha construido
un adaptador físico general ni se presenta esta prueba como una prueba del robot.

### Límites y marcos: datos de configuración encontrados

`cruzr_s2_robot_description.yaml` declara 500 Hz; elevador y cintura tienen
1,57 rad/s y 10 rad/s². El URDF de planificación instalado especifica 0,78 rad/s
en esos ejes, mientras el CAD completo tenía cero. La auditoría conserva ambas
fuentes y toma el menor límite positivo sólo como dato de comparación: no modifica
los límites ni acredita dinámica real. También informa la intersección de los
límites de posición, sin sustituirla automáticamente en el planificador.

El URDF nativo recogido tiene 25 enlaces, no contiene cabeza y utiliza marcos
distintos para sensores/herramientas. Bajo la hipótesis explícita de alinear
`mobile_base_link` con `base_link`, los marcos comunes de brazo están próximos
en las tres referencias; el sensor izquierdo difiere aproximadamente 180°.
Los centros de herramienta respecto a la muñeca son aproximadamente
`[0, 0.08862, +0.094] m` a izquierda y `[0, 0.08862, -0.094] m` a derecha.
La configuración YAML usa 0,089 m en su segunda coordenada: diferencia de 0,38 mm.

La auditoría calcula matrices explícitas `cad_tool_to_native_tool`, con la
convención `p_native = T @ p_CAD`. Estas matrices resuelven la conversión entre
esos archivos; no son una medida del montaje real ni deben copiarse como `R`
del sensor sin respetar sus marcos. No se ha sustituido el marco del CAD por
el nativo ni se ha alterado la orientación de la abrazadera.

## Reproducción y evidencia

Instalar las dependencias fijadas sólo en `.venv/general-home`, según el
[README](../../scripts/teleoperation/general_home/README.md). Se añadió
`unicorn==2.1.4`; el entorno tiene nueve paquetes fijados. Con una copia local
de los archivos del runtime, las auditorías son reproducibles sin robot:

```bash
.venv/general-home/bin/python scripts/teleoperation/audit_home_runtime_contract.py \
  --runtime-root /ruta/evidencia/runtime --output /tmp/runtime-contract.json

.venv/general-home/bin/python scripts/teleoperation/audit_motion_interpolation.py \
  --binary /ruta/evidencia/runtime/opt/walker/manipulation_planners/lib/libinterpolation_path_planner.so \
  --output /tmp/native-interpolation.json

.venv/general-home/bin/python scripts/teleoperation/cruzr_plan_home.py \
  --plan --state /ruta/estado.json --scene /ruta/escena.json \
  --timing-law cubic-rest --output /tmp/home-cubic.json
```

Las salidas deben ser nuevas. Los JSON/HTML incluyen procedencia y hashes; no
son autorizaciones. Evidencia de esta intervención:
`../Humanoide-vla-evidence/20260910T142312Z_HOME-GEOMETRY-MOTION-QUALIFICATION/`.
Incluye backups `before/`, copias runtime y sus manifiestos, análisis topológico,
`model-bounded-weld.json`, `runtime-contract-audit.json`,
`native-interpolation-audit.json`, vista 3D y verificación final.

## Punto de reanudación

1. Cerrar la representación de las interfaces móviles y la cobertura de las
   once mallas aún abiertas; confirmar el registro físico del modelo derivado.
2. Al restablecer la conexión, recoger estado articular fresco y comprobar el
   contrato de despacho completo. No liberar el E-stop para obtener datos por
   decisión automática del planificador.
3. Preparar una prueba acotada desde una postura y un recorrido ya revisados,
   registrar consignas/medidas con tiempo, verificar seguimiento y margen de
   parada. No sirve un `ACTION_SUCCEEDED` aislado ni provocar contacto para medir.
4. Habilitar sólo el dominio comprobado; resolver aparte el HOME interno del
   arranque. Un ensayo PICO→HOME no valida todos los estados 20D.

Registro y reversión: ANL-01 en [SYSTEM_CUSTOMIZATIONS.md](../SYSTEM_CUSTOMIZATIONS.md).
No hay nada que instalar o recargar en el robot por estos cambios.
