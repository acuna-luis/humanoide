# Reutilizar cálculos de trayectorias con abrazaderas

2026-09-14, Europe/Madrid. Fichas ANL-01 / VLA-01. Esta guía distingue
**métodos reutilizables, resultados reutilizables bajo condiciones y aprobación
física**. Reutilizar un cálculo no concede una aprobación nueva de movimiento.

## Qué hemos obtenido y dónde sirve

| Activo | Uso en otro escenario | Condición de reutilización |
|---|---|---|
| Modelo cinemático 20D y geometría de abrazaderas | HOME, READY, ENTRY y análisis de otras posturas | Mismos modelos, montaje, unidades, marcos y correspondencia articular; comparar hashes y estado real del efector |
| Cotas de desplazamiento por cadena relativa, dirección e intervalos | Comprobar otros recorridos sin depender sólo de muestras | Ejecutar el método con el nuevo recorrido, error y geometría; no copiar el resultado anterior |
| Cotas cilíndricas de triángulos alrededor de una articulación | Acelerar comprobaciones cerca de ejes y uniones | Transformación al eje correcta y dominio angular cubierto; prueban superficies CAD, no material físico ni autorización de solapamientos |
| Pruebas continuas de separación interna | Evitar repetir pruebas al cambiar sólo mesa/caja | Misma geometría y el nuevo dominio articular, incluido error, contenido en el dominio probado |
| Pares con geometría relativa invariante | No recalcular por cada posición del robot en la sala | Ningún eje relativo cambia; mantener hipótesis de ejes auxiliares y montaje. Invariancia no equivale a separación |
| Generador de etapas y retorno inverso | Preparar ensayos de posturas vacías | Revisar nuevos extremos, cada estado intermedio, límites, escena y contrato de ejecución; los wrappers actuales sólo aceptan ENTRY360/410 |
| Análisis de función cúbica y límites configurados | Calcular tiempos propuestos para otras amplitudes | Mismo contrato/binario aplicable; comprobar versión, hashes y configuración. No demuestra seguimiento o parada |
| Ajuste visual, nube y anclaje de distancia | Actualizar posición de mesa/caja sin medir manualmente todos sus ejes | Captura pertinente y consistente, dimensiones conocidas, asociación correcta y error acotado para el uso previsto |
| Captura y análisis pasivos | Verificar inmovilidad, errores observados y diferencias de postura | Obtener una lectura nueva; las lecturas anteriores son evidencia histórica |

**Reutilización ya demostrada:** de ENTRY360 a ENTRY410 se conservaron nueve
pruebas internas mediante inclusión exacta del dominio; dos necesitaron nuevo
cálculo. No se extrapoló por parecido visual de las posturas. Ver
[revisión ENTRY410](REVISION_ENTRY410_MESA725_20260914.md) y
[pruebas de ENTRY360](ENTRY360_ETAPAS_E_INTERFACES_20260914.md).

## Qué cambia según el escenario

| Cambio | Qué conservar | Qué actualizar o comprobar |
|---|---|---|
| Robot más cerca/lejos de la misma mesa | Geometría interna y pruebas cuyos dominios sigan cubiertos | Mesa/caja en el marco del robot y todos los pares contra escena; lectura de postura |
| Mesa girada, desplazada o con otra altura | Modelo del robot y métodos | Pose y dimensiones de escena, incertidumbre angular/espacial y recorridos contra escena |
| Caja en otro lugar del mismo tablero | Modelo de mesa si se mantiene válido | Pose de caja, acceso, agarre y posibles oclusiones; no trasladar automáticamente la mesa |
| Otra postura inicial tras teleoperación | Modelo y biblioteca de pruebas | Estado 20D medido, recorrido y dominio; un resultado PICO→HOME no cubre cualquier postura |
| Misma ruta, velocidad diferente | Geometría nominal si el camino es idéntico | Error de seguimiento, dinámica, temporización y parada; si aumenta el error, revisar también geometría |
| Caja sujeta o carga distinta | Herramientas de cálculo | Geometría de carga, agarre, masas/dinámica y escena; el retorno vacío no es un retorno cargado |
| Cambio de abrazaderas, montaje o firmware | Herramientas compatibles y evidencia histórica | Modelos/registro, versiones, hashes, grupos y límites; reaplicar sólo adaptaciones compatibles |

Trasladar o girar conjuntamente todo un modelo mediante una transformación
rígida conserva sus distancias internas. Mover sólo el robot respecto de la
mesa **no** conserva las distancias robot–mesa. Del mismo modo, una transformación
común cámara–robot no elimina el desacuerdo entre el ajuste RGB y la nube.

## Ejemplo real: por qué la escena se recalcula

Con mesa de 725 mm de altura y separación declarada de **160 mm desde la punta
del chasis**, la escena anclada produjo un contraejemplo entre abrazadera derecha
y tablero expandido bajo ±1° y 50 mm por cara. Al confirmar aproximadamente
**220 mm**, acceso y retorno pasaron los 90 pares robot–escena de ese modelo.

**220 mm no es una distancia universal**, ni el mínimo seguro calculado, ni una
banda de tolerancia demostrada. Depende de esta postura, caja, mesa, giros,
montaje y modelo de incertidumbre. Las hipótesis ±1°, 50 mm y margen2 mm tampoco
son especificaciones del fabricante o valores universales. Sus perfiles
mantienen la incertidumbre física total sin calificar.

## Reutilizar pruebas internas sin perder trazabilidad

1. Conservar el informe fuente, sus modelos y hashes; no sobrescribirlo.
2. Construir el nuevo dominio con extremos, tramos intermedios y error articular.
3. Comparar modelo, nombres y orden de articulaciones. La inclusión de límites
   debe ser exacta; no redondear para hacer entrar un dominio nuevo.
4. Reutilizar únicamente las pruebas que cubran el dominio nuevo. Calcular de
   nuevo las demás. Conservar siempre los pares de abrazaderas y entorno.
5. Mantener separado el resultado matemático de las exclusiones solicitadas y
   de la validación física. Registrar procedencia, alcance y resultado.

El comprobador existente implementa este flujo para informes compatibles:

```bash
.venv/general-home/bin/python scripts/vla/reuse_entry_boundary_proofs.py \
  --source-interfaces /ruta/interfaces-origen.json \
  --target-interfaces /ruta/interfaces-nuevas.json \
  --proof /ruta/pruebas-fronteras-origen.json \
  --orbit-proof /ruta/prueba-orbitas-origen.json \
  --output /ruta/reutilizacion-nueva.json
```

`--proof` admite varios archivos. Para las pruebas que no cubran el dominio:

```bash
.venv/general-home/bin/python scripts/vla/prove_entry_interface_boundaries.py \
  --interfaces /ruta/interfaces-nuevas.json \
  --only-pending-from /ruta/reutilizacion-nueva.json \
  --relative-chain --distance-only --seconds-per-pair 10 \
  --output /ruta/pruebas-nuevas.json
```

Un presupuesto agotado queda pendiente; no significa colisión ni aprobación.
Estas herramientas no son un ejecutor ni una caché general automática de todas
las trayectorias. Las pruebas de superficies no acreditan separación de sólidos
anidados ni tolerancias mecánicas del montaje.

La lista del propietario en
[`entry410_owner_interface_exclusions.json`](../../config/vla/offline/entry410_owner_interface_exclusions.json)
contiene 13 pares concretos y los hashes del modelo. Es una decisión documentada
para la revisión offline de ENTRY, no un certificado de falsos positivos ni
una modificación de las protecciones de Motion. No convertirla en una lista
global de exclusiones para cualquier efector o trayectoria.

## Actualizar la escena con cámaras

No se necesita medir manualmente cada eje en cada ciclo si una percepción
validada proporciona la pose y una incertidumbre adecuada. El procedimiento
reutilizable es conservar las dimensiones de objetos identificados, adquirir
RGB/nube/TF pertinentes y actualizar su pose. Si cambia sólo la pose del robot,
transformar la escena requiere localización válida o una observación nueva.

Las herramientas actuales son una base offline, con anotaciones de esquinas;
**todavía no constituyen un registro automático validado**. Se usan:

- `capture_entry_scene_readonly.py`: captura pasiva; no ordena movimiento.
- `fit_entry_fixture_pose.py`: ajuste con dimensiones y esquinas declaradas.
- `diagnose_entry_plane_disagreement.py`: compara regiones; evita confundir
  extrapolación de un plano con corrección demostrada de calibración.
- `anchor_entry_scene_to_chassis_gap.py`: anclaje longitudinal parcial a una
  distancia desde la punta del chasis; conserva los giros estimados.
- `review_entry_fixture_hypotheses.py`: vuelve a comprobar acceso y retorno.

El anclaje actual supone distancia en +X hasta el borde frontal proyectado en
y=0, malla base con origen cero y escala unitaria, y correspondencia de la punta
real con esa malla. Trasladar juntos mesa y caja sólo corresponde cuando se
conserva su pose relativa, como se supuso al retirar el robot. No usar esta
operación si sólo se mueve la caja. No desplazar una calibración global para
forzar que una escena particular encaje.

Las recetas completas y las limitaciones observadas están en la
[revisión de escena y distancia](REVISION_ENTRY410_MESA725_20260914.md).

## Tiempos y ejecución: resultados distintos

Para la función cúbica revisada `q=q0+(q1−q0)(3u²−2u³)`, con reposo en extremos:
`v_pico=1,5·|Δq|/T` y `a_pico=6·|Δq|/T²`. Estas fórmulas permiten proponer tiempos
para otras amplitudes. No establecen un límite global finito de jerk al enlazar
reposos, ni prueban orden de grupos, seguimiento o distancia de parada reales.
La evidencia del binario y sus límites figura en
[geometría y Motion](../teleoperation/CRUZR_HOME_GEOMETRIA_Y_MOTION.md).

Los 75 s de ENTRY410 son una propuesta concreta READY→ENTRY por cinco grupos,
sin HOME→READY ni esperas de comprobación. No reutilizarlos como duración de
un agarre, un retorno general o el flujo VLA completo. El retorno inverso sólo
es candidato equivalente geométricamente si comienza en el extremo esperado,
permanece vacío y la escena no ha cambiado; tras interrupción se necesita el
estado medido y una recuperación específica.

## Conservar después de una actualización

Guardar fuera del robot los modelos originales, informes, entradas, fuentes
locales pendientes de commit y manifiestos SHA256. Las evidencias de esta serie
están en `../Humanoide-vla-evidence/20260914T*/`, referenciadas de forma exacta en
los informes enlazados; no bastan los enlaces sin copiar sus archivos privados.
Conservar perfiles offline y recetas versionadas, sin secretos ni paquetes
grandes en Git. Comparar las versiones nuevas antes de reutilizar resultados;
no restaurar una configuración antigua completa ni estados transitorios.
Seguir [reaplicación tras actualización](../guides/CRUZR_REAPLICAR_CAMBIOS_TRAS_ACTUALIZACION.md).

Esta intervención es documental: no añade instalador/ejecutor, no altera
geometría o tolerancias y no mueve el robot. La autorización solicitada para el
ensayo físico sigue siendo una tarea distinta y no queda validada por esta guía.
