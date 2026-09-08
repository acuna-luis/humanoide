# Disponibilidad bajo E-stop — 08-09-2026

## Alcance

Petición: revisar lo disponible, sin completar arranque. Operador declara paro
principal accionado y paro de chasis liberado. Diagnóstico aproximado 07:53–07:57
Madrid según reloj PC. Las lecturas de reloj Motion/Vision parecen unos 25 s
atrasadas respecto al PC; no se midió sincronización con precisión ni se corrigió.
El robot registra +08:00, PC Europe/Madrid (+02:00); conservar ambas referencias.

Lecturas SSH, metadatos de contenedores, logs y suscripciones puntuales con
timeout. Docker estaba activo en ambos hosts antes de ejecutar docker ps:
no se activó por socket. No llamadas de servicio, WebSocket PC, órdenes,
publicadores de movimiento, cambios de modo, reinicios ni despliegues.
No se ejecutaron los servicios listados. No es monitor continuo ni preflight PASS.

## OBSERVADO ahora

| Componente | Resultado | Alcance |
|---|---|---|
| Red | Motion .11.2 y Vision .11.3 accesibles por Wi-Fi USB .42.215, vía .42.2 | Ethernet eno1 DOWN; no se cambió conexión |
| Principal / servo-chasis | `/emb/estop_key_state=1`, `/emb/servo_estop_key_state=0` | Coincide con reporte del operador |
| Control Center | última transición del log actual: `WaitEStopRelease` | No transición posterior ni StartMotion en ventana actual consultada |
| Hardware Motion | esperando `/mc/rosa_control/start` | No se llamó ese servicio |
| Actuadores | topic anunciado, Writer count 0; echo agotó 7 s | No salud, posición, velocidad ni consigna actuales demostradas |
| Estado articular completo | no pudo descubrir tipo `/mc/whole_joint_states` | No hay muestra actual ni HOME medido |
| Cabeza | echo `/mc/head/joint_states` agotó 7 s | No posición actual demostrada |
| Fuerza/par | no se identificaron topics FT en listado actual | No lectura de fuerza ni vigilancia preventiva |
| Manipulación | Action server count 0, client count 1 | Status sin muestra; no declarar libre por ausencia de mensajes |
| Bloqueos de módulo | `locked=false`, nombre vacío | No equivale a actuadores habilitados ni permiso de mover |
| Walker mode | sin muestra, timeout | Estado inferido de log CC, no respuesta transaccional |
| Carga | `/emb/chrg_input_status=0`, baterías reportan discharging | Log contenía anuncio de carga anterior; no sustituye lectura actual ni inspección del cable |
| Baterías | SOC 67,0 % / 98,4 %; 49,8 V ambas; 30/29 °C | Diferencia SOC 31,4 puntos; no diagnóstico BMS ni aprobación de movimiento |
| Guard Vision | disabled, inactive/dead, sin ejecución en este arranque | No intercepta HOME interno del Control Center |
| VLA control/inference | exited y restart=no ambos | No se arrancaron; `robot_command` dio salida vacía, no recuento válido de publicadores |
| PC | ubt-controller active/running, UI de usuario inactive | No se abrió WebSocket; estado STOP del publisher no corroborado |

## Hallazgos auxiliares

- Netdata Vision está unhealthy: healthcheck no conecta a localhost:19999.
  No se reinició. Por sí solo no demuestra fallo de Motion ni seguridad.
- CC registró al arrancar timeouts de catálogo de movimientos; después anotó
  obtención exitosa. También avisos de versión embedded y conexiones MQTT
  fallidas. No se atribuye causa raíz sin diagnóstico específico.
- CameraInfo `/sensor/camera/stereo_left/image/info` responde, pero ancho/alto
  cero y sello cero, frame `stereo_left_link`. No usar como par imagen/joints
  sincronizado ni confundir con el topic rectificado observado el 07-09.
  No se inició streaming ni capturó una imagen en esta revisión.
- `/emb/emb_power_state` entrega data=1; no se asigna significado de seguridad
  sin contrato de esa enumeración.
- Docker logs incluyen sesiones anteriores. El log actual `cc_main.latest.log`
  se consultó aparte para evitar atribuir avisos FT/arranques históricos a hoy.
- Los logs recuperados contienen shutdown lógico del 07-09 hasta Term; eso no
  prueba que se apagara físicamente el chasis al finalizar la jornada.

## Evidencia y cambios

Raíz externa `../Humanoide-vla-evidence/`:

- `20260908T055405Z_BOOT-READONLY/`: inventario Motion/Vision, guard y hashes.
- `20260908T055525Z_ESTOP-AVAILABLE/`: resultados primarios, logs, script y hashes.
- `20260908T055640Z_ESTOP-AVAILABLE/`: consultas auxiliares, log CC actual y hashes.

Recolector local nuevo: `scripts/collect_estop_available_readonly.py`, queries
fijas, timeouts y evidencia exclusiva. `--supplement` consulta sólo auxiliares.
Las consultas pueden crear nodos CLI efímeros de diagnóstico, nunca goals o
publicadores de mando. Datos crudos externos, no añadidos a Git. Los nombres
de contenedor usados se redescubrieron antes; revisar de nuevo si cambia instalación.

Conclusión: la disponibilidad observada es coherente con la espera del paro,
pero no demuestra salud completa. HOME→READY no queda aprobado; no liberar el
paro ni iniciar Motion para convertir esta revisión en ensayo. No hay cambio
remoto que revertir. Quedan pendientes geometría/trayectoria y verificación
física/operativa posterior; no se ha resuelto ninguna mediante estas lecturas.
