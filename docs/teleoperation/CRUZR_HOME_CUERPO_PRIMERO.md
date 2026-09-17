# HOME: cuerpo a cero antes de los brazos

2026-09-16, Europe/Madrid — HOME-BODY-FIRST-04.
Petición del propietario: modificar y cargar cruzr/home. Operador confirma
E-stop pulsado y HOME; lectura previa verifica principal1, servo0, cargador0,
MetaMove con hash esperado y XML anterior exacto. No se envían acciones.

## Cambio y alcance

Orden: cabeza/elevador/cintura a cero (3,75 s), apertura relativa de ambos
hombros (2,5 s), bajada abiertos (10 s), cierre de brazos abajo (3,75 s).
Total20 s, mismas consignas y tiempos que open_v3, sólo se reordena el cuerpo.
Al enderezar se conservan ángulos de brazos, no su posición cartesiana.
Afecta también HOME automático de arranque y llamadas de otros flujos.
No valida posturas arbitrarias, carga sujeta, proximidad a muebles ni parada.
Los barridos geométricos de open_v3 no califican este nuevo orden.

Fuente: `scripts/teleoperation/tasks/cruzr_internal_home_body_first_v4_20s.xml`.
Generador/validador: `scripts/teleoperation/cruzr_internal_home_body_first.py`.
Destino Motion, contenedor `walker-motion.manipulation_robot_app-1`:
`/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/cruzr/home.xml`.
Antes SHA256 `05174d2b4cf003b9b1c5274cd445b0d4faefe4276c5fbe8e59e68e6b64ee8cbe`.
Después SHA256 `e3d0656424a3611d89262ae645f127d975920fd09c437f9ef9c07725d69dc49c`.
La tarea y task_list conservan nombre/registro; no se cambian protecciones.
Preflight de `cruzr_blue_workbin_cycle.sh` reconoce el hash exacto nuevo y exige
la misma biblioteca MetaMove; desconocidos siguen rechazados.

## Reproducción

Desde raíz del repositorio, con condiciones físicas revisadas y paro mantenido:

```bash
python3 scripts/teleoperation/cruzr_install_internal_home_body_first.py --check
python3 scripts/teleoperation/cruzr_install_internal_home_body_first.py --preflight
python3 scripts/teleoperation/cruzr_install_internal_home_body_first.py --install
python3 scripts/teleoperation/cruzr_install_internal_home_body_first.py --reload
```

Instalación atómica con control de hash concurrente y respaldo. Instalador sólo
acepta open_v3 exacto o esta versión; tras firmware distinto debe revisarse.
Reload reinicia exclusivamente manipulación; no llama StartMotion ni libera
el paro. Una recarga no demuestra operatividad ni autoriza liberar el E-stop.
Seguir guía CRUZR_V020_BOOT_GUARD si queda WaitStartMotion.

Respaldo robot: `/etc/walker/trajectory-overlays/20260916T114457.191983Z_home_body_first_v4/`.
Copia externa previa: `../Humanoide-vla-evidence/20260916T114256Z_HOME_BODY_FIRST/home.json`
(contiene el XML leído). Evidencia instalación:
`../Humanoide-vla-evidence/20260916T114519.052551Z_INTERNAL-HOME-CHANGE/`.
Evidencia recarga:
`../Humanoide-vla-evidence/20260916T114548.005531Z_INTERNAL-HOME-CHANGE/`.
Los relojes PC/robot difieren; usar recibos e identidad de proceso.

Reversión: bajo paro y condiciones revisadas, restaurar sólo home.xml desde
home.before.xml del respaldo, verificar SHA anterior y recargar con el
instalador histórico `cruzr_install_internal_home.py --reload`. No ejecutar
HOME ni reiniciar automáticamente al revertir. Conservar cambios ajenos.

Verificación local: diez pruebas (secuencia sin comandos de brazo en primera
etapa, preservación de consignas/tiempos, hash, rechazos, instalación atómica,
conflictos concurrentes y contrato canónico). Sintaxis Bash correcta.
INSTALADO verificado por hash tras escribir. Prueba física PENDIENTE.
Resultado final de recarga y disponibilidad: véase actualización al final.

## Resultado posterior

VERIFICADO: reinicio único de manipulación, StartedAt pasó de
2026-09-16T11:41:44.036544394Z a2026-09-16T11:45:26.685601422Z.
Hash nuevo intacto y paro mantenido después. RECARGA solicitada/completada como
reinicio de proceso; carga funcional de tareas PENDIENTE porque Motion espera
ListControllers y Control Center permanece WaitStartMotion tras el paro.
No liberar para probar: procede ciclo completo supervisado según guía v0.2.0.
No se reinició Control Center/hardware ni se envió StartMotion, HOME o rearme.

2026-09-16 11:56 UTC — Tras reinicio completo comunicado por operador,
comprobación sólo lectura `cruzr_boot_ready.sh --check` rc0: Motion3/3,
cámaras2/2 en seis topics con marcas crecientes y RELEASE_TECHNICAL_CHECK=passed.
Preflight del instalador confirma principal1, servo0, cargador0, MetaMove esperado
y HOME body-first-v4-20s exacto. Se indica liberación supervisada manteniendo
brazos abajo/vacíos y zona libre. Puede ejecutar HOME interno; liberación,
fin de arranque y ensayo de trayectoria aún pendientes. Cero movimientos del
agente. Evidencia: ../Humanoide-vla-evidence/20260916T115604.369673Z_INTERNAL-HOME-CHANGE/.
