# Arranque incompleto: Control Center antes de Motion — 10-09-2026

## Causa observada

**VERIFICADO en registros de este arranque.** Control Center inició self-check
a las 14:32:09 del reloj del robot después de liberar el E-stop. La comprobación
terminó con `passed=false`, cuatro errores y estado `Fault`: los servicios x86
de archivos y sistema todavía no estaban disponibles; las comprobaciones de
reloj y latencia no pudieron obtener la IP del otro ordenador. Cámaras, energía,
servos y sobrecorriente sí pasaron. El servicio self-check de Motion arrancó a
las 06:33:00Z, unos 51 segundos después del inicio del autodiagnóstico de Vision.

Motion estaba esperando su arranque normal; no se observó un nuevo crash de hw.
No había servidor de acciones ni muestra de actuadores. Esto distingue este
incidente del fallo EtherCAT 6002 del 08-09 y del aviso de mapa del 09-09.
El anillo rojo comunicado por el operador coincide con este estado Fault;
no se modificó la expresión facial ni la base de fallos.

## Recuperación y prevención instaladas

El usuario pidió corregir el arranque y confirmó E-stop principal pulsado,
brazos abajo y estables, abrazaderas vacías/sin contacto y zona despejada.
Una lectura nueva confirmó principal=1 antes de cada intervención de proceso.

1. Reinicio único del Control Center existente: salió de Fault y quedó en
   `WaitEStopRelease`. No se reinició Motion ni se enviaron objetivos de movimiento.
2. Instalación de `scripts/upgrade/cruzr_cc_start_when_ready.py` en Vision como
   `/etc/walker/boot/cruzr_cc_start_when_ready.py` (0644), visible mediante el
   bind mount existente. Su `--check` pasó dentro del contenedor real.
3. Cambio de **una sola línea** en
   `/home/walker/.config/udoke/walker/compose.yml`: el comando de
   `system.control_center` pasa a
   `python3 /etc/walker/boot/cruzr_cc_start_when_ready.py --start`.
   `patch_cc_readiness_compose.py` prepara y valida exclusivamente ese cambio.
4. Recreación de **sólo** ese servicio con `--no-deps --no-build --pull never`.
   Se verificaron imagen, entorno, entrypoint y bind mounts iguales al contenedor
   anterior, y los demás identificadores de contenedor sin cambios.
5. El registro nuevo demuestra tres respuestas consecutivas de Motion y
   `STARTING_VENDOR_CONTROL_CENTER=1`. El guard antiguo continúa
   **disabled/inactive**; no se ha reactivado su recuperación automática.

La espera exige respuestas reales de
`/self_check/x86/file_presence_check`, no sólo un nombre publicado en DDS.
Tres respuestas correctas, separadas por 10 segundos; cualquier fallo reinicia
el contador. Cada consulta vence como máximo a los 12 segundos y la ventana
total es de 420 segundos. Si vence, el wrapper no inicia Control Center y sale
con error. La política Docker `restart=always`, que ya existía, puede volver a
intentar arrancar el contenedor. El wrapper no reinicia un Control Center activo.

Una vez listo Motion, se ejecuta el **comando original de UBTECH**. Se conserva
el autodiagnóstico completo, sus paros y su HOME interno. La espera no demuestra
ausencia de fallos de cámaras, EtherCAT, sensores ni de la trayectoria de HOME.
Exige `HW_TYPE=cruzr_s2_v1` y el hash del binario CC revisado: ante actualización
del proveedor debe revisarse la adaptación antes de volver a arrancar.

## Uso a partir de ahora

Durante el arranque supervisado, mantener el E-stop principal pulsado con los
brazos abajo, vacíos y sin contacto. Esperar a que Control Center solicite
liberarlo (`WaitEStopRelease`): ahora esta fase ocurre después de las respuestas
de Motion. Liberarlo puede iniciar el HOME interno del fabricante.
Si hay Fault o no llega esa solicitud, consultar el diagnóstico; no repetir
Power/KEY1 para intentar saltar una fase. La discrepancia del procedimiento de
apagado de esta unidad sigue documentada por separado.

Comprobación del wrapper desde el **host Vision**, sin arrancar otro CC:

```bash
docker exec walker-system.control_center-1 bash -lc \
  'source /opt/walker/setup.bash; python3 /etc/walker/boot/cruzr_cc_start_when_ready.py --check'
docker logs --tail 60 walker-system.control_center-1
```

No ejecutar manualmente `--start` dentro de un contenedor que ya ejecuta CC.
El valor predeterminado del wrapper es sólo comprobación.

## Copia, integridad y reversión

Backup remoto previo:
`/home/walker/.config/udoke/walker/compose.yml.before-cc-ready-20260910T065831Z`.
El script nuevo no existía; se instaló sin sobrescribir un archivo distinto.

| Archivo | SHA-256 |
| --- | --- |
| Compose anterior | `eef1b29dcd4f7c5c29bc1b2fa13cc65ef18caa9132ed1d6cacb4486d938d94c3` |
| Compose instalado | `47ec176b30008d652814321780319d45c177fc6e48e7b91366c5e6871b9d785a` |
| Wrapper instalado | `6afcc790c2d3b7be8027974a3fbb81839f0842c42b459ede3e406c0c4a4bb3ea` |
| Binario CC permitido | `465b1a440875992b1a2562cde2ff452cc26b5d78bf06daa4e05460f8d9dccdf5` |

Reversión: bajo E-stop confirmado y supervisión, restaurar **sólo** el comando
original desde el backup, preservando cambios posteriores. Recrear únicamente
`system.control_center`, con el mismo proyecto y sin dependencias, build ni pull.
El archivo de espera puede quedar sin uso; no habilitar el guard antiguo como
parte del rollback. Recuperar el comando antiguo vuelve a exponer la carrera
de arranque, por lo que se debe comprobar Motion antes de liberar el paro.

## Validación y punto de reanudación

**VERIFICADO:** ocho pruebas locales, incluyendo respuestas fallidas/falsas,
reinicio del contador, vencimiento del plazo, rechazo de hardware/binario
distintos, ausencia de ejecución en `--check` y preservación del compose.
Configuración validada con Docker Compose y prueba funcional dentro del robot.
Arranque real del wrapper y posterior ejecución del CC original verificados.

**VERIFICADO antes de liberar:** comprobación instalada sólo `--check`, rc0;
tres respuestas x86, seis cámaras con muestras reales en dos rondas, versión
v0.2.0, WaitEStopRelease y principal/servo/cargador=1/0/0. Se indica al operador
liberar el paro bajo las condiciones físicas confirmadas; puede iniciar HOME
interno. Sin otra orden de movimiento ni reinicio en esta comprobación.

**VERIFICADO después de liberar:** el usuario comunica que cree terminado el
arranque. El log nuevo registra liberación principal a las 15:07:47 UTC+8,
selfcheck `passed=true`, error0 a las 15:07:59 y `StartMotion succ` a las
15:08:17, seguido de `AutoTaskMode`. Una lectura SQLite sólo lectura devuelve
`fault_current=[]`. Consultas nuevas: paros0/0, cargador0, servidor de acciones1,
writers RobotCommand0 y VLA exited/restart=no en ambos hosts.

Muestra fresca completa de los veinte actuadores: todos habilitados/sin errores,
`MEASURED_HOME=1`, posición absoluta máxima0,002972 rad (brazos0,000959 rad),
velocidad máxima0 y delta consigna0,002972 rad. Baterías97,1%/72,8%.
Sólo consultas en esta fase; no se enviaron nuevos movimientos ni reinicios.
Recuperación software y postura HOME verificadas, evidencia `after-release/`.

**PENDIENTE:** confirmación visual del anillo blanco y repetir un arranque
completo en frío para comprobar la prevención ante la carrera original.
No se ha instalado ni ejecutado la nueva trayectoria PICO→HOME `open_v2`
durante esta intervención.

Evidencia externa:
`../Humanoide-vla-evidence/20260910T064413Z_BOOT-READONLY/`:
diagnóstico, originales y compose preparado, hashes, instalación, lectura del
paro, reinicio, recreación y registro nuevo. Los relojes PC/robot difieren unos
29 segundos; comparar instancia y secuencia, no mezclar timestamps sin ajuste.
