# Instrucciones para agentes

Este archivo es un punto de entrada para Claude y otros agentes que lo lean.
Las instrucciones comunes del proyecto están en [AGENTS.md](AGENTS.md): léelas
íntegramente y sigue su orden de inicio. No presupongas que el estado físico,
las autorizaciones o los archivos privados de una sesión anterior siguen
vigentes en otro equipo.

Para el piloto de SmolVLA con pelota, empieza además por
[el relevo portable](docs/vla/RELEVO_PORTABLE_SMOLVLA.md) y sus referencias.
Conserva cambios locales ajenos y nunca envíes órdenes por el mero hecho de
leer el relevo. Ante peligro inmediato, acciona el paro de emergencia sin
esperar a HOME; véase `AGENTS.md` para la recuperación posterior.

**Estado de SmolVLA (10-11-2026, ~18:53):** SmolVLA **se ha ejecutado en el
brazo físico** mediante `scripts/vla/smolvla_physical_bridge.py` (3 pasos
recortados a 0,05 rad, SUCCEED, seguimiento ≤2,4 mrad), con autorización del
propietario. La pila lease/guardia de Codex y su gate quedan congelados como
historia. Véase la sección más reciente de
[docs/vla/SMOLVLA_NATIVE_ARM_STEP_20261110.md](docs/vla/SMOLVLA_NATIVE_ARM_STEP_20261110.md)
y la ficha `SMOLVLA-PHYSICAL-BRIDGE-20261110`. Antes de mover, recomprobar
estado físico y pedir autorización actual; el brazo quedó fuera de la postura
PICO previa.
