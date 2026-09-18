# 2026-09-18 — Primer arranque con HOME v7 detenido: hombro izquierdo fuera de límite

Horas del robot en CST (Madrid = CST − 6 h). Relacionado:
[codo fuera de límite](2026-09-18_HOME_ARRANQUE_CODO_FUERA_LIMITE.md).

## Causa

| Hora | Evento |
|---|---|
| 18:22:48 | `cruzr/home` (v5-18s) tras teleoperación: SUCCESS. |
| 18:27:48 | `Singapore/separate_right_cruzr`: brazos al frente. |
| 18:28:05,6 | **E-stop pulsado** durante `MetaClamp` (CC `Estop state changed: 1`). |
| 18:28:10 | `robot_app` termina 5,02 s después ("delta_t between two beat … bigger than 5s"): comportamiento normal tras E-stop (igual 19:03:49→19:03:54 y otras 6 veces desde el 16-09). Tarea FAILURE; brazos fuera de HOME. Apagado 18:29:21 sin recuperar HOME. |
| 18:44 | v7 instalado bajo E-stop. El instalador no comprobaba la postura; el agente tampoco la releyó (asumió brazos en HOME por la lectura de 09:41 Madrid). **Error de proceso.** |
| 18:52:55 | Arranque: HOME v7. `L_shoulder_roll` 0,1084 > límite blando 0,0987. El paso de codos lleva el resto del brazo en su valor actual: 500 consignas izquierdas rechazadas → FAILURE; cabeza/elevador/cintura abortados a medio camino. Derecho: codo 0,068 corregido (SUCCESS). |

v5 habría fallado igual: el paso de codos sólo protege los codos.

## Recuperación ejecutada (autorizada por el propietario)

1. Gate: postura idéntica a la lectura tras el fallo (error 0), paros 0/0,
   cargador 0, acción 1, bloqueo de contacto rc0. Barrido previo desde esa
   postura: desbloqueo 166 mm; v7 completo ≥156,6 mm (cota 90,8).
2. 18:59:46 [`cruzr_home_unlock_left_roll_20260918.xml`](../../scripts/teleoperation/tasks/cruzr_home_unlock_left_roll_20260918.xml)
   (sólo roll izquierdo −0,05) copiado temporalmente, SUCCEED; roll 0,0589;
   resto de articulaciones Δ ≤ 0,0001 rad. XML eliminado.
3. 19:01:18 `cruzr/home` (v7) desde brazos al frente y cuerpo flexionado:
   SUCCEED en 15,06 s reales (13,45 nominales), 11 MetaMove correctos, 0 avisos
   de límite, final |q| ≤ 0,00278 rad, sin errores de actuador.
4. Captura pasiva 60 s (2.850 muestras, hueco máx. 32 ms): error de consigna
   máx. 0,0119 rad (R_shoulder_yaw, recorrido 2,50 rad); velocidad máx. 0,70 rad/s
   (cabeza), 0,56 (elevador 2), 0,54 (R_shoulder_yaw); 0 muestras en fallo o
   deshabilitadas. Primer ensayo físico de v7 desde postura elevada: correcto.
5. CC sigue en `Fault`: apagado/encendido con E-stop PENDIENTE.

Evidencia: `../Humanoide-vla-evidence/20260918_V7_FAIL_RECOVERY/`.

## Correcciones

- HECHO: el instalador exige `--measure-home` (E-stop liberado, HOME ≤ 0,02 rad)
  del mismo arranque, < 30 min y sin tareas posteriores antes de `--install`.
  Probado en vivo 19:18 CST (MEASURED_HOME=1) y con tests.
- HECHO: norma en `AGENTS.md` y guía `CRUZR_HOME_CUERPO_PRIMERO.md`: terminar con
  `cruzr/home` antes de E-stop/apagado; recuperar antes de apagar.
- PENDIENTE: paso de límites genérico o respuesta de UBTECH (pregunta 4).
- PENDIENTE: motivo operativo del E-stop de 18:28:05 (a confirmar por el operador).
