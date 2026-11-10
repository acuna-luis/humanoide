# Instrucciones para agentes

Este archivo es un punto de entrada para Claude y otros agentes que lo lean.
Las instrucciones comunes del proyecto están en [AGENTS.md](AGENTS.md): léelas
íntegramente y sigue su orden de inicio. No presupongas que el estado físico,
las autorizaciones o los archivos privados de una sesión anterior siguen
vigentes en otro equipo.

Para el piloto de SmolVLA con pelota, empieza por
[docs/vla/SMOLVLA_PUENTE_FISICO_20261110.md](docs/vla/SMOLVLA_PUENTE_FISICO_20261110.md):
es el documento vigente (estado, puente, comandos, requisitos en otra máquina y
siguientes pasos). El [relevo portable](docs/vla/RELEVO_PORTABLE_SMOLVLA.md)
anterior queda como historia. Conserva cambios locales ajenos y nunca envíes
órdenes por el mero hecho de leer el relevo. Ante peligro inmediato, acciona el
paro de emergencia sin esperar a HOME; véase `AGENTS.md`.

**Estado de SmolVLA (10-11-2026, ~19:10):** la metodología grabaciones →
SmolVLA → robot físico está **validada físicamente** con
`scripts/vla/smolvla_physical_bridge.py`: 3 pasos de brazo y después un intento
de agarre de 50 pasos con brazo derecho y mano v4, todos `SUCCEED`. La tarea de
la pelota no se completó (faltan datos). El brazo quedó fuera de HOME y la mano
v4 **cerrada**, quizá sujetando la pelota. La pila lease/guardia de Codex y su
gate quedan congelados como historia. Antes de mover, recomprobar el estado
físico y pedir autorización actual.
