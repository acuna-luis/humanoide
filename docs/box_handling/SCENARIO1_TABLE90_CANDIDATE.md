# Escenario 1: depósito en mesa de 90 cm

2026-10-01, Europe/Madrid — BOX-01-TABLE90-CANDIDATE.
Rama `feat/scenario1-deposit-table-90cm`; sin commit ni push.

## Estado vigente

**INSTALADO y CARGADO por la tarea nativa. DEPÓSITO PROBADO FÍSICAMENTE.**
El operador confirma mesa original funcional de45 cm y destino90 cm, misma caja,
abrazaderas, agarre y disposición horizontal. Son datos del operador, no nuevas
mediciones del agente. Confirmó preparación física y ausencia de otro control.

El ensayo real terminó navegación get1, visión, agarre, retirada, navegación put1
y depósito/apertura con resultado nativo SUCCEED. Pausa antes de HOME.
El operador confirma caja apoyada estable en mesa90, completamente liberada de
ambas abrazaderas y recorrido de HOME libre. HOME SUCCEED y dos muestras MEASURED_HOME=1, velocidad0; máximo corporal
0,002684rad. Final --check rc0 confirma estado/hashes tras cerrar la prueba.
La sujeción y liberación en el checkpoint optimistic siguen etiquetadas assumed;
la confirmación del operador se registra aquí sin falsear evidencia de sensores.

Checkpoint del tramo de depósito (histórico): `deposit-trial/checkpoint.json`, stop_after=deposit,
completed=retreat/navigate_put1/deposit, box_state=unknown (correcto: no se ha
verificado liberación en ese segmento). Se reanudó con declaración
released/recovery-confirmed y preflight fresco. grasp-trial y deposit-trial están
consumidos; checkpoint final home-trial contiene verify_released/home/verify_home,
sin fallo y box_state=released. No reutilizar checkpoints consumidos.

## Cálculo e integración

Delta de altura:0,90−0,45=+0,45 m. Se trasladan exclusivamente las dos Z absolutas
iniciales de manos:0,65→1,10 m. Los puntos relativos originales producen Z1,10 m
hasta10 s y Z0,90 m a12 s. Son coordenadas de tarea, no una medición independiente
del suelo o de la base de la caja. Se conserva la calibración funcional declarada.

Se conservan X/Y, orientación, descenso20 cm, tiempos, torso, box_size original,
control de fuerza, vallas, detección de colisión y apertura. No se trasladan
consignas articulares del estudio local al robot: Motion calcula sus articulaciones.
Agarre, mapa de puntos, retirada y HOME no se han editado; SDK intacto.

Optimistic selecciona por defecto `config/box_handling/scenario1_table90_geometry.json`.
Entradas standard conservan el perfil original. Runtime obtiene tarea de depósito
del perfil, comprueba paquete y hashes, sin fallback a45. Perfil/hash propios
impiden cruzar checkpoints45/90. El manifiesto del bundle conserva physical_validation=pending/executable=false
como estado inmutable de su creación, no como estado actual del robot; review.json,
--plan y la ficha posterior registran el ensayo real.
Compatibilidad `calculated_pending_motion` indica
origen calculado del perfil; no se cambia a verified para fabricar validación.

Paquete/tarea:
`local_scenario1_deposit/3e142cd1eda7e4a0d625a566ff9b86127d6ec0fee430004c55ced8caf17118cf`.
Instalación aditiva en Motion, contenedor redescubierto
`walker-motion.manipulation_robot_app-1`, ID3e1296b4…; imagen9f7acf4b….
XML bajo `/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/`
y YAML bajo `/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config/meta_clamp/`,
ambos con ruta de tarea anterior y extensión correspondiente.
XML SHA25626bb3b13d5f606dd4691045f509853a1621a8aeec0c3ef798caf300a6dbf2c62;
YAML SHA256f3fdf22c7687d3b4376dafa1975b56ba0d0da8fa0930d4b53d4058a462ddcc69.
Tres dependencias originales y seis archivos del modelo/HOME nativo se pinnean en
`scenario1_table90.py`; se comprueban antes de las etapas físicas.

La instalación creó dos archivos previamente ausentes, sin sobrescribir vendor,
sin reinicios ni movimiento. Recibo/rollback remoto:
`/var/tmp/cruzr-scenario1-deposit/3e142cd1eda7e4a0d625a566ff9b86127d6ec0fee430004c55ced8caf17118cf/`.
El recibo inicial loaded=not_verified es histórico; el ensayo posterior demuestra
carga/ejecución nativa. Conserva ese recibo y registra la prueba por separado.

## Modelo y alcance de la revisión

URDF actual leído de Motion: raíz mobile_base_link, objetivos
left_hand/right_hand/torso; distinto del CAD archivado. SHA256c01acb40…;
descripción, task_stack y bibliotecas también contrastados/pinneados.
Los estudios del CAD antiguo se conservan como hipótesis históricas, no baseline
activo. La máscara original del torso deja libre XYZ en el estudio condicional.

Con URDF nativo,41/41 muestras por perfil entre6/10/12 s convergen. Desde las
articulaciones ROS nombradas medidas después del agarre,61/61 muestras por perfil
con regularización0,001 convergen y no exceden límites URDF de velocidad por
diferencias finitas. Error máximo posicional de manos90≈0,0001823 mm.
La primera búsqueda sin regularización saltaba entre ramas y fallaba dos muestras
en cada perfil; esto no prueba imposibilidad ni representa trayectoria nativa.

CAD realmente instalado, todas las parejas conservadas, cabeza medida incluida:
61 muestras no añaden parejas solapadas respecto a HOME. Los27 solapes de CAD
presentes también en HOME no se borran ni se declaran automáticamente inocuos.
No hay certificado continuo, reproducción exacta de interpolación nativa,
modelo exterior de caja/mesa, ni garantías de aceleración. El ensayo autorizado
usa controles nativos y operador junto al paro; no convierte ese estudio en certificado.

## Cambios de estado y evidencia

Primera lectura rechazó cargador; nueva lectura lo confirmó libre y HOME, pero
mapa vacío/FSM_WAITSETMAP. Se preparó `utars_nav_map` y relocalización global con
`CRUZR_MAP_NAME=utars_nav_map ./scripts/cruzr_blue_workbin_map_route.sh --check --fast`.
Ambas acciones status4/NAVIGATION_READY. El script histórico terminó rc1 al
rechazar la secuencia get1/put1; no se editó task.json. Mapa activo/localización
se conservan. Caché transitoria Motion `/tmp/cruzr_map_runtime_<sha256(map_name)>.state`.
Durante navegación put1 aparecieron LOCATION_LOST/LOCATE_RUNNING y el controlador
se recuperó: llegada y resultado exitosos antes de depósito. No se desactivó
localización ni anticolisión. Primer check tras liberación rc78 por muestras de
seguridad obsoletas: ninguna orden; segunda lectura rc0, seguida de retorno y verificación HOME.

Raíz de evidencia externa y backups privados:
`../Humanoide-vla-evidence/20261001_SCENARIO1_TABLE90/`.
Incluye base-commit.txt, before/, continuation-before/, after/, hashes, bundle,
install/stdout.json, native-current.json/urdf, current-cad.tar, estudios IK/CAD,
current-baseline-check*, navigation-prepare.txt, installed-check, grasp-trial,
held-check*, held-joints, deposit-trial-check, deposit-trial, deposited-joints,
current-home, released-check*, home-trial, final-check, final-related-tests y
physical-validation.json. Las fuentes locales sin commit se respaldan.
CAD/binarios/credenciales no entran en Git. No se instalaron paquetes PC.

## Recetas y comprobaciones

```bash
./scripts/optimistic_scenario1.sh --plan
python3 -B scripts/box_handling/prepare_scenario1_table90.py --output /ruta/nueva/table90
python3 -B scripts/box_handling/scenario1_table90_install.py --bundle config/box_handling/table90_candidate/bundle.json --install --evidence-dir /ruta/nueva/install
./scripts/optimistic_scenario1.sh --check --evidence-dir /ruta/nueva/check
```

`--stop-after deposit` permite ensayo supervisado acotado y pausa antes de
verify_released/HOME. El ciclo completo está habilitado para el hash exacto del perfil probado; un
perfil modificado no puede heredar esa prueba. PHYSICAL_QUALIFICATION en la fuente
pura enlaza hashes de checkpoints y declaraciones del operador. Todos los
controles de salud/modelo/HOME siguen activos; no hay flag de cualificación.

Receta histórica del retorno realizado; no ejecutar con el checkpoint ya consumido:

```bash
./scripts/optimistic_scenario1.sh --resume ../Humanoide-vla-evidence/20261001_SCENARIO1_TABLE90/deposit-trial/checkpoint.json --box-state released --recovery-confirmed --check --evidence-dir /ruta/nueva/check-released
./scripts/optimistic_scenario1.sh --resume ../Humanoide-vla-evidence/20261001_SCENARIO1_TABLE90/deposit-trial/checkpoint.json --box-state released --recovery-confirmed --evidence-dir /ruta/nueva/home
```

Collector sólo lectura: `collect_scenario1_table90_model.py --mode model|cad|joints|home --output /ruta/nueva`.
Auditores locales: `audit_scenario1_table90_ik.py --urdf <URDF-nativo> --torso-orientation-only --initial-joints <named-state.json> --samples-per-segment 20 --continuity-weight 0.001 --output <nuevo.json>`;
`audit_scenario1_table90_collision.py --urdf <URDF-CAD> --package-root <CAD> --ik-report <informe> --output <nuevo.json>`.
Usan SciPy/NumPy del entorno existente `.venv/general-home`; no publican comandos.

577 pruebas pertinentes correctas, incluidas9 nuevas. Verifican dos cambios Z,
pines/identidad/bootstrap, rechazo de modificaciones fuerza/torso/manifiesto,
instalación aditiva/conflictos y pausa depósito sin liberación/HOME. AST/Bash y
diff check correctos. Suite legacy instalador excluida:17 errores de fixtures ya
reproducidos en git archive del commit base; no se modificó ese instalador legacy.

## Reversión

PC: restaurar selectivamente fuentes previas desde before/ y retirar sólo archivos
nuevos table90; preservar cambios posteriores y locks ajenos. Retirar la rama no
revierte archivos sin commit. Robot: retirar únicamente los dos archivos aditivos
si sus hashes coinciden con rollback_remove_only_if_sha256_matches del recibo;
no reemplazar originales, no reiniciar ni mover como parte del rollback.
No descargar/relocalizar el mapa automáticamente; documentar cambios posteriores.
Una reversión de archivos no cambia la postura ni el estado físico de la caja.
