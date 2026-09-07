# Salida con muñeca fija: contraste offline

## Cierre condicional del bloque de pares cruzados

`audit_fixed_wrist_cross_pair_bounds.py` verifica hashes del generador y
geometría del informe AABB, su contrato de 121 posturas por dirección, y
descendencia de cada link respecto al hombro rotado. Para cada par aplica
min(d_AABB)-R·0,005/2; R es radio máximo de las esquinas de la caja local
respecto al pivote, envolviendo todos los puntos de la geometría representada.
La distancia AABB en cada muestra es una cota inferior de la separación de
las superficies incluidas; se resta el desplazamiento máximo entre muestras.

459 de 462 pares dan cota positiva. Los tres restantes son exactamente
L_roll–torso, R_roll–torso y R_yaw–torso, refinados en el apartado STL con
cotas positivas condicionales. Así, los pares cruzados representados quedan
separados bajo las hipótesis rígidas/numéricas, NO el robot físico completo.
No se obtiene porcentaje global de seguridad a partir de este recuento.

Evidencia externa `20260907_fixed_wrist_cross_pair_bounds.json`; fuentes y
resultados por par preservados. Se repiten seis tests de las primitivas AABB
y cota inter-muestras, correctos. Sin conexión ni movimiento.

### Pendientes que este resultado no cierra

- Abrazaderas y montaje real, incluido soporte/patitas frente a robot.
- Pares internos de cada brazo y geometría propia shoulder_pitch ausente.
- Postura/escena reales, correspondencia del modelo y error acotado.
- Seguimiento de ejes retenidos, distancia de parada y energía/carga.
- Inicio/rearme y retorno real, distintos del conjunto ideal de posturas.

No repetir el barrido de los mismos 462 pares sin cambiar hipótesis; priorizar
estas lagunas de cobertura. Las diagonales L174/R178 no son cotas inferiores
de separación global y no deben consumirse como margen de frenado.

## Cota entre muestras para los tres pares refinados

`audit_shoulder_between_samples.py` comprueba hashes de geometría/kernel y
que cada link sea descendiente del único hombro rotado y torso no lo sea.
Calcula R como radio máximo de vértices respecto al pivote (cota por exceso
del radio al eje). Para paso máximo h=0,01 rad, todo punto de un triángulo
se desplaza como máximo R·h/2 desde la muestra más cercana. La distancia
entre superficies es Lipschitz respecto a ese desplazamiento.

Con d(theta)>=min(d_muestras)-R·h/2 se obtienen:

| Par contra torso | Reserva entre muestras | Cota inferior condicional |
|---|---:|---:|
| L_shoulder_roll | 0,594 mm | 10,621 mm |
| R_shoulder_roll | 0,594 mm | 10,620 mm |
| R_shoulder_yaw | 1,695 mm | 18,501 mm |

Es una cota del intervalo continuo PARA ESTAS SUPERFICIES RÍGIDAS y este
único giro, suponiendo correctas las distancias numéricas. No incluye error
numérico certificado, contención de sólidos, discrepancia de montaje/mesh,
resto del robot, abrazaderas, escena ni frenado. No equivale a holgura física
certificada ni validación continua del robot completo. La vuelta ideal tiene
el mismo conjunto de estados, no se demuestra equivalencia con el controlador.

Tres tests pasan (cota conocida, rejilla irregular, rechazo de entradas);
evidencia externa `20260907_shoulder_between_samples.json` con hashes.
Sin robot, red, movimiento ni cambios de seguridad.

## Extensión STL a 61 posturas por par

Ejecutado `audit_fixed_wrist_shoulder_witness.py --samples 61`: 183 cálculos
de distancia entre superficies, tres pares hombro–torso, shoulder_roll 0…-0,6
rad en pasos de 0,01 rad. Otro brazo y resto de articulaciones a cero sintético.
Las tres distancias mínimas permanecen en el inicio (ángulo 0):
L_roll 11,214783 mm, R_roll 11,213466 mm y R_yaw 20,195897 mm.
No se encontró distancia cero en las muestras. La vuelta ideal referencia
las mismas muestras en orden inverso, no repite ni verifica el controlador real.

Evidencia externa `20260907_fixed_wrist_shoulder_path_61.json`: cada postura,
distancia, triángulos, estadísticas BVH y hashes; archivo nuevo sin sobrescribir
testigos iniciales. Cinco casos y 300 referencias del kernel pasaron al inicio;
py_compile y git diff --check correctos.

Este resultado refina sólo los tres avisos AABB y no cubre intervalos entre
muestras, contención de sólidos, brazos consigo mismos, útil real, geometría
faltante, escena, seguimiento, parada ni márgenes físicos. No habilita el
movimiento. Sin conexión al robot ni cambios remotos.

## Refinamiento STL de los tres testigos iniciales

Durante revisión se encontró defecto en triangle_distances_batch de
analyze_vla_clearance_guards_e6_0d.py: distancia de vértices a caras y aristas
entre sí no detectaba todos los cruces arista–interior de cara. Contraejemplo
A=[(0,0,0),(4,0,0),(0,4,0)], B=[(1,1,-1),(1,1,1),(2,1,1)] devolvía 1
en vez de 0. Corregido con cruce segmento/plano y pertenencia al triángulo,
en ambos sentidos. Cinco casos deterministas pasan y 300 casos aleatorios
coinciden con referencia escalar ampliada mediante resolución lineal independiente.
Los históricos de distancia triángulo/malla que usaban esa rutina NO quedan
revalidados por esta corrección: deben regenerarse antes de usarlos como evidencia
de separación. No afecta por sí mismo al filtro AABB ni a punto–triángulo.

Nuevo audit_fixed_wrist_shoulder_witness.py calcula sólo los tres testigos
de postura URDF cero sintético con BVH y rutina corregida:

| Par frente a torso_link | Distancia entre superficies |
|---|---:|
| L_shoulder_roll_link | 11,2148 mm |
| R_shoulder_roll_link | 11,2135 mm |
| R_shoulder_yaw_link | 20,1959 mm |

No intersección de superficies encontrada por el cálculo en estos testigos.
No se realizó test de contención de sólidos ni recorrido completo, tolerancias,
flexión o correspondencia física. No autorización de movimiento. Evidencia
externa 20260907_fixed_wrist_shoulder_witness.json con hashes, IDs de triángulos
y estadísticas. Sólo cambios locales, sin robot/red/despliegue.

## Ampliación brazo–cuerpo/brazo contrario

`audit_fixed_wrist_arm_body.py` recorre salida y vuelta de cada hombro por
separado, otro brazo a cero sintético: 242 muestras por lado y 231 pares
de links por lado (siete links de brazo/sensor frente a 26 de cuerpo y siete
del otro brazo). No representa estado actual ni geometría de abrazadera.

Resultado de AABB mundiales: solapamiento/contacto de envolventes para
L_shoulder_roll_link–torso_link, R_shoulder_roll_link–torso_link y
R_shoulder_yaw_link–torso_link. El primer testigo está en ángulo cero.
Los restantes 230 pares L y 229 R presentan separación positiva en las
muestras. NO se eliminan los pares próximos a la fijación ni se etiqueta
su contacto como permitido. Requieren contraste geométrico más fino.

Faltan mallas propias L/R_shoulder_pitch_link. No se comprobó brazo consigo
mismo, abrazaderas, entorno, barrido continuo, errores ni frenado. Por ello
no es una validación del brazo completo pese a ampliar su cobertura.

Tres tests del cálculo AABB pasan (separación, contacto/solapamiento, entradas
inválidas). Evidencia externa `20260907_fixed_wrist_arm_body.json`, hashes de
fuentes incluidos. Sin robot/red/movimiento. Próximo refinamiento: distinguir
solapamiento de cajas de envolvente de intersección de mallas en los tres
pares identificados; no ignorarlos para producir un aprobado.

## Resultado observado en el modelo

`audit_clamp_fixed_wrist_exit.py` evalúa por separado cada hombro roll desde
cero sintético hasta -0,6 rad, 121 muestras, todos los demás ejes fijos a cero.
Es el tramo inicial histórico, no una orden ejecutable ni postura real.

La transformación wrist_pitch_link→sixforce_link permanece invariante:
máxima variación de componente 4,44e-16 L y 5,55e-16 R. Esto coincide con
inv(G·A)·(G·B)=inv(A)·B para movimiento rígido común aguas arriba.
No significa que la holgura inicial sea positiva ni que el robot físico
retenga exactamente los demás ejes bajo carga.

Distancia mínima del ORIGEN DEL SENSOR a las AABB del cuerpo:

| Lado | Inicio | Final | No decrece en las muestras |
|---|---:|---:|---|
| L | 228,168 mm | 518,189 mm | Sí |
| R | 219,961 mm | 518,182 mm | Sí |

No es distancia de la patita ni barrido continuo del brazo completo. El torso,
base y demás joints se mantienen a cero sintético; no se incluye escena real.

## Medidas del operador

L=174 mm, R=178 mm, diagonal patita→punto del cuerpo identificado por operador
como más próximo. Fotos 1–3 L, 4 R; hashes conservados en contrato de montaje.
Son puntos físicos diferentes del origen de sensor: no restar estas medidas
de las distancias de la tabla como si fuera error de calibración. Falta registro
de extremos en el modelo y postura sincronizada; residual no calculable.
Una distancia de un par de puntos no prueba una cota inferior de separación
entre todas las superficies. No completar transformación ni incertidumbre
a partir de esa única longitud.

## Alcance y reanudación

Resultado útil: candidato con geometría interna rígida constante y separación
sensor–cuerpo creciente al muestrear. Pendientes: holgura inicial fuera de la
fijación prevista, montaje, cobertura del brazo/entorno, volumen continuo,
postura actual, seguimiento y parada. No aprobación física.

Evidencia: raíz externa Humanoide-vla-evidence,
`20260907_fixed_wrist_exit.json`, incluye hashes de URDF, SDK y código.
Sin red, publicación, cambios de modos ni movimiento. No repetir mediciones
con robot energizado/paros liberados.
