# Discrepancia del procedimiento de apagado — Cruzr S2 v0.2.0

Fecha de la observación: 2026-08-21  
Robot: Cruzr S2, SN `WAE001UBT60000669`  
Configuración: abrazaderas, `HW_TYPE=cruzr_s2_v1`  
Sistema: v0.2.0  
Imagen de Control Center: `utars-integration:zs2_vision-v0.2.0`

## Resumen

El procedimiento de apagado descrito en el manual oficial no coincide con el
panel físico del robot entregado ni con la máquina de estados incluida en el
binario v0.2.0.

El manual exige un botón físico denominado **Servo Control Button**, pero no
existe un control identificable con ese nombre y aspecto en la unidad
entregada. Además, una vez recibida una solicitud válida de apagado, Control
Center v0.2.0 ordena expresamente pulsar el paro de emergencia para continuar.
Este requisito no aparece en la sección de apagado normal del manual.

No se dispone del código fuente de Control Center. Las conclusiones relativas
a v0.2.0 proceden de la definición de la interfaz instalada, las cadenas del
binario distribuido y los registros de ejecución del propio robot.

## 1. Procedimiento del manual oficial

Fuente: `2-Cruzr_S2_Product_Manual.pdf`, sección **5.3.2 Power-Off
Operation**, páginas PDF 15–16.

1. Asegurar que el robot está en damping.
2. Abrir la tapa trasera y pulsar el **Servo Control Button** mostrado en la
   figura 5-3-5.
3. Hacer doble pulsación del **Start button** trasero y mantener la segunda
   pulsación durante cinco segundos. El robot debe anunciar el apagado.
4. Mantener la pulsación y esperar hasta que la pantalla y las luces se
   apaguen.
5. Solo entonces abrir la tapa y pulsar el interruptor blanco de alimentación
   de la parte superior, mostrado en la figura 5-3-7.
6. Finalmente, pulsar el botón metálico del chasis para dejarlo levantado y
   comprobar que su indicador verde se apaga.

La tabla del mando de la sección 5.4.2 añade que antes de apagar debe hacerse
**Homing First, Then Sit Down**. En la misma tabla:

- Home: `F Down + D`.
- Enter Damping Mode: `F Down + C`.
- Sentar el mecanismo: `Y2` hacia abajo.

El manual no incluye el paro de emergencia dentro de 5.3.2. Lo describe en
5.3.3 como una operación de emergencia e indica que su recuperación requiere
reiniciar toda la máquina.

## 2. Hardware físico entregado

En la unidad inspeccionada:

- no existe un botón que pueda identificarse inequívocamente con el **Servo
  Control Button** representado en la figura 5-3-5;
- bajo la tapa se encuentra el pulsador blanco identificado en la placa como
  `KEY1`, asociado a la alimentación de la parte superior;
- sí existe el botón exterior trasero utilizado como Start/Power button;
- sí existe el paro de emergencia rojo y el botón metálico del chasis.

Por tanto, no es posible ejecutar literalmente el paso 2 de 5.3.2. Tampoco debe
confundirse la doble pulsación de cinco segundos del **Start button** con
`KEY1`: el propio manual sitúa el interruptor blanco en un paso posterior,
después de que pantalla y luces se hayan apagado.

La causa exacta de esta diferencia no puede determinarse con los archivos
entregados. Las explicaciones posibles son:

- manual correspondiente a otra revisión física;
- botón eliminado, trasladado o sustituido en la unidad actual;
- cambio del flujo de apagado en v0.2.0 sin actualización del manual.

UBTECH debe confirmar cuál de ellas es correcta y facilitar el SOP aplicable al
número de serie entregado.

## 3. Comportamiento verificable de v0.2.0

### 3.1 Interfaz de apagado instalada

La interfaz `emb_task_msgs/srv/ShutDown` instalada con v0.2.0 contiene:

```text
uint8 DEF_DEADLINE=15
uint8 deadline_sec

string CONFIRM_STR=confirm-to-shutdown
string confirm_str
---
bool success
string message
```

El 2026-08-21 se envió:

```text
deadline_sec: 15
confirm_str: confirm-to-shutdown
```

El servicio `/emb/pm_shutdown` respondió:

```text
success: true
```

### 3.2 Máquina de estados y mensaje incorporado al binario

El binario de Control Center v0.2.0 contiene las cadenas y símbolos:

```text
WaitShutdownReady
Shutdown
/sys/pre_shutdown_notify
confirm-to-shutdown
```

También contiene literalmente:

```text
请在确保安全的情况下，按下急停键，继续关机流程
```

Traducción:

> Después de garantizar la seguridad, pulse el botón de emergencia para
> continuar el proceso de apagado.

### 3.3 Registro de la prueba actual

Después de aceptar la solicitud, Control Center registró:

```text
Power off request state changed: 1
JoystickMode --(RequestShutdown)-> WaitShutdownReady
```

El robot anunció el texto chino anterior y permaneció encendido en
`WaitShutdownReady`. Los ordenadores Motion y Vision siguieron accesibles. Esto
demuestra que `success=true` confirma la aceptación de la solicitud, no la
finalización del apagado.

Registros anteriores de v0.2.0 muestran que, después de la confirmación física
esperada, la transición normal es:

```text
WaitShutdownReady --(ActionSucc)-> Shutdown
```

## 4. Riesgo observado al utilizar KEY1 aisladamente

En una prueba anterior se pulsó `KEY1` sin haber completado primero la
secuencia lógica de apagado. La conectividad de los ordenadores desapareció de
inmediato y, en el siguiente arranque, varios registros JSON de Docker
contenían bytes NUL y `docker logs` devolvía un error de formato.

La correlación es compatible con un corte abrupto de alimentación. No prueba
por sí sola un defecto físico de `KEY1`, pero confirma que no debe emplearse
como sustituto del apagado lógico mientras los ordenadores siguen activos.

## 5. Estado seguro al cerrar este informe

- Robot sentado.
- Robot en damping.
- Abrazaderas vacías.
- Zona despejada.
- Solicitud de apagado aceptada.
- Control Center en `WaitShutdownReady`.
- Paro de emergencia todavía no pulsado.
- `KEY1` y botón del chasis todavía no pulsados.

## 6. Confirmaciones solicitadas a UBTECH

1. Facilitar el SOP de apagado aprobado para esta revisión física y este número
   de serie.
2. Identificar sobre una fotografía anotada cada botón de la unidad entregada.
3. Confirmar si el **Servo Control Button** fue eliminado, trasladado o
   sustituido y por qué el manual sigue mostrándolo.
4. Confirmar si v0.2.0 exige intencionadamente pulsar el paro de emergencia en
   cada apagado normal.
5. Confirmar si la doble pulsación mantenida del Start button sigue siendo la
   entrada normal o si `/emb/pm_shutdown` es un equivalente oficialmente
   soportado.
6. Indicar el criterio observable para saber cuándo es seguro pulsar `KEY1` y,
   después, apagar el chasis.
7. Indicar la posición correcta del paro durante el siguiente encendido y el
   procedimiento normal para liberarlo.
8. Facilitar un manual actualizado para v0.2.0 y para el hardware realmente
   suministrado.

## 7. Mensaje breve en inglés para el chat

```text
Hello Viki, Mr. Zhu and Lucio,

While validating the normal shutdown procedure after upgrading our Cruzr S2 to v0.2.0, we found a discrepancy between the official Product Manual, the hardware delivered and the current software behaviour.

Section 5.3.2 of the manual says to enter damping mode, press a physical “Servo Control Button”, then double-click and hold the rear Start button for five seconds, wait until the screen and lights are off, press the white upper-body power switch, and finally switch off the chassis. However, our delivered unit does not have an identifiable Servo Control Button matching Figure 5-3-5.

In v0.2.0, the official `/emb/pm_shutdown` request is accepted and Control Center changes from `JoystickMode` to `WaitShutdownReady`. The installed Control Center binary and its runtime log then explicitly state in Chinese: “After ensuring safety, press the emergency-stop button to continue the shutdown process.” The robot remains powered on until that confirmation is provided. This emergency-stop requirement is not included in the manual’s normal shutdown section.

Could you please confirm the approved shutdown SOP for our hardware revision and serial number, whether pressing the emergency stop is intentionally mandatory on every v0.2.0 shutdown, and provide an updated annotated control diagram/manual? Please also confirm exactly when it is safe to press the white KEY1 switch and the chassis power button.

For safety, the robot is currently seated, in damping mode and waiting in `WaitShutdownReady`; we have not yet pressed the emergency stop, KEY1 or the chassis button.
```
