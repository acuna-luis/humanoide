# Reanudación E6.1 después de HOME↔READY satisfactorio

**08-09, HOME→READY→ENTRY ejecutado:** [evidencia y estado](2026-09-08_READY_ENTRY_AUTORIZADO.md).
Ambas acciones SUCCEED/status=4; ENTRY 20D error 0,003835 rad, velocidad 0,
actuadores sanos. Captura completa de la transición: pico reportado 0,107861 rad/s.
Último estado ENTRY, VLA detenido/writers 0. Confirmación visual posterior
pendiente; retorno ENTRY→READY y cinco shadow (0/5) pendientes.
Esta actualización prevalece sobre los estados históricos HOME/ENTRY pendiente.

Fecha: 2026-09-08. Solicitud del propietario: continuar el plan asumiendo
funcionales las rutas recién ensayadas, actualizando bloqueantes.
Estado: PREPARACIÓN E6.1 AVANZADA; sin otra orden de movimiento/inferencia.

## Decisión y siguiente etapa

HOME→READY→HOME deja de figurar como bloqueante pendiente de ensayo con el
montaje actual: [ciclo físico y confirmaciones](2026-09-08_HOME_DESDE_READY_AUTORIZADO.md).
Se conserva el resultado geométrico de cada análisis con su alcance; no se
regeneran PASS del proxy retirado ni se altera READY. El siguiente experimento
es E6.1: transición READY↔ENTRY de cabeza/elevador/cintura, seguida de cinco
sesiones task 0/P14 en shadow con fixture SUPPORTED_LOW. No es un nuevo ensayo
NO_BOX/task 0 ni movimiento del checkpoint.

## Bloqueantes cerrados o precisados

| Gate | Estado vigente y evidencia |
|---|---|
| HOME↔READY con montaje actual | CERRADO como ensayo físico satisfactorio, extremos medidos y confirmados |
| Instalación de READY↔ENTRY | VERIFICADO hoy: ambos XML remotos coinciden byte a byte con previews; task-list 224c6fca…fac1b, entradas Reverse=false/TimeRatio=1.0 |
| Aceptación de límites E6.1C | VERIFICADA por auditor existente; aceptación explícita del 04-09 válida para 12 s, 0,15 rad/s y 0,5 rad/s² provisionales. No pedir de nuevo esa misma aceptación |
| Compatibilidad de brazos con ENTRY | VERIFICADO offline sobre READY medida hoy: error máximo proyectado al frame 40 de 0,001054597 rad, menor que 0,01 |
| Perfil P14 remoto | RESUELTO: faltaba en ambos hosts; instalado por adición exclusiva y hash verificado |
| Código de evidencia shadow | RESUELTO: componentes activos antiguos carecían de captura/deltas completos; actualizados con backup |
| Chequeo que aceptaba runtime antiguo | RESUELTO: --check compara ahora hash del validador Motion y de inferencia Vision; rechazo real de ambos antiguos y PASS tras actualización |
| READY↔ENTRY físico | PENDIENTE: no ejecutado. No hereda la validación física de HOME↔READY |
| Escena SUPPORTED_LOW actual | PENDIENTE: existe manifiesto/fotos/cotas históricos; no es observación actual ni se ha colocado hoy |
| Cinco sesiones shadow desde ENTRY | PENDIENTE: 0/5. No arrancadas desde HOME |
| Publicador VLA/E6.2–E7 | PENDIENTE de ENTRY, escena, cinco shadow y revisión/autorización física propia |

## Auditoría nueva sin rehabilitar el proxy antiguo

`scripts/audit_ready_entry_resume.py` consume la muestra READY archivada del
ensayo de hoy, contrato 20D, XML y URDF. Distingue referencia archivada de estado
fresco y no puede autorizar movimiento. Rechaza estados incompletos/no finitos,
no READY, XML con brazos, dimensiones o duraciones inesperadas y extremos fuera
de límites. No importa ROS ni abre conexiones.

Resultados:

- Los XML comandan exactamente seis ejes en tres grupos; los 14 brazos quedan
  sin nuevos objetivos. Conservándolos se llega a ENTRY a 0,001054597 rad del
  mismo frame 0 de episode_000040; no se mezclan episodios ni se ajusta el target.
- Los extremos cumplen límites URDF. Una curva monótona entre ellos también
  cumple los límites de posición; esto no demuestra interpolación real.
- Hipótesis quíntica de 12 s: ida v=0,130418330 rad/s, a=0,033465359 rad/s²;
  vuelta v=0,130433310 rad/s, a=0,033469203 rad/s². Son cotas del diseño,
  no medidas del controlador. El pico 2,049366 del anterior retorno HOME pertenece
  a otra tarea y no permite afirmar que E6.1C respete 0,15 rad/s.
- Análisis del árbol cinemático: sensor/abrazadera respecto a torso, brazos
  propios y contrarios conserva transformación relativa si brazos/montaje son
  rígidos y no derivan. Comprobación independiente mediante FK para torso y
  muñeca en ambos extremos confirma la invariancia. No equivale a medir holgura
  inicial, rigidez, flexión o hold real.
- Relaciones que cambian: cabeza, elevador y base. Barrido condicional nuevo
  de ambas rutas: 2.048 intervalos/sentido (4.096 total), envolventes esféricas
  de orientación libre y cota de movimiento entre muestras. En el caso de error
  de centro supuesto 75 mm + reserva 10 mm, cota mínima contra geometrías
  variables evaluadas: 263,492 mm ida y 263,489 mm vuelta; ninguna inconclusa.
  Los otros tres casos también separan. Estas cifras NO son holguras físicas.
- head_yaw_link carece de geometría propia: permanece explícito. El barrido
  sólo cubre útil contra geometrías variables disponibles, no toda autocolisión
  del robot, estabilidad, suelo/mesa, seguimiento o frenado. Centro sixforce y
  errores siguen siendo hipótesis; no se completó la transformación del clamp.

Se conserva `physical_authorized=false`. El análisis anterior sin el barrido
está archivado como primera versión; el reporte vigente es
`endpoint-dependencies-screen.json`.

## Preparación shadow instalada sin arrancar contenedores

Objetivo: disponer de P14 y conservar RGB/estado/targets/deltas exactos al
realizar después las cinco sesiones, evitando otro hueco de evidencia.

| Host | Archivo bajo /home/walker/cruzr-vla/additional/safe-runtime | Cambio |
|---|---|---|
| Motion y Vision | cruzr_s2_vla_task0_p14_shadow_e6_1b.json | Ausente→3f7f55521c9d294cdfc0161bb5f3e523c4090fb251152bdbeac672c542a646a7 |
| Motion | cruzr_s2_shadow_validator.py | 0c7848c2…23ab9→45805b89c5d75c97cbc64021dafd385d9dae75197b66cfb87cd94edf75ad93f8 |
| Vision | cruzr_s2_inference_shadow.py | 4279d911…7750e→840c93e24bd8e24e42d79734bca5c8045b5207f2711f15323a7e83801b7cac22 |

Copias no utilizadas del otro componente en cada host no se actualizaron.
Se revisaron diffs antes de reemplazar: validador añade estado/target/deltas
con signo/máximo; inferencia añade PNG y JSON del par suministrado al modelo.
No se cambió checkpoint, overlay GR00T, tasks Motion, límites o protecciones.

Backup en cada host: `/home/walker/cruzr-vla/backups/20260908T065815Z_E6_1-RESUME/`,
con archivo original y manifest.json (rutas, SHA anterior/nuevo y modo).
Sustitución atómica, verificación de hash anterior/nuevo y VLA exited/restart=no.
Vision no tenía el directorio padre backups: el primer intento falló antes de
sustituir el archivo; se creó ese padre y se completó sólo Vision, sin repetir
Motion. Intento y resultados conservados. No se arrancó ningún contenedor.

Rollback: con VLA detenido, comprobar SHA nuevo del destino y SHA anterior del
backup; restaurar atómicamente sólo el componente correspondiente conservando
el modo del manifiesto. Para los perfiles añadidos (estado previo ausente),
retirar únicamente cada archivo si conserva el hash 3f7f5552…646a7. Los
contenedores quedan detenidos; el --check nuevo rechazará el runtime antiguo.
No ejecutar --deploy general para este rollback.

El cambio local a `run_ubtech_vla_shadow.sh` hace obligatorio cotejar los dos
componentes usados en sus hosts antes de validar/iniciar shadow. El --check
original pasó con código antiguo; tras el refuerzo se demostraron rechazo del
validador antiguo, rechazo de inferencia antigua y PASS con ambos actualizados.

## Validación y punto de reanudación

- Seis tests del auditor nuevo (incluida FK independiente) correctos.
- Cinco tests del validador shadow correctos; ocho casos E6.1B y chequeo local
  completos; aceptación E6.1C válida. Sintaxis Bash correcta.
- --check remoto P14 con identidad de fuentes: PASS, writers de mando 0.
- Lectura final HOME medido, actuadores sanos y velocidad 0; contenedores
  exited/restart=no. No hay monitor persistente.

Secuencia preparada: celda vacía y preflight fresco → HOME→READY ya ensayado →
verificación READY 20D → ensayo específico READY→ENTRY (tres grupos, 12 s) con
medida/observación → ENTRY 20D frente al frame 40 → inmovilizar y colocar el
fixture histórico en sus marcas sin contacto → cinco sesiones shadow separadas.
Antes del retorno retirar fixture y medir ENTRY; luego ENTRY→READY→HOME.
La colocación actual del fixture y la primera maniobra del elevador no se dan
por autorizadas o realizadas a partir del éxito de brazos anterior.

Pendientes de la nueva maniobra: revisión completa robot/escena y seguimiento
real de los seis ejes (incluida velocidad/aceleración), inspección física actual
y autorización específica antes del primer ENTRY. El candidato está concretado
en archivos ya instalados; no precisa repetir instalación, recarga ni HOME de
arranque. No se debe rearmar/reiniciar desde READY para ejecutar el ensayo.

Evidencia externa: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260908T065815Z_E6_1-RESUME/`. Scripts, capturas,
instalaciones, rechazos, tests y reporte incluidos en manifiesto SHA-256.
