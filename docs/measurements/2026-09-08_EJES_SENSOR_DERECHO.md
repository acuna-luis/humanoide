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
