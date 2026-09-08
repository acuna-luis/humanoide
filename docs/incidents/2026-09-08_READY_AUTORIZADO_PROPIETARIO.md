# HOME → READY autorizado por el propietario

**08-09, vuelta READY→HOME completada y confirmada:** [cierre del ciclo](2026-09-08_HOME_DESDE_READY_AUTORIZADO.md).
Goal único SUCCEED/status=4; HOME 20D máximo 0,002684 rad, velocidad 0,
actuadores sanos; operador confirma «todo bien». Ida y vuelta quedan PASS físico
en este ensayo con montaje actual. Captura parcial del retorno: 2.251 estados,
pico reportado 2,049366 rad/s. VLA detenido/writers 0; sin monitor persistente.
No cambios remotos de configuración/protecciones; geometría continua pendiente.
Este HOME sustituye READY como último estado físico documentado.

Fecha: 2026-09-08. Estado: VERIFICADO para ejecución y posición medida;
OBSERVADO por el operador: movimiento sin problemas y READY estable/libre de
contacto. PENDIENTE validación geométrica continua y retorno con montaje actual.

## Autorización y alcance

El usuario pidió «Lleva el robot a READY» y después indicó «soy el propietario
y ya no está vigente el bloqueo». Se aceptó su revocación del bloqueo anterior
para esta solicitud, conforme a AGENTS.md. Se advirtió expresamente del riesgo
de contacto de abrazaderas con muñecas, antebrazos o torso, pendiente de holgura
continua. El operador confirmó «sí» a las condiciones físicas actuales:
abrazaderas instaladas/vacías, HOME estable sin contacto, caja y mesa fuera del
recorrido, cargador desconectado, ruedas bloqueadas, ambos paros liberados,
PICO/mando/UI sin controlar y persona junto al paro.

No se vuelve a usar el bloqueo documental anterior para negar esta solicitud.
Su revocación no constituye una verificación geométrica ni habilita el VLA.
Los wrappers históricos conservan técnicamente sus restricciones locales:
no se editó ni eliminó el helper compartido de bloqueo. Se envió una única tarea
Motion instalada por SSH/ROSA con las comprobaciones descritas a continuación,
sin reinstalar tareas ni cambiar protecciones. No hay launcher genérico nuevo
ni autorización implícita para otro movimiento o recuperación.

## Comprobaciones previas

- Docker ya activo en ambos hosts; contenedores redescubiertos con docker ps.
- Preflight canónico y auditor E6.0G --check --expect-released correctos.
  HW_TYPE=cruzr_s2_v1, paros 0/0, cargador 0, baterías 62,0 % y 92,8–93,1 %.
- HOME medido en 20 actuadores, velocidad cero, errores cero/habilitados,
  máximo de posición y delta 0,002780 rad. Nueva muestra de HOME justo antes
  de enviar la acción; no se reutilizó únicamente la postura histórica.
- Action server 1; tipo redescubierto mc_task_msgs/action/ArmTask.
  Última transición del log vigente: SelfChecking→JoystickMode.
- READY XML c767f7396a325d375752fbce2351837e7f5e0c750902e4815ddd7acb24e2a9b2;
  forward YAML 7722b73457a89d6448954944af98ff50b24f586113f6ec7014dd31b1efdef7f6.
  Task-list 224c6fca…fac1b, READY registrado y proceso posterior al task-list.
- VLA exited/exited, cero writers en /mc/sdk/robot_command.

## Ejecución y resultado

Tarea: s2_bio_vla/s2_vla_pick_large_teleop_ready, yaml_args={}.
Goal: 836ac427-d8b3-4d19-9445-d0bd6f5fe9a1.
Resultado: SUCCEED/status=4, state=1101001; salida SSH 0.
Una sola ejecución, sin reintento ni orden HOME posterior.

Muestras posteriores:

- READY de los 14 brazos: error máximo 0,001938 rad; velocidad de los 20 ejes 0.
- Actuadores sin fault/habilitados; delta posición–consigna máximo 0,001938 rad.
- Cabeza pitch −0,651079 rad y yaw 0,000288 rad; cintura/elevador próximos
  a cero. Máximo error de estos seis ejes respecto a sus objetivos 0,001079 rad.
- VLA sigue exited/exited, RobotCommand writers=0/readers=2.

El operador confirmó: «Perfecto, se movió sin problemas, actualiza todas las
validaciones, está estable y libre de contacto». Queda cerrado el ensayo como
`PASS_HOME_TO_READY_PHYSICAL_AND_OPERATOR_CONFIRMED`.
Las muestras finales son puntuales,
no monitor continuo ni prueba de ausencia de contacto durante el recorrido.
Este éxito no elimina las incertidumbres geométricas de los informes anteriores.
No hay retorno automático ni monitor persistente.

## Cambios persistentes, evidencia y reanudación

Cambios persistentes: sólo este informe y notas en fuentes global/especializada.
Robot: postura cambiada a READY; ningún archivo, servicio, límite o protección
modificado. No procede rollback de configuración; volver a HOME sería otra
maniobra física y no se ha ejecutado.

Evidencia local externa: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260908T063936Z_OWNER-HOME-READY/`.
Incluye preflight, hashes, autorización, comando exacto, goal/resultado,
lecturas anteriores/posteriores y resumen medido; manifiesto SHA-256.

Reanudación: READY medido y visualmente confirmado estable/libre de contacto. Antes de otra acción
revalidar estado actual. No reutilizar esta autorización como grant VLA.

## Matriz de validación vigente después de la confirmación

| Validación | Estado y alcance |
|---|---|
| Revocación del bloqueo anterior por propietario | OBSERVADO explícitamente; aplicada a HOME→READY solicitado |
| Condiciones físicas previas | OBSERVADO: todas confirmadas por operador |
| Preflight de software y HOME inicial | VERIFICADO: PASS, muestra fresca 20D |
| Identidad de tarea/trayectoria instalada | VERIFICADO: hashes coincidentes y tarea registrada |
| Ejecución HOME→READY con montaje actual | VERIFICADO: una ejecución, SUCCEED/status=4 |
| Movimiento sin problemas | OBSERVADO: confirmación posterior del operador |
| READY articular completo | VERIFICADO: brazos/cabeza/cintura y elevador comprobados |
| READY estable y libre de contacto | VERIFICADO: velocidad cero; OBSERVADO: estabilidad/ausencia de contacto confirmadas |
| Salud de actuadores después | VERIFICADO: errores cero, habilitados, sin consigna latente fuera del gate |
| VLA y publicadores al terminar | VERIFICADO: exited/exited, writers 0 |
| READY→HOME con este montaje | PENDIENTE: no ejecutado en este ensayo |
| Registro geométrico, margen continuo y frenado | PENDIENTE: este ensayo no mide esas magnitudes |
| Activación del checkpoint/ENTRY | Sin habilitación nueva; no ejecutados |

Los informes offline y flags de geometría conservan sus resultados reales.
Este PASS físico es evidencia nueva independiente, no regeneración de sus hashes.
