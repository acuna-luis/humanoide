# Retroceso inicial de ArcPreciseController — 22-09-2026

Estado al 22-09-2026, 10:08 CEST (Europe/Madrid): **diagnóstico estático y
correlación con el ensayo VERIFICADOS; alternativa de avance PENDIENTE**.
Esta intervención sólo consultó Vision y analizó copias locales. No envió
tareas, velocidades ni cambios de configuración; no reinició contenedores.
La última comprobación física instrumental sigue siendo la posterior al
[ensayo de 5 cm](GET1_PUT1_MAPA_Y_EJECUTOR.md#ensayo-supervisado-de-objetivo-frontal5cm--2026-09-22-0955-cest),
con robot detenido en HOME y desplazamiento neto de 7,503 mm hacia atrás.
No presentar ese dato histórico como una lectura fresca de esta intervención.

## Hallazgo

El objetivo estaba correctamente situado **5 cm delante**. `x_tilt=-0.05`
representa la posición del robot en el marco del objetivo: por sí solo no
indica que el objetivo se haya interpretado al revés. El cálculo de dirección
produce un objetivo de velocidad positivo para ese caso.

La causa inmediata de la primera orden negativa está en `setStartToGoal()`:

```text
prev_planned_vx = odometry.linear.x - 0.05
```

Partiendo de odometría cero, el estado interno comienza en −0,05 m/s.
En la primera iteración, `preciseControl()` calcula velocidad objetivo +0,03 m/s,
pero limita el incremento a 0,1 m/s² × 0,1 s = 0,01 m/s. Sale **−0,04 m/s**:
coincide con la salida real registrada por el planificador. La configuración
`allow_backward: true` permite transmitir esa velocidad negativa.
El mensaje «Initial velocity: 0.050000» imprime un valor absoluto; no prueba
que la velocidad interna inicial fuera positiva.

Esto explica el inicio del retroceso y corrige la sospecha previa sobre el signo
del objetivo. No demuestra qué habría ocurrido de haber dejado continuar la
tarea; el monitor la canceló. No se ha determinado la intención del proveedor
al introducir la resta. No se ejecutó ni parcheó el ELF.

## Evidencia del binario y configuración

Unidad WAE001UBT60000669, Vision `192.168.11.3`, contenedor redescubierto
`walker-nav.freepnc_task-1`, ID
`fb7f64a6949c61d8df1bfbc757d084b33d21d7ddb918199953774d1bdf9e548d`, imagen
`glcr.rd.ubtrobot.com/runtime/cruzr-s2/utars-integration:zs2_vision-v0.2.0`.
PID 84 ejecuta `freepnc_task_module_node -p nav_freepnc_config_utars`;
`/proc/84/maps` confirma la biblioteca cargada desde la ruta inspeccionada.

| Archivo dentro del contenedor | SHA-256 |
| --- | --- |
| `/opt/walker/arc_precise_controller/lib/libarc_precise_controller.so` | `872b967b4b397ea6f683bacf007b95588ba55d00b0fcb7964a6844bc972b31d3` |
| `/opt/walker/nav_freepnc_config_utars/share/nav_freepnc_config_utars/config/navigation/navi_local/arc_precise_controller_params.yaml` | `7da0de27d2ebfc7c712e118ba95ecf5e3ed5a7ecb5d6301a3742e53da1ac12c3` |
| `/opt/walker/nav_freepnc_config_utars/share/nav_freepnc_config_utars/config/navigation/bt_navigator/behavior_tree/navigate_to.xml` | `6be7480d0ef28a1955a1a1964c70826e6d274f9b2c148609c634791e105fe4e2` |

Se cotejaron nuevamente los hashes remotos después de copiar. Rutas regulares,
root:root, modo 0644, dentro de la capa del contenedor (sin bind específico).
Configuración original: `allow_backward=true`, distancia 0,7 m, tolerancia
0,012 m, histéresis 0,005 m y tiempo 25 s. El árbol de navegación pasa de MPPI
a ArcPrecise y conserva ramas de bumper/recuperación.

Decompilación Ghidra 12.1.3 con símbolos DWARF, corroborada por instrucciones
AArch64 y constantes del ELF. Direcciones siguientes relativas al ELF; Ghidra
añade base `0x100000`:

- `0x26ed0..0x26ef0`: lee velocidad de odometría, carga constante de `0x41398`,
  ejecuta `fsub` y guarda `prev_planned_vx_`. Constante double = 0,05.
- `preciseControl` desde `0x26390`: cálculo de dirección, aceleración y filtro
  de velocidad con el miembro `allow_backward_`.
- `setNaviGoalLevel(int)` en `0x25f70`: devuelve true sin cambiar campos.
  **Cambiar `level` no ajusta esta fase precisa.**
- `setNaviSpeed(float)` en `0x26ce4`: devuelve true sin cambiar campos.
  Los métodos base `setNaviSpeed(Twist)`, `setSmoothNaviSpeed(float)` y
  `setAllowBackward(bool)` devuelven false sin cambiar campos. Por tanto no se
  puede tratar la velocidad solicitada como un techo efectivo de esta fase,
  ni afirmar que añadir `allow_backward` al JSON modificaría el miembro interno.
- `initialize()` lee `allow_backward` del YAML una vez; una instancia ya
  inicializada no recarga el archivo al recibir otro objetivo.

El nodo de árbol `ControllerActionNode::on_send` también lee una entrada
`allow_backward` de la blackboard y usa true si falta. Este campo del mensaje
de control y el campo leído del YAML por ArcPrecise son mecanismos distintos.
No se ha validado un parámetro por objetivo que configure el segundo.
Los avisos de recuperación de tipos DWARF se conservan en los logs: el
pseudocódigo no se considera fuente original ni sustituto compilable.

## Alternativa preparada, sin activar

**Prioridad posterior del operador (10:10 CEST): centrarse en el agarre.**
Este candidato queda aparcado; no es un requisito para continuar el diagnóstico
de la caja ni una modificación autorizada para aplicar automáticamente.
[Reanudación de agarre](../incidents/2026-09-22_FRONTAL_SPS_ALCANCE_ICEORYX.md#revision-centrada-en-el-agarre-22-09-2026).

[Perfil candidato](../../config/box_handling/arc_precise_forward_only.candidate.yaml):
única diferencia funcional respecto al original, `allow_backward: false`.
El filtro de `preciseControl` descartaría la primera velocidad negativa,
produciendo cero en ese instante. El cálculo offline **no valida** la llegada,
el frenado, la velocidad angular ni el comportamiento ante obstáculos.

No está instalado, cargado ni probado físicamente. Tampoco está conectado a
`force_escenario1.sh`; `front_nudge.py --run` sigue bloqueado. Sustituir el YAML
global afectaría otras aproximaciones que requieran retroceder. Antes de
activarlo, debe prepararse aplicación/reversión verificable y una activación
controlada de la instancia, preferiblemente con alcance aislado al ensayo.
No asumir recarga en caliente, ni reiniciar navegación como consulta.

La siguiente prueba, una vez preparada y autorizada, debe ser exclusivamente
la aproximación supervisada, con pose/odometría, salud, zona y control exclusivo
verificados de nuevo. Mantener el monitor de desplazamiento y parada; no
incluir agarre automático. Después hacen falta detección fresca de la caja
y validación de alcance/IK. La selección frontal entre laterales ya estaba
comprobada; el agarre y la aproximación siguen pendientes.

## Reproducción offline

Desde la raíz del repositorio, con el archivo privado ya capturado:

```bash
arc_evidence=/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922T080049Z_ARC_PRECISE_DIAG
python3 scripts/box_handling/analyze_arc_precise_start.py \
  --binary "$arc_evidence/vendor/opt/walker/arc_precise_controller/lib/libarc_precise_controller.so"
```

El script comprueba el hash exacto y rechaza otras versiones. Reproduce sólo el
primer paso longitudinal alineado a 5 cm desde reposo; no simula el robot ni
accede a ROS/SSH. Resultado: original −0,04 m/s, filtro candidato 0 m/s.

La receta de decompilación versionada es
[decompile_box_selection.py](../../scripts/box_handling/decompile_box_selection.py)
con filtros `preciseControl`, `computeVelocityCommands`, `setStartToGoal`,
`initialize`, `setNaviGoalLevel`; su manifest conserva el comando completo.
[InspectArcPrecise.java](../../scripts/box_handling/InspectArcPrecise.java)
exporta instrucciones/constantes del proyecto local usando `-process`,
`-noanalysis`, `-readOnly`; las direcciones están ligadas al hash anterior.

## Registro NAV-01-ARC-DIAG y reversión

Destino de los cambios: exclusivamente archivos PC de diagnóstico, perfil
candidato y documentación. Fuente reproducible: scripts enlazados, perfil,
receta y copias con hashes. Instalación/activación en robot: **NO REALIZADAS**.
Verificación: hashes remotos/locales coinciden; instrucciones y constantes
corroboran la resta; cálculo reproduce −0,04 m/s; rechazo de versión distinta;
perfil conserva todos los demás parámetros; helper físico continúa bloqueado.

Backup previo y evidencia externa:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922T080049Z_ARC_PRECISE_DIAG`.
Incluye `before/`, `after/`, inventario, copias vendor, `arc-decompile/`,
`arc-assembly.txt`, `controller-action-decompile/`, cálculo, hashes y validación.
El primer tar devolvió rc2 por buscar `nav_task_manager` (ruta inexistente);
los demás archivos se capturaron. La segunda captura de `nav_taskmanager`
y el nodo del árbol terminó rc0. La biblioteca/configuración relevantes se
validaron individualmente: no se trata el primer rc2 como éxito íntegro.

Reversión PC: retirar sólo los archivos nuevos enumerados de esta intervención y
revertir selectivamente las entradas documentales desde `before/`, preservando
los cambios ajenos. No hay rollback remoto ni restitución física que ejecutar.
No se restauran estados transitorios. Punto de reanudación de navegación si se retoma: preparar activación
aislada del candidato o solución del proveedor. Prioridad vigente: diagnóstico
de agarre enlazado arriba; no repetir el ciclo completo.
