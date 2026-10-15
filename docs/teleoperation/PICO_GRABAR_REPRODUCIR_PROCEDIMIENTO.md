# Grabar y reproducir PICO con abrazaderas — procedimiento reutilizable

ID: PICO-REPLAY-WORKFLOW-20261014. Fecha: 14-10-2026, Europe/Madrid.
Estado: primera reproducción confirmada por SDK y por el operador. Alcance:
perfil `utars` de abrazaderas, robot estacionario; no modelo aprendido.

## Lo que ya sabemos y no hay que investigar en cada intento

- `record` y `player` existen en `walker-motion.manipulation_robot_app-1`.
  Redescubrir contenedor si cambió el despliegue; no repetir una auditoría del SDK
  si la versión/hash permanece igual.
- El grabador añade fecha/hora al nombre. Usar el archivo real listado, no
  adivinar `nombre.motion`. Un archivo de 50 bytes no se considera una toma útil.
- Los archivos inspeccionados son JSON `robot: Utars`, `source: utars_teleop`,
  canales `q` y `t`. La grabación puede incluir cabeza y ambos brazos.
- Comparar por **nombres de articulaciones** de `/mc/joint_states`, con el
  orden de `config/motion_sdk/joint_order/utars_joints.yaml`. Los valores de
  `/mc/actuator_state` son útiles para fallos/habilitación, pero no se comparan
  directamente contra `q`: pueden tener signos diferentes.
- El player de SHA256
  `8744a30ecce20c414dcf67b60d9aa7ac486bab752d5eee3de08a7336d65ddf0d`
  tiene un bug en el argumento explícito `--loop 1`. **Omitir `--loop`**;
  el predeterminado verificado es una reproducción. No repetir debugger,
  disassembly ni interposer como parte del preflight habitual. No alterar el SDK.
- `rosa run` puede devolver código 0 aunque el proceso hijo haya abortado:
  exigir resultado de aplicación y revisar stderr, no sólo rc.
- Esta reproducción fija no necesita relocalizar mapa/get1 ni activar visión
  de cajas o VLA. No añadir esas etapas a un replay estacionario.

Si cambian modelo de robot/efector, binario, archivos de orden articular,
firmware o contenedores, volver a contrastar compatibilidad antes de aplicar
esas conclusiones. Esta página no certifica otra build ni otro efector.

## Preparación local, sin robot

Analizar el archivo con el inspector reutilizable:

```bash
python3 scripts/teleoperation/inspect_pico_motion.py ~/grabaciones_cruzr/ARCHIVO_REAL.motion
```

Entrega hash, duración, grupos, postura inicial/final y articulaciones que
cambiaron; rechaza datos no finitos, tiempos no crecientes, dimensiones
incorrectas y perfiles/canales no soportados. No conecta ni mueve.

Para comparar geometría inicial con un `sensor_msgs/JointState` ya guardado
como JSON, usar `--joint-state-json MUESTRA.json`. Ese resultado **no** verifica
antigüedad, reposo, seguridad o colisiones: la muestra debe adquirirse de nuevo
en el preflight, nunca aceptar una muestra histórica como permiso de movimiento.

Se conservó el criterio usado en el ensayo: diferencia inicial menor de
0,02 rad por articulación. No sustituye comprobar trayectoria ni garantiza
continuidad de cualquier grabación futura.

## Secuencia para el siguiente intento

1. **Una sola confirmación física completa por intento:** abrazaderas actuales
   instaladas/vacías, recorrido de brazos y cabeza libre, cargador fuera,
   persona junto al paro y otros mandos detenidos. Una petición de información
   durante la preparación no exige volver a pedir autorización. Si cambia el
   estado físico o el control, volver a verificarlo.
2. **Archivo:** comprobar ruta y hash originales en PC/Motion y el perfil.
   No volver a copiar o generar derivados si ya existen con el hash esperado.
3. **Estado actual:** adquirir paros, cargador, batería, actuadores, articulaciones,
   status de acciones y controladores. Usar consultas pasivas, daemon desactivado,
   timeout y QoS correcto. Agrupar las consultas independientes; en este equipo
   grupos de cuatro CLI funcionaron mejor que ocho arranques simultáneos.
4. **Admisión:** postura inicial por nombre, reposo (incluidas ruedas), sin
   fallos ni actuadores deshabilitados, sin otra acción/controlador de mando,
   modo de trabajo conocido y compatible, batería y alimentación aptas.
   El status de manipulación no sustituye la exclusividad de todos los clientes.
   Si alguna comprobación falla, explicar el bloqueo antes de más cambios.
5. **Velocidad:** para primera prueba de una grabación nueva, preparar una
   copia más lenta, sin modificar posiciones. El ensayo validó factor 2 del
   editor = tiempos dobles. Confirmarlo en el archivo derivado antes de usarlo;
   una ayuda que dice `speed_mult` no basta para inferir su sentido.
6. **Ejecutar una vez** con el player nativo sin `--loop`. Comunicar justo
   antes del comienzo. No instalar un ejecutor alternativo ni corregir signos
   a mano. Conservar resultado/logs y supervisión física.
7. **Cierre:** comprobar resultado de aplicación y estado final; no repetir
   automáticamente ni enviar HOME. Guardar evidencia y documentación.

Las baterías del ensayo estaban en 28,6/36,8% y se comprobó el criterio local
usado (>20%). Son datos históricos, no el estado del siguiente intento.

## Recetas ya contrastadas

En el contenedor Motion, con `/opt/walker/setup.bash` cargado:

```bash
# Grabar; Ctrl+C detiene sólo el grabador, no la teleoperación.
rosa run manipulation_outline_sdk record -- --robot utars --output NOMBRE_SIN_EXTENSION

# Preparar copia a mitad de velocidad; usar destino NUEVO, conservar original.
rosa run manipulation_outline_sdk editor -- scale --input ORIGINAL.motion --output LENTA.motion --factor 2.0

# FÍSICO: sólo después del preflight y confirmación actuales.
rosa run manipulation_outline_sdk player -- --robot utars --input LENTA.motion
```

Usar rutas reales y absolutas. El perfil `utars` no se extrapola a manos v3/v4
ni pinzas. La teleoperación y reproducción son clientes exclusivos; sólo el
grabador pasivo puede coexistir con la teleoperación para registrar datos.

## Resultado que valida este procedimiento

La copia `prueba_pico_01_lenta_20261014.motion` tenía posiciones idénticas a la
original, tiempos dobles y duración 33,68 s. Preflight: máximo error inicial
0,002876 rad, reposo y actuadores sin fallos. El intento corregido duró
aproximadamente 35,3 s, incluido lanzamiento, y reportó:

```text
Action finished with is_finished=true, bag has been played successfully
```

El operador confirmó: «la prueba ha funcionado perfectamente». No se mandó HOME.
El turno fue interrumpido antes de la lectura final prevista; no afirmar que
se obtuvo una medición posterior de reposo en ese intento. La confirmación física
del operador y el éxito del SDK son las evidencias disponibles.

[Receta y antecedentes del ensayo](PICO_MOTION_PRUEBA_01_20261014.md).
Evidencia: `../Humanoide-vla-evidence/20261014_PICO_REPLAY_CORRECTED/`;
aprendizaje/documentación e inspector:
`../Humanoide-vla-evidence/20261014_PICO_REPLAY_WORKFLOW/`.

## Cambios de esta intervención

Sólo PC: este procedimiento, inspector local y pruebas, enlaces en índices y
resultado actualizado del ensayo. Sin consultas/órdenes al robot ni nuevos
replays para preparar el procedimiento. SDK y motion originales intactos.
Before/after y hashes conservados fuera de Git. Reversión selectiva de estos
archivos nuevos/notas, conservando ediciones posteriores. No commit ni push.


### PICO-V4-GEOMETRIC-REPLAY-20261015 — derivado preparado, ejecución pendiente

Usuario solicita reproducir toma05 y confirma manos vacías, trayectoria libre,
cargador fuera, persona junto al paro y otros mandos detenidos. Estado técnico
leído: CCJoystickMode, PCSTOP/UIinactiva/sinpico_control; cuerpo/manos reposo,
sinfaults/deltaactuador máximo0,003284rad, paros0/0, batería56,3/60,5%,
cargador0, móduloslibres. SDK OutlineSdkPlay tiene1server/0clientes; controladores
manipulation/force_torque/dexterous_hand running. Primera consulta a endpoint
ROS2supuesto de controllers falló sin invocar movimiento; descubrimiento real
/mc/controller_manager/list_controllers rosa_control_msgs/srv/ListControllers
y consulta correcta. No asumir nombres/tipos antiguos.

Preparación geométrica: scripts/teleoperation/pico_v4_bag_to_motion.py, sin
publicadores ni cambiosSDK. Consume bagSHAverificado sólo lectura; cabeza y
brazos desde órdenes por nombre, dedos desde posiciones medidas. Valida nombres,
finitos, tiempos estrictos, SQLite yhash; salida exclusiva nueva. Usa cabeceras
con origen común para sincronía, retiene primera/última postura hasta cubrir
ventana común, factor2 tiempos (mitadvelocidad), sin cambio de posiciones.
No reproducecorriente/torque ni modos5/7 originales. Se ha comunicado al usuario
que esta prueba vacía repite geometría, sin demostrar sujeción o fuerza.
SDKinstalado soporta --robot utars_with_v4_hand; ordencontrastado YAML instalado.
Playerhash8744a30ecce20c414dcf67b60d9aa7ac486bab752d5eee3de08a7336d65ddf0d.
No --loop por bugconocido; no se modifica SDK/interpone código para ejecutar.

Derivado88,6730752s, SHA256
c2aa12373b4209a77cdc594787f475762b130b468c7fda403473b95f414b2003.
HostMotion .../prueba_v4_05_20261015T101134Z_462191/derived/
take05_geometry_slow.motion; appMotion /tmp/pico_v4_replay_take05_20261015/
take05_geometry_slow.motion. Hashes comparados después de copiar; originalbag
intacto. Archivo .motion no conserva el esfuerzodeagarre; no confundirlo con
réplica exacta de mando corriente. Mayorpaso por muestra0,03682rad en dedos;
brazos≤0,003287rad, cabeza0,004rad; interpolaciónSDK a mitadvelocidad.
Comparacióninicio por nombres: cabeza0,004410rad, brazoizq0,005340,
brazodcha0,005435, manoizq0,001151, manodcha0,003643 (<0,02rad).

Evidencia take05-conversion/receipt.json, take05-derived-stage.json,
take05-replay-current-state.json, take05-initial-comparison.json,
take05-pc-control-exclusion.json y take05-running-controllers.json.
Recrear: ejecutar convertidor en entornoROS con tipos del bag y --time-scale2
--expected-sha256 del original, copiar derivado nuevo al appMotion y comparar
hash; freshpreflight + físico antes de ejecutar una sola vez playerSDK.
Reversión: conservarbag original, retirar selectivamente derivado/helper si se
descarta; sinconfiguraciónpersistente de robot cambiada. Ensayo físico de este
derivado aún PENDIENTE; no se envió movimiento por la preparación.


### PICO-V4-GEOMETRIC-REPLAY-20261015 — PROBADO FÍSICAMENTE, terminado

15-10-2026 Europe/Madrid: 12:21:54–12:23:24. Una ejecución del
player oficial --robot utars_with_v4_hand --input
/tmp/pico_v4_replay_take05_20261015/take05_geometry_slow.motion, sin--loop.
returncode0, stderrvacío, resultado textual `Action finished with
is_finished=true, bag has been played successfully`. Usuario confirma durante
la pasada que repite bien movimiento y cierreizquierdo, sin resistencia ni
movimiento inesperado reportado. Hardwarelogs de vigilancia sin patrones de
salto/SAFEOP/sobreesfuerzo/fault en el alcanceconsultado.

Postflight nuevo: velocidadmáxima0 en cuerpo ydedos, sinerror_code, delta
actuador/consignamáximo0.003044677rad. Errores respecto
al final del derivado porgrupo: {"head": 0.0013271863844168674, "left_arm": 0.002721995185922088, "right_arm": 0.003044676516222866, "left_hand": 0.005752515730995, "right_hand": 0.0013422536705656185}. Máximo
~0,005753rad en manoizquierda. Estado medido enreposo, conserva postura final
de la toma; NO HOME. Sin nuevos objetivos, cambios de modo o reinicios alfinal.
Clienteplayer terminó; PICO/web se mantuvieron sin mando durante replay.

Queda demostrada reproducción GEOMÉTRICA en vacío de cabeza/brazos/dedos a
mitadvelocidad. No se reproduce el esfuerzo original ni se valida agarrar una
pieza. La escasa variación de mano derecha pertenece a esta toma; no se añade
un cierre inventado. Bagoriginal y sus corrientes/modos se conservan intactos.
No se reprodujeron directamente topics ROS/EtherCAT ni se desactivaron
protecciones; se usó SDK nativo ya instalado. No extrapolar a replay de fuerza
o retención de objetos.

Evidencia: take05-replay-result.json, .stdout/.stderr.log,
take05-replay-postflight.json y -postflight-summary.json, comparacióninicio
y archivos de conversión/stage. Fuentes reproducibles del convertidor nuevo y
los helpers de captura/inspección en repo; before/after/hash externos en esta
carpeta privada. No commit/push.

Próximas tomas con mismoSDK/perfil: reutilizar conversor, nombres/orden y
recetaSDK comprobados; no repetir investigación binaria/interposer. Sí validar
bag/hash/cobertura/rangos, derivado y comparaciónactual de postura/repose/
paros/cargador/fallos/exclusividad. No usar rawactuator para compararq: comparar
por nombres con whole_joint_states y estados reales de manos. No--loop1.
Cambios de efector/software requieren redescubrimiento del contrato.
