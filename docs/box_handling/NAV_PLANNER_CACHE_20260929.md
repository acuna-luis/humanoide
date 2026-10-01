# NAV-PLANNER-CACHE-01 — destinos guardados después de cargar el mapa

29-09-2026, Europe/Madrid, 14:44–14:45 CEST. **Causa y recarga del planificador
VERIFICADAS; recorrido físico con el ejecutor corregido PENDIENTE.**

## Causa confirmada

El intento `20260929T123411Z_OPTIMISTIC_SCENARIO1_789402` falló en
`navigate_get1`, antes de visión o agarre. El código externo `7218013` y la
descripción `GOAL_OUTCOSTMAP` no distinguen todas las causas internas. El log de
`walker-nav.freepnc_task-1` concreta ésta:

```text
12:02:18 loadMapInfo: target_points size: 0
12:02:23 getTargetPointsJson. json size=0
12:33:48 logo_nav mode: target point id=get1 not found in map
```

Horas UTC del log Docker, distintas de los segundos impresos por el proceso;
se correlacionaron objetivos y secuencia. El mapa se cargó antes de guardar
get1/put1. El archivo y la API ya contenían ambos destinos, pero el planificador
buscaba el ID en su vector `target_points_`, todavía vacío.

El binario instalado de `freepnc_task_module_node` coincide con la copia
analizada: SHA256 `54da620905aa6816bb29a8e5983823172b02fe1f36cae68a407de5c420b812ea`.
Su `startPlanning` devuelve el estado interno `GOAL_OUTCOSTMAP=7214001` al no
encontrar el ID, antes de publicar la meta. `setMap` relee el archivo y sustituye
la lista. No hay filtro que descarte `precise_marker`; `mark_point.id=false`
no explica este fallo. No era necesario ampliar rango, tolerancia ni velocidad.

## Corrección en el ejecutor

Fuentes PC compartidas por optimistic/improved:

- [scenario1_runtime.py](../../scripts/box_handling/scenario1_runtime.py):
  `sync_planner_map()` antes del primer objetivo, una vez por sesión. Requiere
  `utars_nav_map/FSM_WAITNAVIGATE`, planificador `READY` o `FINISH`, recarga
  nativa terminada en `READY`, puntos sin cambios, mismo mapa y poses frescas
  después. No reintenta un objetivo de navegación abortado.
- [scenario1_action_client.py](../../scripts/box_handling/scenario1_action_client.py):
  cliente `planning`, endpoint `/vnav/action/planning`, tipo
  `vnav_task_msgs/action/VnavCommand`. Sólo admite exactamente `command` y
  `map_name`, comandos `check_state`/`set_map`, mapa `utars_nav_map`. Rechaza
  objetivos, velocidades, otros mapas y comandos de movimiento. Conserva
  comprobación de API nativa, servidor único, lease, UUID y cierre tras fallo.
- [scenario1_contract.py](../../scripts/box_handling/scenario1_contract.py):
  `set_map` exige terminal `status=4` y `READY`; sólo la consulta previa admite
  también `FINISH` de una navegación anterior.
- [scenario1_console.py](../../scripts/box_handling/scenario1_console.py):
  muestra inicio y duración de la sincronización. La explicación genérica de
  `GOAL_OUTCOSTMAP` incluye ID no cargado, sin afirmar necesariamente coordenada
  fuera de la cuadrícula. El registro original permanece intacto.

Se conservan `logo_nav` por ID y `free_nav` por pose. La recarga no añade
verificaciones completas entre etapas: se realiza una sola vez en la sesión,
también si la primera navegación es put1 al reanudar. Una sesión nueva recarga
porque otro cliente puede haber cambiado los puntos. `--check` sigue siendo de
lectura y no recarga; las fuentes se activan al iniciar el siguiente `--run`
o la reanudación correspondiente. No necesitan instalación ni reinicio.

La operación usa directamente el `set_map` de PLANNING, **no** `map_set` del
gestor de navegación ni relocalización. La implementación nativa recarga también
cuadrícula/elementos, activa temporalmente costmaps y los deja pausados en reposo;
la navegación siguiente los activa mediante su flujo normal. Publica una
velocidad cero al acabar. No envía cabeza, brazos ni trayectoria de chasis.
No se debe ejecutar durante una navegación activa.

## Verificación de la recarga real

Antes: `--check` rc0, sesión `20260929T124248Z_OPTIMISTIC_SCENARIO1_818833`,
salud/HOME de inicio comprobados; mapa `utars_nav_map`, `FSM_WAITNAVIGATE`.
Con el lock compartido del ejecutor y nuevas consultas de mapa/estado/PLANNING,
se ejecutó únicamente la recarga, usando el cliente restringido anterior:

- Objetivo `cdcda444-bbc5-44b4-b9f9-be97cb76bb07`:
  `set_map`, `utars_nav_map`; resultado `status=4`, `READY`, código `1214002`.
- Duración total observada de esa invocación: **6,361 s**, incluido arranque del
  cliente aislado. No es medición de un ciclo ni del cliente persistente.
- Log posterior: `target_points size: 2`, `getTargetPointsJson. json size=2`,
  `send cmd vel x y yaw: (0,0,0)` y `set_map succeed with state = READY`.
- SHA256 de `/etc/walker/map/utars_nav_map/umap/umap.json` antes/después:
  `0346173f3251e6f4ec66e7cb6868b0541cab8a6d5c87ac5b8a726ca7037b42c6`.
  Puntos y archivo persistente idénticos.
- Después: `--check` rc0, sesión `20260929T124520Z_OPTIMISTIC_SCENARIO1_826913`,
  salud/HOME comprobados y mismo mapa/FSM. Los mensajes de lease al cerrar los
  workers se conservan como ruido de cierre pendiente; no se ocultaron.

No se envió `navigation_start`, agarre ni HOME. Se corrigió y verificó la lista
cargada; el siguiente ensayo físico aún debe confirmar el recorrido completo.

**Pruebas offline: 299 correctas**, incluyendo caché inicial vacía, recarga una
vez, ambos modos, FINISH sólo en consulta, fallos/timeout/cancelación, cambios de
mapa/puntos/poses durante la recarga y bloqueo de agarre ante rechazo posterior.
`--plan` correcto; `git diff --check` sin incidencias.

## Evidencia, dependencias y reversión

Evidencia externa:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260929T123551Z_NAV_PLANNER_FIX`.
Incluye logs antes/después, descubrimiento del endpoint/esquema,
`planner-refresh-result.log`, análisis de binarios, `tests.json`/`tests.txt`,
fuentes y SHA256 antes/después. `apply-native-planner-refresh.py` conserva la
invocación exacta realizada; para reaplicar, usar el flujo versionado de
`Runtime.sync_planner_map()` y sus controles, no una orden aislada del chat.

Destino remoto del cambio transitorio: caché del proceso PLANNING en Vision,
contenedor `walker-nav.freepnc_task-1`, ID `fb7f64a6949c…`. No se modificaron
archivos remotos, parámetros, mapa, SDK, límites ni servicios. Depende del
contrato nativo observado y del mapa actual disponible en disco.

Reversión del PC: restaurar selectivamente los módulos desde `before/`, que
preserva los cambios anteriores no confirmados en Git, y retirar esta nueva
prueba/notas. Reversión remota: no restaurar la lista vacía obsoleta; cualquier
carga posterior del mapa reconstruye la caché con los datos guardados. El mapa
persistente permanece idéntico. Tras actualizar software, redescubrir endpoint,
tipo y semántica de `set_map` antes de reutilizar esta integración.
