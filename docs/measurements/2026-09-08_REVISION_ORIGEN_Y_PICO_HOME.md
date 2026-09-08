# Revisión del origen instalado y comprobación PICO→HOME

2026-09-08. Resultado: revisión del origen en el modelo instalado completada;
recorrido comprobado parcialmente con márgenes condicionados, NO aprobado para
movimiento físico. Ningún objetivo, cambio de modo, reinicio ni movimiento enviado.

## Hallazgo que sustituye la suposición anterior

Se redescubrió Motion y se leyó su URDF y las mallas instaladas desde
`/opt/walker/cruzr_s2_description/share/cruzr_s2_description/` en el contenedor
`walker-motion.manipulation_robot_app-1`.
El URDF instalado SHA256 `26182d7abd1f5499d95a9bf753ef90d93fbee6db73906404e3f7ea2bb0763775`
difiere del SDK archivado. Contiene **L_hand_link y R_hand_link** en lugar de
las pinzas PGC históricas; también hay cambios de estructura y geometría del
robot. Por tanto, la afirmación anterior de que no había geometría de las
abrazaderas no describe el modelo actualmente instalado.

En las mallas instaladas, cada sensor es un cilindro de diámetro 45 mm,
con Z entre −26,5 y 0 mm. El plano terminal delantero está en Z=0 del marco
sixforce_link. La transformación fija de la mano en ese marco tiene origen:

| Mano | X mm | Y mm | Z mm |
|---|---:|---:|---:|
| Izquierda | −94 | 0 | 11,5 |
| Derecha | +94 | 0 | 11,5 |

El origen de la malla de mano está en el plano frontal Z_hand=0 y las mallas
abarcan 100 × 70 × 132,617 mm. La orientación del marco de mano del proveedor
NO es automáticamente la del marco de la ficha (+Z hacia contacto y +Y patitas).
Se recalculó FK con todos los joints necesarios presentes en la muestra nueva;
los sentidos aproximados de los sensores coinciden con la revisión anterior.

**Cerrado en el modelo:** origen, ejes y transformaciones fijas identificados.
**No sustituido por una certeza física:** la cara externa fotografiada aún no
está registrada inequívocamente con esa cara del CAD; la alineación axial
comunicada daría 0, mientras el origen de mano vendor está a 11,5 mm. Ambos
quedan contemplados en el intervalo 0–40 mm mantenido para el análisis. La
medida radial 95 mm es compatible con 94 mm nominales y error declarado 2 mm.

## Datos del usuario incorporados

- 95 mm P–eje por lado, misma altura y alineación longitudinal con cara externa.
- Orientaciones cualitativas bilaterales confirmadas por técnico, según usuario.
- Error lineal declarado de 2 mm y contención de todas las piezas en la geometría
  declarada. Esto no establece un error angular en grados ni el seguimiento del robot.
- Se actualiza el contrato de observaciones sin asignar una transformación ROS
  validada a `mounts`: no hay publicador ni exportación de colisión habilitados.

El nominal del CAD tiene profundidad 132,617 mm, superior a 130+2 mm por
0,617 mm. El cálculo usa el mayor valor y añade margen; no recorta el CAD para
forzarlo a coincidir. La asociación exacta de sus superficies con el útil real
sigue sin demostración completa.

## Recorrido comprobado

Muestra fresca 11:53:59 UTC, clasificada OTHER (no HOME/READY), reposo y gate de
actuadores/consignas correcto. Propuesta offline de dos tramos: brazos a cero
con cuerpo conservado, después cuerpo a cero; 20 ejes dentro de límites.
Curva quintica con reposo en extremos, duración matemática **25,870372 s**,
velocidad de diseño 0,15 rad/s y aceleración 0,5 rad/s²; valores de diseño,
no límites dinámicos certificados ni equivalencia con un controlador instalado.

Chequeo de abrazaderas contra links del robot y entre sí, con cajas orientadas:
2.002 muestras (1.001 por tramo), cotas continuas por desplazamiento máximo de
puntos entre muestras; tres pares se refinaron con 2.001 muestras del tramo.
Se usó toda la incertidumbre axial 0–40 mm y margen lineal 2 mm, sin inventar
un único origen. El volumen lleno incluye las patitas y todo el soporte por
la declaración de contención. Es deliberadamente más grande que las superficies.

Resultado condicionado: separación continua positiva de esos volúmenes frente
al resto del robot salvo sus propios sensores/wrist_roll/wrist_pitch. Los tres
pares de elevador refinados conservan cotas inferiores 11,41 / 10,09 / 8,69 mm.
Los solapamientos alrededor de las propias muñecas no prueban contacto real:
las cajas llenan huecos de montaje; se conservaron en el informe sin exenciones.

Se refinó mano vendor frente a wrist_pitch con distancias entre triángulos:
separaciones nominales ≈16,12 mm izquierda y 15,97 mm derecha en tres puntos.
Después, desplazando la malla al radial 95 mm y cubriendo todo el intervalo axial
con nueve muestras, cota Lipschitz entre ellas y cambio de wrist_roll a lo largo
del recorrido, las cotas inferiores de separación superficial son:

| Mano | Cota inferior condicionada tras margen lineal de 2 mm |
|---|---:|
| Izquierda | 1,28 mm |
| Derecha | 0,86 mm |

Estas cotas corresponden a superficies del CAD desplazado: **no demuestran
contención física del útil real en esa malla detallada**, ni validan contacto
con sus otras piezas de fijación. No incluyen error angular, deformación,
seguimiento/frenado, ni precisión del CAD del robot. Una distancia entre
superficies tampoco sustituye por sí sola un análisis de sólidos.

## Decisión y pendientes concretos

**No aprobar ni generar un ejecutor físico a partir de este resultado.**
La revisión del modelo no exige repetir las cotas ya dadas. Para cerrar una
ruta física faltan correspondencia del útil con la geometría detallada en la
zona de muñeca y sus apoyos, comprobación robot–robot/escena, y verificación de
interpolación y márgenes dinámicos del transporte de comandos. La incertidumbre
axial no impide hacer cálculos, pero deja un margen condicionado pequeño y no
resuelve por sí sola esas comprobaciones.

## Evidencia y reproducción

Directorio externo:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260908T115359.543954Z_PICO-HOME-CHECK/`.
Incluye captura de joints/actuadores, `runtime.urdf`, `runtime-meshes.zip`,
`home-proposal.json`, `geometry-check-1001.json`, `geometry-refinement.json` y
`origin-interval-mesh-check.json`, además de los scripts usados para refinarlos.
Las lecturas remotas sólo guardaron artefactos en el PC.

El checker versionado es
`scripts/teleoperation/check_pico_home_geometry_offline.py` (sólo offline).
Validaciones: cuatro comprobaciones analíticas de separación SAT; 3 tests del
modelo clamp, 8 del modelo simplificado y 3 del planificador offline pasan.
Los informes indican alcance y limitaciones, y conservan hashes de sus entradas.
