# Demostraciones de manos Cruzr S2

Estos scripts orquestan exclusivamente tareas de fábrica ya instaladas en el
robot. No instalan XML, no activan GR00T/VLA y no convierten las secuencias en
manipulación autónoma. Antes de cualquier movimiento identifican las manos por
sus topics ROS 2, leen batería, cargador y paros y verifican los XML contra
`factory_tasks.sha256`. Las primitivas referenciadas por los gestos y el mando
se verifican además contra `factory_meta.sha256`.

## Orden obligatorio

1. Instalar físicamente las manos siguiendo el SOP de UBTECH.
2. Completar homing sin errores.
3. Dejar ambas manos vacías y el robot en `home`.
4. Mantener 1,5 m libres alrededor y sobre los brazos.
5. Preparar una segunda persona junto al paro físico.
6. Ejecutar primero el diagnóstico:

```bash
./scripts/hands/check_hands.sh --model auto
```

Si no detecta inequívocamente v3 o v4, no se debe forzar el modelo.

Los XML pueden auditarse antes de instalar las manos, también sin movimiento:

```bash
./scripts/hands/check_factory_tasks.sh
```

## Demostraciones en vacío

Todos los comandos se pueden comprobar sin movimiento sustituyendo `--run`
por `--check`.

```bash
# Movimiento secuencial de dedos y apertura/cierre bimanual.
./scripts/hands/demo_dexterity.sh --run --model auto

# Pinzas pulgar-índice, pulgar-medio y pulgar-anular; sólo v4.
./scripts/hands/demo_precision_v4.sh --run

# Gesto con brazo derecho y retorno a cero.
./scripts/hands/demo_expressive.sh --run --model auto

# Coreografía compacta recomendada para el vídeo del CEO, sin objetos.
./scripts/hands/demo_ceo.sh --run --model auto
```

`--yes` omite la confirmación inicial únicamente en las demostraciones sin
objetos. No omite ninguna comprobación técnica.

## Demostraciones con objetos

Estas tareas contienen trayectorias fijas de fábrica: no localizan la bandeja
ni el mando con la cámara. Primero deben ensayarse en vacío y después con un
objeto ligero, sin personas dentro del alcance.

```bash
./scripts/hands/demo_functional.sh --check --demo plate --model auto
./scripts/hands/demo_functional.sh --run   --demo plate --model auto

# Sólo manos v4.
./scripts/hands/demo_functional.sh --check --demo remote
./scripts/hands/demo_functional.sh --run   --demo remote
```

El script siempre se detiene para que un operador apoye el objeto antes de
abrir las manos. Si se cancela en ese punto, no ejecuta automáticamente `home`.

## Recuperación con manos vacías

Si una demostración en vacío termina entre tareas, retirar primero cualquier
objeto, despejar completamente los brazos y ejecutar:

```bash
./scripts/hands/recover_hands_home.sh --check --model auto
./scripts/hands/recover_hands_home.sh --run --model auto
```

No debe usarse mientras otra acción siga activa ni con un objeto agarrado.

## Qué se puede afirmar en el vídeo

- `Factory hand dexterity`: movimientos de dedos y pinzas preprogramados.
- `Factory fixed-pose manipulation`: bandeja o mando en pose preparada.
- No anunciar `autonomous object manipulation`: estas tareas no ejecutan un
  detector, grasp planner ni política VLA.
