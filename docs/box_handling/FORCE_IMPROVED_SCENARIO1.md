# Ejecutor mejorado del escenario 1

28-09-2026, Europe/Madrid. **BOX-01-EXEC-IMPROVED — implementado en el PC,
verificado offline; integración y prueba física PENDIENTES.**

El usuario solicita un ejecutor nuevo y pide explícitamente asumir la geometría
actual de `force_escenario1.sh`. Se conserva esta secuencia y sus parámetros:
get1 → habilitar visión → `local_front_box/separate_right_cruzr` →
`cruzr/mobot_back_20` → put1 → `wrc_cruzr/put_cruzr_wrc_low` → `cruzr/home`.
No se sustituyen XML/YAML, límites, tamaños internos ni distancias del proveedor.
El perfil registra `operator_assumed_existing`, no una validación física nueva.

## Uso

Desde la raíz del repositorio:

```bash
# Sólo plan local, sin conexión:
./scripts/force_improved_scenario1.sh --plan

# Sin argumentos equivale a --check: comprobaciones, sin movimiento:
./scripts/force_improved_scenario1.sh --check

# Ejecución presencial supervisada del ciclo:
./scripts/force_improved_scenario1.sh --run

# Terminar tras confirmar la caja separada y sujeta, sin retroceso ni transporte:
./scripts/force_improved_scenario1.sh --run --stop-after grasp

# Continuación explícita de una pausa limpia; vuelve a comprobar el estado:
./scripts/force_improved_scenario1.sh --resume /ruta/de/evidencia/checkpoint.json
```

`--wifi` añade el salto SSH conocido. Reutiliza el ASKPASS existente y exige la
clave SSH del host conocida; no incorpora credenciales. `--evidence-dir` admite
un directorio nuevo. `--profile` acepta sólo el esquema, tamaño y tareas revisados;
no es un mecanismo para inyectar otras tareas o trayectorias.

`--check` descubre contenedores, valida imagen/HW_TYPE, dependencias SPS y WRC,
variante HOME/biblioteca, controlador, acción libre, dos paros, dos baterías≥20%,
cargador, dos muestras articulares frescas e inmóviles y HOME inicial20D.
Consulta mapa y get1/put1 sin cargar ni relocalizar; código55 indica preparación
necesaria. No inicia adaptadores, instala tareas ni ejecuta percepción. Requiere
el paquete SPS del ejecutor anterior ya instalado y coincidente; si falta,
rechaza con diagnóstico y no lo instala automáticamente.

`--run` exige terminal y `CONTINUAR` después del preflight. La preparación de mapa
se hace dentro de la etapa autorizada. Tras el agarre exige `SUJETA`; antes del
depósito exige `DEPOSITAR`; antes de HOME exige `LIBRE`. Son comprobaciones
presenciales del estado físico y del montaje, no mediciones automáticas de fuerza.
La tarea WRC original incluye abrir las abrazaderas dentro de su XML; este
ejecutor no introduce una parada entre el descenso y esa apertura.

## Supervisión y recuperación

- Intención y resultado de cada etapa se guardan atómicamente, con fsync, en PC
  y Motion. Un fallo/interrupción deja estado indeterminado y bloquea continuidad.
- El cliente nativo emite UUID, aceptación real, feedback, estados y resultado.
  Ante plazo, señal o pérdida del heartbeat solicita cancelar sólo su UUID y
  observa el resultado terminal durante un plazo acotado. No hay reintentos de
  acciones físicas ni apertura/HOME automáticos después de fallar.
- El supervisor renueva un lease comprobado por el cliente. EOF, heartbeat
  perdido o fallo del watchdog revocan la renovación. La sesión SPS dura como
  máximo900s; es un límite técnico, no una estimación de duración del ciclo.
- Se mantiene el lock local compartido con workbin y el lock remoto SPS durante
  la sesión. Se vuelven a comprobar controladores y acción libre en cada etapa.
  Los locks no arbitran todos los posibles mandos externos: el operador debe
  mantener PICO/UI/mando manual fuera del control simultáneo.
- HOME final requiere dos muestras20D recientes con velocidad/consigna dentro
  del contrato existente y posición absoluta<0,02rad. Un resultado exitoso de
  `cruzr/home` por sí solo no completa el ciclo.
- Se puede reanudar únicamente desde un checkpoint limpio cuya última etapa sea
  `verify_held` o `verify_released`, con caja reconfirmada y mismo perfil, arranque,
  contenedores, dependencias y puntos del mapa. El origen se marca consumido antes
  de armar la continuación; no se publica otra copia limpia antes de reclamarlo.
  Un intento fallido después de reclamarlo exige revisión de la evidencia nueva;
  no se reutiliza el origen ni se borra el marcador para repetir el movimiento.

Una cancelación aceptada o terminar SSH **no demuestra parada física**. Cuando el
resultado queda indeterminado se conserva la evidencia y no se envía otra etapa.
El nuevo cliente usa una adaptación local de la API Python ROSA revisada: corrige
la aceptación inferida del handle y copia el UUID al cancelar, sin modificar el
SDK. Comprueba antes de enviar el AST de las clases nativas y las interfaces
generadas; una versión distinta requiere revisión. La compatibilidad real y la
cancelación física todavía no se han ensayado con este ejecutor.

## Percepción y geometría

En el punto donde Singapore solicita percepción, después de sus preparaciones
de cabeza/brazos, el adaptador temporal obtiene dos capturas consecutivas. Cada
una pasa el contrato existente de frescura y TF exacta. Exige coherencia≤2cm/3°
y timestamps crecientes; entrega la segunda pose original de cámara, sin promedio.
El plazo nativo existente sigue vigente: una captura lenta o incoherente falla.
Se guardan ambas detecciones y el diagnóstico de estabilidad.

Esto no certifica alcance, IK, identidad de objeto ni sujeción. Se conserva el
selector frontal actual y su paso vertical0,22±0,04m; el modelo para encajes de
menor paso sigue pendiente de medidas. Tampoco se convierte la trayectoria WRC
en un depósito a100cm: se mantiene la geometría indicada por el usuario. No se
integra el avance corto no cualificado ni se amplían límites.

## Fuentes, verificación y reversión

- [Entrada](../../scripts/force_improved_scenario1.sh) y [CLI](../../scripts/box_handling/scenario1_cli.py).
- [Supervisor](../../scripts/box_handling/scenario1_runtime.py), [cliente nativo](../../scripts/box_handling/scenario1_action_client.py).
- [Contrato de etapas](../../scripts/box_handling/scenario1_contract.py), [comprobaciones](../../scripts/box_handling/scenario1_checks.py), [percepción](../../scripts/box_handling/scenario1_perception.py).
- [Perfil con geometría actual](../../scripts/box_handling/scenario1_current_geometry.json).

Receta de validación local, sin robot:

```bash
bash -n scripts/force_improved_scenario1.sh
PYTHONDONTWRITEBYTECODE=1 python3 -B -m unittest discover \
  -s scripts/box_handling -p 'test_scenario1_*.py'
./scripts/force_improved_scenario1.sh --plan
git diff --check
```

VERIFICADO:99 pruebas offline de contratos, API nativa simulada, cancelación,
estado indeterminado, rechazo de acción, percepción, locks/lease, HOME incompleto
y reanudación de un solo uso. Sintaxis Bash/Python3.10, ayuda y plan local pasan.
No se ejecutaron --check/--run contra el robot. Tampoco hubo instalación, reinicio,
nueva captura real ni modificación de mapas, tareas, SDK o servicios.

Instalado: sólo fuentes PC y permiso ejecutable de la entrada. Cargado en robot:
no. Probado físicamente: no. Al ejecutarse, transmite código en memoria y crea
evidencia/adaptadores temporales en Motion; los adaptadores usan los archivos SPS
existentes verificados por hash. No cambia su autoarranque ni sus archivos.

Evidencia de construcción, hashes y backups documentales:
`../Humanoide-vla-evidence/20260928_IMPROVED_SCENARIO1_BUILD/`.
Se verificó que el script original y las fuentes SPS revisadas mantienen sus
hashes. Cada uso genera evidencia PC fuera de Git y, al armar, una carpeta
`/tmp/cruzr-scenario1-*` en Motion; sus rutas se registran en events.jsonl.
Reversión de esta intervención: retirar los archivos nuevos `scenario1_*`, sus
tests y la entrada, y revertir selectivamente las notas desde `before/`.
No hay cambios remotos que revertir en esta intervención; preservar evidencia de
cualquier ejecución posterior y reconciliar primero acciones/caja indeterminadas.

Punto de reanudación: comprobar el nuevo ejecutor en lectura contra la instalación
actual; después, ensayo supervisado por etapas con condiciones físicas nuevas.
