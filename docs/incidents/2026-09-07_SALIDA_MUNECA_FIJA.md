# Salida con muñeca fija: contraste offline

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
