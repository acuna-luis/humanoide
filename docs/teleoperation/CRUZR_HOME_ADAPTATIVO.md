# HOME con apertura según la postura

**Ampliación posterior del 10-09:** el [planificador para posturas generales](CRUZR_HOME_DESDE_POSTURA_GENERAL.md)
añade cobertura del robot completo, estudio de contraejemplos y búsqueda offline
desde estado archivado. Su integración física sigue pendiente. El planificador
de este documento sigue limitado
a sus familias PICO/brazos abajo; no se amplió su autorización ni se instaló.

## Estado del 10-09-2026

**VERIFICADO LOCALMENTE; reducción de apertura/tiempos NO ACTIVADA en Motion.**
El propietario pide aplicar la optimización y evitar abrir de más, tanto desde
PICO como al volver a HOME desde otras posturas. Se implementó la selección de
etapas en un planificador sin conexión a ROS; aún no sustituye el HOME interno
ni la tarea PICO instalada. Ambos XML conservan sus hashes y veinte segundos.

**Sí se ha aplicado al ejecutor existente** la salida sin movimiento cuando ya
está en HOME: después del preflight exige dos lecturas nuevas, JointState y
actuadores sanos, posición20D dentro de0,005rad y velocidad JointState≤0,002rad/s.
Sólo entonces imprime `RESULT=ALREADY_HOME_MEASURED` y `MOVEMENT_COMMANDS=0`.
No pregunta para ejecutar, no consulta la ruta ni envía otra acción. Una lectura
ausente/inválida aborta; una postura válida fuera de HOME sigue por el gate PICO
original. Se corrigió también la propagación del fallo de la primera captura SSH.
No se ha añadido una vía para aceptar posturas PICO desconocidas en `--run`.

## Regla implementada en el planificador

Fuente: [`plan_clamp_home_adaptive.py`](../../scripts/teleoperation/plan_clamp_home_adaptive.py).
Orden de veinte articulaciones idéntico al gate existente. Sólo clasifica forma
de brazos PICO o brazos bajados, con cuerpo casi a cero o en la referencia
flexionada conocida. Posturas de agarre interrumpido o formas distintas se
rechazan; el planificador no es un HOME universal para cualquier posición.

1. Si necesita bajar brazos o recoger un cuerpo flexionado, cada hombro abre
   sólo hasta `min(roll_actual, −0,50 rad)`. El signo negativo es apertura hacia
   fuera en estos dos hombros. Conserva exactamente los otros ángulos al abrir.
2. Un brazo ya abierto a−0,60rad conserva−0,60; no se le suma otra apertura.
   Cada lado se calcula por separado. Si ambos ya tienen apertura suficiente,
   se omite esa etapa completa.
3. La bajada conserva esas aperturas individuales. El cuerpo se recoge después.
   Sólo se cierran los hombros cuando los demás ángulos de brazo ya están abajo.
4. Con brazos ya abajo y cuerpo casi a cero se evita abrir y bajar de nuevo.
   Pequeños errores de posición reciben su corrección explícita; no se declaran
   exactamente cero. Un HOME numérico exacto genera cero etapas.

La apertura mínima candidata de−0,50rad equivale a28,6°, frente a−0,60rad/34,4°
de la ruta instalada. No es un porcentaje de extensión total del brazo.
Desde PICO nominal cambia unos17,2°, frente a23° de la apertura anterior.

## Resultados numéricos

Se usan máximos comparativos quintic de0,30rad/s,0,35rad/s² y1,50rad/s³, inferiores
a los máximos globales calculados del PICO20s. Son límites del candidato, no
especificaciones verificadas del fabricante ni garantía por cada articulación
frente a su perfil anterior. Cada etapa se redondea hacia arriba a milisegundos.
Para la bajada PICO se conservan al menos10s; las correcciones menores duran
al menos1s. Esto no acredita que Motion use esa interpolación.

| Entrada nominal | Duración calculada | Comportamiento |
|---|---:|---|
| PICO, cuerpo exactamente a cero | 15,417s | Apertura reducida, bajar, cerrar |
| PICO, cuerpo flexionado de referencia | 18,544s | Incluye recogida del cuerpo |
| Brazos abajo, cuerpo exactamente a cero | 0s | Ya HOME; sin etapas |
| Brazos abajo, cuerpo flexionado | 9,377s | Abrir, recoger cuerpo, cerrar |
| PICO ya abierto a−0,55/−0,62rad | 13,876s | Conserva apertura y omite abrir |
| PICO con hombros a−0,60/−0,30rad | 15,750s | Sólo abre más el segundo hombro |
| PICO con hombros casi cerrados a+0,02rad | 16,376s | Abre ambos antes de bajar |

Los tiempos son nominales, sin preflight/red ni verificación final. Un pequeño
error real del cuerpo añade una corrección de al menos1s; por eso15,417s no
es una promesa para toda postura clasificada cerca de HOME.

Auditoría de siete casos,501muestras por etapa más cota entre muestras:
límites articulares nominales correctos y sin pares no locales con cota nominal
negativa. En el PICO reducido la menor cota al torso es135,03mm. Se conservaron
envolventes,2mm geométricos e intervalo axial0–40mm; no se eliminaron pares nuevos.

**La activación sigue incompleta.** Con el escenario de error5° por articulación
independiente quedan25–35pares no locales sin separación demostrada por la
cota conservadora, según el caso; no son25–35colisiones observadas. Tampoco hay
cota de parada ni equivalencia del interpolador real. El resultado conserva
`physical_approval=false`, `installable=false` y los bloqueantes concretos.
No genera un XML ejecutable ni un permiso de instalación a partir sólo de la
separación nominal. Cambiar automáticamente el HOME de arranque requiere además
una implementación en el controlador que lea y clasifique su postura actual;
copiar una ruta fija calculada desde PICO no implementaría esa lógica.

## Comprobación y reanudación

Ocho pruebas nuevas: apertura limitada, conservación de cada brazo, omisión de
apertura sobrante, HOME sin acción, recogida del cuerpo con brazos abiertos,
corrección de errores pequeños, continuidad/picos y rechazo de entradas inválidas.
Las22pruebas del ejecutor pasan, incluidas dos nuevas para la salida sin movimiento
y propagación de errores SSH. Sintaxis Bash y compilación Python correctas.

Una consulta real de JointState devolvió stdout vacío y diagnóstico ROSA
`Failed to get message type of topic`, pese a returncode0; el planificador lo
rechazó, sin convertir ausencia de datos en ceros. El preflight real posterior
abortó al detectar que no estaban ambos paros liberados. Lecturas independientes
posteriores confirmaron principal1 y servo0. No se ha acreditado una postura
actual ni ejecutado el caso HOME sin movimiento en el robot durante esta
intervención; su lógica quedó probada con datos simulados.

Reproducir con una captura archivada válida y un archivo de salida inexistente:

```bash
python3 scripts/teleoperation/plan_clamp_home_adaptive.py \
  --input /ruta/a/jointstate.yaml \
  --snapshot-dir ../Humanoide-vla-evidence/20260908T115359.543954Z_PICO-HOME-CHECK \
  --output /tmp/adaptive-home-plan.json
```

Punto de reanudación: comprobar el seguimiento y asentamiento reales del perfil
vigente, acotar el movimiento durante parada y cerrar el análisis de separación
con esos datos antes de activar una reducción de apertura. El nuevo planificador
ya representa las etapas dependientes de postura para esa integración posterior.
La petición de activar los tiempos reducidos en el robot permanece pendiente.

Registro/evidencia privada:
`../Humanoide-vla-evidence/20260910T120838Z_ADAPTIVE-HOME/`.
Incluye respaldo PC previo, siete planes/auditorías, consultas reales y fuentes.
No se instalaron paquetes, archivos ni servicios en Motion/Vision. Para revertir
la mejora operativa del PC, restaurar selectivamente el ejecutor desde `before/`
de esta evidencia, preservando cambios posteriores; eso conserva el arreglo
anterior del hash HOME y no modifica el robot. El planificador nuevo puede
retirarse por separado. Sin commit ni push.
