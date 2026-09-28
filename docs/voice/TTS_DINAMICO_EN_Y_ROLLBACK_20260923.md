# TTS dinámico en inglés: instalación y rollback

23-09-2026, Europe/Madrid. **VOICE-EN-04 — instalado; prueba nativa y de lanzador
correctas; primera tarea real pendiente.** Usuario autorizó instalar con rollback.
Paro principal leído en1 antes y durante la instalación. Ningún movimiento,
reproducción de audio, tarea real ni reinicio de servicios enviado por el agente.

## Comportamiento

Los valores de las60 variables pasan por el mismo método nativo
`task_manager::TtsClient::on_send`. La adaptación llama primero al método original,
conservando validación de entradas y excepciones, y sólo después localiza el
objetivo de voz:

- FILE=0: no cambia nada; los WAV españoles siguen su ruta anterior.
- TTS=1 y texto conocido: traducción inglesa y `language=en`.
- Números/texto sin chino: conserva el texto y fija `language=en`.
- Texto chino compuesto exclusivamente de cláusulas conocidas: traducción de
  esas cláusulas, conservando números/texto no chino.
- Chino desconocido o fallo de localización: conserva **el objetivo original**,
  sin sustituirlo por un mensaje genérico, y escribe un aviso `[VOICE_EN]` en stderr.

El diccionario compilado tiene346 entradas revisadas del catálogo/fragmentos.
Esto **integra la ruta dinámica**, pero no promete traducir cualquier frase futura:
los mensajes desconocidos pueden seguir sonando en chino como alternativa ante fallo.
No hay traducción por red, espera a modelos ni dependencia del PC en ejecución.
Conversación libre/otros clientes de voz distintos de TtsClient no se interceptan.

## Instalación concreta

- Vision, montaje compartido `/etc/walker/voice/dynamic_en_v1/`: biblioteca
  `libvoice_en.so`, prueba `native_test` y cuatro archivos fuente bajo `source/`.
- Sólo en `walker-system.ae_bt_master-1`:
  `/opt/walker/ae_master/bin/run_ae_bt_worker.sh` incluye el adaptador por
  `LD_PRELOAD` antes de lanzar el worker de tareas.
- No se modificó `libtask_manager_lib.so`, el ejecutable ae_master ni el entrypoint
  general. El lanzador original está respaldado, con metadatos y hash.

SHA adaptador: `b74f48d954de6e8cad7b170d515b49020b5627cbafb2e27d781d4e99551105b8`.
El lanzador comprueba ese hash y los de `libtask_manager_lib.so` y
`libsys_task_msgs.so`; si faltan o cambian, usa la voz nativa y avisa. Conserva
cualquier LD_PRELOAD previo. Los campos de control de movimiento no se modifican.
Las siete rutas instaladas se releen y sus hashes coinciden.

La adaptación usa interposición del símbolo C++ y una declaración compatible
con el ABI específico v0.2.0. No es una extensión oficial de UBTECH. Como no se
instala Tts.h, se contrastó la declaración con Tts.action/Tts.cxx y con accesores
reales de la biblioteca. La prueba nativa verifica tamaño192, direcciones de los
campos y enlace del slot de la tabla virtual al adaptador. El guard de hashes
impide reutilizarlo silenciosamente tras una actualización incompatible.

## Validación y estado cargado

Compilación nativa ARM con g++ existente; prueba enlazada contra las bibliotecas
reales: error conocido→inglés, número→inglés, chino desconocido conservado, FILE
inalterado, velocidad/volumen conservados y enlace de tabla virtual correcto.
Resultado `NATIVE_ABI_AND_VTABLE_BINDING_PASS; GOALS_SENT=0; PLAYBACK=0`.

Se repitió la prueba **a través del lanzador instalado**, sustituyendo la función
`rosa` por una función de prueba que verifica LD_PRELOAD y ejecuta native_test.
No se creó ningún worker real ni se envió una acción. La lectura previa no encontró
workers activos; el adaptador se cargará al lanzar el próximo worker con ese script.
Un worker anterior que siguiera en marcha conservaría su entorno previo.
La primera ejecución real y la escucha de un mensaje dinámico quedan PENDIENTES.

El lanzador original contiene `source /opt/walker/ae_bt_worker/setup.bash`, ausente
en esta imagen. Ese aviso preexistente se conservó; la prueba utilizó el entorno
completo de `/opt/walker/setup.bash`, como el proceso padre. No se atribuye el aviso
al adaptador ni se declara corregido. El primer intento de compilación también
falló por Tts.h ausente; ambos intentos se conservan en la evidencia.
Cuatro tests locales de localización/rollback pasan, incluido rechazo de cambios
ajenos antes de restaurar. No hubo pruebas de movimiento ni de parada física.

## Respaldo y rollback de esta capa

Evidencia externa: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260923_VOICE_DYNAMIC`.
Recibo: `install/receipt.json`. Originales inmediatos y diarios:
`install/remote-receipts-and-originals.tar.gz`.
Copia persistente en Vision: `/etc/walker/voice/deployments/cruzr-voice-20260923T085523Z`.
Los originales del paquete español anterior permanecen en su respaldo separado.

Para retirar **sólo el adaptador dinámico**, con el paro principal pulsado y sin
una tarea activa que se pretenda modificar, desde la raíz del repositorio:

```bash
python3 scripts/voice/deploy_voice_assets.py \
  --rollback-receipt /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260923_VOICE_DYNAMIC/install/receipt.json \
  --evidence /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/VOICE_EN04_ROLLBACK_NUEVO
```

La carpeta de evidencia debe ser nueva. El rollback verifica hashes, restaura
primero el lanzador original y retira sólo los seis archivos nuevos registrados.
No reinicia procesos: un worker que ya hubiera cargado la biblioteca la conserva
hasta salir. No forzar su terminación como parte de este comando. Tras finalizar
ese worker, los siguientes vuelven a la voz nativa. El script rechaza cambios
posteriores ajenos y registra restauraciones parciales para poder revisarlas.

Para volver además a **todos los avisos anteriores a la instalación española**,
retirar primero VOICE-EN-04 con el comando anterior y después ejecutar el rollback
VOICE-ES-03 descrito en [la instalación española](INSTALACION_Y_ROLLBACK_20260923.md).
No restaurar tar completos sobre `/opt/walker`; no borrar respaldos ni otros cambios.

## Reproducción y fuentes

[Adaptador y prueba](../../scripts/voice/dynamic/voice_en.cpp),
[declaración ABI](../../scripts/voice/dynamic/tts_abi.hpp),
[tabla de traducciones](../../scripts/voice/dynamic/translations.hpp),
[compilador/prueba nativa](../../scripts/voice/build_dynamic_native.py),
[preparador](../../scripts/voice/prepare_dynamic_install.py),
[instalador y rollback](../../scripts/voice/deploy_voice_assets.py).

Compilar con `build_dynamic_native.py --evidence /RUTA/NUEVA --remote-dir /tmp/RUTA_NUEVA`;
conservar/copy los dos binarios y el lanzador original en el directorio de build.
`prepare_dynamic_install.py --build /RUTA/BUILD --output /RUTA/DEPLOYMENT_NUEVO
--native-sha HASH_VERIFICADO --messages-sha HASH_VERIFICADO` produce payload/plan.
Instalar con deploy_voice_assets.py --deployment ... --evidence ... --apply sólo
tras una revisión nueva. No repetir ahora sobre el destino ya instalado.
Fuentes exactas, recibos, binarios y hashes quedan en la evidencia; compilación
y pruebas escribieron sólo directorios de build, no SDK original ni paquetes.
Sin commit ni push. Estado: instalado; carga comprobada en prueba aislada;
uso real del worker y escucha aún pendientes.
