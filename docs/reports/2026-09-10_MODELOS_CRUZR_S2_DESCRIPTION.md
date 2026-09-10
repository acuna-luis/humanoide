# Modelos de descripción 3D del Cruzr S2

**VERIFICADO local, 2026-09-10, Europe/Madrid.** Revisión solicitada por el
usuario. No se modificaron los paquetes recibidos, no se instaló nada ni se
conectó al robot. Sólo se registra el hallazgo en documentación.

**Distribución local:** ambos paquetes se conservan como entradas originales
del proveedor, excluidas de Git mediante `.gitignore` (130 archivos, unos
107 MB). Un clon del repositorio requiere recuperarlos del paquete del proveedor
o de la copia externa y comprobar los hashes indicados más abajo. La limpieza
del índice no modifica ni elimina sus archivos. El manifiesto completo previo
está en `../Humanoide-vla-evidence/20260910T122441Z_COMMIT-CLEANUP/vendor-files-before.json`.

## Finalidad y diferencias

Son dos variantes de un paquete ROS 2. Ambas declaran nombre interno
`cruzr_s2_description`, versión `0.0.1`, mantenedor de dominio UBTECH y licencia
Apache 2.0; el URDF identifica una exportación de SolidWorks. Esos metadatos
no demuestran por sí solos la procedencia o vigencia del montaje físico.

| Carpeta | Extremos de los brazos | Contenido |
|---|---|---|
| [`cruzr_s2_description`](../../cruzr_s2_description/) | Pinza PGC con dos dedos deslizantes por lado | 64 archivos, 59 STL, 52 enlaces y 51 uniones |
| [`cruzr_s2_description_splint/cruzr_s2_description`](../../cruzr_s2_description_splint/cruzr_s2_description/) | Una abrazadera rígida por lado | 66 archivos, 61 STL, 48 enlaces y 47 uniones |

Enlaces/uniones incluyen elementos pasivos y fijos: esos recuentos no son
el número de motores. Hay mallas almacenadas que no utiliza el URDF.

- `meshes/`: superficies STL de piezas del robot y efectores.
- `urdf/`: unión entre piezas, ejes, transformaciones, límites articulares,
  masas/inercia y geometrías visuales/de colisión.
- `launch/display.launch.py` y `config/rviz/`: comprobación `check_urdf`, visor
  RViz, coordenadas y controles para variar articulaciones del modelo.
- `package.xml` y `CMakeLists.txt`: dependencias e instalación del paquete.

Permiten visualizar posturas, calcular posiciones de piezas y aportar modelos
a simuladores o comprobadores de colisiones. El URDF incluye opciones MuJoCo,
pero estas carpetas no contienen un escenario/controlador de simulación completo.
Tampoco contienen las trayectorias HOME/READY/ENTRY ni acciones Motion.
El lanzador publica estados articulares sintéticos y TF para el visor;
no contiene controladores de actuadores.

La comparación de hashes de todos los archivos comunes muestra una sola
diferencia: el URDF. `splint` añade `L_hand_link.STL` y `R_hand_link.STL`.
En su árbol sustituye las dos bases PGC y cuatro dedos por `L/R_hand_link`,
fijos a `L/R_sixforce_link`. Los enlaces/uniones comunes son semánticamente
idénticos: no cambia el torso ni los brazos al elegir esa variante.

Las mallas de abrazadera ocupan **100 × 70 × 132,62 mm** en sus ejes locales,
sin margen añadido; contienen 9.997 y 9.999 triángulos. Su representación
muestra cara rectangular, soporte y fijación. `splint` es la variante pertinente
para estudiar abrazaderas; esta revisión no recalifica su correspondencia
exacta con las piezas montadas en la unidad.

El modelo sitúa el origen de cada enlace de abrazadera respecto al sensor:

| Enlace | XYZ en `sixforce`, mm | RPY aproximados, grados |
|---|---|---|
| `L_hand_link` | −94; 0; +11,5 | 0; −90; 180 |
| `R_hand_link` | +94; 0; +11,5 | 180; −90; 180 |

Son valores del modelo, no mediciones nuevas. El origen de `hand_link` no se
identifica automáticamente con el punto P del centro de almohadilla definido
durante las mediciones físicas; comprobar esa correspondencia antes de reutilizarlos.

## Relación con lo ya disponible y detalles de integración

Se comparó con `runtime.urdf` y `runtime-meshes.zip` de
`../Humanoide-vla-evidence/20260908T115359.543954Z_PICO-HOME-CHECK/`.
**Las dos mallas de abrazadera son idénticas byte a byte a las extraídas del
robot.** Sus enlaces y uniones de montaje también coinciden. No aportan una
geometría nueva de abrazadera que antes faltase en esa captura.

El URDF completo difiere del runtime: incluye más ruedas/piezas pasivas y
enlaces intermedios de cabeza/hombros; cambian algunas relaciones del árbol
y la denominación de la unión torso/cintura. Antes de sustituirlo hay que
comparar la cinemática resultante y las referencias articulares.
`audit_pico_home_open_path.py` y `audit_internal_home_open_path.py` usan su
`--snapshot-dir`, URDF/ZIP y envolventes archivadas, no estas carpetas
automáticamente. Disponer de STL no convierte sus comprobaciones basadas
en envolventes en comprobaciones exactas de superficies.

Detalles encontrados:

- Ambos paquetes tienen el mismo nombre ROS: elegir una variante por workspace
  para evitar duplicar la identidad del paquete.
- El lanzador usa `joint_state_publisher_gui`, dependencia omitida en ambos
  `package.xml` (sí declaran `joint_state_publisher`). No se instaló para esta revisión.
- RViz tiene `Collision Enabled: false`: muestra la geometría visual por
  defecto. No elimina los bloques de colisión ni altera protecciones del robot.
- Faltan bloques `<collision>` en seis enlaces de ambos modelos:
  `head_base_link`, `head_yaw_link`, `L/R_arm_base_link` y
  `L/R_shoulder_pitch_link`. Algunos son referencias intermedias; revisar
  cobertura antes de considerar un análisis de todas las piezas completo.
- No se compiló ni lanzó ROS/RViz. Para usar el GUI, preparar una sesión ROS
  aislada de la telemetría real del robot.

## Evidencia y conservación

Parseo XML y árbol conectado sin ciclos ni hijos con varios padres correctos;
todas las mallas referenciadas existen. Comparación completa de hashes y
enlaces/uniones; lectura de STL y representación local. No hubo estados ROS
publicados ni trayectorias ejecutadas.

| Fuente | SHA256 |
|---|---|
| URDF base | `06083544f182b9336ad6f40040a5a79955c19897cb0b78d9f597888dce0c2fa0` |
| URDF splint | `e1f2633a4d4c06d36c18f6a86895d8a645827ad0171b2700159035f7db242e63` |
| Runtime archivado, 08-09 | `26182d7abd1f5499d95a9bf753ef90d93fbee6db73906404e3f7ea2bb0763775` |

Evidencia y manifiesto de los 130 archivos:
`../Humanoide-vla-evidence/20260910T112000Z_DESCRIPTION-REVIEW/`.
Las carpetas recibidas siguen intactas y sin commit. No hay instalación que
revertir; la evidencia conserva los documentos anteriores a esta revisión.
Punto de reanudación, si se solicita integrarlos: elegir `splint`, contrastar
cinemática/montaje y preparar visualización o análisis aislado.
