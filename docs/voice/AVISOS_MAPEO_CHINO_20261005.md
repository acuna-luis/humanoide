# Avisos chinos de cierre de bucle durante cartografía

**VOICE-MAPPING-08 — 05-10-2026, Europe/Madrid. OBSERVADO por lectura.**
Usuario escucha chino al mapear. No se reproduce audio, ordena movimiento,
interrumpe cartografía, cambia idioma/configuración o reinicia servicio.
Traducción de estos avisos nativos todavía NO integrada.

## Frases y origen

Speech Service recibe repetidamente estas peticiones TTS y registra callbacks
de reproducción inicial/final con envío de éxito:

| Texto recibido | Significado en español |
|---|---|
| 正在回环,请减速或原地等待 | Se está cerrando el bucle; reduzca la velocidad o espere en el sitio. |
| 回环完成，请继续建图或保存地图 | Cierre de bucle completado; continúe creando el mapa o guárdelo. |

Se explica el significado del aviso; no se está ordenando movimiento al robot.
El cierre de bucle reconoce una zona recorrida para ajustar la coherencia del
mapa. Estas frases no anuncian un error por sí solas.

Metadatos y binarios leídos en contenedores redescubiertos: ambos literales
están en /opt/walker/mapping2d_lidar/lib/libmapping2d_lidar.so, cargada por
/opt/walker/task_mapping2d/lib/task_mapping2d/task_mapping2d_node dentro de
walker-nav.mapping2d-1. SHA256 biblioteca:
d328ae093f9706a2aaccc172d5e3894aa78965bb9c6c5bb38a14f0ee7911478e.
No aparecen en los ejecutables leídos de Control Center/backend ni en los
mapeados consultados de VSLAM/nav_taskmanager. Esto identifica la ruta de
cartografía LiDAR como origen de los textos, fuera de los adaptadores existentes.
No se ha interceptado la llamada para demostrar el ABI específico del cliente.

libvoice_cc.so y libbrake_voice.so están cargadas en Control Center y backend,
respectivamente: no se perdió simplemente su carga. VOICE-BOOT-05 sólo cubre
sus textos de Control Center; VOICE-BRAKE-07 sólo cubre el aviso exacto del freno;
VOICE-EN-04 cubre TtsClient de workers. Ninguna cubre automáticamente este otro
cliente nativo. Añadir frases al catálogo no cambia por sí solo su reproducción.

Ejemplos de objetivos chinos del diario:
1ef409bd-9108-491b-a9c6-2346c29f00f7 y f5720de7-ba59-40f6-9140-1b19a61c25d0
(23:47:13/18 hora nativa); f3d6f2c5-be85-48da-9cc2-961b86e1ebff y
02bbae14-ad20-414e-b22b-b7b0a8ff5a22 (23:48:10/15). Tras la cartografía del
operador, navegación registra MAPPING_SUCCESS 2D, SAVE_MAP_SUCCEED visual y
FSM_Mapping SUCCEEDED sobre utars_nav_map a23:48:41 hora nativa. Es un nuevo
estado respecto al diagnóstico anterior; no demuestra localización posterior,
calidad del mapa nuevo ni la existencia de get1/put1. El agente no lo inició.

## Continuación, evidencia y reversión

Pendiente preparar una adaptación específica de ese emisor, con respaldo del
lanzador/bibliotecas y compatibilidad por hash, conservar parámetros/resultados,
probar sin audio/comandos y activar en un inicio autorizado sin interferir con
cartografía activa. No parchear texto del binario original, ni asumir que cambiar
el idioma de cruzr_say_english.sh modifica estos avisos automáticos.

Lecturas reproducibles, redescubriendo antes los contenedores:

```bash
ssh walker@192.168.11.3 'docker ps --format "{{.Names}}"'
ssh walker@192.168.11.3 'docker logs --since 15m --tail 450 walker-voice.speech_service-1'
ssh walker@192.168.11.3 'docker logs --since 10m --tail 350 walker-nav.nav_taskmanager-1'
```

Evidencia: ../Humanoide-vla-evidence/20261005_MAPPING_CHINESE_VOICE/.
JSON conservan comandos/resultados de logs, lectura de procesos/bibliotecas,
SHA del binario y frases exactas. Cambios persistentes sólo en estas notas PC;
respaldo previo before/, posterior after/ y manifiesto SHA256. Reversión local
selectiva desde before/ y retirada de esta nota, preservando cambios posteriores.
No configuración remota que restaurar, commit ni push. diff-check correcto.
Estado: origen/frases OBSERVADOS; integración/prueba nativa/voz española PENDIENTES.
