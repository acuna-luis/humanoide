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
│   └── vendor/       # Manual de producto recibido del proveedor
├── scripts/
│   ├── custom_tasks/ # Behavior Trees XML instalados por los scripts
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

Lista de movimientos de brazos permitidos:

```bash
./scripts/cruzr_brazos_sin_manos.sh --list
```

El catálogo de funciones y ejemplos está en
[docs/guides/CATALOGO_FUNCIONALIDADES_CRUZR_S2.md](docs/guides/CATALOGO_FUNCIONALIDADES_CRUZR_S2.md).

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
