# Revisión concreta de la habilitación del ensayo READY

**Actualización vigente — 2026-09-14: HOME→READY nuevo probado físicamente,
5/5 etapas con éxito.** El propietario aporta los cinco resultados Motion
`SUCCEED` (state 1101001, status 4) y confirma el ensayo exitoso desde HOME.
Se cierra el pendiente de primera ejecución del acceso
`ready410_h63_access_01..05_forward` para este ensayo. Se registra lentitud:
122 s nominales; duración real no cronometrada. La ejecución fue mediante ROSA
directo con un `force_ready.sh` modificado por el operador; el agente conserva
ese archivo. ENTRY/VLA y el monitor Python no quedan probados por este ensayo.
Esta actualización prevalece sobre los estados históricos de READY pendiente.
[Resultados, cinco Goal ID, alcance y evidencia](ENSAYO_HOME_READY_NUEVO_20260914.md).


2026-09-14, VLA-01. Alcance: ensayo vacío supervisado de una etapa de READY.
No equivale a validación de ENTRY, ejecución VLA o retorno general.

La autorización del propietario ya existe. Su protocolo es accionar el E-stop
ante cualquier comportamiento preocupante. UBTECH respondió al mensaje del
incidente —que incluía el SIGABRT— indicando reiniciar después del E-stop.
No exigir una reparación previa de ese incidente como condición inventada.
La respuesta tampoco es una medición de tiempo o distancia de frenado.

## Evidencia que ya se puede aprovechar

- El ensayo PICO→HOME del11-09 completó la acción y HOME; el operador confirmó
  suavidad y ausencia de contacto. Sus2103 muestras no presentan fallos:
  error máximo consigna/posición0,007568924rad, velocidad máxima0,243997rad/s,
  separación máxima entre muestras0,031702s. Es otra trayectoria; estos máximos
  observados no se convierten en cotas garantizadas para READY.
- Orden de grupos y límites configurados ya contrastados; objetivos de cabeza
  corregidos, XML instalados y sus hashes verificados después del arranque.
- Captura nueva de98 muestras: cabeza−0,430665rad y resto próximo a HOME,
  inmóvil y con salud válida. No inferir del registro que la escena física
  pueda cambiar sin nueva comprobación.
- Las54 incidencias del informe son pares internos identificados explícitamente
  (chasis/ruedas, uniones del elevador, hombros, codos y muñecas). No incluyen
  escena ni abrazadera contra torso en este informe. Se conservan como avisos,
  sin convertirlos en certificados; no confundirlos con otra lista histórica
  de13 pares. Todos los restantes1018 pares tienen certificación del recorrido
  en el modelo, condicionado a la geometría y banda de error declaradas.

## Dos defectos del control local corregidos

1. Antes, el monitor admitía cualquier combinación de ángulos dentro de los
   mínimos/máximos de cada articulación. Esa caja incluye poses que no pertenecen
   al segmento calculado. Ahora exige que exista un mismo progreso s en[0,1]
   para todos los ejes móviles, dentro de su tolerancia, y verifica aparte los
   ejes estacionarios. Se calcula mediante intersección de intervalos, también
   cuando los ejes avanzan en sentidos opuestos. No impone una ley temporal ni
   demuestra el comportamiento entre muestras o después de cancelar.
2. El límite genérico0,02rad del JSON podía superar la banda geométrica±1°
   (0,017453rad). Ahora las tolerancias de posición y de ejes estacionarios
   deben caber también en `geometry_joint_error_rad`, extraído del informe.
   La tolerancia de velocidad tiene otras unidades y no se compara con ángulos.

Fuentes: `scripts/vla/runtime/entry410_single_stage_remote.py`,
`scripts/vla/entry410_stage_contract.py`, `scripts/vla/ready410_trial_contract.py`.
Pruebas en `test_entry410_corridor.py` y regresiones:31 casos pasan. Incluyen
una pose dentro de los límites individuales pero fuera del segmento conjunto,
ruido admisible, sentidos opuestos, inmovilidad, sobrepaso, no finitos y
tolerancias mayores que el cálculo. No se reducen protecciones del fabricante.

## Protocolo de ensayo propuesto y alcance pendiente

Seleccionar una sola etapa, contrastar la postura20D y control exclusivo,
registrar estados desde antes del envío y exigir resultado SUCCEED y llegada
inmóvil. El operador observa el recorrido y usa el E-stop ante aproximación
preocupante, contacto, ruido o movimiento inesperado. Fallo: sin reintento,
sin HOME automático y con recuperación según la guía de UBTECH.

El ensayo deberá comprobar el despacho y seguimiento efectivos de las tareas
nuevas. No exigir que ya estén probadas físicamente para llamarlo primer ensayo;
tampoco marcar esas pruebas como realizadas al preparar un JSON. La identidad
de archivos/proceso se documenta por separado de la carga/ejecución del árbol.
La cota máxima de parada sigue sin medirse. La supervisión y la cancelación
del cliente no son una garantía de distancia de frenado.

Este documento y `protocol-review.json` son una revisión y propuesta de ensayo,
**no un archivo de habilitación ejecutable**. No se emitió `authorized:true`
ni se envió movimiento en esta intervención. La captura actual no obliga a
repetir el movimiento de cabeza ya completado.

## Evidencia y mantenimiento

`../Humanoide-vla-evidence/20260914_READY_COMMISSIONING_REVIEW/` contiene captura,
propuesta de protocolo, referencia y revisiones regeneradas, pruebas, fuentes
y backups en before/. Los paquetes anteriores vinculados a fuentes modificadas
caducan; no editar sus hashes manualmente. Comparar los XML regenerados contra
la instalación existente antes de considerar cualquier reinstalación.

Cambios persistentes sóloPC; el monitor se envía como código efímero al usar el
ejecutor. Reversión selectiva desde before/, preservando trabajo ajeno. El
monitor anterior no debe usarse para evitar el nuevo rechazo de una pose fuera
del segmento. No se modificaron configuración o archivos del robot.
