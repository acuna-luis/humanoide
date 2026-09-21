# 2026-09-18 — HOME de arranque detenido: codo derecho fuera de límite blando

Lectura remota únicamente. Horas del robot en CST (Madrid = CST − 6 h).

## Secuencia

| Hora | Evento |
|---|---|
| 15:15:38 | (arranque anterior) `cruzr/home` body-first v4 SUCCESS. |
| 15:20:07–15:20:30 | `Singapore/separate_right_cruzr` SUCCESS: brazos extendidos al frente, codos casi rectos. Sin avisos de límite. |
| 15:21:28 | Motion pierde controladores (E-stop/apagado) con los brazos extendidos. No se ejecutó `put`/`cruzr/home`. |
| 15:22–15:25 | Nuevo arranque; `cruzr/originalhome` ya instalado y cargado (MOT-05). |
| 15:27:30 | Self-check OK → StartMotion → `cruzr/home` (body-first v4, `e3d06564…`). |
| 15:27:42–46 | Cabeza/elevador/cintura a cero: SUCCESS. |
| 15:27:46–49 | `open_arms`: izquierdo SUCCESS; **derecho FAILURE**, error `0.400192` en J2 (no se movió). |
| 15:27:49 | `LimbMotion fail, reason 19` → StartMotion fail → CC `Fault`. |

## Causa

`R_elbow_roll_joint` medido **0,0280 rad**; límite blando Motion
`[-2.62873, 0.0187266]` (URDF `[-2.6529, 0.0349]`, margen ≈0,93°).
`open_arms` usa `delta_joint_angles` y mantiene J4 en su valor actual, así que
cada consigna del brazo derecho contenía J4 = 0,0268 > 0,0187:
`ValidateCmdWithLimit` rechazó las 1.251 consignas y el brazo entero no se movió.

El codo quedó en ~0,019 al terminar `separate_right_cruzr` (sin avisos) y cedió
≈0,009 rad al perder el control con el brazo horizontal. El HOME (codo = 0) está
sólo 0,0187 rad por debajo del límite, de modo que cualquier postura con el codo
recto es vulnerable.

## Estado leído después (≈09:3x Madrid)

CC `Fault`; servidor de acción de manipulación 1; motores de brazos
habilitados (status 4663, error 0); paros 0/0, cargador 0. Cuerpo a cero,
brazo izquierdo abierto (`L_shoulder_roll` −0,5257), derecho sin abrir
(`R_shoulder_roll` 0,0560, `R_elbow_roll` 0,0280), velocidades 0.

## Recuperación ejecutada (autorizada por el propietario)

- Gate previo: bloqueo de contacto rc0; postura = lectura anterior (error máx.
  0,00288 rad, velocidad 0); servidor de acción 1; paros 0/0; cargador 0.
- [`cruzr_home_resume_right_elbow_20260918.xml`](../../scripts/teleoperation/tasks/cruzr_home_resume_right_elbow_20260918.xml)
  SHA `6e0ca790…580b8f`, copiado temporalmente a
  `config/cruzr/home_resume_right_elbow.xml` **sin** `task_list` ni recarga:
  `robot_app` resuelve `{root}/{task}.xml` al recibir el objetivo (VERIFICADO).
- 15:41:36 CST objetivo aceptado → `SUCCEED` (status 4). Codo derecho: 256
  consignas iniciales rechazadas (≈0,5 s) y después dentro de rango; seis
  MetaMove `moved successfully`.
- Final: todas las articulaciones |q| ≤ 0,00268 rad, velocidad 0; codos
  R −0,00077 / L −0,00086; ningún actuador con error.
- XML temporal eliminado del contenedor tras el éxito.
- CC sigue en `Fault`: apagado/encendido completo con E-stop pulsado PENDIENTE.
- Evidencia: `../Humanoide-vla-evidence/20260918T074108Z_HOME-RESUME-ELBOW/`.

## Corrección definitiva

- HOME v5: paso inicial que meta ambos codos en rango (ver MOT-01).
- Norma: no pulsar E-stop ni apagar con los brazos fuera de HOME; terminar los
  escenarios con `cruzr/home`.
- Informar a UBTECH: rechazo de todo el brazo cuando una articulación no
  comandada empieza fuera de su límite blando.
