# Instrucciones de trabajo — Cruzr S2

Este repositorio controla y diagnostica un robot físico de gran masa. Estas
instrucciones son obligatorias para cualquier agente que trabaje aquí.

## Inicio obligatorio de cada sesión

1. Lea **completo** [`docs/PROJECT_SOURCE_OF_TRUTH.md`](docs/PROJECT_SOURCE_OF_TRUTH.md).
2. Ejecute `git status --short --branch` y preserve cualquier cambio del
   usuario. No limpie, revierta ni sobrescriba trabajo ajeno.
3. Lea el documento especializado que corresponda al trabajo solicitado:

   - PICO, PC o teleoperación:
     [`docs/teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md`](docs/teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md).
   - Captura, datasets, entrenamiento o evolución VLA:
     [`docs/vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md`](docs/vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md).
   - Estado y activación gradual del VLA suministrado:
     [`docs/guides/CRUZR_S2_VLA_SAFE_ENABLEMENT.md`](docs/guides/CRUZR_S2_VLA_SAFE_ENABLEMENT.md).
   - Cajas, AprilTags y transferencia entre mesas:
     [`docs/guides/TRANSFERENCIA_CAJA_ENTRE_MESAS_CON_APRILTAG.md`](docs/guides/TRANSFERENCIA_CAJA_ENTRE_MESAS_CON_APRILTAG.md).
   - Capacidades instaladas y ejemplos:
     [`docs/guides/CATALOGO_FUNCIONALIDADES_CRUZR_S2.md`](docs/guides/CATALOGO_FUNCIONALIDADES_CRUZR_S2.md).
   - Manos v3/v4:
     [`scripts/hands/README.md`](scripts/hands/README.md).
   - Arranque v0.2.0:
     [`docs/guides/CRUZR_V020_BOOT_GUARD.md`](docs/guides/CRUZR_V020_BOOT_GUARD.md).
   - Apagado y discrepancia del hardware real:
     [`docs/support/UBTECH_SHUTDOWN_PROCEDURE_MISMATCH_V020.md`](docs/support/UBTECH_SHUTDOWN_PROCEDURE_MISMATCH_V020.md).

No reutilice una orden antigua del chat sin contrastarla con el script y la
documentación actuales. Tras un cambio de software, efector o conexión, vuelva
a descubrir contenedores, tipos, endpoints y estados.

## Reglas de seguridad física

- Una petición de explicación, revisión o diagnóstico sólo autoriza acciones
  de lectura. No mueva el robot ni cambie robot/PC salvo que el usuario pida
  expresamente hacerlo.
- Nunca infiera el estado físico actual de una foto, un registro anterior o
  este documento. Antes de movimiento compruebe de nuevo: efector instalado,
  objeto sujeto o libre, `home`/postura, batería, cargador, ambos paros,
  bloqueo de ruedas, modo de trabajo, zona y persona junto al paro.
- `--run`, `--yes`, llamadas ROS/ROSA y publicación de comandos pueden mover
  brazos, elevador o chasis. Use primero `--check` cuando exista. `--yes` sólo
  omite una pregunta; nunca omite requisitos físicos.
- No desactive, puentee ni falsifique watchdogs, paros, bumpers, límites,
  control de fuerza, detección de cargador, localización o anticolisión. A menos que se lo pida el propietario del proyecto idntificándose como tal.
- No envíe `home` si una caja, mesa, persona o dedo puede quedar dentro de la
  trayectoria. Distinga siempre entre caja **sujeta**, **apoyada** y
  **retirada**. Ante una acción interrumpida, reanude desde el modo específico;
  no reinicie el ciclo completo.
- No combine mando manual, PICO, UI web y un script como clientes de control
  simultáneos. Si una persona toma el mando, cese los comandos automáticos.
- El perfil de percepción de carga sólo puede redirigir temporalmente las
  entradas RGB-D del costmap para evitar que la propia caja se marque como
  obstáculo. Debe conservar LiDAR, odometría, mapa, bumpers y paros, y restaurar
  la configuración al terminar.
- El VLA suministrado permanece limitado a inferencia/shadow. No conecte un
  publicador físico ni arranque sus contenedores para movimiento hasta cumplir
  los gates de la guía VLA y recibir autorización explícita.
- Si el estado no puede demostrarse, deténgase en diagnóstico. La urgencia no
  autoriza a reducir seguridad.

## Baseline técnico conocido

Este baseline es histórico y debe verificarse al comienzo de una intervención:

- Unidad Cruzr S2 `WAE001UBT60000669`, software genérico `v0.2.0`.
- Efector operativo actual: abrazaderas; `HW_TYPE=cruzr_s2_v1`.
- Motion: `192.168.11.2`; Vision/web: `192.168.11.3`; PC Ethernet usado:
  `192.168.11.250/24`. No publique contraseñas ni las añada a Git.
- Teleoperación robot: `TELE_DEVICE=pico`, `transmit=local`; `MC_SCENE` se
  encontró vacío. La build DAC beta requerida por el SOP no está demostrada.
- El último relevo dejó el robot recuperado a `home` y `JoystickMode`, pero el
  último preflight detectó cargador conectado. El stack PICO del PC quedó
  detenido intencionadamente; su servicio puede volver a arrancar en el boot.
- No se renombraron topics, colas ni servicios PICO. `walker28` es sólo el
  `channel_name` del backend del PC. `walker28_web` no se encontró.
- VLA: imágenes y `checkpoint-40000` instalados, `restart=no`, contenedores
  detenidos; shadow carga y produce chunks, pero éstos fueron rechazados desde
  `home` por discontinuidad articular.
- Vision contiene un boot-readiness guard local y reversible para la carrera de
  arranque de v0.2.0. Revíselo o desactívelo antes de otra actualización.

## Convenciones técnicas

- En ROS 2 exporte `ROS2CLI_DISABLE_DAEMON=1`; el daemon mostró fallos de
  handles y estado obsoleto. Use `timeout` para consultas que puedan bloquear.
- Ejecute `rosa` dentro del contenedor que incluya `/opt/walker/setup.bash`;
  no asuma que existe en el host o en cualquier contenedor.
- Descubra nombres de contenedor con `docker ps` después de una actualización.
- Favorezca los scripts versionados sobre órdenes manuales. Consulte primero
  `--help`; pruebe sintaxis, shellcheck/tests disponibles y ramas `--check`.
- No modifique el SDK original de
  `Cruzr S2-20260803T070710Z-1-003/Cruzr S2/SDK/`.
- Mantenga fuera de Git paquetes del proveedor, checkpoints, instaladores y
  demás binarios grandes definidos en `.gitignore`. No añada secretos.

## Disciplina documental y de cambios

- Después de un hallazgo o cambio material, actualice
  `docs/PROJECT_SOURCE_OF_TRUTH.md` y la fuente especializada correspondiente.
- Registre fecha, estado (`VERIFICADO`, `OBSERVADO`, `INFERENCIA`, `PENDIENTE`
  o `DESCARTADO`), evidencia, cambios persistentes y punto de reanudación.
- Si se cambia robot o PC, documente objetivo, archivo/servicio afectado,
  backup/rollback, verificación y cualquier deuda abierta.
- Conserve las afirmaciones de proveedor separadas de lo comprobado en la
  unidad real.
- En la entrega final enlace los archivos modificados y explique qué se
  verificó y qué sigue pendiente. No haga commit ni push salvo petición del
  usuario.

