# READY nuevo → ENTRY410: ensayo físico completado

2026-09-14, Europe/Madrid. Ficha VLA-01. Registro: 2026-09-14T21:35:48.973702+02:00.

**PROBADO FÍSICAMENTE CON ÉXITO EN EL ENSAYO COMUNICADO: 5/5 etapas.**
El propietario confirma «validamos que todo salió bien», aporta la salida de
las cinco llamadas y una fotografía final. Se acepta como resultado físico
comunicado y se cierra el pendiente de primer ensayo de estas cinco tareas.
No se exige repetirlas para reconocer este resultado.

## Evidencia aportada

Familia `s2_bio_vla/ready410_h63_entry_XX_forward`, etapas 01 a 05 en orden,
`yaml_args={}`. Cada invocación de `./force_entry.sh` muestra un objetivo
aceptado y finalizado por Motion:

| Etapa | Goal ID | desc / state / status |
|---|---|---|
| 01 | `aa87b6c6-06bc-446e-aa89-087b11f4a991` | SUCCEED / 1101001 / 4 |
| 02 | `f5f30d31-73cb-499b-a210-46847c26b356` | SUCCEED / 1101001 / 4 |
| 03 | `c72f293c-c1f0-4f9e-bada-8955c2b4ec37` | SUCCEED / 1101001 / 4 |
| 04 | `43271492-5687-4b1f-865a-700f28afe06a` | SUCCEED / 1101001 / 4 |
| 05 | `4801b2ea-f2df-472a-b88d-d5f654be4d28` | SUCCEED / 1101001 / 4 |

OBSERVADO en terminal aportado: las cinco tareas estaban disponibles y fueron
ejecutadas con éxito en ese proceso. OBSERVADO por el operador: el recorrido
salió bien. La fotografía documenta el resultado visual. No hay traza articular
ni tiempos de inicio/fin en el extracto; no inventar errores, tiempos de parada
ni duración real. El éxito corresponde a estas etapas en este ensayo, no a
inversas, otras escenas ni a propuestas todavía no generadas por el VLA.

## Estado y siguiente paso

HOME→READY nuevo ya fue completado en el ensayo anterior. READY→ENTRY410 queda
ahora también completado. Punto de reanudación: captura fresca de articulaciones
y estado, después propuestas task 0 en shadow desde ENTRY410 y evaluación de
continuidad. No repetir HOME/READY/ENTRY ni arrancar publicación física del VLA
por registrar este resultado. La prueba directa no valida el monitor Python.

## Identidad, reproducción y cambios

- Evidencia privada: `../Humanoide-vla-evidence/ENTRY_OPERATOR_SUCCESS_20260914T213548+0200/operator-report.json`; respaldo documental
  en `before/` y script actual en `sources/force_entry.sh`.
- SHA-256 del script actual: `8e7eca5b346716f8295765399805152d624f26a2ff23c6bac748f8925f539dd1`. Se conserva sin modificaciones; no
  se afirma que sea idéntico a todas las versiones de las cinco invocaciones.
- Motion: `walker-motion.manipulation_robot_app-1`, XML en
  `/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/s2_bio_vla/`.
  Recibo de instalación previo con hashes en
  `../Humanoide-vla-evidence/20260914_READY410_EXECUTOR/install/receipt.json`.
  No se ha hecho una nueva lectura de los XML remotos en este registro.
- Receta de preparación, instalación y restauración: [paquete READY410](PAQUETE_READY410_CORREGIDO.md).
  Mantener copia de XML y registro; tras firmware comparar compatibilidad y
  hashes antes de reaplicar. No restaurar estados transitorios de ejecución.
- Esta intervención registra el ensayo realizado por el operador; no modifica
  sus scripts, no instala ni recarga tareas y no envía movimientos. La reversión
  de los cambios documentales es selectiva desde `before/`. Sin commit/push.

Este registro prevalece sobre textos históricos que indican ejecución de ENTRY
pendiente. El siguiente resultado shadow se documentará separado del éxito físico.

## Comprobación posterior de ENTRY por el agente

VERIFICADO mediante captura fresca de 98 muestras por nombre articular:
velocidad máxima 0 rad/s; discrepancia máxima con el extremo ENTRY410
0,0027803096 rad (0,1593°), en head_pitch_joint. La suma de duraciones
XML es 74 s nominales, no cronometrados. Se conserva measured-entry.json
y capture/capture.json en la evidencia. Esto comprueba la postura posterior,
no reconstruye el seguimiento durante el movimiento anterior.

Antes del shadow: INFERENCE_CONTAINER=exited, CONTROL_CONTAINER=exited,
COMMAND_PATH_SAFE=publishers:0. Se exportaron logs anteriores y se comprobaron
hashes antes de iniciar benchmark_vla_shadow.py --task-id 0 --duration 30.
El alcance es generación de propuestas sin publicador de movimiento; se
conservarán resultado y cierre de contenedores en esta misma evidencia.

## Continuación VLA task 0 desde ENTRY: resultado shadow

**VERIFICADO: seis propuestas recibidas y seis aceptadas por el perfil shadow
actual**, durante una sesión de 30 s. La cámara registrada muestra la caja azul
completa sobre la mesa. El estado llega por /mc/whole_joint_states, 20 ejes sin
valores por defecto; antigüedad máxima de estado en la validación 2,071 ms.
Se usó el perfil existente cruzr_s2_clamps_groot_n15_20d_shadow_v1, sin modificar
umbrales: evalúa 14 ejes de brazos para los saltos y velocidades de movimiento;
los otros seis figuran bloqueados en el perfil. No llamar a este resultado
validación física de las 20 salidas, validación de colisión o parada.

| Medida | Resultado |
|---|---:|
| Propuestas aceptadas | 6/6 |
| Máximo cambio inicial propuesto, brazos | 0,107586675 rad = 6,1643° |
| Articulación con ese máximo | R_shoulder_pitch_joint |
| Umbral inicial del perfil shadow existente | 0,35 rad |
| Máxima velocidad entre puntos propuesta, brazos | 0,365442 rad/s |
| Inicialización interna nodo/modelo | 27,143 s |
| Arranque observado hasta nodo disponible, incluyendo preparación | 79,394 s |
| Primera inferencia del modelo | 1,598 s |
| Mediana de las cinco inferencias posteriores | 0,436 s |
| Mediana de la iteración completa posterior | 0,479 s |
| Periodo configurado de propuestas / horizonte | 5 s / 0,72 s |

Los tiempos internos están anidados; no sumarlos. El arranque exterior incluye
más trabajo que la inicialización instrumentada y no debe describirse entero
como cálculo del modelo. La aceptación shadow usa su umbral propio; el primer
punto lleva tiempo 0, de modo que el salto inicial de 6,16° requiere resolver
la entrada temporal y el seguimiento antes del primer envío físico. No se
altera la propuesta ni se la ejecuta por haber pasado este filtro amplio.
Las seis propuestas son evaluaciones desde estado inmóvil; no demuestran
continuidad bajo movimiento ni el bucle completo de agarre.

**Cierre efectivo:** INFERENCE_CONTAINER=exited, CONTROL_CONTAINER=exited,
COMMAND_PATH_SAFE=publishers:0. Sin movimientos del agente, sin recarga Motion,
sin cambios de firmware, tareas o límites. Se respaldó la evidencia anterior
antes del arranque que renueva los logs. La modificación fue temporal: arrancar
contenedores shadow, solicitar inferencia task 0, detenerlos y exportar.

Reproducción de este ensayo sin movimiento:
`python3 scripts/vla/benchmark_vla_shadow.py --task-id 0 --duration 30 --output-dir DIRECTORIO_NUEVO`.
Exige contenedores detenidos y ausencia de publicadores físicos; conserva hashes
y comprobaciones. Fuentes utilizadas en sources/; antes/resultados de runtime en
shadow-benchmark/previous y shadow-benchmark/results; report.json y
shadow-observation.json contienen tiempos y métricas. La restauración del estado
temporal se completó al detener ambos contenedores; no restaurar logs antiguos
sobre los nuevos. No reinstalar nada por este ensayo.

**Punto de continuación:** el acceso HOME→READY→ENTRY ya se ha probado. La
primera sesión shadow desde ENTRY también está hecha. Falta adaptar y comprobar
el ejecutor físico para ENTRY410/task 0, incluida la transición al primer punto
y el consumo de propuestas frescas; el lanzador NO_BOX_READY retirado no se
reactiva con estos resultados. Después corresponde un tramo físico limitado,
no volver a probar el acceso ni repetir por inercia la misma sesión shadow.
