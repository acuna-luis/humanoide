# Instalación de avisos españoles y rollback — 23-09-2026

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
[Detalles, límites y rollback](TTS_DINAMICO_EN_Y_ROLLBACK_20260923.md).

**VOICE-ES-03: INSTALADO EN DISCO Y VERIFICADO; carga y reproducción pendientes.**
El usuario autorizó instalar y confirmó E-stop pulsado durante el arranque.
Se comprobó principal1 antes de instalar y antes de cada grupo. No se liberó,
reinició ningún servicio, envió movimiento ni reprodujo audio.

## Resultado exacto

- 291 WAV españoles en `/etc/walker/voice/es_local_v1/`, compartido por los contenedores de Vision.
- Dos JSON de apoyo: catálogo y objetivos TTS ingleses con `language=en`, instalados como archivos, **sin conectar un nuevo dispatcher**.
- 600 XML de tareas en cuatro contenedores: las llamadas fijas TtsClient pasan a `file="true"` y `tts="/etc/walker/voice/es_local_v1/ID.wav"`.
- 56 rutas de audio hablado sustituidas (7 grabaciones × dos rutas de modelos × cuatro contenedores). Música y efectos conservados.
- 949 hashes finales verificados por una consulta independiente. Los hashes previos coincidieron con el respaldo.

Contenedores: `walker-system.ae_bt_master-1`, `walker-nav.nav_taskmanager-1`,
`walker-voice.speech_service-1`, `walker-system.control_center-1`.
Los destinos exactos y hashes están en `deployment-v2/plan.json` de la evidencia.
La duplicación refleja sistemas de archivos de contenedores diferentes, no
600 avisos distintos. Se conservan todos los campos de control de las tareas;
sólo se cambian `tts` y `file` en nodos de voz fijos.

**TTS inglés:** el aviso propio de arranque ya usaba inglés y permanece intacto.
Los 60 campos dinámicos conservan su comportamiento nativo; pueden producir
chino. El catálogo inglés está preparado, pero su traducción/idioma efectivo
no está integrado en ese cliente. No se presenta como traducido todo el sistema.
Las grabaciones habladas provienen de la revisión ASR anterior; en particular,
la respuesta infantil breve sigue siendo una propuesta semántica («Aquí estoy»).
Se han instalado por la autorización nueva, sin afirmar una escucha verificada.

## Contrato de reproducción comprobado

Lectura de `libtask_manager_lib.so`, función TtsClient::on_send y sus referencias:
puertos `tts`, `file` y `speed`; con file activado escribe FILE=0/file_path y
sin él TTS=1/text. Contrato Tts.action respalda FILE=0 y TTS=1. La ruta española
se encuentra en el montaje `/etc/walker` accesible al servicio de voz.
No se modificó la biblioteca. SHA256 de la copia inspeccionada:
`1e6308ab4c55eeba16d7c96de9a0585018a173f03da0db4bc3e9533f749323fa`.
Cambiar sólo texto a inglés no cambia el idioma por defecto `zh`; por eso los
avisos fijos usan ahora sus WAV españoles. La prueba de reproducción real está
pendiente y no se ejecutó ninguna tarea para escucharla.

## Respaldo y recibo de instalación

Evidencia PC: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260923_VOICE_INSTALL`.
Recibo concreto: `run/receipt.json`, deployment SHA256
`e609e1813b2e8505d33b304cfabbf60cf6ef6872d1c1fe6105e3e89059e5b19c`.

Copia persistente en Vision: `/etc/walker/voice/deployments/cruzr-voice-20260923T083811Z`.
Incluye `plan.json`, `payload/`, `before/`, `receipts/` y `remote_helper.py`.
Cada archivo tiene intención previa y confirmación posterior en el diario.
Los originales inmediatos y diarios se copiaron además al PC en
`run/remote-receipts-and-originals.tar.gz`.
El respaldo general anterior permanece en
`../Humanoide-vla-evidence/20260923_VOICE_ROLLBACK/originals_verified/`.
No se depende de `/tmp` para el rollback; el directorio temporal de transferencia
queda como staging, y la copia operativa está en `/etc/walker/voice/deployments/`.

## Rollback ejecutable

El comando siguiente **restaura archivos** y requiere E-stop principal pulsado.
No reinicia ni reproduce sonidos. Comprueba que cada destino siga teniendo
el hash instalado: si otro trabajo lo cambió, se detiene sin sobreescribirlo.
Restaura los archivos anteriores con propietario, permisos y marcas de tiempo;
retira únicamente los archivos nuevos registrados. Conserva diarios y respaldos,
y puede dejar directorios vacíos. Carga de árboles o cachés debe verificarse
por separado después de un arranque controlado.

Desde la raíz del repositorio:

```bash
python3 scripts/voice/deploy_voice_assets.py \
  --rollback-receipt /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260923_VOICE_INSTALL/run/receipt.json \
  --evidence /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/VOICE_ROLLBACK_EJECUTADO_NUEVO
```

La carpeta de evidencia debe ser nueva. Ante interrupción, revisar los diarios:
el rollback admite entradas ya restauradas y registra cada avance. Si faltara
la copia persistente remota tras una actualización, reconstruir primero su
`before/`, plan y diarios desde el tar externo en la misma ruta y comprobar
la compatibilidad; **no aplicar el tar sobre la raíz del robot**.
No ejecutar restauración general de imágenes/configuraciones ajenas a voz.

## Reproducción de la instalación

Fuentes versionadas:
[preparador](../../scripts/voice/build_spanish_install.py),
[instalador/rollback](../../scripts/voice/deploy_voice_assets.py),
[test de conflicto y restauración](../../scripts/voice/test_voice_deploy.py).
El preparador exige un destino nuevo y produce payloads/hash/plan desde el
catálogo y los originales verificados. El instalador comprueba todos los grupos
antes de cambiar archivos, respalda cada original inmediato y reemplaza cada
archivo atómicamente. La operación completa de varios archivos no es una sola
transacción: una interrupción se resuelve con el recibo, nunca repitiendo a ciegas.

```bash
python3 scripts/voice/build_spanish_install.py \
  --package ../Humanoide-vla-evidence/20260923_VOICE_ROLLBACK/package \
  --backups ../Humanoide-vla-evidence/20260923_VOICE_ROLLBACK/originals_verified \
  --output /RUTA/PRIVADA/DEPLOYMENT_NUEVO
python3 scripts/voice/deploy_voice_assets.py \
  --deployment /RUTA/PRIVADA/DEPLOYMENT_NUEVO \
  --evidence /RUTA/PRIVADA/CHECK_NUEVO
# Sólo para una instalación nueva autorizada, con los hashes originales:
python3 scripts/voice/deploy_voice_assets.py \
  --deployment /RUTA/PRIVADA/DEPLOYMENT_NUEVO \
  --evidence /RUTA/PRIVADA/INSTALL_NUEVO --apply
```

No repetir ahora: los destinos ya contienen la versión instalada. El check
sin --apply sólo prepara staging y verifica, sin sustituir activos.
Cuatro tests locales pasan, incluida restauración y rechazo de cambios ajenos;
preparación XML compara estructuralmente todos los campos no relacionados con voz.
Se añadió capstone/pyelftools al entorno privado de voz para inspección de sólo
lectura; no paquetes ni cambios de binario en el robot. Sin commit ni push.

## Reanudación

Mantener el paro mientras se prepara el siguiente paso de arranque. La instalación
no verifica por sí sola que Control Center, Motion y cámaras estén listos para
liberar. No se provocó una recarga; distinguir archivos instalados de árboles
cargados y audios realmente reproducidos. La integración de TTS dinámico inglés
queda pendiente y no se sustituyen sus mensajes por avisos genéricos.
