# Ejes del sensor derecho: cálculo con postura leída

2026-09-08, muestra 11:24:29 UTC. INFERENCIA de correspondencia física;
VERIFICADO el cálculo local con muestra y URDF archivado. Sin movimiento.

La lectura sólo consulta contenedores, actuadores, joints y status de acciones.
Velocidad máxima observada 0 rad/s; delta máximo posición–consigna 0,002876 rad.
Postura OTHER, no HOME/READY. Status capturado contiene una acción cancelada (5);
no certifica ausencia de otros clientes ni preflight completo de movimiento.

Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260908T112429.567210Z_PICO-HOME-CHECK/right_sensor_axes.json`.
URDF archivado del 03-09: SHA256
`06083544f182b9336ad6f40040a5a79955c19897cb0b78d9f597888dce0c2fa0`.
Todas las articulaciones móviles de la cadena base→R_sixforce_link tenían
lectura; no se sustituyeron valores ausentes por cero. No se ha contrastado
otra vez este URDF con el runtime instalado.

Columnas de R_base_sensor calculadas, suponiendo correspondencia base +X delante,
+Y izquierda del robot y +Z arriba:

- +X sensor ≈ hacia el centro (izquierda del robot).
- +Y sensor ≈ arriba.
- +Z sensor ≈ delante.

El usuario describe almohadilla derecha vertical mirando al centro y patitas
arriba. Definiendo un marco didáctico del útil con +Z normal a la cara hacia
la caja, +Y hacia el borde con patitas y +X completando una base dextrógira,
la postura idealizada da:

```text
R_sensor_util ≈ [[ 0, 0, 1],
                 [ 0, 1, 0],
                 [-1, 0, 0]]
```

Es un candidato equivalente a +90° sobre Y para ESTE marco del útil, no una
medición exacta. Se calcula R_sensor_util = R_base_sensor.T @ R_base_util;
la matriz completa, antes de idealizar a ángulos rectos, está en la evidencia.
Los decimales del cálculo no representan precisión física.

Este marco del útil NO se debe mezclar con el borrador anterior de límites que
usaba +X hacia las patitas. Habría que transformar también límites y origen.
No se modifica `config/clamp_mount_requalification.json` ni se da por registrado
el montaje. Pendiente: correspondencia física y runtime del modelo, relación con
marco dimensional, precisión angular y traducción del origen.

Para contraste visual del técnico, identificar en la postura de la muestra:
normal de la almohadilla hacia el centro, dirección hacia patitas arriba y
prolongación del antebrazo hacia delante. Si no coinciden, revisar postura,
marcos y montaje; no corregirlo enviando objetivos de prueba arbitrarios.
Una traslación aislada sólo proporciona una dirección y no determina toda R.
No existe una trayectoria física de identificación validada en esta intervención.

## Confirmación comunicada y cálculo izquierdo

El usuario comunica «verificado por técnico» tras el resultado derecho. Se
registra como confirmación presencial comunicada de las direcciones derechas;
no como medida angular exacta ni verificación de hash del URDF instalado.

Lectura nueva izquierda: 2026-09-08 11:26:59 UTC, sin movimiento enviado.
Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260908T112659.345210Z_PICO-HOME-CHECK/left_sensor_axes.json`.
Cadena completa con posiciones medidas. El cálculo sitúa +X sensor hacia la
izquierda del robot (fuera del centro para este brazo), +Y arriba y +Z delante.
Así la almohadilla izquierda que mira al centro apunta hacia -X sensor.
Con +Z útil normal a almohadilla y +Y hacia patitas, el candidato idealizado es:

```text
R_sensor_util_izquierdo ≈ [[0, 0, -1],
                          [0, 1,  0],
                          [1, 0,  0]]
```

Equivale a Ry(-90°). INFERENCIA pendiente de contraste del técnico para el
lado izquierdo. Se mantienen las limitaciones de registro, marco dimensional
y modelo indicadas arriba; ningún contrato de colisión ha sido modificado.

## Confirmación bilateral y siguiente medición

2026-09-08: el usuario comunica también «confirmado por el técnico» para el
lado izquierdo. OBSERVADO por confirmación presencial comunicada: sentidos
cualitativos bilaterales compatibles con R_derecha≈Ry(+90°),
R_izquierda≈Ry(-90°), con +Z útil hacia la cara de contacto y +Y hacia patitas.
La incertidumbre angular, correspondencia del URDF instalado y traslación
siguen PENDIENTES. No convertir esta confirmación en certificado metrológico.

Siguiente objetivo: situar el centro P de la cara exterior de almohadilla.
Definimos provisionalmente el origen del útil en P. Referencia física S:
centro de la cara de fijación entre soporte y sensor, identificada por el
patrón de tornillos. No usar sin más el centro aparente de la carcasa cilíndrica.
El registro entre S y el origen sixforce_link debe resolverse con el modelo;
una distancia S→P no es automáticamente la traslación ROS.

Medir S→P en tres direcciones de la postura descrita, por lado: lateral hacia
el centro (positivo para esta ficha física), vertical (positivo arriba),
longitudinal (positivo delante). Anotar mm con signo, puntos en fotos, instrumento
y error estimado. No medir una diagonal. Si S no es accesible/identificable,
registrar esa limitación sin desmontar ni mover para obtener la medida.
Lateral hacia el centro corresponde aproximadamente a +X sensor en derecho y
-X sensor en izquierdo. Las otras direcciones corresponden a +Y y +Z sensor.

No reutilizar A=95 mm como distancia al centro P sin confirmar los mismos
extremos. El centro P se obtiene de las dimensiones reales de la cara, no
asignando 70/100 a arriba/ancho según el dibujo histórico. Al definir origen P,
las cotas y límites antiguos deben trasladarse y reorientarse antes de usarse.

## Distancia perpendicular P–eje declarada

2026-09-08: usuario precisa «la distancia más corta entre el centro de la
almohadilla y el eje de fijación unidimensional es 95mm». OBSERVADO por declaración:
distancia punto–recta 95 mm, no distancia punto–punto P–S. El mensaje no
especifica lado; no duplicar como medición bilateral independiente.

Para una recta con dirección Z_sensor y punto A conocido sobre ella:
sqrt((P_X-A_X)^2+(P_Y-A_Y)^2)=95 mm. No determina componente longitudinal,
reparto X/Y ni registro de A con el origen ROS. Si el técnico confirmara además
que P y el eje están a igual altura en la postura descrita, entonces el offset
perpendicular sería aproximadamente +95 mm X_sensor derecho o -95 mm izquierdo,
pero esa igualdad todavía no se ha confirmado. Incertidumbre pendiente.

Siguiente información útil: lado medido, diferencia de altura entre P y eje,
y distancia longitudinal entre S y el pie de la perpendicular trazada desde P.
No modificar traslación ROS ni aplicar 95 mm al origen S automáticamente.

## Confirmación bilateral de 95 mm e intervalo de S

2026-09-08: usuario confirma distancia P–eje de 95 mm en ambos brazos. Añade
que S está oculto en estructura metálica y su distancia proyectada al eje está
entre 0 y 40 mm. Se conserva como intervalo comunicado, sin asignarlo a una
componente ROS: falta referencia inicial, sentido y precisar la proyección.

Centro del intervalo 20 mm y semiancho 20 mm: representación ilustrativa, no
medición de S ni desviación estadística. Para un análisis conservador, una vez
registrado ese intervalo en el marco correcto, considerar la unión de posiciones
admisibles de la geometría a lo largo del intervalo (y del recorrido); comprobar
sólo ambos extremos tampoco basta en general. Un extremo único no maximiza el
riesgo frente a todos los obstáculos. La reserva ±20 mm no incluye los errores
de orientación, dimensiones, 95 mm, otros offsets ni seguimiento del robot.
Sin modificación del contrato ejecutable ni movimiento.

## Referencia externa del intervalo en foto anotada

2026-09-08: usuario aporta foto con segmento rojo «40 mm» entre extremos axiales
visibles del cilindro plateado. Interpretación de la anotación: referencia 0 en
la cara junto al soporte negro (izquierda de la imagen), +40 hacia la cara junto
a la muñeca (derecha de la imagen). Así queda definida una coordenada externa
para el intervalo comunicado; posición central ilustrativa 20 mm hacia muñeca.

La longitud es declaración anotada, no una medición fotogramétrica nueva. La
foto no identifica el origen sixforce_link dentro del conjunto ni demuestra que
S, definido antes como centro de cara de fijación, esté dentro en lugar de sobre
una cara externa. No confundir incertidumbre del origen ROS con incertidumbre de
S. Lado de esta foto no identificado explícitamente; no consta medida axial
bilateral independiente. Pendiente resolver caras/origen con CAD o referencias
físicas, conservando el intervalo como hipótesis comunicada, no traslación ROS.

## P a la misma altura y alineado con cara externa

2026-09-08: usuario responde «misma altura» y después «alineado» a la pregunta
sobre centro P y cara del cilindro junto al soporte. OBSERVADO por declaración,
aplicado al contexto bilateral sin nueva medida independiente por lado.

Para eliminar ambigüedad, F es el centro del eje en ESA CARA EXTERNA. F no es
por definición S (cara real de fijación oculta) ni O (origen sixforce_link).
En direcciones del sensor, F→P nominal derecha [95,0,0] mm e izquierda
[-95,0,0] mm. No hay valores de precisión para las igualdades declaradas.

Si, y sólo si, O está sobre el eje entre F y 40 mm hacia la muñeca, entonces
O→P derecha [95,0,z] e izquierda [-95,0,z] mm, con z∈[0,40]. El signo positivo
se debe a que +Z sensor apunta hacia delante, contrario al desplazamiento F→O.
Centro ilustrativo z=20, semiancho 20, no transformación validada. Ubicación
real de O, contención del intervalo, errores restantes y registro del modelo
siguen pendientes. No fijar traducción en contrato ejecutable con esta hipótesis.

HTML actualiza campos y punto naranja a F; dibuja P a offset lateral ±95 mm,
a igual altura y misma coordenada axial que F. Resto de geometría es ilustrativo.
