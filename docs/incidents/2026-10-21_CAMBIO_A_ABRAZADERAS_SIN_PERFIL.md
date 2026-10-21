# Cambio físico a abrazaderas con perfil v4 aún activo

21-10-2026, Europe/Madrid. ID `EFFECTOR-CLAMP-MISMATCH-20261021`.

## Estado y hallazgo

**OBSERVADO por el operador:** cambió las manos v4 por abrazaderas con el robot
apagado; después liberó el paro. No ejecutó el selector de efector ni un HOME
manual. Esto no demuestra la postura ni la salud actuales.

**VERIFICADO mediante consultas de lectura:**

- `bash scripts/hands/cambiar_efector.sh --to clamp --check` terminó con código 0,
  pero indicó que ni los archivos ni los procesos coinciden con el destino
  clamp. Ese retorno no certifica perfil clamp ni HOME.
- Los nueve servicios Motion y Control Center conservan
  `HW_TYPE=cruzr_s2_v1_sps`. La muestra de manipulación estaba en `restarting`.
- Los snapshots de ambos hosts muestran `active_session: null`; no hay una
  sesión del selector pendiente que reanudar en esos snapshots.
- En el arranque actual, hardware registra `hand cnt=0`. La inicialización de
  `dexterous_hand_controller` agota la espera de `get_version` y registra
  `Unknown hand type` / fallo de inicialización.
- Control Center supera SelfCheck, pero StartMotion falla con reason 19 y
  termina en Fault. No se ha verificado HOME actual.

El cambio físico no cambió el perfil de software: sigue intentando cargar el
controlador de manos v4 sin esas manos presentes. Es el mismo patrón documentado
en el [incidente del 15-10](2026-10-15_ARRANQUE_SIN_MANOS.md). La lectura no
demuestra una avería del sensor de fuerza/par ni autoriza HOME o un reinicio.

## Punto de reanudación

Está pendiente aplicar el perfil clamp con la
[receta coordinada existente](../guides/CAMBIO_EFECTOR_ABRAZADERAS_MANOS_V4.md).
Si no hay HOME medible porque el arranque sigue fallido, la receta contempla:

```bash
bash scripts/hands/cambiar_efector.sh --to clamp --apply --secured-recovery
```

**No ejecutado en esta intervención.** Requiere brazos asegurados por personal
capacitado, preparación física actual y los gates de la guía y del selector.
El modo conserva las comprobaciones de paros, cargador y baterías, además del
respaldo y la verificación; al liberar físicamente el paro puede continuar el
HOME nativo. No es una consulta ni una autorización de movimiento. No se ha
autorizado movimiento ni comprobado HOME actual en este diagnóstico.

## Evidencia y cambios

Evidencia privada:
`../Humanoide-vla-evidence/EFFECTOR-20261021T065940Z-53b52e6b/`.
Consultas de perfil, snapshots y logs del arranque actual; sin acciones,
publicación de comandos, reinicios, recreación o cambios de configuración del
robot. El `--check` sólo produjo su evidencia diagnóstica en el PC.

Cambios locales de esta intervención: este informe, su enlace en el README de manos
y registros actuales en la fuente global, el índice de adaptaciones y la guía de arranque.
Respaldo previo del README en `before-docs/scripts/hands/README.md` dentro de la
evidencia. Reversión documental selectiva: retirar este informe y su bloque del
README, conservando las demás ediciones. Sin commit ni push.
