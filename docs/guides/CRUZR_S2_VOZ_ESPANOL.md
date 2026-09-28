# Voz y avisos en español: inventario inicial

**23-09-2026 — VOICE-EN-04: ruta TTS dinámica integrada e instalada.**
Adaptador local para TtsClient:346 traducciones/fragmentos; texto/números en EN;
FILE español intacto. Chino desconocido conserva objetivo original y registra
aviso, sin ocultar errores. Lanzador de ae_bt_worker carga biblioteca con hashes
fijados; no se toca biblioteca vendor. Siete rutas verificadas. Paro1 mantenido.
Prueba nativa de ABI/enlace y prueba del lanzador correctas, cero objetivos/audio.
Sin workers activos en lectura previa; se aplica al próximo worker. Primera tarea
real/escucha pendientes; sin reinicios. Rollback independiente devuelve lanzador
y elimina sólo archivos de esta capa, preservando el paquete español anterior.
Recibo externo: ../Humanoide-vla-evidence/20260923_VOICE_DYNAMIC/install/receipt.json.
Respaldo persistente: /etc/walker/voice/deployments/cruzr-voice-20260923T085523Z.
[Detalles, límites y rollback](../voice/TTS_DINAMICO_EN_Y_ROLLBACK_20260923.md).

**23-09-2026 — VOICE-ES-03: avisos españoles instalados en disco.**
Autorizado con paro principal pulsado, comprobado antes de cada grupo.
291 WAV +2 JSON en /etc/walker/voice/es_local_v1;600 XML ahora usan FILE español;
56 rutas de audio hablado sustituidas. Música/efectos intactos.949 hashes finales
verificados. Sin reproducción, recarga, reinicio ni movimiento. Dinámicos60
conservan ruta nativa (puede hablar chino); EN sólo preparado, no integrado.
Rollback ejecutable con recibo y originales inmediatos persistentes:
/etc/walker/voice/deployments/cruzr-voice-20260923T083811Z;
copia externa ../Humanoide-vla-evidence/20260923_VOICE_INSTALL/run/.
Fuentes build_spanish_install.py/deploy_voice_assets.py y test, bajo scripts/voice.
Cuatro tests pasan. Instalado: sí; carga/reproducción: PENDIENTES.
[Instalación, límites y comando de rollback](../voice/INSTALACION_Y_ROLLBACK_20260923.md).

**23-09-2026 — VOICE-ES-02: respaldo verificado y síntesis local preparados.**
Inventario vivo:344 textos TtsClient distintos,284 fijos (274 chinos),60 variables.
291 WAV ES locales Piper:284 textos +7 propuestas de audios hablados transcritos
con Whisper local. TTS EN preparado con language=en;600 copias XML sólo texto.
Música/efectos conservados por petición explícita. No se instaló/reprodujo nada
ni se enviaron movimientos. Audición humana/idioma efectivo del dispatcher e
integración de variables dinámicas pendientes; respuesta infantil breve ambigua.
Seis tar externos con4278 entradas verificadas +ejecutable TTS separado;173 rutas
de audio entre contenedores,21 hashes distintos. Identidades Docker/metadata
privadas, permisos y hashes preservados. Ensayo de rollback offline de XML/audio;
no restauración remota. Primer tar con log transitorio cambiante rechazado y
conservado como fallo; sólo originals_verified/ es válido.
Paquete, modelos/atribución, entorno y hashes:
`../Humanoide-vla-evidence/20260923_VOICE_ROLLBACK`.
Fuentes/receta/alcance y rollback: `docs/voice/VOZ_LOCAL_Y_ROLLBACK_20260923.md`,
`scripts/voice/`; catálogo actual JSON y traducciones adicionales versionados.
Cambio persistente sólo PC: Piper1.8.0 añadido al entorno privado de voz y modelos
Piper/Whisper descargados; GPU4070 disponible, generación/transcripción en CPU.
Reversión selectiva de archivos nuevos PC; preservar backups para cualquier
instalación posterior. Ningún cambio en SDK original ni robot. Sin commit/push.

[Paquete local y rollback](../voice/VOZ_LOCAL_Y_ROLLBACK_20260923.md).

**22-09-2026 — VOICE-ES-01: catálogo y paquete ES/EN preparados en PC.**
109 textos fijos y19 variables TtsClient inventariados en snapshot16-09;
traducciones ES/EN y57 copias XML inglesas (sólo literales tts; variables intactas).
Más aviso local de arranque ya inglés:110 audios ES y110 EN, cada uno WAV PCM16
mono16kHz y MP3. Decodificación/duración/señal verificadas; no escucha humana.
22 rutas WAV originales del inventario previo listadas, sin copia/transcripción:
el robot perdió conexión y el operador confirmó apagado/desconectado.
Inventario exhaustivo actual, mensajes compilados/dinámicos y escucha originales
PENDIENTES. No se cambió ni reprodujo nada en el robot. Catálogo y recetas en
`docs/voice/CATALOGO_VOZ_ES_EN.md`; fuentes `scripts/voice/` y TSV versionados.
Paquete, reproductor HTML, ZIP, hashes, versiones y fallos de conexión en
`../Humanoide-vla-evidence/20260922_VOICE_ES_FULL`.
Entorno PC privado `../Humanoide-vla-evidence/voice-tools-venv` (Edge TTS, PyAV,
soundfile; faster-whisper instalado pero no utilizado, sin modelo descargado).
Síntesis remota de textos traducidos, sin envío de grabaciones. Dependencias
fijadas en requirements-frozen.txt. Instalado/cargado/probado en robot: NO.
Reversión: retirar sólo archivos nuevos/entorno privado y revertir notas
selectivamente; no hay configuración remota a restaurar.

[Catálogo completo y audios preparados](../voice/CATALOGO_VOZ_ES_EN.md).

## Inventario inicial (histórico)

22-09-2026, Europe/Madrid. VOICE-ES-01 — OBSERVADO, conversión entonces PENDIENTE.
El operador solicita cubrir todos los avisos, incluidos arranque, navegación,
manipulación y conversación. No se han sustituido audios ni modificado tareas.

Fuentes localizadas:

- Las tareas XML del proveedor contienen TtsClient con texto chino. Ejemplos:
  我要开始工作啦 → «Voy a comenzar la tarea»;
  需要帮助移动一下箱子 → «Necesito ayuda para mover la caja»;
  当前机器人连接充电器，拒绝执行任务 → «El robot está conectado al cargador. No se puede ejecutar la tarea».
  Son traducciones propuestas; no instaladas. No todas las tareas archivadas están activas.
- Vision/speech_service conserva WAV en
  /opt/walker/ivr_client/ivr/models/player/tip/ y muestras en player/demo/.
  Los nombres incluyen 开机音.wav y 在的-female_01.wav; no se escucharon ni
  se ha demostrado qué archivos utiliza actualmente cada evento.
- El aviso de arranque propio usa /etc/walker/boot/cruzr_boot_voice.py;
  su fuente versionada solicita TTS en inglés (language=en).
- El servicio de voz y el motor TTS son contenedores separados:
  walker-voice.speech_service-1 (zs2_vision-v0.2.0) y
  walker-voice.tts-1 (tts:v0.8.8.server), observados en docker ps.

Pendiente: inventario completo de avisos dinámicos y errores, ubicación de sus
textos, formatos requeridos por el reproductor, soporte real del TTS español,
voz elegida y frases de conversación. No afirmar que language=es funcione por
existir un campo language. Audios grabados pueden cubrir mensajes fijos; una
conversación variable requiere además síntesis y generación en español.

La primera consulta SSH de inventario respondió; una segunda consulta que
incluía GetSpeakerList no llegó al robot: timeout de conexión a192.168.11.3:22.
No se obtuvo lista de voces. No implica ausencia de soporte español.
No se reprodujeron sonidos, activaron micrófonos, reiniciaron servicios ni
modificaron archivos remotos. Al recuperar conexión, continuar consultas de
lectura y preparar correspondencia evento→texto/audio, backups, aplicación
reversible y validación de cada categoría, conservando significado de avisos.

Evidencia privada: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922T114535Z_VOICE_INVENTORY`.
Incluye inventory.py/inventory.jsonl y consulta de detalles no completada.
Cambio PC sólo documental; reversión selectiva de documentos, sin rollback
remoto. Instalado: ninguno; cargado: ninguno; probado en español: PENDIENTE.
