# Resultado de la revisión ampliada PICO→HOME

2026-09-08. **Revisión ampliada realizada; validación física NO completada y
trayectoria NO aprobada para ejecución.** Cero objetivos, movimientos, reinicios
o cambios de modo/protecciones enviados. No se declara cerrado un gate sin evidencia.

## Comprobaciones añadidas

- Nueva lectura de joints/actuadores a las 12:08:02 UTC. Postura OTHER, gate de
  reposo correcto. Diferencia máxima frente a la muestra de la curva revisada:
  0,0003835 rad, en driving_wheel_left_joint. No se ha ejecutado esa curva.
- Análisis amplio de 376 pares de geometrías del URDF instalado en 202 estados
  de los dos tramos. Pares rígidos o directamente conectados se enumeran aparte
  como relaciones estructurales, no como permisos generales de contacto.
- Los 33 primeros casos de solapamiento de cajas se refinaron con distancias
  exactas entre triángulos de las mallas instaladas. 31 presentan distancia
  positiva en esos puntos; dos tienen distancia cero:
  head_pitch_link–torso_link y lifter_pitch_3_link–torso_link, ya en la postura
  inicial. No se afirma contacto físico: pueden ser solapamientos de modelado
  en uniones. Falta identificar el tratamiento previsto de esas superficies.
- Se evaluaron otros 40 puntos de codos, muñecas y shoulder_yaw frente al torso:
  ninguno presenta intersección superficial. Esto refina muestras; no es una
  prueba continua de todos los pares y de todos los sólidos físicos.
- Se leyeron plantillas de movimiento y configuración de planificador instaladas.
  HOME derecho usa MetaMove, joint_angles, duration=5.0, siete objetivos cero.
  La trayectoria de abrazaderas usa follow_joint_space_trajectory con dos fases
  de 1,5/1,0 s y otros objetivos. La variante dual HOME OMPL usa joint_angles,
  duration=5.0, enable_ompl_planner=true, tolerancias de colisión 0,02 y diez
  interpolaciones. No se activó ni llamó a ninguna de estas tareas.

## Por qué no se convierte en autorización física

La propuesta calculada es otra curva, de 25,870372 s y dos fases con ley quintica.
Los parámetros de las plantillas pueden modificarse, pero leer duración/objetivos
no demuestra que su interpolación y ejecución reproduzcan la curva revisada.
El transporte local del VLA tiene una ley quintica, pero su contrato está limitado
a otro alcance: READY, 14 ejes y una fuente de objetivo; no cubre esta recuperación
20D ni aporta por sí solo una cota física de frenado o seguimiento. No se amplió
ese alcance para sortear la validación.

Los 2 mm declarados se conservaron como error lineal de medición. No establecen
una cota angular o dinámica. El límite inferior condicionado de 0,86 mm de la
revisión anterior sólo se aplica al modelo y a los supuestos allí registrados.
No se puede asignar error cero a lo que no se ha medido, ni convertir la
contención dentro de una caja en correspondencia exacta con huecos de la malla.
La escena externa tampoco se reconstruyó; las confirmaciones de zona libre no
constituyen una malla registrada del entorno.

## Estado final y continuación necesaria

El origen del modelo instalado y las medidas declaradas están documentados.
El análisis disponible no acredita la ejecución física PICO→HOME. Siguen
necesarias la correspondencia de las superficies de montaje/uniones y una
comprobación del transporte exacto de ejecución con límites de seguimiento y
parada, seguida de la revisión física de la escena aplicable al recorrido.
No se genera un ejecutor ni se marca PASS físico para satisfacer una petición
de cierre. La validación requiere esas evidencias o un procedimiento de
recuperación del fabricante aplicable a esta postura; una prueba física sin
esos límites no cerraría de forma fiable el gate que pretende medir.

## Evidencia

Directorio: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260908T115359.543954Z_PICO-HOME-CHECK/`.
Nuevos artefactos: `robot-robot-broadphase.json`,
`robot-robot-mesh-witnesses.json`, `robot-torso-mesh-check.json`,
`installed-home.yaml`, `installed-arm-trajectory.yaml`,
`installed-home-ompl.yaml`, `installed-planner.yaml` y
`validation-decision.json`. Incluye scripts de reproducción de los análisis.
La lectura nueva está en `20260908T120802.199658Z_PICO-HOME-CHECK/`.

Esta revisión complementa
[la revisión de origen y primer barrido](2026-09-08_REVISION_ORIGEN_Y_PICO_HOME.md).

## Indicaciones de UBTECH comunicadas después de la revisión

El usuario comunica que el técnico UBTECH considera falsos positivos las dos
parejas cabeza–torso y lifter_pitch_3–torso presentes desde la postura inicial.
Se registra como criterio técnico comunicado para esas parejas, sin desactivar
anticolisión ni generalizar la exclusión a otras superficies o trayectorias.

Después comunica que UBTECH no tiene procedimiento aplicable y proporciona
«error articular de 5ª y error espacial de 2mm». Se interpreta 5ª como 5° para
esta evaluación, sin precisión sobre máximo por articulación, simultaneidad ni
si 2 mm es una cota global de toda la geometría o sólo de un punto del útil.
No se proporcionó desplazamiento ni tiempo máximo de parada.

La reserva derecha anterior era 0,855924 mm después de error geométrico 2 mm.
Si los nuevos 2 mm son error adicional de seguimiento, la reserva pasa a
−1,144076 mm: ya no hay prueba de separación, aunque esto no demuestra colisión.
Si los 2 mm eran la misma tolerancia geométrica, no cubren automáticamente el
error articular ahora declarado.

Para ilustrar la sensibilidad angular, 5° causan hasta 8,724 mm de cambio de
posición a 100 mm de un eje. Con el brazo de palanca conservador de 349,935 mm
usado en la comprobación local de muñeca, la cota por un solo giro es 30,528 mm
(2 L sin(θ/2)). No es un desplazamiento observado ni se suman arbitrariamente
errores espaciales/articulares que pudieran describir la misma fuente. Un límite
espacial de un punto no controla por sí solo orientación y barrido del resto.

**Resultado:** el margen anterior no certifica las tolerancias recién comunicadas.
La aceptación de falsos positivos nominales no resuelve el error durante el
movimiento. La propuesta actual permanece no aprobada para ejecución; haría
falta una envolvente robusta a esas tolerancias, separación suficiente y cota
de parada, no elevar un umbral para declarar PASS. Cero movimiento enviado.

## 2026-09-08 — alternativa y parada hipotética, análisis offline

**OBSERVADO EN CÁLCULO; NO VALIDACIÓN FÍSICA.** Se evaluó primero el destino
HOME, sin mandar comandos al robot. Para responder sin nuevas preguntas se
adoptó un escenario de diseño: velocidad 0,02 rad/s, respuesta 0,5 s y frenado
constante mínimo 0,1 rad/s². Con velocidad limitada durante la respuesta,
v·t + v²/(2a) = 0,012 rad = 0,68755°. Se sumó a los 5° articulares declarados:
intervalo de giro ±5,68755°. Estos parámetros **no están verificados como cotas
del controlador**; no son una garantía conservadora de su parada real.

Se calculó la distancia entre la malla instalada de cada abrazadera, desplazada
según la hipótesis de registro, y su propia muñeca pitch. El barrido continuo
cubre el error de wrist_roll y todo el intervalo axial 0–40 mm. Subdivisión
adaptativa con cota Lipschitz: distancia central menos radio máximo respecto al
eje multiplicado por semiancho angular y menos semiancho axial. Se descontaron
2 mm geométricos y otros 2 mm como error espacial relativo adicional, para este
escenario; si describen la misma fuente, esta suma es deliberadamente restrictiva.

- Izquierda: cota de separación superficial 4,304315 mm; reserva 0,304315 mm.
- Derecha: cota de separación superficial 4,018193 mm; reserva 0,018193 mm.
- 134 evaluaciones exactas STL, 68 celdas aceptadas, ninguna pendiente en este
  dominio local. El radio calculado es 191,114 mm, menor que la cota genérica
  usada anteriormente; por eso la estimación anterior no demuestra colisión.

**Cierre local condicional:** este par no impide HOME dentro de este modelo y
estos intervalos. No certifica el resto del robot, todos los errores articulares
simultáneos, la escena, la correspondencia física de la malla ni la ejecución.
La pequeña reserva derecha tampoco justifica ampliar los supuestos.

Se compararon tres caminos nominales: brazos simultáneos, izquierdo primero y
derecho primero, seguidos del mismo tramo de cuerpo. Con 101 muestras por tramo,
la menor separación SAT fuera de las tres parejas locales de montaje de cada
brazo fue la misma: **25,055996 mm**, abrazadera derecha–lifter_pitch_2_link.
Las parejas locales se conservan en los informes; separarlas para comparar no
las excluye de la validación. Cambiar el orden no mejora ese cuello de botella.
Esta comparación es muestreada, sin certificado de incertidumbre global.

No se aprueba el ejecutor PICO→HOME: queda completada esta comprobación local y
la comparación de órdenes; la envolvente global con errores y la equivalencia
con el controlador siguen sin demostrarse. No se movió ni reconfiguró el robot.

Evidencia reproducible en el directorio indicado arriba:
`home-endpoint-uncertainty-check.json`, `home-local-continuous-uncertainty.json`,
`home-order-comparison.json` y los scripts `check_home_uncertainty.py`,
`refine_home_uncertainty.py`, `compare_home_orders.py` (ejecutar desde la raíz del
repositorio, en ese orden; usan exclusivamente los archivos archivados).
