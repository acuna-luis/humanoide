# Asociación de la segunda caja: orientación rechazada

**BOX-01-ASSOCIATION-DIAGNOSTIC — 02-10-2026, Europe/Madrid.**
OBSERVADO en el diario del operador; diagnóstico y presentación instalados PC.
Carga del mensaje nuevo PENDIENTE. No se amplían tolerancias ni se envían
órdenes al robot. No se ha resuelto la causa física/perceptiva de la discrepancia.

## Hallazgo y alcance

Ensayo `time ./scripts/optimistic_scenario1.sh --cycle 2 --run`, evidencia
`../Humanoide-vla-evidence/20261002T105632Z_OPTIMISTIC_SCENARIO1_503729/`.
Batch: dos solicitadas, una completada, interrupción en grasp de la segunda.
Los checkpoints por caja conservan diez etapas/HOME medido para la primera y
navigate_get1/enable_vision para la segunda. Sujeción y liberación siguen siendo
asumidas tras éxito técnico; el log no confirma físicamente su estado.

La transición cycle_boundary/cycle_ready conserva sesión y workers, revalida
HOME/mapa y registra physical_commands_sent=0. La segunda caja no repite la
carga inicial de mapa. Esto confirma carga de la funcionalidad de tanda y una
transición real; no un ensayo completo de dos depósitos ni un ahorro de tiempo
comparado. Los hashes archivados coinciden con las fuentes previas a este cambio
para runtime/perception/alignment/CLI/console/nav_correction.

Segunda caja antes del ajuste: X=0,790372931m, excede máximo0,79m en0,373mm.
Objetivo correctivo X=+20,372931mm para dejar20mm dentro del límite. Navegación
termina con éxito y dos poses frescas; residual máximo1,443mm/0,445°.
Segunda captura posterior: X=0,756795851m, Y=0,092173203m, Z=0,308552981m,
dentro del gateXYZ original (Z en base_link, no altura al suelo).

Las parejas visuales de cada postura son coherentes: antes5,984mm/0,588°;
después3,839mm/1,263°. El fallo pertenece a la asociación ENTRE posturas,
calculada sobre las medias de parejas en odometría local. Tras compensar el
chasis: traslación6,656716mm frente al máximo20mm y rotación completa del
cuaternión5,482393° frente al máximo3°. No es otro fallo de llegada ni un exceso
de distancia de la caja. La diferencia de ángulos Euler indica aproximadamente
4,908° de roll y −2,512° de yaw; éstos describen la estimación y no prueban un
giro físico. No se reduce la comparación a yaw para ocultar roll/pitch.

El operador responde que **no pudo comprobar** si la caja permaneció inmóvil.
No se puede atribuir el cambio a ruido visual ni a movimiento real. Calibración,
causa y comportamiento de orientación tras cambios de punto de vista PENDIENTES.
El agarre nativo de la segunda caja no se envió; tampoco retirada, depósito,
HOME de recuperación o siguiente caja. Los errores de lease aparecen durante
el cierre, después del rechazo primario. El estado físico actual requiere una
comprobación presencial y recuperación específica; no se deduce del diario.

## Cambio reproducible

Destino persistente: PC, scenario1_perception.py, scenario1_runtime.py y
scenario1_console.py, tests/fixture y documentación versionados. El comparador
conserva20mm/3° y lanza SelectionConsistencyError, subclase de ValueError,
con los valores medidos y máximos. Error/checkpoint contienen ambos valores;
el evento de asociación fallida añade measurement. Entradas malformadas o frames
incompatibles siguen abortando sin inventar una medición. Si la distancia finita
de entrada desborda al calcularla, se rechaza y el diagnóstico JSON usa null.
La consola identifica la comparación tras el ajuste y no anuncia un agarre.
También muestra correctamente cero ajustes, que antes aparecía vacío.

El mismo guard conserva frescura/TF, XYZ, fullSO3, número y distancia de ajustes,
llegada y watchdogs. No entrega una pose rechazada, no sustituye la selección ni
repite la acción. La última captura original sigue siendo referencia de agarre.
Dependencias: contrato y asociación existentes, supervisor y SPS transitorio.
Activación: la próxima sesión autorizada transmite las fuentes en memoria; no
hay instalación de XML/YAML, modificación del SDK o reinicio de contenedores.
No se ejecuta --run ni --check remoto en esta intervención del agente.

```bash
python3 -m unittest scripts.box_handling.test_scenario1_perception \
  scripts.box_handling.test_scenario1_box_alignment \
  scripts.box_handling.test_scenario1_console
bash -n scripts/optimistic_scenario1.sh
./scripts/optimistic_scenario1.sh --plan --cycle 2
git diff --check
```

Fixture: scripts/box_handling/fixtures/box_alignment_rotation_20261002.json,
contiene las dos asociaciones exactas del diario con su ruta y SHA256. Replay
rechaza5,482393° con traslación6,656716mm. Prueba de integración combina esas
asociaciones reales con preparación/objetivo simulados y verifica que no se
envía agarre nativo ni se escribe una referencia válida después del rechazo.
No es replay completo de DDS ni prueba física. Pruebas adicionales conservan
rechazos por posición/orientación, límites exactos y formatos de diagnóstico.

## Respaldo y reversión

Estado previo exacto, HEAD, git-status, manifiestos before/after, resumen del
incidente y resultados en
`../Humanoide-vla-evidence/20261002_BOX_ASSOCIATION_ROTATION_DIAGNOSTIC/`.
Reversión selectiva: restaurar los archivos modificados desde before/ y retirar
la fixture/documento nuevos, preservando cambios posteriores. No restaurar
checkpoints ni estados remotos. Los dos locks del usuario se conservan.
No se ha hecho commit ni push. La carga del nuevo diagnóstico y un ensayo
completo de varias cajas siguen PENDIENTES.

**VERIFICADO offline:**750 pruebas pertinentes correctas, incluidas siete
regresiones nuevas; 113 de percepción/asociación/consola pasan. Se conserva la
exclusión legacy test_scenario1_deposit_install con errores previos documentados.
AST, sintaxis del wrapper, --plan --cycle2 y diff-check correctos. Lista exacta
de módulos y resultados en tests.json/tests.txt del respaldo externo.

Fuentes exactas de esta revisión (SHA256):

- [scenario1_perception.py](../../scripts/box_handling/scenario1_perception.py): `d501fbb66d134d09939fc03afcd00b9fdb35dd701e9209dc8f2e3986e4669486`.
- [scenario1_runtime.py](../../scripts/box_handling/scenario1_runtime.py): `ea28ffa845565f6d22e75b403313b5ec1b12d0e70b19cff673392d07e0f6bcf0`.
- [scenario1_console.py](../../scripts/box_handling/scenario1_console.py): `973178d7f07e4af1a52418e792dbade3a6b86db0e308cf71e880d652bf4bd16a`.
- [test_scenario1_perception.py](../../scripts/box_handling/test_scenario1_perception.py): `27d40fe767919d73c9b792d4e9ce25b64b1a6f28889ea53d18276525c8824db1`.
- [test_scenario1_box_alignment.py](../../scripts/box_handling/test_scenario1_box_alignment.py): `9a95bddbb2fb20fbaec6a2443d93c0538e75ac7341e7ea2b7d87cf897c1d84d4`.
- [test_scenario1_console.py](../../scripts/box_handling/test_scenario1_console.py): `74d4f335c14260e1ce494f9bc880919b399e5c23618397992bd5f2ed1741b344`.
- [box_alignment_rotation_20261002.json](../../scripts/box_handling/fixtures/box_alignment_rotation_20261002.json): `1bdd8486f95e9a2cf0a398484828a22471622e4d2a5f9a8c0f7501d3f9d98574`.
