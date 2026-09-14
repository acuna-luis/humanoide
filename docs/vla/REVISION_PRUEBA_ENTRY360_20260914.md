# ENTRY360: revisión para preparar una prueba física

**Actualización posterior del mismo día:** se completó la prueba continua de
fronteras de once parejas y se preparó una secuencia por etapas de 75 s. Los
resultados siguientes conservan la revisión inicial. Véase la
[actualización y requisitos restantes](ENTRY360_ETAPAS_E_INTERFACES_20260914.md).

2026-09-14, Europe/Madrid. VLA-01. **Geometría offline verificada en su alcance;
prueba física no habilitada.** Petición: comprobar ENTRY360 y validarlo para
ensayo. No se ha ejecutado READY, ENTRY, recuperación ni VLA físico. Tampoco
se ha instalado una tarea, recargado Motion, reiniciado o cambiado protecciones.

## Resultado

`trial-review.json` queda en `NOT_QUALIFIED_FOR_PHYSICAL_TRIAL`. No es una
petición de permiso adicional ni falta de autorización del usuario: hay datos
que la revisión no demuestra. El resultado distingue el ensayo aislado de
postura, con abrazaderas vacías, de usar esa postura como entrada del VLA para
coger la caja de la mesa de 80 cm.

| Comprobación | Resultado |
|---|---|
| Entrada 360 frente al parquet original, task0/frame0 | Vector 20D coincide exactamente |
| Acceso y retorno, escena visual ampliada 50 mm, ±1° y 2 mm | 1018 pares certificados por ruta; 90/90 contra escena |
| Avisos internos | Mismos 54; 30 invariantes y 24 interfaces móviles |
| Nuevo análisis específico de interfaces 360 | 696 muestras; ningún testigo CAD fuera de las cajas de referencia |
| Estado actual de actuadores | 354 muestras, inmóvil, sin fallos/deshabilitados observados |
| Compatibilidad del ejemplo 360 con mesa de 80 cm | No demostrada; altura inferida del ejemplo ≈64 cm |
| Tarea Motion específica de 360, seguimiento y parada | No validados |

Los 50 mm siguen siendo una hipótesis exploratoria de traslación, no una cota
metrológica de toda la escena ni de su error angular. Las superficies ocultas,
dimensiones y correspondencia con el montaje real no quedan certificadas por
los 90 pares del modelo. Los 54 avisos no se excluyen ni se transforman en una
aprobación física por no encontrar un contacto nuevo en las muestras.

## Mesa e imagen original de entrenamiento

Se vuelve a leer la primera fila y el primer fotograma del episodio 360. El
extractor verifica identidad, task0, timestamp0 y coincidencia exacta de sus
primeros veinte valores de estado con el extremo calculado. La imagen fuente
ya verificada se conserva también en la evidencia anterior.

Sobre la imagen 960×576 se anotan los extremos exteriores del borde trasero
de la caja: `[311,318]` y `[638,310]` píxeles. Se conservan las mismas hipótesis
del comparador anterior: caja del dataset de 603 mm de ancho y 217 mm de alto,
suelo 150 mm por debajo de `base_link`, calibración/montaje de cámara archivados.
El resultado es **0,641826 m** de altura del apoyo desde el suelo. Variar cada
coordenada de las marcas ±4 píxeles da **0,622472–0,660257 m**.

Es **inferencia, no medición ni intervalo de error total**. La calibración
archivada y las dimensiones asumidas pueden introducir sesgo; no se ordena
bajar la mesa a 64 cm ni se declara que eso bastaría para habilitar el VLA.
La diferencia respecto a 80 cm exige resolver compatibilidad de observación y
alcance. Esa compatibilidad afecta al agarre VLA; **por sí sola no es un
requisito geométrico de un ensayo aislado de postura vacía**.

La extracción ejecutó además revisiones básicas de la escena original con
presupuesto de 5 s: se conservan sus timeouts como diagnósticos incompletos.
No sustituyen ni invalidan los certificados previos de la escena visual+50 mm,
que son otra consulta y otro método. No se presenta un timeout como colisión.

## Interfaces específicas de 360

Se transforma únicamente el formato del informe de alternativas para reutilizar
el auditor; se conservan exactamente puntos, pares, conteos, geometría y hashes.
La salida identifica ahora genéricamente `ENTRY_ROUTE_INTERFACE_DIAGNOSTIC_NOT_EXEMPTION`:
se corrige un texto que antes decía ENTRY440 aunque el campo `candidate` fuese
360. La primera salida se conserva y se repite con el texto corregido.

En el rectángulo de acceso/retorno+±1°, recortado por límites URDF:

- 30 pares tienen geometría relativa invariante si base y auxiliares permanecen
  fijos; ninguno de los 54 contiene las abrazaderas.
- 24 interfaces móviles: 11 sin intersección de fronteras en las muestras,
  13 con alguna intersección CAD. No se encontraron testigos nuevos fuera de
  las cajas de referencia HOME/PICO; los listados pueden truncarse.
- Esto **no es una demostración continua** de esas 24 interfaces ni de ausencia
  de contención material. Las pruebas de fronteras para ENTRY440 no se
  extrapolan al mayor rango de elevador de ENTRY360.

## Lecturas actuales, sin actuación

Captura pasiva Motion de **10:40:51 a 10:41:02 UTC / 12:40:51 a 12:41:02 local**:
354 mensajes completos de actuadores y dos de cada paro. Paros observados 0/0,
velocidad máxima 0, sin variación de posición durante la captura. Error máximo
consigna solicitada–posición 0,000958738 rad. No hubo transición de paro:
no se midió latencia o recorrido de frenado.

Brazos/cuerpo próximos a HOME (máximo absoluto sin cabeza 0,000958738 rad),
cabeza pitch −0,430665106 rad/yaw +0,000383495 rad. No es HOME20D completo.
Diferencia máxima respecto al inicio archivado de la ruta: **0,001725728 rad**.
La observación no sustituye una lectura y comprobación física inmediatamente
anteriores a un futuro movimiento.

Se recalculan ambas rutas sustituyendo el inicio archivado por ese vector 20D
recién medido y manteniendo después todo el error de ±1°. Acceso y retorno
conservan **1018 certificados, 54 avisos, 0 pendientes y ningún timeout**.
No se consume parte del error para justificar el desplazamiento del inicio.
`current-route-review.json` contiene esos cálculos; se repite también el
diagnóstico de interfaces para el dominio correspondiente al nuevo inicio.

Vision se redescubre y captura de nuevo RGB/nube/CameraInfo/TF mediante el nodo
pasivo existente. Imagen y nube comparten `1789382521092207000 ns`; TF consultado
en ese instante. CameraInfo sigue con marca0. Se revisa la imagen de la caja
apoyada en la mesa; la foto no demuestra por sí sola zona libre ni contorno
completo. Los lectores temporales terminan por su propio límite; no son un
watchdog ni envían cancelación/parada. Ningún contenedor se instala o reinicia.

## Propuesta temporal, todavía offline

READY→360 cambia principalmente cabeza y los tres tramos del elevador. El
segundo tramo cambia **2,155627 rad (≈123,5°)**. El runner E6.1C histórico sigue
apuntando al episodio040 y a otras tareas; **no debe usarse para ejecutar360**.

Se calcula una propuesta cúbica entre reposos, con progreso común supuesto:

```text
q(u) = q0 + (q1−q0) (3u²−2u³), u=t/T
T = 65 s para READY→360
velocidad máxima analítica = 0,0497452 rad/s
aceleración máxima analítica = 0,00306124 rad/s²
```

Los caps de diseño 0,05 rad/s y 0,05 rad/s² son una propuesta lenta, no valores
certificados por UBTECH ni mediciones del robot. La ley tiene saltos de
aceleración al enlazar reposos; no se atribuye cota global finita de jerk. La
emulación numérica previa de la cúbica no valida el despacho real de grupos,
la consigna inicial, el seguimiento o la parada para esta tarea360.

El JSON fija `installable=false`, no incluye transporte de ejecución y no
genera XML instalable. No se atribuyen esos 65 s al flujo completo de VLA.

## Herramientas, evidencia y reproducción

- Nuevos PC: `scripts/vla/prepare_entry360_trial_review.py` y su test.
  Consolidan evidencias por hash, conservan el vector original y calculan la
  propuesta temporal; no conectan al robot ni pueden aprobar/ejecutar una tarea.
- Nuevo `scripts/vla/review_entry_from_passive_state.py`: recompone acceso y
  retorno con el estado capturado, conserva error/modelo y rechaza evidencia
  inconsistente. No contiene transporte de ejecución.
- Cambio de texto en `scripts/vla/audit_entry_route_interfaces.py`; no cambia
  el algoritmo, los sólidos, márgenes o exclusiones.
- **15 tests pasan**, incluidos identidad del primer estado, dominios,
  geometría básica y comprobación de velocidades/aceleraciones de la propuesta.
  Sin instalar paquetes; se usan los entornos Python existentes.
- Evidencia: `../Humanoide-vla-evidence/20260914T104001Z_ENTRY360-QUALIFICATION/`.
  Informe final: `trial-review-current.json`, con `current-route-review.json`
  y `current-interfaces360.json`. Informes del inicio archivado conservados:
  `trial-review.json`, `interfaces360-final.json`,
  `candidate360/selection.json`, `passive-analysis.json` y `scene-capture.json`.
  Imágenes/dataset y captura con binarios codificados quedan fuera de Git.
- `before/` respalda documentos y auditor anteriores; `final-sources/` conserva
  código/documentación finales. `evidence.sha256` y los hashes de cada informe
  fijan fuentes, versiones y resultados. No hubo cambios remotos persistentes.

Desde la raíz, con un directorio de salida nuevo:

```bash
ENTRY360_EVIDENCE="../Humanoide-vla-evidence/20260914T104001Z_ENTRY360-QUALIFICATION"
ENTRY360_OUT="$(mktemp -d /tmp/cruzr-entry360-review.XXXXXXXX)"

.venv/general-home/bin/python scripts/vla/audit_entry_route_interfaces.py \
  --review "$ENTRY360_EVIDENCE/current-route-review.json" \
  --output "$ENTRY360_OUT/interfaces.json" --steps 9

.venv/general-home/bin/python scripts/vla/prepare_entry360_trial_review.py \
  --review "$ENTRY360_EVIDENCE/current-route-review.json" \
  --interfaces "$ENTRY360_OUT/interfaces.json" \
  --selection "$ENTRY360_EVIDENCE/candidate360/selection.json" \
  --trace "$ENTRY360_EVIDENCE/passive-current/trace.jsonl" \
  --trace-analysis "$ENTRY360_EVIDENCE/passive-analysis.json" \
  --output "$ENTRY360_OUT/trial-review.json"

PYTHONPATH=scripts/vla .venv/general-home/bin/python -m unittest \
  test_prepare_entry360_trial_review test_audit_entry_route_interfaces \
  test_prepare_vla_entry_bundle
```

El código0 de estas herramientas significa que completaron la revisión, **no
autorización física**. La salida conserva el estado de no cualificado.

Para repetir la inferencia de altura, `prepare_vla_entry_bundle.py` acepta la
anotación archivada `annotations360.json` junto con las entradas/hashes del
informe `candidate360/selection.json`; `commands.json` conserva los argumentos
exactos. Para repetir lecturas, redescubrir primero conexión/contenedores y
usar los capturadores pasivos versionados con nuevas carpetas de evidencia.

Tras firmware, restaurar selectivamente código/evidencia compatibles. Reversión
PC: retirar sólo los tres archivos nuevos y restaurar el auditor desde su
backup, preservando trabajo ajeno; actualizar estas referencias. No hay
configuración remota que restaurar. Sin commit/push.

Punto de reanudación: cerrar la correspondencia física de escena/interfaces y
el contrato de ejecución/seguimiento/parada para un ensayo limitado360. Para
continuar además con el agarre VLA, resolver la compatibilidad con la mesa e
imagen actuales.
