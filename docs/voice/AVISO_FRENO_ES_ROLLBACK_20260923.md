# Aviso del freno: cambio de idioma y rollback

23-09-2026 Europe/Madrid. **VOICE-BRAKE-07: instalado; emisión real pendiente.**
El usuario aclaró que sólo quería cambiar el idioma. No se corrigió ni alteró
el diagnóstico de freno bloqueado, su condición, estado físico o control.

Texto encontrado en backend_service_vision:
«当前抱闸被锁死，请操作底盘解抱闸按钮，解锁抱闸».
Audio español generado localmente: «El freno del chasis está bloqueado. Utilice
el botón de liberación del freno del chasis para desbloquearlo».
Esto reproduce el significado del aviso, no verifica que el freno esté bloqueado.

## Integración

Sólo la asignación de Tts_Goal en backend_service_vision y sólo esa frase exacta
se adapta a FILE0 con /etc/walker/voice/brake_es_v1/brake_locked.wav.
La asignación nativa se ejecuta primero; otros objetivos, FILE previos, mensajes
desconocidos y todos los campos ajenos a texto/tipo/ruta conservan sus valores.
Si el WAV deja de ser legible después de cargar, utiliza traducción TTS inglesa
con language=en. La biblioteca no modifica el binario del emisor ni su lógica.
No es una API oficial del proveedor; compatibilidad fijada con hashes de binario,
biblioteca de mensajes y archivos nuevos. Si el guard falla al arrancar, mantiene
voz nativa. No afecta otros ejecutables aunque hereden LD_PRELOAD.

Vision: seis archivos nuevos bajo /etc/walker/voice/brake_es_v1/ (WAV, biblioteca,
test y3 fuentes); sólo en walker-system.backend_service-1 se modifica
/opt/walker/entrypoint.sh insertando el guard justo antes del eval original.
Se comprobó que ese entrypoint no está en un montaje compartido. Se mantienen
setup, transformación de comando y eval originales; no se modificó Control Center.

## Pruebas y activación

Siete hashes releídos correctos. Compilación nativa ARM con g++ existente;
prueba enlazada con libsys_task_msgs valida asignación, frase exacta, campos,
mensaje desconocido, FILE y entrada original. Antes de instalar prueba fallback
EN; después, prueba a través del entrypoint instalado ejecuta únicamente el test
y confirma FILE español. GOALS=0, PLAYBACK=0. Sintaxis shell/Python correctas.
No se lanzó un backend nuevo, reinició servicio ni envió movimiento o audio.
Paro principal1 verificado por instalador antes y durante el cambio.

La instancia existente no se recarga. Se aplicará al próximo inicio de
backend_service por su entrypoint. Emisión real/escucha de esta frase PENDIENTES;
no provocar un bloqueo del freno para probarla. No hace falta reinstalar.

## Respaldo y rollback

Originales externos (entrypoint, binario y biblioteca de mensajes; tar conserva
metadatos): /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260923_VOICE_BRAKE_BUILD/originals.tar.gz.
Original-hashes.json, fuentes, comandos de compilación y pruebas en la misma carpeta.
Recibo y originales inmediatos: /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260923_VOICE_BRAKE_DEPLOY/receipt.json y
remote-receipts-and-originals.tar.gz. Respaldo persistente:
/etc/walker/voice/deployments/cruzr-voice-20260923T100637Z.

Con paro pulsado y directorio de evidencia nuevo:

```bash
python3 scripts/voice/deploy_voice_assets.py \
  --rollback-receipt /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260923_VOICE_BRAKE_DEPLOY/receipt.json \
  --evidence /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/VOICE_BRAKE07_ROLLBACK_NUEVO
```

Restaura primero el entrypoint y retira sólo los seis añadidos, con guard de
hashes y diario. No reinicia procesos: si ya estaba cargada la biblioteca, el
rollback en ejecución requiere el siguiente inicio controlado del servicio.
Mientras siga el proceso antiguo y falte WAV puede usar inglés. No afecta a las
capas de voz ES03, EN04, CC español o retirada de anuncio inglés.

## Reproducción

[Preparador](../../scripts/voice/prepare_brake_voice.py),
[adaptador](../../scripts/voice/backend/brake_voice.cpp),
[test nativo](../../scripts/voice/backend/native_test.cpp),
[catálogo](catalogo_freno_20260923.json).
Generar WAV con synthesize_local_piper.py, catálogo anterior y el modelo Piper
es_ES-sharvard-medium previamente respaldado; WAV y manifest están en
../Humanoide-vla-evidence/20260923_VOICE_BRAKE_AUDIO.
Preparar con prepare_brake_voice.py --evidence /RUTA/NUEVA --audio /RUTA/brake_locked.wav;
instalar deployment/ con deploy_voice_assets.py --deployment ... --evidence ... --apply.
No repetir sobre instalado: el preparador rechaza el entrypoint ya adaptado.
Hashes exactos y plan reproducible en deployment/plan.json. Compilación en /tmp,
pero instalación/rollback no dependen del staging. Sin paquetes/red/firmware ni
commit/push.

## Hashes instalados

- `/etc/walker/voice/brake_es_v1/libbrake_voice.so`: `b9d3876f50dd03f1aaace9ad310764e9f85d4c2850b9ad9c60f778cd918bc319`.
- `/etc/walker/voice/brake_es_v1/brake_voice_native_test`: `4597f1d1551a15463dd4dc874ef711fd51ed81bff5f674661b9c88706725fa3a`.
- `/etc/walker/voice/brake_es_v1/brake_locked.wav`: `180e324c8f87e94598d5780de349bd2d07f9c177d86a1272b98ab070a049d8ca`.
- `/etc/walker/voice/brake_es_v1/source/tts_abi.hpp`: `cb127c696aae0168493920c39689b0c96d86471a24092aba5225c4e18e17ee8f`.
- `/etc/walker/voice/brake_es_v1/source/brake_voice.cpp`: `c96d2d4a5e130c4ed2a6768915daebeaf63d2ba44320e627bc55d20529e09c1b`.
- `/etc/walker/voice/brake_es_v1/source/native_test.cpp`: `64f8691dbad872d179c97985cbec0bd9d894a5d550c3801d548dad4791dc4075`.
- `/opt/walker/entrypoint.sh`: `b95c7d75feb19a7e52c045d9a8da6f7a728d175cb6fd4e187bb73bc9c790091a`.
