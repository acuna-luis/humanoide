# Demostraciones de manos Cruzr S2

**10-11-2026 — fuentes v4 localizadas.** El manual SDK §5.9.2 documenta
control de posición para siete ejes, mientras el demo Cruzr del paquete
inspeccionado enumera seis. Se encontró un URDF v4 EVT3 con 11 articulaciones
móviles sin `mimic`; su correspondencia con los siete estados, montaje y
límites en esta unidad siguen pendientes. La inferencia estática de una rama
interna de corriente no demuestra fuerza, unidades ni control certificado.
No se envió movimiento. [Detalle](../../docs/vla/SMOLVLA_MANO_V4_FUENTES_20261110.md).

**05-11-2026 — cambio supervisado terminado.** Sesión
`EFFECTOR-20261105T112001Z-ea4e3075`: respaldos verificados, perfiles SPS
instalados/cargados, HOME20D y estados de siete ejes por mano verificados.
Las demostraciones de dedos y la comprobación visual final quedan pendientes;
las lecturas no autorizan un movimiento nuevo. Ver la
[ficha de activación](../../docs/SYSTEM_CUSTOMIZATIONS.md#effector-v4-activation-20261105).
El `check_hands.sh` posterior detectó ambas manos y validó 16 tareas, pero
terminó rc40 porque `cruzr/home.xml` es el HOME v8 adaptado del proyecto, no
el hash de fábrica fijado en el manifiesto. No se cambió ni se dio por válida
su compatibilidad para estas demos; revisar antes de ejecutarlas.

**05-11-2026 — preparación anterior al cambio de perfil.**
El log de Motion identificó versión4 a ambos lados, mientras Motion y
Control Center conservaban `HW_TYPE=cruzr_s2_v1`. El selector supervisado se
incorporó a esta rama y su `--check` confirmó entonces que faltaba el cambio.
Ver arriba el estado posterior. La activación puede iniciar HOME y
requiere las condiciones físicas y autorización correspondientes. Consultar
la [guía de cambio](../../docs/guides/CAMBIO_EFECTOR_ABRAZADERAS_MANOS_V4.md).

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
