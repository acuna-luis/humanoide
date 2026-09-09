# PICO a HOME abriendo los brazos antes de bajarlos

2026-09-09 — Implementación local verificada; instalación y ensayo físico pendientes.

El operador informó contacto entre abrazadera y cuerpo durante la tarea anterior
`cruzr/pico_to_home_owner`. Su primer movimiento llevaba simultáneamente los
siete ejes de cada brazo a cero. Al cerrar los hombros durante el descenso,
las abrazaderas se acercaban al cuerpo. El reconocimiento correcto de la postura
PICO no validaba ese recorrido. La tarea antigua queda retirada del ejecutor.

La revisión `cruzr/pico_to_home_open_v2` utiliza cuatro etapas:

| Etapa | Acción | Duración nominal |
|---|---|---:|
| Abrir | Ambos hombros roll a −0,60 rad (unos 34,4° de apertura en el modelo S2); conserva la configuración PICO del resto del brazo | 10 s |
| Bajar abiertos | Lleva a cero los demás ejes de brazo y mantiene ambos hombros roll en −0,60 rad | 40 s |
| Recoger cuerpo | Cabeza, elevador y cintura a cero con los brazos todavía abiertos | 15 s |
| Cerrar al final | Hombros roll a cero, con los brazos ya bajados y el cuerpo en HOME | 15 s |

Los 80 segundos corresponden a los movimientos programados; preflights y
verificaciones añaden tiempo. Se conserva la primitiva MetaMove y las
protecciones del controlador. No se han cambiado parámetros del fabricante.

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
- Doce pruebas comprueban las referencias, orden de etapas, persistencia de
  apertura, correspondencia entre orden articular y XML, rechazo del XML antiguo,
  duración de espera suficiente y conservación del diagnóstico cuando falla ROS.
- Las duraciones limitan el máximo analítico a menos de 0,08 rad/s **si** el
  interpolador fuera quintic. No es una velocidad medida ni una garantía sobre
  el interpolador real.
- Barrido offline de ambas referencias, 501 muestras por etapa, con el URDF y
  las envolventes archivados: mínimo muestreado de 69,79 mm fuera de los pares
  locales de unión de cada muñeca. Descontando una cota global de movimiento
  entre muestras, la menor reserva condicional es 7,95 mm. El informe conserva
  todos los pares locales; no se han creado exenciones de colisión.
- La cota anterior presupone una interpolación común y monótona entre los
  objetivos. No cubre desviaciones articulares simultáneas, frenado, escena ni
  discrepancias del montaje real. El contacto previo impide tratar este análisis
  como aprobación física. No se ha ejecutado movimiento con esta revisión.

El generador `scripts/teleoperation/cruzr_pico_home_open_path.py` describe los
objetivos. `audit_pico_home_open_path.py` reproduce el barrido sin ROS ni red:

```bash
./scripts/teleoperation/cruzr_pico_to_home_owner.sh --check
python3 scripts/teleoperation/audit_pico_home_open_path.py \
  --snapshot-dir ../Humanoide-vla-evidence/20260908T115359.543954Z_PICO-HOME-CHECK \
  --samples 501 --output /tmp/pico-home-open-audit.json
```

El archivo de salida debe ser nuevo. Los datos de evidencia permanecen fuera
de Git. Véase la entrada de esta revisión en PROJECT_SOURCE_OF_TRUTH.md para
el directorio de resultados y las copias previas a la modificación.

## Puesta en servicio pendiente

Después de resolver el contacto y comprobar físicamente el montaje, con robot
estable y E-stop accionado, `--install` y `--reload` preparan **esta revisión**.
Ambos mantienen sus comprobaciones y confirmación local. No deben ejecutarse
durante un apagado ni con alimentación parcial. El reinicio supervisado posterior
al E-stop debe seguir la guía de arranque de esta unidad.

Con el sistema recuperado y la escena comprobada, `--preflight` sólo lee.
`--run` solicita la confirmación humana existente, vuelve a medir la postura
después de la confirmación y ejecuta una sola vez. Una interrupción no se reanuda
desde un punto intermedio: detiene el flujo y exige revisar el estado real.
No se publica HOME directo ni se intenta hacer simétricos los brazos al fallar.

La zona a comprobar incluye **toda la apertura lateral**, además del descenso.
Las abrazaderas deben estar vacías; no usar esta ruta para soltar una caja ni
para salir de una postura posterior a contacto. El ensayo físico y la revisión
del barrido real siguen pendientes.

## Reversión

Las copias anteriores sirven para auditar el incidente, no para volver a
habilitar el recorrido que produjo contacto. Si se retira esta revisión,
mantener suspendida la recuperación automática. La instalación nueva conserva
el backup de task_list para retirar únicamente su entrada y su XML con el
robot detenido y sin sobrescribir otros cambios.
