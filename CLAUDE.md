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

**Estado del último relevo de SmolVLA:** el usuario pidió detener el ensayo
y cambiar de agente. La documentación y algunos cambios locales pueden estar
sin commit; preserva el `git status` completo y lee la sección más reciente de
[relevo](docs/vla/RELEVO_PORTABLE_SMOLVLA.md). La copia portable anterior quedó
desactualizada; consulta el `LEEME.md` de `RELEVO_CLAUDE_20261110` si existe,
y contrasta sus manifiestos y omisiones. La inferencia y un watchdog sintético
pasaron sin goal físico; **SmolVLA no se ha ejecutado en el brazo**. El gate de
despacho permanece cerrado y la causa del incidente 731084 no está identificada.
No sustituyas estado actual ni requisitos físicos por confirmaciones antiguas.
