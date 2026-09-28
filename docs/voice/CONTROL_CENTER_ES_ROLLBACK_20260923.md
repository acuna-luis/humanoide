# Control Center: español e inglés con rollback

**23-09-2026 — VOICE-BOOT-05: primera reproducción real confirmada.**
Reinicio realizado por operador. Silencio inicial: guard esperando Motion0→3/3
antes de ejecutar Control Center; cámaras6topics2/2 con timestamps crecientes.
Después registra carga VOICE_CC y conversión a FILE español. Speech Service recibe
/etc/walker/voice/control_center_es_v1/audio_es/cc_016.wav, goal
021f9637-e809-4195-bcee-ae44c9dcf6e8; callbacks de inicio y fin y envío de éxito.
Operador confirma escuchar en español «Gire y libere el botón de parada de emergencia».
Queda verificada carga real y escucha de ese aviso, no de todos los24 ni batería.
Paro leído1 durante diagnóstico; CC alcanza WaitEStopRelease. No liberación,
reinicio, reproducción ni movimiento ordenados por agente; sólo consultas.
Los mensajes de shutdown de PID942 pertenecen al proceso anterior, no a fallo del
nuevo arranque. No inferir fallo por nivel E de callbacks: describen inicio/fin.
Evidencia: /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260923T094542Z_VOICE_BOOT_CHECK.

23-09-2026, Europe/Madrid. **VOICE-BOOT-05: INSTALADO; uso real y escucha PENDIENTES.**

El operador autorizó instalar y comunicó paro pulsado. La lectura verificó1 antes
y durante la instalación y después. No se reinició ningún servicio, reprodujo
sonido, liberó paro ni envió movimiento.

## Qué cambia

Control Center tiene un cliente TTS propio, fuera de los XML y workers adaptados
por ES03/EN04. El arranque actual confirmó emisiones chinas en tts_impl.cpp.
La nueva biblioteca intercepta únicamente copias/asignaciones nativas Tts_Goal
cuando el ejecutable se llama control_center (o el test aislado). Primero ejecuta
la copia original y después adapta el objetivo; otros tipos de mensaje y procesos
no se traducen. El binario vendor y libsys_task_msgs no se modifican.

- 24 textos exactos conocidos se convierten de TTS1 a FILE0, con WAV españoles.
- Batería con patrón chino observado y dos porcentajes válidos entre0 y100:
  texto inglés con los números originales y language=en; admite decimales.
- FILE existentes, mensajes desconocidos y batería fuera del patrón se conservan.
- Velocidad, volumen, pitch, speaker, format, interrupción y guardado se conservan.
- Si un WAV deja de ser legible tras la carga, el texto conocido usa TTS inglés.
- Si faltan archivos o cambian hashes durante el arranque, el lanzador conserva
  la voz nativa completa. No omite comprobaciones de disponibilidad para arrancar.

No es traducción universal, ni cubre conversación libre o cualquier aviso futuro.
No se adapta audio de autocomprobación. El log original de processRequest puede
seguir mostrando chino porque registra antes de copiar/traducir el objetivo;
los mensajes [VOICE_CC] y la escucha ayudan a verificar la vía posterior.

## Destinos y compatibilidad

Vision, montaje compartido `/etc/walker/voice/control_center_es_v1/`:
libvoice_cc.so, voice_cc_native_test,24 WAV,4 fuentes y catálogo:31 archivos nuevos.
Archivo sustituido: `/etc/walker/boot/cruzr_cc_start_when_ready.py` (1).
Se añade únicamente comprobación de hashes y LD_PRELOAD inmediatamente antes
del exec original. Se verifica compatibilidad con binario Control Center y
libsys_task_msgs exactos. Se conserva un LD_PRELOAD previo, si lo hubiera.

La interposición C++ no es una API oficial del proveedor. Está limitada a la
versión/hash comprobados. El desensamblado muestra copias por PLT en
ActionClient<Tts>::start (0x5b3630 y0x5b3664), después de construir el objetivo.
No se han cambiado callbacks, esperas ni resultados de acciones.

SHA biblioteca: `39eaf4aa9bc49f4fd33285073f979e5b6d84837e315cb0515a4b9848fa8c5625`.

SHA lanzador instalado: `ff9e119846c89ecc8ed3a3682c6d513abd4956cd2dff1af24da3ef932092184a`.

## Verificación y activación

32 hashes remotos releídos sin diferencias. Prueba nativa ARM enlazada con la
biblioteca real:24 textos por copia y asignación, campos preservados, entrada
original intacta, batería decimal, desconocidos, valores fuera de rango y FILE.
Antes de instalar se probó fallback inglés sin archivos; después, conversión
FILE con los24 WAV instalados. GOALS=0, PLAYBACK=0 en ambos casos.
Comparación AST demuestra que, retirando el bloque de voz, el lanzador conserva
exactamente su lógica anterior. Se ensayaron carga válida y fallback por hash
incorrecto. Cuatro pruebas locales de localización/rollback también pasan.

El proceso actual PID942 no tiene cargada la biblioteca. **Se cargará al próximo
inicio de Control Center mediante el lanzador**, sujeto a los hashes y gates
originales. No hace falta volver a instalar. No se autorizó ni ejecutó un reinicio
en esta intervención. Preparar por separado el arranque supervisado; la carga
no demuestra salud física ni que sea adecuado liberar el paro.
Primera emisión real y escucha de los nuevos avisos: PENDIENTES.

## Respaldo y rollback

Copia externa del lanzador, binario y biblioteca de mensajes anteriores:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260923_VOICE_CC_BUILD/originals.tar.gz`.
Metadatos tar y hashes en original-hashes.json; fuentes y receta en la misma carpeta.
Original inmediato del archivo sustituido y diarios del instalador:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260923_VOICE_CC_DEPLOY/remote-receipts-and-originals.tar.gz`.
Recibo: `20260923_VOICE_CC_DEPLOY/receipt.json`.
Respaldo persistente Vision: `/etc/walker/voice/deployments/cruzr-voice-20260923T093840Z`.

Con paro principal pulsado, desde la raíz del repositorio:

```bash
python3 scripts/voice/deploy_voice_assets.py \
  --rollback-receipt /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260923_VOICE_CC_DEPLOY/receipt.json \
  --evidence /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/VOICE_CC_ROLLBACK_NUEVO
```

La carpeta de evidencia debe ser nueva. Restaura primero el lanzador anterior,
retira sólo los31 archivos añadidos y rechaza cambios posteriores desconocidos.
No reinicia ni descarga bibliotecas de procesos activos: si ya se hubiera cargado,
el siguiente arranque controlado activa el rollback. Mientras sobreviva ese
proceso, no se considera completada la reversión en ejecución; al faltar WAV,
los conocidos pueden usar inglés. Los backups se conservan.
ES03/EN04 son independientes y permanecen instalados. Para retirar todas las capas:
CC primero, EN04 después y ES03 al final, con sus recibos documentados.
No restaurar imágenes ni tar completos sobre el robot.

## Receta reproducible

Fuentes: [preparador](../../scripts/voice/prepare_cc_voice.py),
[adaptador](../../scripts/voice/control_center/voice_cc.cpp),
[prueba nativa](../../scripts/voice/control_center/native_test.cpp),
[prueba del lanzador](../../scripts/voice/test_cc_launcher.py),
[catálogo](catalogo_control_center_20260923.json).

```bash
# Sólo para una nueva preparación revisada; no repetir sobre lo instalado.
python3 scripts/voice/prepare_cc_voice.py \
  --evidence /RUTA/PRIVADA/BUILD_NUEVO \
  --audio ../Humanoide-vla-evidence/20260923_VOICE_CC_AUDIO/audio_es \
  --catalog docs/voice/catalogo_control_center_20260923.json
python3 scripts/voice/test_cc_launcher.py /RUTA/PRIVADA/BUILD_NUEVO
python3 scripts/voice/deploy_voice_assets.py \
  --deployment /RUTA/PRIVADA/BUILD_NUEVO/deployment \
  --evidence /RUTA/PRIVADA/DEPLOY_NUEVO --apply
```

El preparador respalda antes de compilar y no instala. Compila con g++ existente
bajo /tmp, sin instalar paquetes; no depende de ese staging para rollback.
El despliegue exige hashes anteriores y paro; escritura atómica por archivo,
con diario de intención. Ante interrupción, revisar recibo, no repetir a ciegas.
Regeneración de WAV mediante synthesize_local_piper.py y el modelo/atribución
ya respaldados en20260923_VOICE_ROLLBACK. No se cambió red ni firmware.
Sin commit/push.
