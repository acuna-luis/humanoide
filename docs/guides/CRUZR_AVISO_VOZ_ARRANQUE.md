# Aviso de voz y pantalla al encender el Cruzr S2

## Ampliación visual — 2026-09-10

**VERIFICADO en la pantalla de esta unidad:** `巡检` es el recurso del catálogo
`inspection.mp4`, un anillo azul con un barrido animado. Se conserva la frase
inglesa. Después del chequeo previo y de la voz, el servicio muestra ese vídeo
mientras continúa comprobando la primera espera de liberación del E-stop.
No significa que hayan terminado el autodiagnóstico, StartMotion o HOME.

El visor conserva la expresión nativa por debajo. Sólo añade el vídeo cuando
la expresión del proveedor es `breath`; cualquier otra expresión, incluida
una advertencia roja/amarilla/naranja o pantalla de apagado, tiene prioridad.
No se llama a servicios de expresión, no se publica un color y no se modifica
la base de fallos. No usar este vídeo fuera de la fase inicial de encendido
como permiso de movimiento; el propio catálogo también permite seleccionarlo
manualmente para otros usos.

La indicación usa permisos de visualización que caducan en **12 segundos**.
Se renuevan mediante lecturas de Motion, las seis cámaras con marcas crecientes,
paros/cargador y el mismo proceso de CC. Si se libera el paro, cambia la fase,
falla una lectura o termina el servicio, se retira la indicación; la caducidad
en el navegador también protege frente a una caída del proceso. No se promete
retirada instantánea ante pérdida de datos. Las advertencias nativas se muestran
en cuanto cambia su elemento de vídeo. Espera máxima del aviso visual: 30 min.

Archivos adicionales: `scripts/upgrade/cruzr_boot_visual.py` y
`scripts/upgrade/cruzr-boot-ready.js`, instalados en `/etc/walker/boot/` de Vision.
El gestor añade una referencia al JavaScript en el `index.html` conocido de
`walker-web.web-expression-1`. Rechaza una página distinta tras una actualización.
Los archivos del visor sobreviven al reinicio normal del contenedor. Si se
recrea con la misma imagen, la preparación vuelve a aplicar el añadido;
puede requerir recargar el visor si éste ya había abierto la página anterior.
Una actualización a otra imagen exige revisar el contrato antes de instalar.

`cruzr-boot-voice.service` sigue habilitado, ahora `Type=simple`, con duración
limitada dentro del programa y sin reinicio automático. Conserva el registro
de voz única por boot. `--check` continúa siendo sólo lectura; `--check --visual`
permite una prueba explícita del aviso visual, con todas las comprobaciones
previas, sin repetir voz. `--prepare-display` sólo instala el añadido conocido
y deja la indicación desactivada.

Pruebas: 23 casos Python, prueba Node de caducidad/prioridad/fallos y prueba
en Chromium real con el MP4 instalado. Captura de la pantalla real confirma
el anillo azul. Renovaciones finales medidas: 8,543 / 8,751 / 8,701 s.
El preview de este encendido permanece activo hasta salir de la espera inicial,
perder una comprobación o alcanzar su límite de 30 min. La primera implementación refrescaba cada unos 18 s; se
paralelizaron las consultas y se eliminó la carga repetida del entorno ROS
en la lectura de /proc y del log, para conservar el permiso de 12 s. El arranque completo con voz y vídeo combinados queda pendiente
del próximo encendido normal; no se reinició el robot para ensayarlo.

Durante la instalación se recargó la sesión gráfica. Cerrar LoadingScreen
cerró también la sesión kiosk de LightDM y apareció el login; se restauró
mediante un reinicio exclusivo de `lightdm.service`, después de comprobar
que su sesión sólo inicia el visor. Autologin y vídeo restablecidos. CC,
backend de expresiones y contenedor web conservaron ID y StartedAt. No se
enviaron comandos de articulaciones/chasis ni cambios de modo.

Backup completo previo: `/etc/walker/boot/backups/20260910T102219Z_BOOT-VISUAL/`.
Reversión: detener el aviso/preview, restaurar de ese backup `cruzr_boot_voice.py`
y `cruzr-boot-voice.service`, restaurar `index.before.html` como el index del
contenedor de expresiones y ejecutar `systemctl daemon-reload`. Mantener el
wrapper de CC. La indicación pendiente caduca aunque no se recargue la pantalla.
No reiniciar CC/Motion para aplicar ni probar cambios de pantalla.

Evidencia: `../Humanoide-vla-evidence/20260910T102219Z_BOOT-VISUAL/`.

## Uso habitual

1. Preparar el encendido con brazos abajo, abrazaderas vacías, robot estable,
   recorrido libre y una persona junto al paro. Mantener pulsado el E-stop principal.
2. Encender mediante chasis → KEY1 → Power, según la disposición de esta unidad.
3. Esperar la frase en inglés **“Ready to release the emergency stop.”** y la
   aparición del vídeo **巡检**, el anillo azul con barrido animado.
4. Con las condiciones físicas anteriores conservadas, liberar el E-stop.
   Puede comenzar el HOME interno de arranque. Esperar a que termine la
   inicialización antes de activar PICO o ejecutar tareas.

La frase confirma las comprobaciones técnicas **previas a liberar el paro**.
El autodiagnóstico completo y StartMotion se ejecutan después. La animación
identifica visualmente esta espera; un sonido genérico de encendido u otro
color de la cara no son esta señal.

Si no se oye, mantener el paro y comprobar desde el PC, sin Codex:

```bash
./scripts/cruzr_boot_ready.sh --check
```

Ese comando sólo consulta. La salida `LISTO PARA LIBERAR EL E-STOP` exige el
estado de arranque correcto; un fallo de conexión o de lectura da `NO LISTO`.
No usar esta secuencia para recuperar una detención durante teleoperación o
después de un contacto: consultar la guía de recuperación correspondiente.

## Funcionamiento y límites

El wrapper de Control Center espera tres respuestas funcionales de Motion y
dos rondas de las seis cámaras, con marcas temporales que avanzan, antes de
ejecutar el comando original de UBTECH. Las seis suscripciones se consultan
en paralelo. Se conserva el autodiagnóstico y HOME interno del proveedor.

El servicio separado `cruzr-boot-voice.service` se ejecuta en **Vision**, una
vez por arranque del ordenador. Espera al Control Center actual y comprueba
de nuevo Motion, cámaras, E-stop principal=1, servo E-stop=0 y cargador=0.
El archivo de log debe estar abierto por el proceso actual; no basta el enlace
`cc_main.latest.log`, que puede conservar el encendido anterior. Sólo acepta
la primera fase `WaitEStopRelease`, sin modos de operación previos en ese proceso.

La voz utiliza exclusivamente `/sys/speech/tts`, tipo `sys_task_msgs/action/Tts`,
idioma `en`, volumen de esa frase 80, y texto fijo. Vuelve a comprobar Motion y
los paros inmediatamente antes de solicitar audio. No envía HOME, StartMotion,
cambios de modo ni reinicios; no modifica el volumen global. La ampliación
visual descrita arriba acompaña al chequeo sin alterar las expresiones nativas.
No reintenta una solicitud de voz fallida. El límite de espera es siete minutos.

Se registra `/proc/sys/kernel/random/boot_id` antes de esperar para impedir que
reiniciar el servicio repita la instrucción durante una recuperación. Esto
identifica el arranque de Vision; no demuestra por sí solo la postura física.
La preparación de brazos abajo y zona libre sigue correspondiendo al operador.

Los paros/cargador se leen mediante ROS 2 dentro de `walker-ros.ros2-1`:
el CLI ROSA de esta versión abortó al deserializar `std_msgs/UInt8` en pruebas.
Esas lecturas se rechazaron; no se usaron como valores válidos. Las cámaras
y el servicio Motion se consultan mediante ROSA nativo.

## Instalación, verificación y reversión — 2026-09-10

Archivos versionados:

- `scripts/upgrade/cruzr_cc_start_when_ready.py` → `/etc/walker/boot/` en Vision.
- `scripts/upgrade/cruzr_boot_voice.py` → `/etc/walker/boot/` en Vision.
- `scripts/upgrade/cruzr-boot-voice.service` → `/etc/systemd/system/` en Vision.
- `scripts/cruzr_boot_ready.sh`: consulta alternativa desde el PC.

El comando de compose ya apunta al wrapper; no se cambia otra vez. El binario
de Control Center continúa protegido por su hash v0.2.0. El guard antiguo
`cruzr-v020-boot-guard.service` permanece deshabilitado.

Backup previo a la ampliación:
`/etc/walker/boot/cruzr_cc_start_when_ready.before-voice-20260910T081749Z.py`.
Para retirar sólo el aviso automático, deshabilitar `cruzr-boot-voice.service`
en Vision; conservar la espera preventiva. No reiniciar Control Center como
prueba de audio. El wrapper anterior puede restaurarse desde el backup para
el siguiente encendido si se decide revertir también la comprobación de cámaras.

Evidencia de instalación y pruebas:
`../Humanoide-vla-evidence/20260910T081749Z_BOOT-VOICE/`.
Las pruebas locales cubren respuestas fallidas, timeout, cámaras congeladas o
incompletas, cambio de proceso, paros desconocidos, modo de operación previo,
aviso único por boot y ausencia de voz en `--check`.

**VERIFICADO:** consulta completa en vivo rc0, ambos paros/cargador1/0/0,
Motion3/3 y cámaras2/2 con marcas crecientes. Dieciséis pruebas locales pasan;
la unidad systemd valida y está habilitada. CC conserva ID y StartedAt
07:53:53Z, RestartCount0. Se enviaron dos pruebas de voz: el operador confirmó
que la segunda se entiende bien. La respuesta real fue status4, desc `Success`,
state1001000, msg_type `sys_state_msgs::msg::SpeechState`.

El primer análisis de ese resultado esperaba `SUCCEED` y marcó falsamente la
reproducción como fallida. Se corrigió y se verificó contra la respuesta real
capturada, sin reproducirla una tercera vez. No hubo movimiento, rearme ni
reinicio de CC/Motion durante esta instalación. Los errores de deserialización
ROSA vistos en pruebas correspondieron a los procesos de consulta.

**PENDIENTE:** observar el aviso durante el siguiente encendido completo con
brazos abajo y E-stop pulsado. No se reinicia el robot para probar el sonido.
El nuevo aviso y la espera de cámaras están instalados; la ampliación completa
al arranque en frío se comprobará en ese próximo encendido.

Prueba adicional del servicio en el mismo boot: `systemctl start` terminó rc0
sin reproducir voz, con `VOICE_SKIPPED=already_attempted_this_host_boot`.
Comprueba que el registro impide repetir la instrucción al reiniciar el aviso.
Hashes finales: wrapper `19f06f68…52011b`, voz `a948ce1d…fc7d09`,
unidad `80c791a7…a6887`; hashes completos en la evidencia. No hay commit/push.
