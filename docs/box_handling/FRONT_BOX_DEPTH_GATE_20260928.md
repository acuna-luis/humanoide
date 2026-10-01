# Caja frontal: profundidad y rechazo de posición — 28-09-2026

## Ambigüedad frontal del 30-09-2026

**BOX-01-FRONTAL-AMBIGUITY — VERIFICADO por replay local, sin cambios de código.**
Intento `20260930T072751Z_OPTIMISTIC_SCENARIO1_306856`, `events.jsonl` líneas
699–700: nueve poses detectadas y rechazo
`Ambiguous frontal stacks; do not choose by height or list order`.
Sólo dos candidatas dentro de ±20°, en `base_link`:

| Índice de esa captura | X (m) | Y (m) | Z (m) | Ángulo |
|---|---:|---:|---:|---:|
| 3 | 0,768842 | 0,100831 | 0,086345 | +7,471525° |
| 6 | 1,764667 | −0,258083 | −0,106224 | −8,320535° |

La diferencia de ángulos absolutos es 0,849010°, inferior a 2°. ΔY35,89 cm
impide agruparlas en una misma franja de 8 cm; por eso no se aplica la prioridad
de profundidad. La cercana pasa XYZ si se evalúa aisladamente, pero el selector
compara antes de comprobar alcance: el candidato lejano causa ambigüedad.
No se seleccionó ninguna ni se solicitó segunda captura. La Z es base_link,
no altura al suelo; las poses no permiten determinar si el fondo era caja real
o falso positivo. La preparación de la tarea pudo ejecutarse antes del rechazo.

La consola filtra `reason` por palabras de alerta y omite este texto pese a
`event=failed`: `ConsoleReporter.render(evento700)` devuelve `[]`. El registro
sí conserva la causa. Fallo perceptivo a09:28:00,135 CEST, NoneException≈127 ms
después; resultado de acción6 y cierre/leases posteriores. Llegada a get1
cumplía7,39 mm/0,42°. En el ciclo previo072222 sólo aparece la candidata cercana
en el sector y el checkpoint completa las diez etapas (caja asumida).

Reproducción: cargar `detail.detection` del evento699 y pasarla a
`front_sps_contract.select_report` usando `detail.time_ns` de esa captura;
genera la misma excepción. `probe_front_box.transform_poses` con su
`tf_at_detection.transform` reproduce la tabla. Evidencia derivada, hashes y
respaldo previo: `../Humanoide-vla-evidence/20260930T073831Z_BOX_SELECTION_DIAG`.
Pendiente revisar criterio de selección y presentación de errores; no se
relajaron límites, modificaron controles ni conectó al robot.

## Configuración local y paquete ausente — 28-09-2026 18:35 CEST

**BOX-01-SPS-PREFLIGHT — VERIFICADO offline y en lectura remota.** El intento del operador
`20260928T163254Z_OPTIMISTIC_SCENARIO1_1701585` falló en la lectura inicial
de dependencias, antes de iniciar etapas: faltaba
`/opt/cruzr-front-box/665dc3bff417b03a/front_sps_contract.py` en Motion.
Las fuentes PC reproducen ese ID con la edición local X=[0,35;0,90] m;
el manifiesto se identifica por contenido, por lo que editar límites requiere
un paquete distinto. Esa edición conservaba indebidamente el identificador,
el comentario y el mensaje de reserva de 10 mm. No era sólo admitir X=0,7955 m.

El operador pidió expresamente restaurar X=[0,41;0,79] m. Se restauró sólo
esa línea de `front_sps_contract.py`, conservando Y/Z y el resto del trabajo.
El bundle vuelve exactamente a `bf145fa17e1116fc`, SHA256
`2aacf0d3cab182f596ee0c4b7f2eeb2b9ebab3f01e0b69bd62641af4a1abcd28`.
La caja a X=0,7955 m sigue fuera del intervalo: esta reparación resuelve
la identidad del paquete, no amplía su alcance.

`scenario1_dependencies.py` ahora informa `SPS_PACKAGE_MISSING` con ID,
ruta y receta de instalación/verificación ante una fuente SPS ausente;
un archivo ajeno a ese paquete produce `DEPENDENCY_MISSING`. Captura sólo
`FileNotFoundError` al abrir; no fabrica informes parciales, reutiliza otro
paquete ni omite los hashes. Las demás lecturas y errores conservan su contrato.
El módulo se transmite en memoria con el ejecutor, no pertenece al bundle SPS.

Verificación: **141 pruebas pertinentes pasan**, incluidas selección, incidente,
límites, dependencias, runtime y perfil optimista. Antes de restaurar, la suite
de posición produjo 3 fallos esperados por la discrepancia con X=[0,35;0,90];
ese resultado se conserva y no se presenta como válido. La suite final deja
un `ResourceWarning` de cierre del lock en una prueba SPS, sin errores/fallos.
Comandos exactos en `tests-restored.json`.

Lectura remota: redescubiertos Motion y ROS2, manifiesto del host y las seis
fuentes en host/ambos contenedores coinciden con el bundle restaurado
(`installed-hashes-readonly.json`). No fue necesario instalar ni reiniciar.
El primer `--check-runtime` devolvió 78 por acción ocupada o reposo no verificable;
no permite distinguir ambas causas porque el comprobador no conserva esa respuesta.
Una lectura posterior obtuvo un único publicador de estado y objetivo terminal
4 (`action-state-readonly.json`). Tras ese dato nuevo se repitió sólo el preflight:
**rc0, CHECK_SPS_RUNTIME_OK**, ambos endpoints SPS con cero servidores, hashes y
controladores verificados (`runtime-readonly-after-terminal.json`). No se iniciaron
adaptadores ni enviaron tareas/movimientos. Esto no mide HOME ni valida un agarre.

Backup de la edición local anterior, bundle, pruebas y verificación:
`../Humanoide-vla-evidence/20260928T163456Z_SPS_PACKAGE_PREFLIGHT/`.
Para revertir únicamente el diagnóstico, restaurar selectivamente
`scenario1_dependencies.py` y su prueba desde `before/`; no requiere acción
remota. El backup del contrato conserva la edición X=[0,35;0,90] como evidencia;
no restaurarla al revertir el diagnóstico, pues contradice la elección posterior
del operador. No se instala ese paquete ni se alteran checkpoints anteriores.

## Instalación del rechazo original

**BOX-01-FRONT-DEPTH-GATE, Europe/Madrid. Estado: INSTALADO; preflight de lectura
y pruebas offline VERIFICADOS. Carga perceptiva del adaptador corregido y ensayo
físico PENDIENTES.** Paquete nuevo `bf145fa17e1116fc`; anterior
`74f5507e44addd71`. Esta corrección no recupera la postura posterior al E-stop
ni autoriza liberar el paro o repetir el ciclo.

## Problema y resultado buscado

En el [incidente de la última caja](../incidents/2026-09-28_ULTIMA_CAJA_FONDO_ESTOP.md),
dos cajas bajas estaban en la misma franja lateral, una detrás de otra. El
criterio anterior de menor ángulo favoreció la del fondo: índice 5,
`base_link.x=1,191834 m`, frente al índice 4 a `0,794421 m`. El índice es sólo
la posición dentro de aquella respuesta, no una identidad estable de caja.

Motion registró `X_BaseBox out of limits` a X=1,19508 m, seguido de
`while PositionAndRotationLimit failed, continue Iksolve check`; el chequeo IK
prosiguió y resultó satisfactorio. Por ello, el aviso de límite del proveedor
no se trata como una barrera que siempre aborte la trayectoria. El rechazo
añadido ocurre antes de entregar una respuesta SPS exitosa.

## Regla vigente de selección

[select_front_box.py](../../scripts/box_handling/select_front_box.py) sigue
siendo un selector offline: recibe poses coherentes en `base_link`, conserva
la pose elegida y no comprueba alcance ni autoriza movimiento.

1. Considera X positivo y sector frontal de ±20°. Agrupa pilas verticales con
   diámetro XY máximo de 80 mm y separación entre niveles de 220 ±40 mm.
   Selecciona la caja superior detectada de cada pila coherente; no sustituye
   la superior por su soporte si aquélla queda fuera del sector.
2. Entre cimas de pilas en la misma franja lateral de 80 mm, sólo ordena por
   profundidad si sus alturas difieren como máximo 40 mm y cada separación X
   sucesiva supera 80 mm. Conserva la más cercana; la caja del fondo no gana
   por tener un ángulo aparentemente más centrado.
3. Cimas alineadas a diferentes alturas, cadenas laterales que exceden 80 mm
   o profundidades insuficientemente separadas producen ambigüedad y rechazo.
4. Entre las franjas restantes compara el valor absoluto de `atan2(Y,X)`.
   Una diferencia de como máximo 2° entre las mejores produce rechazo.

La altura resuelve pilas coherentes y comprueba niveles comparables; no
prioriza una pila lateral más alta. Si la frontal está fuera de la envolvente
posterior, no busca otra caja lateral que sí la cumpla. Estas tolerancias son
políticas del selector, no tolerancias de agarre físicamente cualificadas.

## Rechazo antes de la entrega SPS

[front_sps_contract.py](../../scripts/box_handling/front_sps_contract.py)
aplica `front_box_base_link_xyz_10mm_v1` después de seleccionar el objetivo:

| Eje en `base_link` | Intervalo admitido, extremos incluidos |
|---|---|
| X | 0,41 a 0,79 m |
| Y | −0,39 a +0,39 m |
| Z | 0,01 a 1,49 m |

Son los intervalos XYZ del YAML `wrc/separate_right_cruzr` reducidos en 10 mm
por cada cara. **Ese centímetro es una reserva de política, no una cota
calibrada de error TF ni prueba de equivalencia entre `base_link` y el
`X_BaseBox` interno de Motion.** Z tampoco equivale automáticamente a altura
desde el suelo. Cumplir estos intervalos no certifica IK, colisiones, soporte
de la caja, orientación admisible ni trayectoria segura.

Se mantienen detección reciente, resultado de visión válido y TF del instante
exacto. El contrato conserva la pose original en cámara, sin recortar ni
corregir sus coordenadas. Añade `selection.position_gate` como diagnóstico,
con `reachability_checked=false`; el selector conserva
`motion_authorized=false`.

La comprobación se realiza al seleccionar y antes de ambas respuestas nativas
de la transacción. Se vuelve a transformar la pose que realmente se devolverá
y se contrasta con la detección original; una marca `passed` almacenada no
autoriza una pose alterada. Un fallo `BOX_POSITION_REJECTED` invalida la
transacción, borra la selección pendiente y aborta SPS sin sustituir caja.

El flujo improved compara además dos capturas mediante
[scenario1_perception.py](../../scripts/box_handling/scenario1_perception.py).
Si la primera falla este contrato, no solicita la segunda; si falla la
segunda, no entrega ninguna selección. Este bloqueo actúa en el punto
perceptivo del agarre: **no afirma que se eviten la navegación o los MetaMove
preparatorios que el XML ejecuta antes de esa consulta**.

## Pruebas reproducibles

**Suite pertinente: 530 pruebas PASS, cero errores/fallos**, registrada en
`targeted-tests.json` y `targeted-tests.log`. Incluye **40 pruebas específicas**:
9 del incidente, 15 del contrato de posición y 16 del selector. Estas últimas
pueden reproducirse localmente, sin ROS ni acceso al robot:

```bash
python3 -m unittest \
  scripts.box_handling.test_front_box_incident \
  scripts.box_handling.test_front_sps_position_gate \
  scripts.box_handling.test_select_front_box -v
```

La [fixture saneada](../../scripts/box_handling/fixtures/front_box_20260928.json)
contiene cuatro casos y cinco capturas originales numéricas: cámara, TF,
sellos y referencias SHA256/línea, sin imágenes ni credenciales. Las primeras
tres selecciones previas siguen pasando. En ambas capturas del último caso
se elige ahora el índice 4, pero X≈0,794 m supera 0,79 m y la entrega se
rechaza. La caja del fondo sola a X≈1,19 m también se rechaza, sin alternativa
lateral. Se prueban además límites exactos y su siguiente flotante exterior,
poses no finitas, estado alterado, conservación de cámara/TF, pilas verticales
y alturas alineadas ambiguas. Estos resultados no son un ensayo físico.

La primera suite ampliada ejecutó 579 pruebas y produjo 17 errores, todos en
`test_scenario1_deposit_install`. La reproducción aislada con los módulos de
HEAD produjo los mismos 17 errores en 23 pruebas: conflicto preexistente entre
modos de calibración del depósito, antes de las acciones del instalador.
`tests-baseline-note.txt` conserva diagnóstico, hashes y reproducción. No se
ha reparado ni validado esa función de depósito en esta intervención; no
presentar la suite ampliada como completamente correcta.

## Paquete, instalación y verificación

Fuente y receta: [front_box_integration.py](../../scripts/box_handling/front_box_integration.py)
y [front_sps_install_remote.py](../../scripts/box_handling/front_sps_install_remote.py).
SHA256 de `bundle-after.json`:
`2aacf0d3cab182f596ee0c4b7f2eeb2b9ebab3f01e0b69bd62641af4a1abcd28`.
Los tres XML/YAML `local_front_box` son idénticos al paquete anterior
(`tasks unchanged=true`); no se alteran trayectorias ni bibliotecas vendor.

Antes de instalar: conservar el respaldo externo, redescubrir los contenedores
y verificar que ninguna sesión está usando los adaptadores. El instalador
usa nombres concretos y no toma el bloqueo de sesión SPS ni comprueba el
paro por sí mismo. Mantener el estado físico acordado; instalar no exige
habilitar controladores, retirar el paro ni reiniciar.

```bash
# Construcción local revisable; directorio nuevo:
python3 scripts/box_handling/front_box_integration.py --build /ruta/nueva
# Instalación aditiva, sin tareas perceptivas ni movimiento:
python3 scripts/box_handling/front_box_integration.py --install
# Preflight de lectura, cuando acción/controladores estén disponibles:
python3 scripts/box_handling/front_box_integration.py --check-runtime
```

Destinos del paquete `bf145fa17e1116fc`:

- Motion host: `/var/tmp/cruzr-front-box/bf145fa17e1116fc/`, fuentes,
  `manifest.json` e `install-receipt.json`.
- Contenedores Motion y ROS2 descubiertos: seis módulos en
  `/opt/cruzr-front-box/bf145fa17e1116fc/`.
- XML/YAML compartidos en las raíces de configuración de
  `manipulation_task_manager` y `manipulation_meta_tasks`: sólo se aceptan si
  coinciden byte a byte con el bundle; no se sobrescriben destinos distintos.

Verificar los hashes de todas las fuentes en host y ambos contenedores,
tareas/dependencias y bibliotecas, y conservar el recibo. No hay recarga ni
cambio de `task_list.yaml`; el próximo adaptador de sesión cargará el nuevo
directorio. Una copia incompleta no se considera instalación verificada.

`--check-runtime` no inicia adaptadores ni envía acciones, pero exige estado
de manipulación/controladores verificable. Bajo E-stop puede fallar por esa
indisponibilidad aunque los archivos estén correctamente instalados: no
liberar el paro para conseguir un PASS. **No usar `--check` del integrador
como verificación de archivos:** ejecuta `detect_only` y actualiza la caché
`box/0`, al igual que `--check-sps` de los wrappers antiguos.

Los wrappers `force_escenario1.sh`, `force_escenario1_first_part.sh` y los tres
improved calculan el ID desde las fuentes PC actuales. Instalar ese mismo
bundle evita que una actualización local deje rutas ausentes. Los improved
verifican hashes antes de actuar; un paquete ausente o distinto bloquea sin
volver automáticamente al anterior. Un contexto de reanudación anterior
tampoco se debe editar para ocultar el cambio de dependencia.

## Evidencia, reversión y reanudación

**Resultado remoto verificado:** `install-result.json` registra rc0,
`created_tasks=[]`, `originals_overwritten=false`, `restarts=0` y
`movement_commands=0`. `runtime-after.json` registra rc0 y
`CHECK_SPS_RUNTIME_OK`: hashes, grafo, acción inactiva y controladores
comprobados; ambos endpoints SPS con cero servidores. El preflight anterior
también pasó (`runtime-before.json`). `host-hashes-after.json` confirma además
las seis fuentes y el manifiesto del host frente al bundle actual, con rc0.
No se iniciaron adaptadores ni tareas
perceptivas; la próxima sesión utilizará el ID nuevo calculado desde las
fuentes actuales. Eso no demuestra todavía ejecución perceptiva o física.

La inspección previa encontró un worker ROS2 antiguo de la sesión
`cruzr-scenario1-4o5k60o3`: checkpoint con las diez etapas completadas y marca
`stop`, sin servidor SPS nativo de esa sesión. Se conservó la evidencia en
`active-worker-inspection.json`; no se mató ese proceso durante el despliegue.
Su presencia no se presentó como prueba de una acción de control activa ni
se usó para declarar una parada física actual.

Respaldo previo, bundles anterior/nuevo e inventarios:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260928T153324Z_FRONT_BOX_DEPTH_GATE/`.
`before/` conserva los archivos previos a esta intervención. La evidencia del
incidente y `selection-comparison.json` están en
`../Humanoide-vla-evidence/20260928T145208Z_LOWEST_BOX_ESTOP/`.

Reversión de software, sólo sin sesiones consumidoras: restaurar
selectivamente selector/contrato PC desde `before/`, conservar cambios ajenos
y contrastar el ID resultante con `bundle-before.json`. Volvería a utilizarse
`74f5507e44addd71`, si está íntegro en ambos contenedores y host. El paquete
nuevo puede permanecer inactivo como evidencia; **no borrar los XML/YAML
compartidos**, no reiniciar y no restaurar cachés. Esa reversión reintroduce
la selección del fondo y la ausencia de este rechazo; no es una alternativa
automática para permitir un agarre bloqueado ni revierte la postura física.

Punto de reanudación: instalación y preflight de lectura completados. El operador
comunica recuperación a HOME tras recolocar brazos y liberar E-stop; es su
observación, no una nueva medición HOME ni recuperación realizada por el agente.
Comprobar el estado físico actual antes de un nuevo ensayo. Carga perceptiva y
ensayo de agarre de este paquete siguen PENDIENTES; no se han realizado capturas
nuevas ni trayectorias para verificar esta corrección.
