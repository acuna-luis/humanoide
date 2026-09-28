# Voces locales ES y TTS EN con rollback — 23-09-2026

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
[Instalación, límites y comando de rollback](INSTALACION_Y_ROLLBACK_20260923.md).

**VOICE-ES-02 — PREPARADO EN PC, NO INSTALADO.** Se conservan música y efectos por instrucción explícita del operador. No se reprodujo audio, modificó configuración ni envió movimiento al robot.

**Resultado:** 284 textos fijos (274 chinos y 10 numéricos/de prueba), 60 variables, 291 WAV españoles locales (284 de texto y 7 propuestas de grabaciones habladas). Objetivos ingleses con `language=en`. Se han preparado 600 copias XML y comprobado que sólo cambian sus literales `tts`.

[Escuchar todas las voces](/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260923_VOICE_ROLLBACK/package/ESCUCHAR_LOCAL.html) · [Comparar los 7 originales y propuestas](/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260923_VOICE_ROLLBACK/package/COMPARAR_ORIGINALES.html)

[Descargar paquete preparado](/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260923_VOICE_ROLLBACK/voces_locales_es_tts_en.zip) — los tar originales de rollback permanecen separados en la evidencia privada.

## Respaldo original y alcance

Evidencia privada: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260923_VOICE_ROLLBACK`. `originals_verified/` contiene seis archivos tar con **4278 entradas verificadas**, incluyendo XML, configuraciones, interfaces y 173 rutas de audio entre contenedores (21 hashes distintos; muchas copias duplicadas). No confundir entradas con avisos únicos. Incluye WAV grandes sin el límite de 8 MB del inventariador inicial. `/usr/local/bin/tts` respaldado aparte en `tts-server/` (4.905.392 bytes).

Cada entrada registra ruta, SHA256, tamaño, propietario, grupo, permisos, mtime y posible enlace. Los seis inventarios Docker privados conservan imagen, identidad y montajes; pueden contener configuración sensible y permanecen fuera de Git. Los 4278 archivos del tar se contrastaron contra los hashes remotos durante la copia. Cero errores en los manifiestos verificados.

Se recorrieron `/opt/walker` y `/etc/walker`: todos los audios encontrados y archivos de texto relacionados con voz/TTS o texto chino, excluyendo logs, cachés y dependencias. El ejecutable TTS se copió aparte. **No es una imagen completa del robot ni una exportación de todos sus modelos/firmware**. No demuestra que todos los mensajes construidos en binarios estén enumerados. Antes de modificar una ruta no incluida, hay que añadir su respaldo.

El primer intento `originals/` detectó que un archivo transitorio de Loki cambió durante la copia; se rechazó. Se conserva como evidencia fallida y NO se usa para rollback. `originals_verified/` excluye esos registros ajenos a voz y es el respaldo válido.

## Síntesis local y validación

Piper 1.8.0, voz española `es_ES-sharvard-medium`, hablante 1, duración relativa 1,08. Generación íntegramente en CPU del PC, sin servicios de síntesis externos; la RTX 4070 de 8 GB está disponible pero no fue necesaria. [API oficial de Piper](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/API_PYTHON.md) y [ficha/licencia de voz](https://huggingface.co/rhasspy/piper-voices/raw/main/es/es_ES/sharvard/medium/MODEL_CARD). Los modelos se descargaron; los textos/audio no se enviaron a un servicio de síntesis o transcripción.

Se conserva WAV nativo 22.050 Hz y WAV PCM16 mono16.000 Hz por aviso, con hash, duración y voz en sus manifiestos. Todos decodifican y tienen señal no nula. Esto no sustituye una escucha de pronunciación ni prueba de reproducción en el robot. Dependencias del entorno privado y hashes del modelo se archivan.

Whisper small local transcribió los audios. Los efectos generaron falsos subtítulos: esas salidas se descartaron como texto válido. Las canciones no se traducen por decisión del usuario. Las siete grabaciones habladas tienen propuestas basadas en ASR; la infantil de menos de medio segundo es ambigua y usa el significado propuesto de su nombre `在的` («Aquí estoy»), NO una transcripción confirmada. Se ofrece comparación auditiva antes de sustituir.

## TTS inglés y mensajes dinámicos

El contrato nativo respaldado define `FILE=0`, `TTS=1` y `language` por defecto `zh`. `tts-goals-en.json` fija `type=1` y `language=en` para cada frase preparada. Cambiar sólo el literal de un XML no demuestra que su TtsClient seleccione el idioma inglés: las copias XML son borradores de integración, no tareas para ejecutar. Para WAV se debe usar el modo FILE y una ruta remota válida, después de comprobar el servidor/reproductor.

Los 60 campos `{...}` son valores calculados, no frases fijas. `localize_tts_text.py` traduce valores conocidos por coincidencia exacta y rechaza chino no catalogado; conserva números/texto no chino. Tres pruebas cubren error conocido, valor numérico e idioma no mapeado. No está conectado al dispatcher del robot. La cobertura de todos los futuros mensajes dinámicos sigue pendiente: no se falsean errores ni se emiten mensajes genéricos en su lugar.

Las traducciones nuevas preservan errores y recomendaciones del original (incluidos reinicio o reintento desde radiomando); son contenido a revisar, no instrucciones de operación emitidas por este catálogo. Fragmentos concatenados y maniobras ambiguas (`盲走`, sentado adelante/atrás, prefijos/sufijos) requieren contrastar el contexto antes de desplegar. El texto político de demostración se traduce como declaración atribuida del original, no como información verificada sobre actualidad.

## Aplicación futura y rollback

1. Revisar los audios hablados y traducciones; resolver los mensajes dinámicos de las tareas realmente activas. Preparar un manifiesto de instalación que enumere **sólo** los destinos que se vayan a cambiar.
2. Redescubrir host/contenedor e imagen; comprobar que cada destino conserva `before_sha256`. Si difiere, detener esa entrada y respaldar/revisar la versión nueva. No sobreescribir cambios posteriores.
3. Aplicar únicamente las entradas aprobadas de `replacement-plan.json` y `audio-replacement-plan.json`, conservando propietario/permisos y usando escritura atómica. Registrar qué se instaló, qué se cargó y la prueba de cada evento. No se ha implementado ni ejecutado una instalación automática en esta intervención.
4. Para volver atrás, usar el **recibo real de instalación**, no todas las propuestas: comprobar que el destino conserva su `after_sha256`, extraer `backup_member` del tar indicado, verificar `before_sha256`, restaurar atómicamente y reponer permisos/propietario. Verificar después el hash original. Retirar sólo archivos nuevos que consten en ese recibo. Preparar por separado cualquier recarga de servicios.
5. Si el hash posterior ya no coincide, detener el rollback de esa entrada y comparar; no aplicar un tar completo sobre `/opt/walker` o `/etc/walker`. El backup contiene otros XML que pueden controlar movimiento.

Se ensayó el rollback **offline**: recuperación y hash de 656 entradas (600 XML y56 rutas de audio hablado) en `rollback-check-all/`; no fue una restauración en el robot. Los WAV originales completos están en los tar y los planes de audio señalan sus hashes. Música/efectos tienen decisión de conservación y no deben producir escrituras.

Recetas versionadas, sin movimiento:

```bash
python3 scripts/voice/backup_voice_assets.py --output /RUTA/PRIVADA/NUEVA
python3 scripts/voice/prepare_localized_voice.py --inventory /RUTA/inventory --output /RUTA/package
../Humanoide-vla-evidence/voice-tools-venv/bin/python scripts/voice/synthesize_local_piper.py --catalog /RUTA/package/catalog.json --model /RUTA/models/es_ES-sharvard-medium.onnx --output /RUTA/package/audio_es
python3 scripts/voice/prepare_voice_replacements.py --package /RUTA/package --backups /RUTA/originals_verified
python3 scripts/voice/verify_voice_rollback.py --plan /RUTA/package/replacement-plan.json --output /RUTA/rollback-check-nuevo
```

Reversión de esta intervención sólo PC: conservar el respaldo si se prevé instalar; retirar el paquete nuevo y scripts nuevos cuando dejen de ser necesarios, restaurar documentación selectivamente. El entorno privado preexistía desde el 22-09; se añadió Piper y modelos, no paquetes al Python del sistema. No se modificó el SDK original. Sin commit/push.

## Correspondencias de los textos fijos

| ID | Chino original | Español | Inglés TTS |
|---|---|---|---|
| tts_16dc368a89b4 | 101 | 101 | 101 |
| tts_3dd9c0995d54 | 1011 | 1011 | 1011 |
| tts_37834f2f2576 | 102 | 102 | 102 |
| tts_f00f2e7bca65 | 1022 | 1022 | 1022 |
| tts_454f63ac30c8 | 103 | 103 | 103 |
| tts_f8b729102586 | 1033 | 1033 | 1033 |
| tts_ef2d127de37b | 5 | 5 | 5 |
| tts_7902699be42c | 7 | 7 | 7 |
| tts_2c624232cdd2 | 8 | 8 | 8 |
| tts_37a8eec1ce19 | default | default | default |
| tts_f32546e00a00 | put_height的值是： | La altura de depósito es: | The placement height is: |
| tts_c89fbb9c3866 | row是： | La fila es: | The row is: |
| tts_6db48f8c6c61 | sps_ready失败 | Ha fallado la preparación SPS. | SPS readiness failed. |
| tts_0b37df621b45 | target_pos的值是： | La posición objetivo es: | The target position is: |
| tts_16b72e32bc67 | 一号位置ctu指令发送失败 | No se pudo enviar la orden CTU a la posición uno. | Failed to send the CTU command for position one. |
| tts_ca1aefae851c | 一号位置ctu指令发送成功 | Orden CTU enviada a la posición uno. | CTU command sent successfully for position one. |
| tts_057bd2ee3cd2 | 上料任务结束 | Tarea de suministro de material terminada. | Material loading task finished. |
| tts_cc0e8caf2fd1 | 下蹲失败 | No se pudo realizar la sentadilla. | Squatting failed. |
| tts_a359eec0c772 | 下蹲失败，检测运控模块是否异常 | No se pudo realizar la sentadilla. Comprueba si el módulo de control de movimiento presenta errores. | Squatting failed. Check the motion control module for errors. |
| tts_de55841097f2 | 下蹲失败，检测运控模块是否异常，航模可以重试 | No se pudo realizar la sentadilla. Comprueba si el módulo de control de movimiento presenta errores. Se puede volver a intentar desde el radiomando. | Squatting failed. Check the motion control module for errors. You can retry using the radio controller. |
| tts_1bd38d26dd10 | 二号位置ctu指令发送失败 | No se pudo enviar la orden CTU a la posición dos. | Failed to send the CTU command for position two. |
| tts_55eede4c3d59 | 二号位置ctu指令发送成功 | Orden CTU enviada a la posición dos. | CTU command sent successfully for position two. |
| tts_89d8a4a03a60 | 从高处取箱失败，检测运控模块是否异常 | No se pudo recoger la caja en altura. Comprueba si el módulo de control de movimiento presenta errores. | Picking up the box from a high position failed. Check the motion control module for errors. |
| tts_748f63bc24cb | 任务失败，请检查六维力数据是否异常 | La tarea ha fallado. Comprueba si los datos del sensor de fuerza y par de seis ejes presentan anomalías. | The task failed. Check the six-axis force and torque sensor data for abnormalities. |
| tts_2f1d6b98ff25 | 任务失败，请检查行为树文件是否正确 | La tarea ha fallado. Comprueba que el archivo del árbol de comportamiento sea correcto. | The task failed. Check that the behavior tree file is correct. |
| tts_71f07ce98e80 | 任务失败，请重启机器后重试 | La tarea ha fallado. Reinicia el robot antes de volver a intentarlo. | The task failed. Restart the robot before trying again. |
| tts_324225eef1d7 | 任务完成 | Tarea completada. | Task completed. |
| tts_2d7f2258a2db | 任务类型错误 | Tipo de tarea incorrecto. | Incorrect task type. |
| tts_170b3f246731 | 任务结束 | Tarea terminada. | Task finished. |
| tts_68ecb29c5309 | 任务退出 | Se ha salido de la tarea. | Task exited. |
| tts_323e1e499f75 | 位置为三十一，搬大螺丝空料盘 | Posición 31. Transportando la bandeja vacía de tornillos grandes. | Position 31. Transporting the empty tray for large screws. |
| tts_e81ae4fcda4e | 位置为三十一，搬小螺丝空料盘 | Posición 31. Transportando la bandeja vacía de tornillos pequeños. | Position 31. Transporting the empty tray for small screws. |
| tts_ec0278e3a364 | 位置为三十三，搬大螺丝空料盘 | Posición 33. Transportando la bandeja vacía de tornillos grandes. | Position 33. Transporting the empty tray for large screws. |
| tts_d63d6c89b034 | 位置为三十三，搬小螺丝空料盘 | Posición 33. Transportando la bandeja vacía de tornillos pequeños. | Position 33. Transporting the empty tray for small screws. |
| tts_cfc3d518fa5a | 位置为三十二，搬大螺丝空料盘 | Posición 32. Transportando la bandeja vacía de tornillos grandes. | Position 32. Transporting the empty tray for large screws. |
| tts_8af10ff9a438 | 位置为三十二，搬小螺丝空料盘 | Posición 32. Transportando la bandeja vacía de tornillos pequeños. | Position 32. Transporting the empty tray for small screws. |
| tts_68cffa1d990e | 位置为三十四，搬大螺丝空料盘 | Posición 34. Transportando la bandeja vacía de tornillos grandes. | Position 34. Transporting the empty tray for large screws. |
| tts_240a55b869e7 | 位置为三十四，搬小螺丝空料盘 | Posición 34. Transportando la bandeja vacía de tornillos pequeños. | Position 34. Transporting the empty tray for small screws. |
| tts_fff922f76f8a | 位置为二十一，搬大螺丝空料盘 | Posición 21. Transportando la bandeja vacía de tornillos grandes. | Position 21. Transporting the empty tray for large screws. |
| tts_b1ebbdf2e08e | 位置为二十一，搬小螺丝空料盘 | Posición 21. Transportando la bandeja vacía de tornillos pequeños. | Position 21. Transporting the empty tray for small screws. |
| tts_f1f347b37c1e | 位置为二十三，搬大螺丝空料盘 | Posición 23. Transportando la bandeja vacía de tornillos grandes. | Position 23. Transporting the empty tray for large screws. |
| tts_12e48d9f7f9f | 位置为二十三，搬小螺丝空料盘 | Posición 23. Transportando la bandeja vacía de tornillos pequeños. | Position 23. Transporting the empty tray for small screws. |
| tts_1fccd5212ae4 | 位置为二十二，搬大螺丝空料盘 | Posición 22. Transportando la bandeja vacía de tornillos grandes. | Position 22. Transporting the empty tray for large screws. |
| tts_6386d508c7bc | 位置为二十二，搬小螺丝空料盘 | Posición 22. Transportando la bandeja vacía de tornillos pequeños. | Position 22. Transporting the empty tray for small screws. |
| tts_2c67ebada2c0 | 位置为二十四，搬大螺丝空料盘 | Posición 24. Transportando la bandeja vacía de tornillos grandes. | Position 24. Transporting the empty tray for large screws. |
| tts_bfecc5f72c67 | 位置为二十四，搬小螺丝空料盘 | Posición 24. Transportando la bandeja vacía de tornillos pequeños. | Position 24. Transporting the empty tray for small screws. |
| tts_982c4345b02a | 位置为十一，搬大螺丝空料盘 | Posición 11. Transportando la bandeja vacía de tornillos grandes. | Position 11. Transporting the empty tray for large screws. |
| tts_8e693375dda1 | 位置为十一，搬小螺丝空料盘 | Posición 11. Transportando la bandeja vacía de tornillos pequeños. | Position 11. Transporting the empty tray for small screws. |
| tts_d20ebfac27d0 | 位置为十三，搬大螺丝空料盘 | Posición 13. Transportando la bandeja vacía de tornillos grandes. | Position 13. Transporting the empty tray for large screws. |
| tts_86e719908b0b | 位置为十三，搬小螺丝空料盘 | Posición 13. Transportando la bandeja vacía de tornillos pequeños. | Position 13. Transporting the empty tray for small screws. |
| tts_ab6f73a8031d | 位置为十二，搬大螺丝空料盘 | Posición 12. Transportando la bandeja vacía de tornillos grandes. | Position 12. Transporting the empty tray for large screws. |
| tts_b0d9f715e72b | 位置为十二，搬小螺丝空料盘 | Posición 12. Transportando la bandeja vacía de tornillos pequeños. | Position 12. Transporting the empty tray for small screws. |
| tts_2d715de2de06 | 位置为十四，搬大螺丝空料盘 | Posición 14. Transportando la bandeja vacía de tornillos grandes. | Position 14. Transporting the empty tray for large screws. |
| tts_36c2372040d1 | 位置为十四，搬小螺丝空料盘 | Posición 14. Transportando la bandeja vacía de tornillos pequeños. | Position 14. Transporting the empty tray for small screws. |
| tts_6421b957df4c | 位置为四十一，搬大螺丝空料盘 | Posición 41. Transportando la bandeja vacía de tornillos grandes. | Position 41. Transporting the empty tray for large screws. |
| tts_4cc48992f918 | 位置为四十一，搬小螺丝空料盘 | Posición 41. Transportando la bandeja vacía de tornillos pequeños. | Position 41. Transporting the empty tray for small screws. |
| tts_e40dbd18ee46 | 位置为四十三，搬大螺丝空料盘 | Posición 43. Transportando la bandeja vacía de tornillos grandes. | Position 43. Transporting the empty tray for large screws. |
| tts_6c7be4b2aad0 | 位置为四十三，搬小螺丝空料盘 | Posición 43. Transportando la bandeja vacía de tornillos pequeños. | Position 43. Transporting the empty tray for small screws. |
| tts_4b9f3a96d493 | 位置为四十二，搬大螺丝空料盘 | Posición 42. Transportando la bandeja vacía de tornillos grandes. | Position 42. Transporting the empty tray for large screws. |
| tts_51b10528347d | 位置为四十二，搬小螺丝空料盘 | Posición 42. Transportando la bandeja vacía de tornillos pequeños. | Position 42. Transporting the empty tray for small screws. |
| tts_5ea637359ee0 | 位置为四十四，搬大螺丝空料盘 | Posición 44. Transportando la bandeja vacía de tornillos grandes. | Position 44. Transporting the empty tray for large screws. |
| tts_a2638c57e2cc | 位置为四十四，搬小螺丝空料盘 | Posición 44. Transportando la bandeja vacía de tornillos pequeños. | Position 44. Transporting the empty tray for small screws. |
| tts_8e965c88310d | 低头动作失败,退出任务 | No se pudo bajar la cabeza. Se abandona la tarea. | Lowering the head failed. Exiting the task. |
| tts_5e51fe179c2d | 低头异常 | Error al bajar la cabeza. | Error lowering the head. |
| tts_6e3b676cf4e1 | 低头异常，航模可以重试 | Error al bajar la cabeza. Se puede volver a intentar desde el radiomando. | Error lowering the head. You can retry using the radio controller. |
| tts_308b20d44a85 | 停止摆臂动作失败，检测运控模块是否异常 | No se pudo detener el balanceo de los brazos. Comprueba si el módulo de control de movimiento presenta errores. | Stopping the arm swing failed. Check the motion control module for errors. |
| tts_3efd59370cea | 停止摆臂动作失败，检测运控模块是否异常，航模可以重试 | No se pudo detener el balanceo de los brazos. Comprueba si el módulo de control de movimiento presenta errores. Se puede volver a intentar desde el radiomando. | Stopping the arm swing failed. Check the motion control module for errors. You can retry using the radio controller. |
| tts_2ba8a376b2b0 | 充电中表情 | Expresión de carga en curso. | Charging expression. |
| tts_78f4e2d8d6e6 | 充电完成 | Carga completada. | Charging completed. |
| tts_52dd66b3cf15 | 充电桩服务正在启动 | Iniciando el servicio de la estación de carga. | The charging station service is starting. |
| tts_1469eb9508cc | 充电桩环境异常,请检查后重试 | Hay un problema con el entorno de la estación de carga. Compruébalo antes de volver a intentarlo. | There is a problem with the charging station environment. Check it before trying again. |
| tts_b376dc0df82e | 充电检测 | Comprobando la carga. | Checking charging status. |
| tts_ccd29831c343 | 全向行走异常 | Error en el desplazamiento omnidireccional. | Omnidirectional movement error. |
| tts_609087c5bf08 | 关闭摆臂失败 | No se pudo desactivar el balanceo de los brazos. | Disabling arm swing failed. |
| tts_1e7b9fe07b91 | 关闭罩子失败 | No se pudo cerrar la cubierta. | Closing the cover failed. |
| tts_846c6373cf7e | 切换行走模式失败 | No se pudo cambiar el modo de desplazamiento. | Changing the movement mode failed. |
| tts_7b79c19febd8 | 前进失败,退出任务 | No se pudo avanzar. Se abandona la tarea. | Moving forward failed. Exiting the task. |
| tts_a37ab28effac | 剩余电量百分之三十，请尽快充电 | Queda un treinta por ciento de batería. Recarga lo antes posible. | Thirty percent battery remaining. Please recharge as soon as possible. |
| tts_7c048b81ff95 | 动画表情服务正在启动 | Iniciando el servicio de expresiones animadas. | The animated expression service is starting. |
| tts_775847120c66 | 参数异常 | Error de parámetros. | Parameter error. |
| tts_b085762d892d | 双手抬起失败 | No se pudieron levantar ambos brazos. | Raising both arms failed. |
| tts_e2eddc2b63aa | 双手放下失败 | No se pudieron bajar ambos brazos. | Lowering both arms failed. |
| tts_2a3db32b7beb | 双目关闭失败，请检查双目程序 | No se pudo desactivar la visión estéreo. Comprueba el programa de visión estéreo. | Disabling stereo vision failed. Check the stereo vision program. |
| tts_3ead6c3324aa | 双目打开失败，请检查双目程序 | No se pudo activar la visión estéreo. Comprueba el programa de visión estéreo. | Enabling stereo vision failed. Check the stereo vision program. |
| tts_b8cd9ef0f11c | 只有一块电池没法换电 | Sólo hay una batería. No es posible realizar el cambio de batería. | Only one battery is present. Battery swapping is not possible. |
| tts_49cd4752d2f7 | 号点 | Punto número. | Point number. |
| tts_90213d5d7ab0 | 后坐完成 | Movimiento de sentado hacia atrás completado. | Backward sitting movement completed. |
| tts_c3a834dec8bb | 后退失败 | No se pudo retroceder. | Moving backward failed. |
| tts_c2f53d1a351e | 后退失败，检查导航模块 | No se pudo retroceder. Comprueba el módulo de navegación. | Moving backward failed. Check the navigation module. |
| tts_a22c99eb8a5e | 启动定位失败 | No se pudo iniciar la localización. | Starting localization failed. |
| tts_0495785ebf98 | 回正失败 | No se pudo volver a la posición centrada. | Returning to the centered position failed. |
| tts_7ceddb720c3c | 回腰异常 | Error al devolver la cintura a su posición. | Error returning the waist to its position. |
| tts_e956ba151004 | 回零完成 | Retorno a la posición inicial completado. | Return to the home position completed. |
| tts_689b53aeea6a | 大家好，科鲁泽一号机，为您服务 | Hola a todos. Soy Cruzr número uno, a vuestro servicio. | Hello everyone. Cruzr number one, at your service. |
| tts_f8d2ef0933ce | 大模型超时，请检查连接 | El modelo de lenguaje ha superado el tiempo de espera. Comprueba la conexión. | The language model timed out. Check the connection. |
| tts_900bc0a29a6d | 大模型路径规划失败 | Ha fallado la planificación de ruta del modelo de lenguaje. | Language model path planning failed. |
| tts_868d05a30488 | 头部回零异常 | Error al devolver la cabeza a la posición inicial. | Error returning the head to its home position. |
| tts_615ca052ec55 | 头部回零异常，检查运控模块是否需要重启 | Error al devolver la cabeza a la posición inicial. Comprueba si es necesario reiniciar el módulo de control de movimiento. | Error returning the head to its home position. Check whether the motion control module needs restarting. |
| tts_14f8113a46e2 | 头部回零异常，检查运控模块是否需要重启，航模可以重试 | Error al devolver la cabeza a la posición inicial. Comprueba si es necesario reiniciar el módulo de control de movimiento. Se puede volver a intentar desde el radiomando. | Error returning the head to its home position. Check whether the motion control module needs restarting. You can retry using the radio controller. |
| tts_c7dcf8336991 | 头部回零异常，航模可以重试 | Error al devolver la cabeza a la posición inicial. Se puede volver a intentar desde el radiomando. | Error returning the head to its home position. You can retry using the radio controller. |
| tts_5cb654586040 | 头部控制异常 | Error de control de la cabeza. | Head control error. |
| tts_b1e02ae9cc98 | 头部无法回零，检查运控模块 | La cabeza no puede volver a la posición inicial. Comprueba el módulo de control de movimiento. | The head cannot return to its home position. Check the motion control module. |
| tts_4f7799da3044 | 头部无法回零，检查运控模块，航模可以重试 | La cabeza no puede volver a la posición inicial. Comprueba el módulo de control de movimiento. Se puede volver a intentar desde el radiomando. | The head cannot return to its home position. Check the motion control module. You can retry using the radio controller. |
| tts_1af6e5945aeb | 奇偶数是： | La paridad es: | The parity is: |
| tts_1d280880da98 | 导航到保护罩失败 | No se pudo navegar hasta la cubierta de protección. | Navigation to the protective cover failed. |
| tts_bb38c45a39eb | 导航到放箱子点失败，检查障碍物，检查导航模块是否异常 | No se pudo navegar hasta el punto de depósito de cajas. Comprueba si hay obstáculos. Comprueba si el módulo de navegación presenta errores. | Navigation to the box placement point failed. Check for obstacles. Check the navigation module for errors. |
| tts_70e20b7ef367 | 导航到放箱子点失败，检查障碍物，检查导航模块是否异常，航模可以重试 | No se pudo navegar hasta el punto de depósito de cajas. Comprueba si hay obstáculos. Comprueba si el módulo de navegación presenta errores. Se puede volver a intentar desde el radiomando. | Navigation to the box placement point failed. Check for obstacles. Check the navigation module for errors. You can retry using the radio controller. |
| tts_4c3762a5a74f | 导航到目标点失败,退出任务 | No se pudo navegar hasta el punto de destino. Se abandona la tarea. | Navigation to the target point failed. Exiting the task. |
| tts_8a0004a01e3c | 导航到箱子位置失败 | No se pudo navegar hasta la posición de la caja. | Navigation to the box location failed. |
| tts_02a2359cbcd6 | 导航到箱子失败，退出任务 | No se pudo navegar hasta la caja. Se abandona la tarea. | Navigation to the box failed. Exiting the task. |
| tts_b6e861d54695 | 导航定位失败 | La localización de navegación ha fallado. | Navigation localization failed. |
| tts_c43076af623a | 导航定位成功 | Localización de navegación completada. | Navigation localization succeeded. |
| tts_d551b8a66f3d | 导航未开始 | La navegación no ha comenzado. | Navigation has not started. |
| tts_958f2b3e843a | 导航未开始1 | La navegación no ha comenzado. Uno. | Navigation has not started. One. |
| tts_29197acc4a57 | 导航盲走后退异常 | Error de retroceso sin realimentación de navegación. | Error moving backward without navigation feedback. |
| tts_6e3a8374e4c0 | 导航盲走后退异常，航模可以重试 | Error de retroceso sin realimentación de navegación. Se puede volver a intentar desde el radiomando. | Error moving backward without navigation feedback. You can retry using the radio controller. |
| tts_7c7566f98384 | 层数错误 | Número de niveles incorrecto. | Incorrect number of levels. |
| tts_4bdfe9eac470 | 工件已离开 | La pieza ha salido. | The workpiece has left. |
| tts_a26ad97ce73f | 工件抵达，开始工作 | La pieza ha llegado. Comenzando el trabajo. | The workpiece has arrived. Starting work. |
| tts_bb46c5595a74 | 工作中，请注意避让 | Robot trabajando. Mantén libre el espacio de trabajo. | Robot at work. Please keep clear of the work area. |
| tts_cb6b3d18a90a | 底盘绿色常亮灯 | Luz verde del chasis encendida de forma continua. | Chassis green light steadily on. |
| tts_e1f03b58bb68 | 底盘绿色闪烁 | Luz verde del chasis intermitente. | Chassis green light flashing. |
| tts_fa45d138e227 | 建图失败 | No se pudo crear el mapa. | Map creation failed. |
| tts_d149c352ce24 | 开始执行循环任务 | Comenzando la tarea repetitiva. | Starting the repeating task. |
| tts_0d8ccbe0eb04 | 开始执行第 | Comenzando la iteración número: | Starting iteration number: |
| tts_66726fae4fdc | 开始执行第二趟任务 | Comenzando el segundo recorrido de la tarea. | Starting the second task run. |
| tts_7057a263e305 | 开始搬运箱号为1的箱子 | Comenzando el transporte de la caja número uno. | Starting transport of box number one. |
| tts_086fd04498da | 开始搬运箱号为2的箱子 | Comenzando el transporte de la caja número dos. | Starting transport of box number two. |
| tts_8cab41d321c4 | 当前is_placing_box的值是： | El valor actual de is placing box es: | The current value of is placing box is: |
| tts_7362afa2e686 | 当前map_self的值是： | El valor actual de map self es: | The current value of map self is: |
| tts_89f4880f8655 | 当前point3_pick_arrive的值是： | El valor actual de point three pick arrive es: | The current value of point three pick arrive is: |
| tts_93ecead7eb34 | 当前机器人连接充电器，拒绝执行任务 | El robot está conectado al cargador. No se puede ejecutar la tarea. | The robot is connected to the charger. The task cannot be executed. |
| tts_bb9be02d1e1d | 当前正在上桩充电，禁止执行任务 | El robot está acoplándose a la estación de carga. No se permite ejecutar la tarea. | The robot is docking for charging. Task execution is not permitted. |
| tts_e8e26bbeb4c6 | 当前电池电量低于百分之15，拒绝执行任务 | La batería está por debajo del quince por ciento. No se puede ejecutar la tarea. | The battery is below fifteen percent. The task cannot be executed. |
| tts_7a340b6a7250 | 当前电池电量低于百分之40，拒绝执行任务 | La batería está por debajo del cuarenta por ciento. No se puede ejecutar la tarea. | The battery is below forty percent. The task cannot be executed. |
| tts_b20125697049 | 当前电池电量高于百分之八十，等待任务 | La batería está por encima del ochenta por ciento. Esperando una tarea. | The battery is above eighty percent. Waiting for a task. |
| tts_de87b334a5b5 | 您好，我是科鲁泽二号机，欢迎来到优必选智能机器人展厅 | Hola. Soy Cruzr número dos. Bienvenido a la exposición de robots inteligentes de UBTECH. | Hello. I am Cruzr number two. Welcome to the UBTECH intelligent robot showroom. |
| tts_203b284df186 | 我再尝试一次 | Voy a intentarlo una vez más. | I will try once more. |
| tts_633f91d6ad2a | 我准备好了 | Estoy preparado. | I am ready. |
| tts_4f7e5caf7c13 | 我在大箱子点，我要开始搬大箱子了 | Estoy en el punto de cajas grandes. Voy a recoger una caja grande. | I am at the large box location. I will start picking up a large box. |
| tts_debb5d805e69 | 我在大箱子点，我要开始放大箱子了 | Estoy en el punto de cajas grandes. Voy a depositar una caja grande. | I am at the large box location. I will start placing a large box. |
| tts_ec0e7cfa74ff | 我在小箱子点，我要开始搬小箱子了 | Estoy en el punto de cajas pequeñas. Voy a recoger una caja pequeña. | I am at the small box location. I will start picking up a small box. |
| tts_6013652bca32 | 我在小箱子点，我要开始放小箱子了 | Estoy en el punto de cajas pequeñas. Voy a depositar una caja pequeña. | I am at the small box location. I will start placing a small box. |
| tts_f8d1f818b6ca | 我在工作,请注意避让 | Estoy trabajando. Mantén libre el espacio de trabajo. | I am working. Please keep clear of the work area. |
| tts_af476ddc7310 | 我在工作，请注意避让 | Estoy trabajando. Mantén libre el espacio de trabajo. | I am working. Please keep clear of the work area. |
| tts_7bdceb69d01a | 我开始拆垛动作 | Voy a comenzar a desapilar las cajas. | I will start unstacking the boxes. |
| tts_c26a4cc3df79 | 我要做个前坐动作 | Voy a realizar un movimiento de sentado hacia delante. | I will perform a forward sitting movement. |
| tts_d4fec3db1f63 | 我要做个半蹲动作 | Voy a realizar una media sentadilla. | I will perform a half squat. |
| tts_93ba40196adc | 我要做个后蹲动作 | Voy a agacharme hacia atrás. | I will squat backward. |
| tts_9832772970ce | 我要做个打招呼动作 | Voy a realizar un gesto de saludo. | I will perform a greeting gesture. |
| tts_8e517f65df09 | 我要先下桩了 | Primero voy a salir de la estación de carga. | I will leave the charging station first. |
| tts_cc20c90bbf1a | 我要前置抓箱子动作 | Voy a realizar el movimiento previo al agarre de la caja. | I will perform the movement before grasping the box. |
| tts_493f4e2bcf6a | 我要动腰动作 | Voy a mover la cintura. | I will move my waist. |
| tts_03460a506306 | 我要去一号位置拿箱子 | Voy a la posición uno a recoger una caja. | I will go to position one to pick up a box. |
| tts_5884dac31646 | 我要去二号位置拿箱子 | Voy a la posición dos a recoger una caja. | I will go to position two to pick up a box. |
| tts_a5446992cc3f | 我要去放置箱子 | Voy a depositar la caja. | I will go to place the box. |
| tts_6a81469f95e7 | 我要后置抓箱子动作 | Voy a realizar el movimiento posterior al agarre de la caja. | I will perform the movement after grasping the box. |
| tts_759b44daf561 | 我要后退动作 | Voy a retroceder. | I will move backward. |
| tts_6a654b675584 | 我要回初始位置了 | Voy a volver a la posición inicial. | I will return to the initial position. |
| tts_1d79c8b67e54 | 我要回零动作 | Voy a volver a la posición HOME. | I will return to the home position. |
| tts_925ab34062b7 | 我要导航到： | Voy a navegar hasta: | I will navigate to: |
| tts_d99200f91bc8 | 我要开始上桩充电了 | Voy a acoplarme a la estación de carga. | I will dock at the charging station. |
| tts_3fe52377dc9b | 我要开始上桩充电了2 | Voy a acoplarme a la estación de carga. Dos. | I will dock at the charging station. Two. |
| tts_c43d839a9e83 | 我要开始下桩了 | Voy a salir de la estación de carga. | I will leave the charging station. |
| tts_a09996a8d85a | 我要开始下桩充电了 | Voy a salir de la estación de carga. | I will leave the charging station. |
| tts_61245fa78dc1 | 我要开始下桩充电了5 | Voy a salir de la estación de carga. Cinco. | I will leave the charging station. Five. |
| tts_5d3e914b03de | 我要开始下桩操作 | Comenzando la salida de la estación de carga. | Starting the undocking procedure. |
| tts_18e4d2c8fbf2 | 我要开始传输数据了 | Voy a comenzar a transmitir datos. | I will start transmitting data. |
| tts_c30c230cd5ef | 我要开始传输数据了4 | Voy a comenzar a transmitir datos. Cuatro. | I will start transmitting data. Four. |
| tts_1db46001e085 | 我要开始工作了 | Voy a comenzar la tarea. | I will start the task. |
| tts_2ae677672105 | 我要开始工作啦 | Voy a comenzar la tarea. | I will start the task. |
| tts_823535c0f61a | 我要开始工作啦  | Voy a comenzar la tarea. | I will start the task. |
| tts_61cc11b67669 | 我要开始工作啦! | Voy a comenzar la tarea. | I will start the task. |
| tts_fc25a8c52d0c | 我要开始抓取了 | Voy a comenzar el agarre. | I will start grasping. |
| tts_51210759f96e | 我要开始抓取橙子 | Voy a recoger una naranja. | I will pick up an orange. |
| tts_b671e81c7a95 | 我要开始抓取苹果 | Voy a recoger una manzana. | I will pick up an apple. |
| tts_2e1c3f9a32cc | 我要开始接收数据了 | Voy a comenzar a recibir datos. | I will start receiving data. |
| tts_d1be3044652d | 我要开始接收数据了3 | Voy a comenzar a recibir datos. Tres. | I will start receiving data. Three. |
| tts_9b9fa1d781d5 | 我要开始搬第一个位置箱子 | Voy a recoger la caja de la primera posición. | I will pick up the box at the first position. |
| tts_9025af656379 | 我要开始搬第二个位置箱子 | Voy a recoger la caja de la segunda posición. | I will pick up the box at the second position. |
| tts_43c263a411a1 | 我要开始搬箱子动作了 | Voy a comenzar el movimiento para transportar la caja. | I will start the box transport movement. |
| tts_e6871a0d2366 | 我要放箱子动作 | Voy a realizar el movimiento para depositar la caja. | I will perform the box placement movement. |
| tts_9a94327b4479 | 手未运动到初始状态,拒绝执行 | Los brazos no han alcanzado su postura inicial. No se permite la ejecución. | The arms have not reached their initial posture. Execution is refused. |
| tts_55f25d4fac9d | 手臂任务执行错误 | Error al ejecutar la tarea de los brazos. | Arm task execution error. |
| tts_460008739abe | 打开位姿检测失败，检查视觉模块是否需要重启 | No se pudo activar la detección de pose. Comprueba si es necesario reiniciar el módulo de visión. | Enabling pose detection failed. Check whether the vision module needs restarting. |
| tts_e18c67090067 | 打开位姿检测失败，检查视觉模块是否需要重启，航模可以重试 | No se pudo activar la detección de pose. Comprueba si es necesario reiniciar el módulo de visión. Se puede volver a intentar desde el radiomando. | Enabling pose detection failed. Check whether the vision module needs restarting. You can retry using the radio controller. |
| tts_fe279a3e7a38 | 打开摆臂失败 | No se pudo activar el balanceo de los brazos. | Enabling arm swing failed. |
| tts_2f3fe1e07a3a | 打开罩子失败 | No se pudo abrir la cubierta. | Opening the cover failed. |
| tts_44fa5290b06b | 抓取失败,退出任务 | El agarre ha fallado. Se abandona la tarea. | Grasping failed. Exiting the task. |
| tts_a22abeae8224 | 抓取失败，退出任务 | El agarre ha fallado. Se abandona la tarea. | Grasping failed. Exiting the task. |
| tts_51b812650e41 | 投料任务结束 | Tarea de descarga de material terminada. | Material unloading task finished. |
| tts_b581ef5529a2 | 抬头失败 | No se pudo levantar la cabeza. | Raising the head failed. |
| tts_41b30f4df9d6 | 抬手异常 | Error al levantar los brazos. | Error raising the arms. |
| tts_f13841ccf04a | 换手 | Cambiando de mano. | Switching hands. |
| tts_3189da16f0ee | 换电失败，急需人工协助！ | El cambio de batería ha fallado. Se necesita asistencia humana urgente. | Battery swapping failed. Urgent human assistance is required. |
| tts_fdc2bfbb2afa | 搬箱子过程掉了 | La caja se ha caído durante el transporte. | The box was dropped during transport. |
| tts_eed2bf676621 | 搬箱子运控规划失败，退出任务 | Ha fallado la planificación de movimiento para transportar la caja. Se abandona la tarea. | Motion planning for box transport failed. Exiting the task. |
| tts_8c4a9c8b48b3 | 搬起箱子失败 | No se pudo levantar la caja. | Lifting the box failed. |
| tts_b56ee4391986 | 搬运初始化完毕 | Inicialización del transporte completada. | Transport initialization completed. |
| tts_de64a482be5f | 搬运失败，请人工介入处理 | El transporte ha fallado. Se necesita intervención humana. | Transport failed. Human intervention is required. |
| tts_2e764e4e4cb7 | 搬运成功 | Transporte completado correctamente. | Transport succeeded. |
| tts_d05af908ad19 | 撸起袖子加油干！我们是永不停机的新质生产力。 | ¡Manos a la obra! Somos la nueva fuerza productiva que nunca se detiene. | Let's get to work! We are the new productive force that never stops. |
| tts_10621aba535c | 放箱子前伸手失败 | No se pudieron extender los brazos antes de depositar la caja. | Extending the arms before placing the box failed. |
| tts_a5b1f52f642e | 放箱子动作异常，检查运控模块 | Error en el movimiento para depositar la caja. Comprueba el módulo de control de movimiento. | Box placement movement error. Check the motion control module. |
| tts_7df9f16ecbec | 放箱子动作异常，检查运控模块，航模可以重试 | Error en el movimiento para depositar la caja. Comprueba el módulo de control de movimiento. Se puede volver a intentar desde el radiomando. | Box placement movement error. Check the motion control module. You can retry using the radio controller. |
| tts_75a98844976b | 放箱子失败 | No se pudo depositar la caja. | Placing the box failed. |
| tts_76ad02006077 | 放箱子错误 | Error al depositar la caja. | Box placement error. |
| tts_52503161b1ed | 放置异常 | Error de colocación. | Placement error. |
| tts_1164ac511a50 | 放置螺丝失败，请人工处理 | No se pudo colocar el tornillo. Se necesita intervención humana. | Placing the screw failed. Human intervention is required. |
| tts_dc555587e158 | 料盘为空，终止分拣流程 | La bandeja está vacía. Se detiene el proceso de clasificación. | The tray is empty. Stopping the sorting process. |
| tts_79abdd0cd5d2 | 料盘搬运初始化完毕 | Inicialización del transporte de bandejas completada. | Tray transport initialization completed. |
| tts_4a2a94036414 | 料盘搬运失败 | El transporte de la bandeja ha fallado. | Tray transport failed. |
| tts_f2bfd2bb7c01 | 料盘搬运成功 | Transporte de la bandeja completado correctamente. | Tray transport succeeded. |
| tts_70b40bf6a607 | 无法恢复手臂，检查运控模块 | No se pueden devolver los brazos a su postura. Comprueba el módulo de control de movimiento. | The arms cannot be returned to their posture. Check the motion control module. |
| tts_ad428b6ef881 | 无法恢复手臂，检查运控模块，航模可以重试 | No se pueden devolver los brazos a su postura. Comprueba el módulo de control de movimiento. Se puede volver a intentar desde el radiomando. | The arms cannot be returned to their posture. Check the motion control module. You can retry using the radio controller. |
| tts_5e482930369f | 无法恢复腰部位置，检查运控模块 | No se puede recuperar la posición de la cintura. Comprueba el módulo de control de movimiento. | The waist position cannot be restored. Check the motion control module. |
| tts_8c0f3048f80a | 无法获取机器人位姿信息 | No se puede obtener la pose del robot. | The robot pose cannot be retrieved. |
| tts_7bf12bf11557 | 无法获取机器人位姿信息，航模可以重试 | No se puede obtener la pose del robot. Se puede volver a intentar desde el radiomando. | The robot pose cannot be retrieved. You can retry using the radio controller. |
| tts_d6c61c181ab6 | 暂无物料 | No hay material disponible. | No material is available. |
| tts_b3683aa2df7f | 暂无物料箱子 | No hay cajas de material disponibles. | No material boxes are available. |
| tts_ebab7e803e9b | 暂无物料箱子,退出任务 | No hay cajas de material disponibles. Se abandona la tarea. | No material boxes are available. Exiting the task. |
| tts_8dfeaf70c9f5 | 有任务正在执行 | Hay una tarea en ejecución. | A task is running. |
| tts_f0437bad6bf8 | 未充电我要开始下桩了1 | No se está cargando. Voy a salir de la estación. Uno. | Not charging. I will leave the charging station. One. |
| tts_73cd47140b80 | 机器未启动 | El robot no ha arrancado. | The robot has not started. |
| tts_0d0acac0b941 | 机器正在充电 | El robot está cargando. | The robot is charging. |
| tts_71f7d9350069 | 检测地图 | Comprobando el mapa. | Checking the map. |
| tts_822800b4d4c0 | 次任务 | Tarea. | Task. |
| tts_310427034483 | 正在充电 | Carga en curso. | Charging in progress. |
| tts_6754d036d151 | 正在充电,当前电池电量低于百分之40，拒绝执行任务 | Carga en curso. La batería está por debajo del cuarenta por ciento. No se puede ejecutar la tarea. | Charging in progress. The battery is below forty percent. The task cannot be executed. |
| tts_652daddc753b | 正在回收空箱 | Recogiendo las cajas vacías. | Collecting empty boxes. |
| tts_325277b52536 | 正在导航定位可能需要一会儿哦 | Localizando el robot para navegar. Puede tardar un momento. | Localizing the robot for navigation. This may take a moment. |
| tts_e83d2e027cc0 | 正在执行第 | Ejecutando la tarea número: | Executing task number: |
| tts_68469d353053 | 毛宁表示，日方在与中国台湾邻近的西南诸岛部署进攻性武器，刻意制造地区紧张，挑动军事对立，联系到日本首相高市早苗的涉台错误言论，这一动向极其危险，需要引起周边国家及国际社会的高度警惕 | Mao Ning declaró que Japón está desplegando armas ofensivas en las islas del sudoeste próximas a Taiwán, a la que se refiere como parte de China, creando deliberadamente tensiones regionales y fomentando la confrontación militar. Relacionó este hecho con las declaraciones sobre Taiwán de la primera ministra japonesa, Sanae Takaichi, que calificó de erróneas, y afirmó que esta evolución es sumamente peligrosa y exige una gran vigilancia de los países vecinos y de la comunidad internacional. | Mao Ning stated that Japan is deploying offensive weapons on its southwestern islands near Taiwan, which she referred to as part of China, deliberately creating regional tensions and provoking military confrontation. Linking this to Japanese Prime Minister Sanae Takaichi's remarks on Taiwan, which she described as erroneous, she called this development extremely dangerous and said it requires heightened vigilance from neighboring countries and the international community. |
| tts_19da7f67bf4b | 物体丢失 | Se ha perdido el objeto. | The object has been lost. |
| tts_4aa9934131cf | 物体丢失，退出任务 | Se ha perdido el objeto. Se abandona la tarea. | The object has been lost. Exiting the task. |
| tts_6c64a9ef2237 | 物体移动，重新规划 | El objeto se ha movido. Volviendo a planificar. | The object has moved. Replanning. |
| tts_c6117ec8f077 | 现在我们到了桌面机器人展位，悟空机器人，你的第一个智能小伙伴 | Hemos llegado al espacio de robots de sobremesa. Wukong, tu primer compañero inteligente. | We have arrived at the desktop robot stand. Wukong, your first intelligent companion. |
| tts_f73320f0a9c3 | 现在看到的是Walk系列机器人，他正在做物品识别的演示 | Este es un robot de la serie Walk. Está haciendo una demostración de reconocimiento de objetos. | This is a Walk series robot. It is demonstrating object recognition. |
| tts_7476fcfc16f9 | 电量低，请尽快充电 | Batería baja. Recarga lo antes posible. | Low battery. Please recharge as soon as possible. |
| tts_2ec543c32151 | 电量极低，请尽快充电 | Batería muy baja. Recarga lo antes posible. | Very low battery. Please recharge as soon as possible. |
| tts_572befa6a627 | 盲走前进异常 | Error de avance sin realimentación de navegación. | Error moving forward without navigation feedback. |
| tts_096c49e3953d | 科鲁泽一号机，为您服务 | Cruzr número uno, a tu servicio. | Cruzr number one, at your service. |
| tts_df129045f249 | 空箱回收任务结束 | Tarea de recogida de cajas vacías terminada. | Empty box collection task finished. |
| tts_03eb419a97ef | 空箱回收异常 | Error al recoger cajas vacías. | Empty box collection error. |
| tts_93e945bd5031 | 等待三分钟后执行第二趟任务 | Esperaré tres minutos antes de comenzar el segundo recorrido. | I will wait three minutes before starting the second task run. |
| tts_e9f0f2f87dc3 | 箱号错误，请重新指定任务 | Número de caja incorrecto. Selecciona de nuevo la tarea. | Incorrect box number. Please select the task again. |
| tts_bf44e7a663d4 | 箱子已放置完毕 | La caja ha sido depositada. | The box has been placed. |
| tts_26dfcf79df63 | 终止摆臂动作失败，，检查运控模块是否需要重启 | No se pudo detener el balanceo de los brazos. Comprueba si es necesario reiniciar el módulo de control de movimiento. | Stopping the arm swing failed. Check whether the motion control module needs restarting. |
| tts_b0925f6812ee | 终止摆臂动作失败，，检查运控模块是否需要重启，航模可以重试 | No se pudo detener el balanceo de los brazos. Comprueba si es necesario reiniciar el módulo de control de movimiento. Se puede volver a intentar desde el radiomando. | Stopping the arm swing failed. Check whether the motion control module needs restarting. You can retry using the radio controller. |
| tts_04566a1eb4f6 | 结束工作 | Trabajo terminado. | Work finished. |
| tts_d98755b20a76 | 腰部上升异常 | Error al elevar la cintura. | Error raising the waist. |
| tts_f058791e6322 | 腰部上升异常，航模可以重试 | Error al elevar la cintura. Se puede volver a intentar desde el radiomando. | Error raising the waist. You can retry using the radio controller. |
| tts_c3784dcb0f16 | 获取启动标识参数异常 | Error al obtener el parámetro de inicio. | Error retrieving the startup flag parameter. |
| tts_abb826777cb4 | 获取地图 | Obteniendo el mapa. | Retrieving the map. |
| tts_275152e328b7 | 获取导航充电桩类型环境变量参数异常 | Error al obtener la variable del tipo de estación de carga de navegación. | Error retrieving the navigation charging station type environment variable. |
| tts_19e44f6a148f | 获取导航类型环境变量参数异常 | Error al obtener la variable del tipo de navegación. | Error retrieving the navigation type environment variable. |
| tts_39a36cdfe9e5 | 螺丝分拣失败 | La clasificación de tornillos ha fallado. | Screw sorting failed. |
| tts_067c77dc94b5 | 视觉开启失败 | No se pudo activar la visión. | Enabling vision failed. |
| tts_df086657e659 | 视觉模块异常 | Error en el módulo de visión. | Vision module error. |
| tts_f4a26d137ef2 | 视觉模块异常，航模可以重试 | Error en el módulo de visión. Se puede volver a intentar desde el radiomando. | Vision module error. You can retry using the radio controller. |
| tts_7f89d2fc33e4 | 视觉识别错误 | Error de reconocimiento visual. | Visual recognition error. |
| tts_60b8ccd76c9e | 记录腰部位置异常 | Error al registrar la posición de la cintura. | Error recording the waist position. |
| tts_64cb95c6ecbe | 记录腰部位置异常，检测运控模块是否异常 | Error al registrar la posición de la cintura. Comprueba si el módulo de control de movimiento presenta errores. | Error recording the waist position. Check the motion control module for errors. |
| tts_93d6339fd02d | 记录腰部位置异常，检测运控模块是否异常，航模可以重试 | Error al registrar la posición de la cintura. Comprueba si el módulo de control de movimiento presenta errores. Se puede volver a intentar desde el radiomando. | Error recording the waist position. Check the motion control module for errors. You can retry using the radio controller. |
| tts_5eaf405840fc | 设置地图 | Seleccionando el mapa. | Setting the map. |
| tts_b8b5965b96f6 | 设置地图1 | Seleccionando el mapa. Uno. | Setting the map. One. |
| tts_778d4edb183b | 设置地图111 | Seleccionando el mapa. Uno uno uno. | Setting the map. One one one. |
| tts_3199eb8337b8 | 设置地图失败 | No se pudo seleccionar el mapa. | Setting the map failed. |
| tts_41d67261fdb5 | 请您喝水 | Aquí tienes agua. | Please have some water. |
| tts_5bcf3228f196 | 调摆臂动作失败，检测运控模块是否异常 | No se pudo ajustar el balanceo de los brazos. Comprueba si el módulo de control de movimiento presenta errores. | Adjusting the arm swing failed. Check the motion control module for errors. |
| tts_ade472bf3160 | 调整重心失败 | No se pudo ajustar el centro de gravedad. | Adjusting the center of gravity failed. |
| tts_0a1b90a59143 | 调用取箱失败，检测运控模块是否异常 | No se pudo iniciar la recogida de la caja. Comprueba si el módulo de control de movimiento presenta errores. | Starting box pickup failed. Check the motion control module for errors. |
| tts_114707fc1788 | 调用摆臂姿势失败，检测运控模块是否异常 | No se pudo activar la postura de balanceo de los brazos. Comprueba si el módulo de control de movimiento presenta errores. | Activating the arm swing posture failed. Check the motion control module for errors. |
| tts_df26baf4642c | 调用摆臂姿势失败，检测运控模块是否异常，航模可以重试 | No se pudo activar la postura de balanceo de los brazos. Comprueba si el módulo de control de movimiento presenta errores. Se puede volver a intentar desde el radiomando. | Activating the arm swing posture failed. Check the motion control module for errors. You can retry using the radio controller. |
| tts_76a3461f8653 | 超出工作空间，请移动一下再试试吧 | Fuera del espacio de trabajo. Reubica el robot antes de volver a intentarlo. | Outside the workspace. Reposition the robot before trying again. |
| tts_50f917a7177f | 踏步失败 | No se pudo realizar el paso en el sitio. | Stepping in place failed. |
| tts_22a16cf4df96 | 转腰失败 | No se pudo girar la cintura. | Turning the waist failed. |
| tts_13c99c24e904 | 轮 | Iteración. | Iteration. |
| tts_850078cc330d | 运控控制暂时预留 | Control de movimiento reservado para uso futuro. | Motion control reserved for future use. |
| tts_cf195d80fd9b | 还未充电 | La carga todavía no ha comenzado. | Charging has not started yet. |
| tts_f0428d8b60ec | 还未指定任务，请从网页指定任务后重启任务管理器 | No se ha seleccionado una tarea. Selecciónala en la página web y reinicia el gestor de tareas. | No task has been selected. Select a task on the web page, then restart the task manager. |
| tts_6718e09577d0 | 重抓 | Nuevo intento de agarre. | Grasping again. |
| tts_b7fb4803a52d | 错误手臂未到ready状态 | Error. Los brazos no han alcanzado la postura de preparación. | Error. The arms have not reached the ready posture. |
| tts_e24ad0358b19 | 需要帮助移动一下箱子 | Necesito ayuda para mover la caja. | I need help moving the box. |

## Grabaciones habladas

| Original | Español propuesto | Inglés TTS | Revisión |
|---|---|---|---|
| child_01.wav | ¡Hola! Tu compañero robot está preparado. ¡Encantado de conocerte! | Hi! Your robot companion is ready. Nice to meet you! | traducción de transcripción automática; revisión auditiva humana pendiente |
| female_01.wav | Hola. Soy tu compañero robot. Encantado de ayudarte. | Hello. I am your robot companion. I am happy to help you. | traducción de transcripción automática; revisión auditiva humana pendiente |
| male_01.wav | Hola. Soy tu compañero robot. Puedes llamarme cuando quieras. | Hello. I am your robot companion. You can call me whenever you like. | traducción de transcripción automática; revisión auditiva humana pendiente |
| 1.wav | Primero recoge la documentación de los huéspedes para hacer el registro. Después comunícate con ellos por correo electrónico. La cena de la hora feliz del salón es bastante sencilla; el desayuno está bastante bien. | First collect the guests' identification for check-in. Then communicate with them by email. The lounge happy hour dinner is fairly simple; breakfast is quite good. | traducción de transcripción automática; revisión auditiva humana pendiente |
| 在的-child_01.wav | Aquí estoy. | I am here. | propuesta por nombre y ASR de las otras voces; infantil ambiguo |
| 在的-male_01.wav | Aquí estoy. | I am here. | ASR y nombre concordantes; revisión auditiva humana pendiente |
| 在的-female_01.wav | Aquí estoy. | I am here. | ASR y nombre concordantes; revisión auditiva humana pendiente |

## Variables dinámicas pendientes de integración

`{agv_status_message}`, `{arm_clamp_error_msg}`, `{arm_error_put_box}`, `{arm_error_ready_start}`, `{arm_error_wbc_clamp_600_400}`, `{check_error_msg}`, `{clamp_box_edge_error_msg}`, `{clamp_error_msg}`, `{clamp_ready_error_msg}`, `{demon_count}`, `{depallet_error_msg}`, `{end_point2_back_error_msg}`, `{end_point_error_msg}`, `{grab_box_error}`, `{greetings_s2_error_msg}`, `{is_placing_box}`, `{lay_error_msg}`, `{look_high_box_error_msg}`, `{map_self_str}`, `{map_set_error_msg}`, `{message}`, `{move_biped_home_error_msg}`, `{move_box_up_or_down_error_msg}`, `{move_head_error_msg}`, `{move_head_home_error_msg}`, `{move_head_lower_error_msg}`, `{move_head_up_error_msg}`, `{move_head_upper_error_msg}`, `{move_s2_waist_s2_error_msg}`, `{nav_code_str}`, `{nav_error_msg}`, `{odd_enev_num}`, `{pole_message}`, `{push_error_msg}`, `{put_collision_error_msg}`, `{put_error_msg}`, `{put_height}`, `{put_ready_error_msg}`, `{relocation_error_msg}`, `{rept_num}`, `{row_oper_num}`, `{send_success}`, `{separate_error_msg}`, `{set_map_error_msg}`, `{stop_navigation_error_msg}`, `{swing_arm_start_error_msg}`, `{swing_arm_stop_error_msg}`, `{target_pos}`, `{to_box_error_msg}`, `{to_box_error}`, `{to_dest__error}`, `{to_put_error_msg}`, `{to_target_id_error}`, `{toal_time}`, `{transport_vision_switch_error_msg}`, `{tts_object}`, `{ttsresult}`, `{vnav_to_box_error_msg}`, `{voice_rept_num}`, `{voice}`
