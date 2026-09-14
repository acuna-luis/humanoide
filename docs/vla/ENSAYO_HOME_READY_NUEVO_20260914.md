# HOME → READY nuevo: ensayo físico completado

2026-09-14, Europe/Madrid. Ficha VLA-01. Registro realizado: 2026-09-14T21:27:12.376092+02:00.

**PROBADO FÍSICAMENTE CON ÉXITO EN EL ENSAYO COMUNICADO: 5/5 etapas (100 %).**
El propietario informa que partió de HOME, ejecutó las cinco etapas del READY
nuevo y que el resultado fue «todo un éxito», con la única observación de que
fue demasiado lento. Aporta cinco salidas de Motion y una fotografía final.
El 100 % expresa la finalización de las cinco etapas de este ensayo, no una
probabilidad de seguridad ni una validación de cualquier postura o escenario.

## Evidencia de ejecución

Tareas `s2_bio_vla/ready410_h63_access_01_forward` hasta
`s2_bio_vla/ready410_h63_access_05_forward`, en ese orden, con `yaml_args={}`.
El terminal aportado muestra cinco invocaciones de `./force_ready.sh`, cada una
con un objetivo aceptado y el siguiente resultado:

| Etapa | Goal ID | Resultado aportado | Duración XML nominal |
|---|---|---|---|
| 1 — cabeza | `5cb1a20a-5ea6-4051-b767-e5bef8f7f847` | `SUCCEED`, 1101001, status 4 | 6 s |
| 2 — cintura | `43b563a8-a599-46f1-92f3-1d626abfc333` | `SUCCEED`, 1101001, status 4 | 1 s |
| 3 — elevador | `60a225b9-e780-412c-b869-92de56daf312` | `SUCCEED`, 1101001, status 4 | 1 s |
| 4 — brazo izquierdo | `f083ba6d-8f28-4ce9-ad10-a8a8d2aa89a7` | `SUCCEED`, 1101001, status 4 | 57 s |
| 5 — brazo derecho | `19fe1f6e-5219-43e9-9835-27d4ba3dbdf5` | `SUCCEED`, 1101001, status 4 | 57 s |

**OBSERVADO en la evidencia aportada:** aceptación y éxito de cada tarea por
Motion. Esto resuelve la duda de si esos cinco nombres estaban cargados y podían
ejecutarse en ese proceso durante el ensayo. **OBSERVADO por el operador:**
recorrido HOME→READY nuevo exitoso; lentitud excesiva. La fotografía documenta
el resultado visual, pero no aporta una medida articular ni el estado actual.
No se solicitó repetir el ensayo para reconocer este resultado.

## Duración y punto de continuación

Suma de las duraciones de los XML aportados: **122 s (2 min 2 s)**;
114 s corresponden a los brazos. Es tiempo nominal programado, no tiempo real
cronometrado: el terminal no incluye marcas de inicio y fin, ni pausas entre
invocaciones. **PENDIENTE: optimización de velocidad y su ensayo propio.**
No se ha cambiado ninguna duración en esta intervención.

El pendiente «primer ensayo físico del acceso al READY nuevo» queda **cerrado
para este ensayo**. ENTRY, agarre/VLA, retorno e inversas son tareas diferentes
y no se marcan probadas con esta evidencia. No se dispone aquí de traza articular
para cuantificar seguimiento, velocidades finales o distancia de parada.
La prueba aportada fue con ROSA directo; no prueba el monitor Python ni genera
por sí sola su archivo de habilitación. No mantener el resultado físico de READY
como pendiente sólo porque ese archivo no exista.

## Fuentes, identidad y mantenimiento

- Evidencia estructurada aportada por el usuario y copia privada del script:
  `../Humanoide-vla-evidence/READY_ACCESS_OPERATOR_SUCCESS_20260914T212712+0200/`.
- `scripts/force_ready.sh` actual contiene envío directo ROSA; SHA-256:
  `3e077ff76ea9c85d1270cdc4ea6ba8eaaaf864cf9d205fbd2f10e350e2d82104`. Se conserva sin modificar.
  El historial mostrado no permite afirmar que esta copia coincida con las
  cinco versiones/invocaciones utilizadas. Su copia privada puede contener
  información de acceso; no se incorpora al documento ni a Git.
- Destino de los XML: Motion, contenedor
  `walker-motion.manipulation_robot_app-1`, directorio
  `/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/s2_bio_vla/`.
  Recibo y hashes de instalación anteriores:
  `../Humanoide-vla-evidence/20260914_READY410_EXECUTOR/install/receipt.json`.
  No se han consultado nuevamente ni modificado los archivos remotos.
- Receta de preparación/instalación y backups: [paquete READY410](PAQUETE_READY410_CORREGIDO.md).
  Tras actualización, comparar XML y registro con el recibo; no confundir esta
  prueba de los archivos instalados con prueba de una versión modificada.
- Cambios de esta intervención: sólo documentación PC. Respaldo previo en
  `before/` de la evidencia; reversión documental selectiva desde esa copia.
  Sin instalación, recarga, reinicio, movimiento, cambio de script o de velocidad
  por el agente; sin commit ni push.

Este registro sustituye las afirmaciones anteriores de que ninguna de las cinco
etapas de acceso había sido ejecutada. Se conserva la historia de esos informes.
