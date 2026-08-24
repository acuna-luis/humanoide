# Relevo operativo — Cruzr S2 y PICO — 24 de agosto de 2026

Este documento permite reanudar el trabajo el 25 de agosto sin repetir pruebas
ni confundir el último estado conocido con el estado físico que se encuentre al
llegar. La fuente de verdad técnica completa sigue siendo
[`CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md`](CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md).

## 1. Estado al cerrar la sesión

### Robot

- **VERIFICADO:** se detuvo la teleoperación desde el PC.
- **VERIFICADO:** el robot salió de `TeleopMode`; v0.2.0 reinició de forma
  automática componentes de Motion.
- **VERIFICADO:** tras esperar a que reapareciera el servidor de la acción de
  manipulación, la tarea `cruzr/home` terminó con `SUCCEED`, `status=4`. Los
  brazos volvieron a `home` sin mover el chasis.
- **VERIFICADO:** el STOP del PC devolvió primero el robot a `AutoTaskMode`, no
  a control por joystick.
- **VERIFICADO:** el modo se cambió después desde la web a `joystick`; Control
  Center registró la transición y quedó en `JoystickMode`.
- **NO CONFIRMADO:** no se volvió a validar un desplazamiento físico con el
  mando después de esa última transición.
- **NO CONFIRMADO:** no se recibió una confirmación final de robot sentado, en
  damping y completamente apagado.

Últimos estados de seguridad leídos antes de recuperar `home`:

```text
estop_key_state=0
servo_estop_key_state=0
chrg_input_status=0
battery_soc=50.3,49.9
```

### PC al redactar este relevo

```text
eno1: DOWN / NO-CARRIER
PICO por ADB: no presente
ubt-controller.service: active/running
backend activo: SHA-256
0f0d341424f30042cc9189ff215d09007de91f443e4b9b0debaeffa81cda28eb
```

Que `ubt-controller.service` esté activo no significa que la teleoperación
esté conectada. En el snapshot final no había enlace Ethernet al robot ni PICO
visible por ADB.

### PICO

- **VERIFICADO antes del reinicio:** XRoboToolkit 1.1.1 llegó a `Working`, con
  cabeza y controladores, y el PC obtuvo `vr_status=1`.
- **OBSERVADO después del reinicio:** la aplicación no logró reconectar.
- **VERIFICADO:** ADB continuó funcionando durante el diagnóstico inicial,
  pero `wlan0` estaba sin red y el USB volvió como MTP/ADB o
  MTP/accessory/ADB, sin la interfaz Ethernet USB anterior.
- **VERIFICADO:** el PC dejó de tener la interfaz y dirección USB histórica
  `192.168.106.167`; por ello el PICO ya no podía llegar al servicio XR del PC
  por la ruta usada antes.
- **PENDIENTE:** restablecer un transporte de red soportado PICO ↔ PC. No se
  debe interpretar `ADB device` como conectividad XR.

## 2. Qué se cambió hoy en el PC

No se parcheó el robot.

### Backend UBT

Se conserva el cambio obligatorio y reversible:

```text
WebsocketServer.collect: GRIPPER -> CLAMP
```

También se instaló un workaround experimental, limitado a esta configuración
con abrazaderas pasivas:

```text
gatillo izquierdo físico -> booleano vendor Y / b_button
```

El operador sigue teniendo que accionar físicamente el gatillo. No se fuerza
`enable_control`, no se inventa heartbeat, no se cambia el watchdog y no se
modifica el controlador derecho.

Hashes y copias:

| Archivo | SHA-256 | Uso |
|---|---|---|
| backend activo | `0f0d341424f30042cc9189ff215d09007de91f443e4b9b0debaeffa81cda28eb` | clamp + gatillo izquierdo como Y |
| backup previo al workaround de gatillo | `5e40eb7f88d816827d1fa90f52ccae378b33ef0b5696ebc0d92af64c7a4e7ad1` | estado anterior recuperable |
| binario vendor 5.3.0 | `3a094a007842d859ce95974d74fddf74714e1a49a9a75ca32e82fd6ce7b789fa` | rollback completo del backend |

Archivos del repositorio modificados y todavía no confirmados en Git:

```text
docs/teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md
scripts/teleoperation/cruzr_pico_teleop_pc.sh
scripts/teleoperation/patch_ubt_controller_clamp.py
config/systemd/system/ubt-controller.service.d/30-service-lifecycle.conf
```

El drop-in `30-service-lifecycle.conf` cambia únicamente la forma en la que
systemd detiene el stack del PC: usa `SIGTERM`, `KillMode=mixed` y un timeout de
15 segundos. Corrige paradas que antes agotaban 90 segundos. Debe revisarse y
versionarse antes de considerarlo parte estable de la instalación.

### Proceso instalador pendiente

Al cerrar la sesión se observó un proceso antiguo de instalación aún vivo,
iniciado alrededor de las 14:00, con un `sudo install` hijo. No se debe escribir
una contraseña en esa terminal ni asumir que el proceso terminó. Antes de
continuar mañana:

```bash
ps -eo pid,ppid,stat,lstart,args | \
  grep -E 'patch_ubt_controller|/tmp/cruzr-ubt-controller|sudo install'
```

Si sigue presente, comprobar que el backend activo conserva el hash anterior,
cancelar la terminal antigua con `Ctrl+C` y volver a comprobar el hash. No
ejecutar otra instalación en paralelo.

## 3. Evidencia obtenida hoy

### Cadena que sí llegó a funcionar

1. Ethernet PC ↔ Motion/Vision.
2. PICO autorizado por ADB.
3. XRoboToolkit PC Service escuchando en TCP 63901.
4. PICO conectado al servicio XR y `Working`.
5. `ubt-controller` 5.3.0 escuchando en TCP 8082.
6. Backend configurado como `arm=clamp`.
7. Web del robot en `遥操模式 / Remote control mode`.
8. DataChannel abierto y tele-data recibida por el robot.

Esto no produjo una teleoperación física sostenida y validada.

### Botones y gatillo

- Y produjo contacto capacitivo en algún ensayo, pero no un clic mecánico
  `key.b_y` fiable.
- X produjo un clic aislado en una prueba anterior, pero no fue reproducible.
- Dos escuchas directas posteriores del SDK devolvieron gatillo izquierdo
  máximo `0.000` y ningún botón, aunque el tracking de poses había funcionado
  antes.
- La prueba de ocho segundos con el workaround del gatillo no observó
  `b_button=true`; el robot permaneció con `enable=0`.

Conclusión: el mapping está instalado y validado estructuralmente, pero su
entrada física **no está validada extremo a extremo**.

### Heartbeat y watchdog

- El backend espera `{"type":"heartbeat"}` y detiene la operación si pasan
  más de 10 segundos.
- El robot envió callbacks `tele_operation enable=0` aproximadamente cada
  11,1 segundos en la sesión observada.
- Sólo se había observado un `enable=1` temporal durante un ensayo anterior.
- El heartbeat de señalización `AnswerSession: sent heartbeat` no es el
  heartbeat de seguridad esperado por el backend.
- No se amplió, desactivó ni falsificó el watchdog.

Este problema sigue bloqueando la teleoperación útil aunque se recupere la red
del PICO.

### Comportamiento al salir de teleoperación

El comando local STOP usado por el lanzador:

```text
operation_type=1
```

provoca en v0.2.0:

```text
TeleopMode -> AutoTaskMode
```

Durante la transición se reinician contenedores de Motion. Hubo una ventana en
la que `/mc/manipulation/action` no estaba disponible mientras EtherCAT y los
controladores se inicializaban. Una orden `home` sólo debe enviarse después de
que el servidor de la acción haya reaparecido.

Para recuperar el mando físico hubo que seleccionar `joystick` en la web. El
lanzador todavía no automatiza esa restauración porque no se ha identificado
una API oficial segura para hacerlo.

## 4. Deuda conocida que debe resolverse

### P0 — antes de cualquier nueva teleoperación física

1. Inspeccionar el estado físico real del robot al llegar.
2. Cancelar el instalador `sudo install` antiguo si aún existe.
3. Restablecer Ethernet PC ↔ robot.
4. Restablecer una red PICO ↔ PC compatible con XRoboToolkit.
5. Confirmar `Working`, stream TCP 63901 y `vr_status=1`.
6. Repetir la lectura directa de inputs sin mover el robot y demostrar al
   menos un flanco real del gatillo izquierdo.
7. Confirmar que el backend publica `b_button=true` con ese flanco.
8. Resolver con DSA el heartbeat de aplicación de 10 segundos o recibir la
   build exacta `v0.2.0-dac-beta.2`.
9. No pasar a movimiento hasta sostener `enable=1` y heartbeat durante 60
   segundos, con parada verificada.

### P0 — scripts y modos

- `cruzr_recover_to_home.sh` todavía espera la imagen antigua
  `zs2_motion-v0.26.10` y falla su preflight con la imagen oficial v0.2.0
  `utars-integration:zs2_motion-v0.2.0`. Actualizar la validación sin relajar
  las demás comprobaciones.
- `cruzr_pico_teleop_pc.sh --stop` deja el robot en `AutoTaskMode`. Diseñar una
  restauración explícita y verificable a `JoystickMode`, o documentar el paso
  web obligatorio, sin inventar una API.
- Añadir una espera del servidor `/mc/manipulation/action` después de salir de
  TeleopMode y antes de autorizar `home`.
- Revisar e instalar/versionar el drop-in de lifecycle sólo después de una
  prueba de inicio/parada sin PICO y con PICO.

### P1

- Obtener de DSA la matriz de versiones y el paquete exacto DAC.
- Confirmar si el flujo sin pedal está soportado oficialmente.
- Confirmar cómo se restaura el mando físico al abandonar Remote mode.
- Validar B y la grabación/exportación de un episodio antes de recoger datos.
- Sólo después, probar un movimiento pequeño de un brazo y luego STOP.

## 5. Orden exacto para reanudar mañana

### Fase A — inspección, sin mover

1. Comprobar visualmente postura, luces, cargador, paros y obstáculos.
2. Si el robot está apagado, aplicar el flujo de encendido ya validado; si está
   encendido, no reiniciarlo sólo por rutina.
3. Confirmar abrazaderas vacías y correctamente fijadas.
4. No conectar el PICO ni seleccionar Remote mode todavía.
5. Conectar Ethernet y ejecutar:

```bash
ip -br link show eno1
ip -br -4 address show eno1
ping -c 2 192.168.11.2
ping -c 2 192.168.11.3
```

6. Leer paros, cargador, batería y modo de Control Center. No mover aún.
7. Confirmar `JoystickMode` y probar primero el mando con un gesto mínimo del
   elevador o chasis en zona despejada. Si falla, no usar `F abajo + D` a
   ciegas: revisar modo, botón azul de habilitación y paros.

### Fase B — sanear el PC

```bash
cd /home/lacuna/proyectos/Robots/Humanoide
git status --short

ps -eo pid,ppid,stat,lstart,args | \
  grep -E 'patch_ubt_controller|/tmp/cruzr-ubt-controller|sudo install'

sha256sum /opt/ubt/ubt_controller/ubt_controller
systemctl status ubt-controller.service --no-pager
```

El hash activo esperado es:

```text
0f0d341424f30042cc9189ff215d09007de91f443e4b9b0debaeffa81cda28eb
```

No reinstalar ni volver a parchear si coincide.

### Fase C — recuperar PICO ↔ PC

1. Conectar el USB y comprobar:

```bash
adb devices -l
adb shell getprop sys.usb.state
ip -br -4 address
ss -ltnp | grep -E ':63901|:60061|:8082'
```

2. Abrir XRoboToolkit si no está abierto:

```bash
adb shell am force-stop com.xrobotoolkit.client
adb shell am start -W \
  -n com.xrobotoolkit.client/com.unity3d.player.UnityPlayerActivity
```

3. Si no reaparece Ethernet USB, no repetir indefinidamente
   `svc usb setFunctions rndis`; ya falló en este firmware. Usar un transporte
   soportado por la aplicación. Alternativa a validar: conectar el PICO a la
   Wi-Fi del robot para alcanzar el PC por `192.168.11.250`. No registrar la
   contraseña en Git.
4. En el PICO: `Head + Controllers` → `Send data` → confirmar `Working`.
5. Sólo entonces reiniciar una vez el backend si no descubre el visor:

```bash
sudo systemctl restart ubt-controller.service
```

6. Ejecutar únicamente el preflight:

```bash
./scripts/teleoperation/cruzr_pico_teleop_pc.sh --check
```

### Fase D — diagnóstico de input sin movimiento

Antes de Remote mode, ejecutar una escucha directa del SDK y comprobar que el
gatillo izquierdo cambia de `0.0` a un valor alto y vuelve a `0.0`. No seguir
si permanece siempre en cero. Conservar timestamp y salida.

Después verificar en el backend, todavía sin una sesión de movimiento, que ese
flanco alimenta el booleano previsto. Si la API obliga a armar la sesión para
observarlo, hacerlo sólo con el gate físico completo y STOP automático.

### Fase E — gate de seguridad

Sólo si las fases anteriores pasan:

1. Robot en `home`, abrazaderas vacías, cargador desconectado.
2. Envolvente despejada, controladores neutros y paro preparado.
3. Seleccionar `遥操模式 / Remote control mode` en la web.
4. Ejecutar:

```bash
./scripts/teleoperation/cruzr_pico_teleop_pc.sh --run
```

5. No mover los controladores durante el gate.
6. Exigir 60 segundos con heartbeat, `enable=1` y sin watchdog.
7. Ejecutar STOP y comprobar que el robot sale de TeleopMode.
8. Esperar los reinicios de Motion y restaurar `JoystickMode` desde la web.
9. Comprobar que `/mc/manipulation/action` reaparece antes de cualquier home.

## 6. Condiciones de parada inmediata

Detener la prueba y no repetir el gesto si ocurre cualquiera de estos casos:

- `No heartbeat for 10 seconds`;
- `enable_control` vuelve a cero;
- el PICO pasa de `Working` a `Connecting`;
- desaparece TCP 63901, Ethernet o DataChannel;
- el backend selecciona `gripper` en vez de `clamp`;
- aparece movimiento sin un flanco de habilitación recién observado;
- los brazos no parten de home;
- el robot queda en `AutoTaskMode` y el mando físico no responde;
- se reinicia Motion y la acción de manipulación aún no está disponible;
- cualquier ruido, colisión, asimetría, tirón o persona entra en la envolvente.

Nunca desactivar el watchdog ni generar heartbeats ficticios para superar el
gate.

## 7. Apagado al final de la próxima sesión

El flujo verificado de v0.2.0 y la discrepancia con el manual están en
[`../support/UBTECH_SHUTDOWN_PROCEDURE_MISMATCH_V020.md`](../support/UBTECH_SHUTDOWN_PROCEDURE_MISMATCH_V020.md).

Resumen operativo mientras DSA no entregue un SOP corregido:

1. Salir de teleoperación y restaurar `JoystickMode`.
2. Esperar a que Motion termine de reiniciar.
3. Llevar a `home`.
4. Sentar con `Y2` abajo.
5. Entrar en damping con `F abajo + C`.
6. Abrazaderas vacías, zona despejada y nadie tocando el robot.
7. Solicitar el apagado lógico mediante la interfaz v0.2.0 aprobada.
8. Cuando Control Center esté en `WaitShutdownReady` y lo anuncie, pulsar el
   paro rojo; este requisito proviene del software v0.2.0, aunque no aparece en
   la sección de apagado normal del manual.
9. Esperar hasta que pantalla, luces y ordenadores se apaguen.
10. Sólo entonces pulsar `KEY1`.
11. Finalmente apagar el chasis con su botón metálico y comprobar que se apaga
    el indicador verde.

No usar `KEY1` como sustituto del apagado lógico. El manual recibido muestra
un `Servo Control Button` que no existe de forma identificable en esta unidad;
DSA todavía debe aclarar la revisión física correcta.

## 8. Rollback del backend del PC

Sólo con teleoperación detenida, robot inmóvil y sin otra instalación activa:

```bash
sudo systemctl stop ubt-controller.service
sudo install -m 0755 \
  /opt/ubt/ubt_controller/ubt_controller.vendor-5.3.0.bak \
  /opt/ubt/ubt_controller/ubt_controller
sudo systemctl start ubt-controller.service
sha256sum /opt/ubt/ubt_controller/ubt_controller
```

El hash vendor esperado es:

```text
3a094a007842d859ce95974d74fddf74714e1a49a9a75ca32e82fd6ce7b789fa
```

Este rollback elimina tanto `GRIPPER -> CLAMP` como el mapping del gatillo. No
usar el flujo de abrazaderas con el backend vendor sin volver a resolver de
forma segura la selección `clamp`.
