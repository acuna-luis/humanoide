# Salida con muñeca fija: contraste offline

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
