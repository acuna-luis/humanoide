# PICO a HOME abriendo los brazos antes de bajarlos

**10-09-2026 — HOME ya alcanzado:** tras el preflight, el ejecutor comprueba
JointState y actuadores nuevos. Si todos los ejes están dentro de0,005rad de HOME,
inmóviles y sanos, termina `ALREADY_HOME_MEASURED`, sin consultar ni enviar una
trayectoria. Una captura inválida aborta; fuera de HOME se conserva el gate PICO.
Las22pruebas del ejecutor pasan. La [apertura adaptativa](CRUZR_HOME_ADAPTATIVO.md)
está implementada sólo en el planificador; **no cambia todavía estos perfiles20s**.

**Actualización del HOME interno:** `cruzr/home` dispone ahora de una
[definición distinta con apertura relativa de 20 s](CRUZR_HOME_INTERNO_APERTURA.md),
instalada bajo paro y aún sin ensayo físico. Los perfiles PICO descritos aquí
conservan sus XML y tiempos; no confundir su validación con la del HOME interno.

2026-09-10 — **OBSERVADO por el operador:** la ruta open_v2 original funciona
bien, pero resulta lenta. A petición del propietario se añaden perfiles 3× y 4×;
**4× es ahora el valor predeterminado del ejecutor**. Cambio local verificado;
Perfil 4× instalado por el operador, con hash verificado posteriormente;
ensayo físico 4× pendiente. El intento posterior lanzó el HOME interno desde
un cambio de modo, mientras el script fallaba en preflight: véase el
[incidente del 10-09](../incidents/2026-09-10_HOME_INTERNO_TRAS_RELOAD_4X.md).
La instalación/carga de 3× no se ha comprobado.
Este cambio no ha conectado al robot ni enviado movimiento. La comunicación
del operador no determina la postura, paros ni disponibilidad actuales.

En la recuperación anterior se verificaron el XML original instalado y una
interrupción de Motion tras E-stop. La recarga aislada no restablece Motion
después del paro. Se corrigieron sus
mensajes y la propagación de errores del preflight. Una fecha de proceso
posterior al task_list sólo prueba el orden de arranque, no que exista servidor
de acciones: ahora se muestran `TASK_PROCESS_ORDER` y `RUNTIME_STATE` separados.
La versión anterior podía imprimir `RUNTIME_STATE=loaded` con cero servidores.
Esas comprobaciones se mantienen en las veinte pruebas locales actuales.

El operador informó contacto entre abrazadera y cuerpo durante la tarea anterior
`cruzr/pico_to_home_owner`. Su primer movimiento llevaba simultáneamente los
siete ejes de cada brazo a cero. Al cerrar los hombros durante el descenso,
las abrazaderas se acercaban al cuerpo. El reconocimiento correcto de la postura
PICO no validaba ese recorrido. La tarea antigua queda retirada del ejecutor.

Los tres perfiles utilizan los mismos objetivos y cuatro etapas:

| Etapa | Acción | 1× | 3× | 4× (predeterminado) |
|---|---|---:|---:|---:|
| Abrir | Ambos hombros roll a −0,60 rad (unos 34,4° de apertura en el modelo S2); conserva la configuración PICO del resto del brazo | 10 s | 3,333 s | 2,5 s |
| Bajar abiertos | Lleva a cero los demás ejes de brazo y mantiene ambos hombros roll en −0,60 rad | 40 s | 13,333 s | 10 s |
| Recoger cuerpo | Cabeza, elevador y cintura a cero con los brazos todavía abiertos | 15 s | 5 s | 3,75 s |
| Cerrar al final | Hombros roll a cero, con los brazos ya bajados y el cuerpo en HOME | 15 s | 5 s | 3,75 s |
| **Total de movimiento** | | **80 s** | **26,666 s** | **20 s** |

Estos tiempos corresponden a los movimientos programados; preflights y
verificaciones añaden tiempo. Se conserva la primitiva MetaMove y las
protecciones del controlador; sólo cambian duraciones y nombre de cada perfil.
`TimeRatio` sigue en 1,0 y la espera máxima de la acción sigue en 120 s.
No se han cambiado límites del fabricante.

| Opción | Tarea remota exigida | XML local en scripts/teleoperation/tasks/ |
|---|---|---|
| `--speed 1` | `cruzr/pico_to_home_open_v2` | `cruzr_pico_to_home_owner.xml` |
| `--speed 3` | `cruzr/pico_to_home_open_v2_3x` | `cruzr_pico_to_home_open_v2_3x.xml` |
| `--speed 4` u omitido | `cruzr/pico_to_home_open_v2_4x` | `cruzr_pico_to_home_open_v2_4x.xml` |

El perfil elegido se aplica también a `--check`, `--install`, `--reload` y
`--preflight`. Sin argumentos sólo comprueba localmente el perfil 4×.
Si falta el perfil seleccionado en el robot, se detiene antes de mover; no
sustituye el perfil por otro instalado. La confirmación de ejecución identifica
explícitamente `VELOCIDAD=3X` o `VELOCIDAD=4X` y la evidencia guarda el perfil/hash.

El mismo comando local sigue siendo `cruzr_pico_to_home_owner.sh`, pero sus
identificadores remotos, hash y validación XML exigen la revisión nueva. Si sólo
está instalada la tarea anterior, se bloquea antes de enviar una acción. La
instalación nueva añade una entrada y un XML independientes, con backup del
task_list; no sobrescribe silenciosamente la tarea anterior. No debe llamarse
manualmente a la tarea retirada.

## Comprobaciones realizadas

- Las dos referencias admitidas siguen siendo PICO corporal flexionado y PICO
  con cuerpo a cero. Todos los ejes deben cumplir 0,02 rad; velocidad máxima
  0,01 rad/s. No se admiten otras posturas ni mezclas de referencias.
- Veinte pruebas comprueban las referencias, orden de etapas, persistencia de
  apertura, correspondencia entre orden articular y XML, rechazo del XML antiguo,
  duración de espera suficiente y conservación del diagnóstico cuando falla ROS.
  Incluyen selección real del parser Bash en todos los modos y órdenes de
  argumentos, valor 4 por defecto, rechazo de valores inválidos e igualdad exacta
  de los XML al excluir sólo duraciones/nombre. `bash -n` pasa; ShellCheck no está instalado.
- **INFERENCIA condicionada:** con interpolación quintic común, los máximos
  analíticos serían 0,0752 / 0,2256 / 0,3008 rad/s para 1× / 3× / 4×. No son
  velocidades medidas ni una garantía sobre el interpolador real. El URDF
  archivado contiene límites de velocidad cero para elevador; no sirve para
  certificar su dinámica. El informe conserva esa incertidumbre. No se modifica
  ningún límite del controlador.
- Barrido offline de ambas referencias, 501 muestras por etapa, con el URDF y
  las envolventes archivados: mínimo muestreado de 69,79 mm fuera de los pares
  locales de unión de cada muñeca. Descontando una cota global de movimiento
  entre muestras, la menor reserva condicional es 7,95 mm. El informe conserva
  todos los pares locales; no se han creado exenciones de colisión.
- La cota anterior presupone una interpolación común y monótona entre los
  objetivos. No cubre desviaciones articulares simultáneas, frenado, escena ni
  discrepancias del montaje real. El contacto previo impide tratar este análisis
  como aprobación física. El operador comunica éxito de la ruta original;
  los perfiles rápidos no han sido ensayados. Conservar objetivos no verifica
  seguimiento ni distancia de parada a mayor velocidad.

El generador `scripts/teleoperation/cruzr_pico_home_open_path.py` describe los
objetivos. `audit_pico_home_open_path.py` reproduce el barrido sin ROS ni red:

```bash
./scripts/teleoperation/cruzr_pico_to_home_owner.sh --check
python3 scripts/teleoperation/audit_pico_home_open_path.py \
  --snapshot-dir ../Humanoide-vla-evidence/20260908T115359.543954Z_PICO-HOME-CHECK \
  --samples 501 --output /tmp/pico-home-open-audit.json
```

El archivo de salida debe ser nuevo. Los datos de evidencia permanecen fuera
de Git. Evidencia y copias antes/después del cambio de velocidad:
`../Humanoide-vla-evidence/20260910T091420Z_PICO-HOME-SPEED/`, incluido
`timing-review.json`. Los hashes completos están en el manifiesto y el ejecutor.
El XML original conserva SHA256 `6b8309f3c29025baf4d7116888c4f64a4f3a86f0cd74e226642203c194dd6999`.

## Puesta en servicio

Después de resolver el contacto y comprobar físicamente el montaje, con robot
estable, **brazos abajo/vacíos antes de pasar a PICO** y E-stop accionado,
`--install --speed 4` prepara el perfil predeterminado nuevo y
`--reload --speed 4` comprueba/prepara su carga. Los perfiles se instalan por
separado; para 3× se usa `--speed 3` en ambos pasos. Instalar 4× conserva 1×.
Ambos mantienen sus comprobaciones y confirmación local. No deben ejecutarse
durante un apagado ni con alimentación parcial. El reinicio supervisado posterior
al E-stop debe seguir la [guía de arranque de esta unidad](../guides/CRUZR_V020_BOOT_GUARD.md).

**No basta con liberar el E-stop después de `--reload`.** El paro puede detener
el proceso hw; manipulación espera entonces ListControllers y no ofrece acciones.
La recarga no inicia hw, no llama StartMotion y no confirma postura ni HOME.
El mensaje antiguo que indicaba liberar y pasar directamente a preflight se
retiró el 10-09. Si la instalación y el orden del proceso ya están verificados,
repetir `--install` o `--reload` no soluciona este estado.

Si los brazos ya están elevados en PICO, detenerse en diagnóstico y preparar
la recuperación física antes de reiniciar: el HOME interno del arranque no
es la ruta open_v2. No forzar los brazos ni improvisar liberación de frenos.
La espera de Motion instalada en Control Center corrige una carrera de arranque;
no inhibe su HOME interno ni recupera automáticamente el robot después de un paro.

Con el perfil 4× instalado/cargado, el sistema recuperado y la escena comprobada:

```bash
./scripts/teleoperation/cruzr_pico_to_home_owner.sh --preflight
./scripts/teleoperation/cruzr_pico_to_home_owner.sh --run
```

Ambos seleccionan 4×. Para volver al perfil original instalado se añade
`--speed 1` a cada comando; no requiere reemplazarlo por el XML rápido.
`--preflight` sólo lee.
`--run` solicita la confirmación humana existente, vuelve a medir la postura
después de la confirmación y ejecuta una sola vez. Una interrupción no se reanuda
desde un punto intermedio: detiene el flujo y exige revisar el estado real.
No se publica HOME directo ni se intenta hacer simétricos los brazos al fallar.

El wrapper conserva explícitamente el código no cero del auditor y rechaza
cualquier marcador requerido ausente o incorrecto, incluso dentro de una
sustitución de comandos Bash. Se corrigió que el `printf` final pudiera ocultar
fallos del auditor o de `grep`. El flujo sale antes de consultar/ejecutar la ruta;
no se han relajado los límites ni cambiado el XML remoto durante esta corrección.

La zona a comprobar incluye **toda la apertura lateral**, además del descenso.
Las abrazaderas deben estar vacías; no usar esta ruta para soltar una caja ni
para salir de una postura posterior a contacto. El ensayo físico y la revisión
del barrido real a mayor velocidad siguen pendientes.

## Reversión

La reversión del cambio de velocidad es seleccionar `--speed 1`: utiliza la
ruta open_v2 de cuatro etapas que el operador ya probó. No recupera la tarea
directa retirada. Cada instalación respalda task_list y permite retirar sólo
la entrada/XML de su perfil con el robot detenido, preservando las otras tareas.

Las copias anteriores al cambio de geometría sirven para auditar el incidente, no para volver a
habilitar el recorrido que produjo contacto. Si se retira esta revisión,
mantener suspendida la recuperación automática. La instalación nueva conserva
el backup de task_list para retirar únicamente su entrada y su XML con el
robot detenido y sin sobrescribir otros cambios.
