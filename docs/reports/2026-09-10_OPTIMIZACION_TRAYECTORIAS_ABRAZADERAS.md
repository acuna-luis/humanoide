# Revisión de tiempos y geometría con abrazaderas

Fecha: 10-09-2026. **VERIFICADO por cálculo offline; candidatos sin instalar.**

Los modelos recibidos sirven para revisar las trayectorias con abrazaderas.
La mejora que conviene estudiar primero es quitar la etapa de cuerpo de 3,75 s
cuando sus objetivos ya están exactamente alcanzados: PICO→HOME podría pasar
de **20 a 16,25 s**, un ahorro del **18,75 %**, conservando el recorrido nominal
de brazos y los máximos articulares calculados. La igualdad nominal no demuestra
que pueda quitarse una espera física de asentamiento; eso debe comprobarse en
el ejecutor antes de activar esta variante.

El resultado es un comparador reproducible, no una nueva tarea instalada.
Los XML operativos y sus generadores/ejecutor conservan sus hashes previos.
La corrección independiente del preflight, realizada durante esta revisión,
reconoce el HOME ya instalado y no cambia sus tiempos ni puntos de paso.

## Qué aportan las carpetas nuevas

Se comparó la cinemática de `cruzr_s2_description_splint` con el modelo runtime
archivado del 08-09, en 744 estados de las rutas nominales. La mayor diferencia
en el origen de cada abrazadera fue **0,027 mm a izquierda y 0,022 mm a derecha**;
orientación menor de **0,0023°**. Eso permite usar el paquete para representar
estos movimientos de brazos con buena correspondencia respecto al runtime
archivado. No prueba el montaje físico actual ni todos los estados posibles.

La cabeza presenta **4,6 mm** de diferencia entre modelos; no conviene sustituir
el URDF completo sin revisar esa discrepancia. Las mallas de abrazadera ya
coincidían con el runtime: no aportan una reducción nueva de los solapamientos.
Para este análisis se conservó la envolvente archivada completa, el intervalo
de origen de 0–40 mm y los 2 mm de error geométrico. La variante sin `splint`
representa pinzas con dedos, no el efector que se está usando.

[Revisión de paquetes y hashes](2026-09-10_MODELOS_CRUZR_S2_DESCRIPTION.md).

## Comparación PICO→HOME

La columna de separación es la menor **cota nominal calculada** entre las dos
abrazaderas y el torso a lo largo de cada alternativa, incluida la corrección
entre muestras. No es una distancia medida en el robot ni incluye frenado.
Los tiempos son sólo de movimiento: no incluyen preflight, preguntas ni red.

| Alternativa numérica | PICO cuerpo a cero | PICO cuerpo flexionado | Separación mínima al torso |
|---|---:|---:|---:|
| Actual, apertura roll −0,60 rad | 20,000 s | 20,000 s | 163,82 mm |
| Omitir etapas con objetivos exactamente iguales | 16,250 s | 20,000 s | 163,82 mm |
| Recoger cuerpo durante bajada de brazos abiertos | 16,250 s | 16,250 s | 163,82 mm |
| Apertura −0,50 rad; tiempos ajustados a máximos articulares actuales | 15,392 s | 19,143 s | 135,03 mm |
| Apertura −0,45 rad; mismos límites comparativos | 14,946 s | 18,697 s | 129,12 mm |

El ahorro al quitar la etapa del cuerpo sólo existe para la referencia
`pico_body_zero`. Con el cuerpo flexionado esa etapa sí tiene movimiento.
Tampoco se debe interpretar la tolerancia del clasificador de 0,02 rad como
igualdad exacta: el comparador conserva incluso movimientos de 0,001 rad.
Una implementación requiere comprobar objetivo/estado/velocidad frescos y
conservar el comportamiento de inicialización del HOME de arranque.

Reducir la apertura a −0,45 rad pierde aproximadamente **35 mm** respecto al
torso para ahorrar unos 1,3 s adicionales frente a omitir la etapa redundante.
Por eso no es la primera opción recomendada después del contacto anterior.
El mínimo global de todos los pares no locales permanece en **69,79 mm**, junto
al codo izquierdo, y ocultaría esta pérdida de separación al torso si sólo
se mirase una cifra global. Se conservan resultados por par y por etapa.

Recoger cuerpo y brazos simultáneamente mantiene los máximos individuales
calculados, pero cambia cargas combinadas, estabilidad y sincronización real.
Queda como alternativa de estudio, por detrás de eliminar una etapa inmóvil.

## HOME interno y otras trayectorias

El HOME interno abierto usa una primera apertura relativa de −0,4 rad, mientras
que el ejecutor PICO fija el roll en −0,6 rad. Se analizaron por separado.
Para HOME interno se probaron cuatro referencias: PICO y brazos abajo, cada
una con cuerpo flexionado o a cero. Los objetivos nominales quedan dentro
de límites articulares del URDF. Omitir la etapa exacta del cuerpo ahorra los
mismos 3,75 s sólo con cuerpo a cero. No se modificó el árbol que puede ejecutar
Control Center durante el arranque.

| Ruta o fase revisada | Hallazgo y consecuencia |
|---|---|
| READY | Primer bloque explícito de 1,5 s y después `clamp_s2_joints_trajectory`. Esa primitiva nombrada exige su configuración/traza para analizar el recorrido completo. El primer movimiento de cabeza desde HOME ya tiene un pico quintic estimado de 0,8125 rad/s. No acelerar todo el XML por un factor común. |
| ENTRY preview | Hay objetivos explícitos de cabeza/elevador/cintura a 12 s. El torso bajo procede de esos objetivos. Para corregir esa postura hay que revisar la geometría del destino; reducir tiempo no la corrige. |
| Agarre y depósito | Usan MetaClamp y detección/contacto. Las mallas del robot no describen caja, mesa, fuerzas ni apoyo. No se propone reducir umbrales de fuerza o tiempo de asentamiento a partir de este análisis. |
| Apertura y liberación | Hay movimientos cartesianos de apertura de 5 cm en 4 s y descenso de 6 cm en 3 s. Necesitan la postura/IK y geometría de la caja para comparar tiempos; no equivalen a la ruta articular de HOME. |
| Transferencia entre mesas | `--fast` reduce trabajo repetido de comprobación, no constituye un perfil de mayor velocidad física. Navegación requiere mapa/localización y volumen de carga; se conservan LiDAR y las demás protecciones. |

## Qué se verificó y límites del resultado

El comparador usa cinemática directa y cajas orientadas de las envolventes,
501 muestras por etapa más los instantes de fin de cada componente. Comprueba
abrazadera contra los enlaces del robot seleccionados en el informe archivado
y contra la otra abrazadera. Todos los pares locales de fijación permanecen
en el informe: se excluyen únicamente del resumen de pares no locales las
mismas uniones de muñeca/sensor ya identificadas. No se amplían exenciones.

La nueva cota entre muestras utiliza el radio máximo por articulación
independiente y cancela movimientos rígidos comunes a ambas piezas. Es una
cota numérica más ajustada que la anterior aproximación de alcance global;
no significa que el robot haya ganado espacio físico. Para las trayectorias
nominales estudiadas las cotas de los pares no locales son positivas.

Se compararon velocidad, aceleración y cambio de aceleración por articulación
bajo una **interpolación quintic hipotética**, monótona, con los tiempos de cada
componente. Las alternativas de la tabla no aumentan esos máximos individuales
respecto al perfil20s bajo esa hipótesis. No se afirma que Motion interpole así.
En el PICO nominal20s los mayores picos calculados son aproximadamente
0,301 rad/s, 0,370 rad/s² y 1,540 rad/s³.

Acortar uniformemente veinte segundos a quince sí los multiplica por
1,33 / 1,78 / 2,37 respectivamente; a seis segundos por 3,33 / 11,11 / 37,04.
El URDF contiene velocidad0 para los tres ejes de elevador y cintura, por lo
que no proporciona límites dinámicos utilizables para aprobar esas reducciones.

Se conservó como escenario el error de 5° por articulación independiente
comunicado anteriormente por el operador. Con cotas conservadoras de radio,
ese presupuesto deja pares sin separación demostrable, incluso en el perfil
actual: no se obtiene una aprobación robusta frente a ese error. Las cotas
negativas resultantes **no predicen una penetración real**; muestran que ese
método/presupuesto no bastan para demostrar separación. Tampoco existe una
cota de parada medida en la evidencia usada.

El análisis no cubre todas las autocolisiones del robot, suelo/escena, caja,
estabilidad, par motor ni frenado. El informe declara `physical_approval=false`
y `deployable=false`. La revisión y comparación solicitadas quedan hechas;
activar una alternativa requiere contrastar seguimiento/asentamiento reales
en una prueba física independiente. No se solicita repetir mediciones ya dadas.

## Reproducibilidad y registro del cambio

Fuentes nuevas en PC:

- [`review_clamp_trajectory_optimization.py`](../../scripts/teleoperation/review_clamp_trajectory_optimization.py).
- [`test_review_clamp_trajectory_optimization.py`](../../scripts/teleoperation/test_review_clamp_trajectory_optimization.py).

Ejemplo offline, escribiendo a un archivo que no exista:

```bash
python3 scripts/teleoperation/review_clamp_trajectory_optimization.py \
  --snapshot-dir ../Humanoide-vla-evidence/20260908T115359.543954Z_PICO-HOME-CHECK \
  --splint-urdf cruzr_s2_description_splint/cruzr_s2_description/urdf/cruzr_s2_v1/cruzr_s2_v1.urdf \
  --samples 501 --output /tmp/clamp-optimization-review.json
```

Ocho pruebas offline pasan: equivalencia con FK/SAT escalares existentes,
continuidad, tiempos independientes, omisión sólo de igualdad exacta, máximos
analíticos, límites de radio y rechazo de entradas inválidas. Compilación
Python correcta. NumPy y datos archivados ya disponibles; sin instalar paquetes.

Evidencia: `../Humanoide-vla-evidence/20260910T113554Z_CLAMP-TRAJECTORY-OPTIMIZATION/`.
`review.json` conserva por etapa y par las cotas, límites y hashes de fuentes.
`operational-files-before.json` permite comprobar que no se modificaron las
rutas operativas. No hay despliegue ni activación para este comparador; para
retirarlo basta quitar selectivamente sus dos archivos nuevos y referencias
documentales. No modifica el robot ni exige rollback de sus configuraciones.
