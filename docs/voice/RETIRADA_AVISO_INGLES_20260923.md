# Retirada del aviso inglés duplicado de arranque

23-09-2026, Europe/Madrid. VOICE-BOOT-06, instalado y hash verificado.

Petición del operador: retirar «Ready to release the emergency stop» del arranque
normal, ahora que Control Center pronuncia su aviso nativo en español.
`cruzr_boot_voice.py --watch` conserva comprobación técnica y visualización,
pero ya no llama announce(). `--check` sigue siendo sólo lectura; una prueba
manual explícita `--check --announce` conserva la función de voz para diagnóstico.
No se deshabilita el servicio ni se modifica el aviso de recuperación del watchdog.

Destino Vision compartido: /etc/walker/boot/cruzr_boot_voice.py.
SHA instalado: f17c1295bb8ed2e7983840d8725743aa820c59dc5ac4d9368e178737219106f9.
Fuente: [script](../../scripts/upgrade/cruzr_boot_voice.py).
Se actualizó [ayuda del check](../../scripts/cruzr_boot_ready.sh) para no indicar
que hay que esperar la frase inglesa.31 tests pasan; watcher no habla, mantiene
visual y comprobaciones; anuncio manual explícito comprobado con mocks.
Servicio estaba inactive/dead antes de instalar: no queda watcher anterior activo.
No reinicio ni reproducción. Próximo watcher usará la nueva versión; comprobación
real del siguiente encendido pendiente. Paro1 verificado por instalador.

Backup externo, plan reproducible y recibo: /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260923T095118Z_BOOT_VOICE_DEDUP.
Backup persistente remoto: /etc/walker/voice/deployments/cruzr-voice-20260923T095118Z.
Aplicación usa scripts/voice/deploy_voice_assets.py con deployment/plan.json,
hash previo, sustitución atómica y respaldo inmediato. No repetir sobre instalado.
Los originales y metadatos efectivos están en install/remote-receipts-and-originals.tar.gz.

Rollback (con paro pulsado y evidencia nueva):

```bash
python3 scripts/voice/deploy_voice_assets.py \
  --rollback-receipt /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260923T095118Z_BOOT_VOICE_DEDUP/install/receipt.json \
  --evidence /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/VOICE_BOOT06_ROLLBACK_NUEVO
```

Restaura sólo el script si conserva el hash instalado; no cambia Control Center,
WAV españoles ni servicio. Surte efecto en la siguiente ejecución del watcher.
El instalador histórico install_selfcheck_watchdog.sh fija el hash anterior del
módulo de voz (y del gate anterior a CC español); requiere revisión de dependencias
antes de reutilizarlo. No se amplían esos guards ni se reinstala el watchdog aquí.
Cambios de red/movimiento: ninguno. Sin commit/push.
