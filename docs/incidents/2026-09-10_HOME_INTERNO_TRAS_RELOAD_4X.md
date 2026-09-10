# HOME interno después de recarga y cambio de modo — 10-09-2026

## Conclusión verificada

El movimiento comunicado hacia el cuerpo corresponde a **`cruzr/home`**,
lanzado por Control Center durante `StartMotion` después de una petición API
de cambio de teleoperación a `auto_task`. No corresponde a
`cruzr/pico_to_home_open_v2_4x`: los intentos del ejecutor se detuvieron en
preflight, antes de enviar la tarea. La instalación de una ruta alternativa
no sustituye el HOME interno usado por Control Center.

No basta atribuirlo a liberar el E-stop: el registro muestra un cambio de modo
posterior que inició la recuperación de Motion y `LimbMotion`. No se determina
la identidad de la persona/cliente que solicitó ese cambio sólo por este log.

## Secuencia de evidencia

Tiempos siguientes en UTC de Docker; el texto interno de robot usa UTC+8 y
los nombres de evidencia local usan Europe/Madrid (UTC+2).

| Hora UTC | Hecho |
|---|---|
| 09:33:54 | E-stop pulsado durante TeleopMode; hw se detiene y la teleoperación termina |
| Instalación posterior | Perfil 4× registrado una vez, XML SHA256 `6dd482a70e8ec55e02f125eb442b483a12a7c591959e72965214fcc9e02027dc`; task_list SHA256 `c4873861f30b9c0738fda64e07422e33df0171f3b144a5dad4c6cc6ac78c84f1` |
| 09:35:25 | `--reload` reinicia manipulación; `ACTION_SERVERS=0`, sin whole_joint_states, incluso después de la recarga |
| 09:36:34 | E-stop liberado; esto no demuestra Motion operativo |
| 09:38:19 | `onApiWorkModeSwitch() workMode:auto_task`; salida de TeleopMode y comienzo de `StartMotion`, con `motion module not ready` |
| 09:38:30 | Control Center inicia `LimbMotion` después del arranque de hw |
| 09:38:33 | Motion registra `BTree task: 'cruzr/home' is start` |
| 09:38:34 | Órdenes a ambos brazos: siete ángulos cero, duración 6 s; sin la etapa previa de apertura de open_v2 |
| 09:38:37 | E-stop pulsado por el operador; se interrumpe el movimiento |
| 09:38:40 | `StartMotion fail, reason: 19, Limb motion failed`; CC pasa a Fault |
| 09:39:34 | Solicitud de apagado registrada; después hay nuevo encendido comunicado por operador |

Los directorios locales `20260910T113725`, `113822` y `113855` de
`PICO-HOME-OWNER-RUN` no contienen confirmación ni registro de acción. El último
conserva `preflight-before.log` vacío: no permite determinar el motivo concreto
de ese fallo final de consulta. El intento anterior sí acredita servidor cero
y ausencia de estados articulares. El código sale con el fallo antes del bloque
de envío; el auditor usado sólo consulta. No afirmar una causa concreta de red
para la salida vacía sin más evidencia.

## Estado del nuevo encendido y alcance

**OBSERVADO por operador:** detuvo los brazos cuando se aproximaban al cuerpo,
apagó y volvió a encender manteniendo E-stop. Contacto real, ausencia de carga y
postura actual se han preguntado; siguen pendientes de confirmación presencial.

**VERIFICADO por lectura:** ambos hosts accesibles; principal `data: 1`;
nuevo CC llega a WaitEStopRelease a las 09:44:12Z. El servicio autónomo de voz
completa Motion 3/3, seis cámaras en dos rondas y lectura de seguridad, luego
registra TTS Success/status4 a las 09:45:27Z. Esto verifica su ejecución en un
nuevo encendido; audición presencial en este encendido no confirmada.
La voz acredita preparación técnica, no conoce la posición física de las
abrazaderas ni garantiza un HOME interno libre de contacto desde PICO.

**Punto de reanudación:** mantener E-stop; comprobar presencialmente brazos
abajo, vacíos, estables y libres antes de considerar liberación. No usar un
cambio a auto, StartMotion, recarga o reinicio para recuperar desde brazos
elevados. La ruta 4× está instalada pero sigue sin ensayo físico demostrado.
No se ha corregido ni reemplazado el HOME interno del fabricante en esta revisión.

**Intervención del agente:** sólo lectura de logs, inventario y suscripción
acotada al E-stop. Sin reinicios, objetivos, llamadas de servicios ni cambios
remotos. Actualización documental local; no cambia el script ni la configuración.

Evidencia:
`../Humanoide-vla-evidence/20260910T094443Z_RELEASE-AFTER-RELOAD/`.
Incluye logs CC/hw/manipulación, `timeline.txt`, copias de los registros de
instalación/recarga/intentos, journal de voz, alcance y manifiesto SHA256.

## Actualización posterior

El operador confirma brazos abajo, vacíos y libres de contacto y solicita
sustituir HOME interno. Se instaló una apertura relativa de cuatro etapas a
20 s, con principal mantenido y backup, y se reinició sólo manipulación.
La candidata de seis segundos queda sin instalar; ensayo físico pendiente.
[Implementación, evidencia y punto de reanudación](../teleoperation/CRUZR_HOME_INTERNO_APERTURA.md).
