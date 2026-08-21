# VLA y teleoperación del Cruzr S2

Este directorio concentra la documentación para capturar demostraciones con
PICO 4 Ultra Enterprise, preparar datasets, ajustar GR00T N1.5 y desplegar un
checkpoint de forma gradual.

## Documentos

- [Guía de teleoperación, datos y entrenamiento](CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md): arquitectura, compatibilidad v0.2.0, procedimiento completo y criterios de decisión.
- [Checklist de sesión](templates/TELEOP_SESSION_CHECKLIST.md): lista imprimible para preparar, grabar y cerrar una sesión.
- [Manifiesto de ejemplo](templates/session_manifest.example.yaml): metadatos que deben acompañar cada sesión.
- [Registro de episodios](templates/episode_log.csv): cabecera CSV para aceptar o rechazar cada demostración.
- [Activación segura del checkpoint suministrado](../guides/CRUZR_S2_VLA_SAFE_ENABLEMENT.md): estado del shadow mode y bloqueos actuales para movimiento físico.

## Regla esencial

Teleoperar, grabar y entrenar son tres fases distintas. El flujo XR bruto del
PICO sirve para controlar y diagnosticar, pero no es por sí solo un dataset
LeRobot sincronizado. No se inicia una campaña grande hasta inspeccionar una
exportación piloto extremo a extremo.
