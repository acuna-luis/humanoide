# Cruzr S2 — integración y pruebas

Repositorio de documentación, diagnósticos y automatización desarrollados para
la puesta en marcha del humanoide UBTECH Cruzr S2.

## Estructura

```text
.
├── docs/
│   ├── guides/       # Guías de operación y documentos generados
│   ├── reports/      # Revisión técnica, inventario y matriz de capacidades
│   ├── support/      # Preguntas y seguimiento con UBTECH
│   ├── teleoperation/ # Estado operativo PICO, PC y robot
│   ├── vla/          # Teleoperación, datasets y evolución de checkpoints
│   └── vendor/       # Manual de producto recibido del proveedor
├── scripts/
│   ├── custom_tasks/ # Behavior Trees XML instalados por los scripts
│   ├── hands/        # Diagnóstico y demostraciones de manos v3/v4
│   └── *.sh          # Diagnóstico, voz, brazos, cajas, navegación y recovery
└── Cruzr S2-20260803T070710Z-1-003/
    └── Cruzr S2/SDK/ # SDK original del proveedor, sin reorganizar
```

Los paquetes locales `cruzrss2_vla_pack-002/` y
`utars-udoke-config-v0.2.0_offline-001/` no forman parte del repositorio. El ZIP
USD de 184,7 MB del SDK también permanece sólo en disco porque supera el límite
de tamaño de GitHub sin Git LFS.

## Inicio rápido

Todos los comandos siguientes se ejecutan desde la raíz del repositorio.

Comprobación general del ciclo de caja, sin movimiento:

```bash
./scripts/cruzr_blue_workbin_cycle.sh --check
```

Comprobación de navegación y mapa, sin movimiento:

```bash
./scripts/cruzr_blue_workbin_map_route_short.sh --check --fast
```

Comprobación de la transferencia entre mesas y del alineador AprilTag, sin
movimiento:

```bash
./scripts/cruzr_blue_workbin_table_transfer.sh --check --fast
```

Para una demostración fluida, preparar primero la cadena sin movimiento y
ejecutar el ciclo durante los tres minutos siguientes:

```bash
./scripts/cruzr_blue_workbin_table_transfer.sh --check --fluid
./scripts/cruzr_blue_workbin_table_transfer.sh --run --fluid
```

Este perfil acepta el depósito dentro de 50 mm y reduce latencia, pero mantiene
las comprobaciones críticas antes de cada movimiento.

Lista de movimientos de brazos permitidos:

```bash
./scripts/cruzr_brazos_sin_manos.sh --list
```

Después de instalar y hacer homing de las manos, comprobarlas sin movimiento:

```bash
./scripts/hands/check_hands.sh --model auto
```

La coreografía en vacío para vídeo y las pruebas guiadas con objetos están
documentadas en [scripts/hands/README.md](scripts/hands/README.md).

El catálogo de funciones y ejemplos está en
[docs/guides/CATALOGO_FUNCIONALIDADES_CRUZR_S2.md](docs/guides/CATALOGO_FUNCIONALIDADES_CRUZR_S2.md).

La transferencia de una caja entre dos mesas mediante navegación y alineación
AprilTag está documentada en
[docs/guides/TRANSFERENCIA_CAJA_ENTRE_MESAS_CON_APRILTAG.md](docs/guides/TRANSFERENCIA_CAJA_ENTRE_MESAS_CON_APRILTAG.md).

La preparación del PICO 4 Ultra Enterprise, la captura de demostraciones y el
flujo dataset → entrenamiento → shadow están documentados en
[docs/vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md](docs/vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md).
La [versión PDF](docs/vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.pdf) está maquetada
para compartir por correo.

El estado técnico vivo de la conexión PICO → PC → robot, incluidas las
versiones, incompatibilidades, pruebas fallidas, workarounds y gates de
reanudación, se conserva en
[docs/teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md](docs/teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md).

## Seguridad

Los modos `--run`, `--yes` y cualquier acción ROSA de movimiento pueden mover
una plataforma de gran masa y sus brazos. Antes de usarlos deben comprobarse el
estado de los paros, el cargador, la batería, el espacio libre y la presencia de
una persona con el paro físico preparado. ROS 2 y los scripts no sustituyen una
función de seguridad certificada.

## SDK y paquetes externos

El SDK entregado se conserva con su nombre y estructura originales en
[`Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/`](<Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/>).
Los paquetes ignorados deben obtenerse por el canal compartido por UBTECH y
copiarse en la raíz usando exactamente sus nombres originales.
