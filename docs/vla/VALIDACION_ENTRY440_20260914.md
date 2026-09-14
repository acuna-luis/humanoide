# ENTRY440: separación geométrica de acceso y retorno validada offline

2026-09-14, Europe/Madrid. VLA-01. **VERIFICADO para el modelo y las hipótesis
indicados; aprobación de movimiento físico PENDIENTE.** Sin consultas ni cambios
remotos, movimientos, instalación, recarga o nuevas dependencias.

## Resultado nuevo

El par abrazadera derecha–caja que quedaba pendiente en
[la revisión anterior](CIERRE_GEOMETRICO_ENTRY_20260914.md) se resuelve mediante
subdivisión de la caja de error articular. **No se modifica la escena original,
la geometría de las abrazaderas, ±1° ni el margen base de 2 mm.**

| Ruta afín evaluada | Pares certificados | Avisos nominales | Sin demostrar | Tiempo |
|---|---:|---:|---:|---:|
| Inicio archivado → READY → ENTRY440 | 1018 | 54 | 0 | 17,42 s |
| Postura medida tras bajar cabeza → READY → ENTRY440 | 1018 | 54 | 0 | 17,58 s |
| ENTRY440 → READY → postura medida → HOME20D | 1018 | 54 | 0 | 17,03 s |

Los 1018 pares son **90 contra la escena y 928 entre componentes del robot**.
Los 54 avisos nominales permanecen en el resultado; no se han eximido ni
convertido en pares certificados. Ninguna de las tres evaluaciones acaba por
timeout. El comienzo medido procede de `after-joints.json` del ensayo de cabeza
de esta mañana: **es evidencia archivada, no lectura fresca al ejecutar**.
El retorno es vacío y añade explícitamente el tramo final hasta HOME20D.

Una búsqueda numérica independiente con 5973 consultas encontró una separación
de 12,670918 mm en el par derecho–caja al final del tramo. La recomputación
independiente comprueba límites articulares y error ≤1°. **Ese valor no es el
mínimo global garantizado**; la garantía de separación >2 mm proviene de la
partición exhaustiva de cada caja que el certificador acepta, no de la búsqueda.

## Qué cambió en el cálculo

El revisor anterior se detenía para un par cuando no conseguía separar toda la
caja de error de su punto medio. Ahora `entry_subdivided_scene_bounds.py` puede
dividirla en dos mitades, conservando su unión exacta. Cada mitad usa las cotas
direccionales con resto global de segundo orden ya revisadas. Se acepta la
caja madre sólo cuando **todas** las hojas prueban separación; su cota es el
mínimo de las cotas aceptadas. Una hoja sin demostrar, agotamiento del presupuesto
o límite de tiempo devuelve 0, nunca aprobación parcial.

La primera ruta necesitó 1274 consultas de subcajas, con 192 demostraciones de
cajas completas y ninguna partición incompleta. Se subdividen sólo cajas de
semiancho máximo ≤0,020 rad; las más amplias siguen al certificador temporal.
Este umbral distribuye el trabajo numérico y **no cambia el error solicitado**.
Presupuesto: hasta 512 nodos y 5 s por partición; límites mayores disponibles
sólo para cálculo offline, máximo 4096 nodos. Opción explícita
`--uncertainty-partition-nodes 512`, requiere `--directional-bounds`.

`review_entry_fixture_hypotheses.py` incorpora la misma opción y `--padding-mm`.
Para esta revisión usa exclusivamente `--padding-mm 0`: el archivo adaptador
`archived-proxy.json` contiene exactamente los cubos originales y su hash de
origen; se identifica como proxy archivado, **no ajuste visual o calibración**.
El modelo y las entradas se comprueban por hash antes y después.

Tests: 28 pasan para partición, cotas direccionales, revisor, certificador y
refinamiento; otros 2 pasan para las hipótesis de escena. Los cuatro tests nuevos
comprueban cobertura de ambas mitades, rechazo cuando sólo una mitad pasa,
agotamiento del presupuesto y rechazo de entradas/cotas no válidas.

Regresión negativa: con el mismo método ENTRY372 conserva sin demostrar el par
derecho–mesa donde se había recomputado una intersección. La subdivisión no lo
convierte en certificado ni modifica ese contraejemplo.

## Alcance de la validación

Queda resuelto el bloqueo **numérico de separación con mesa/caja para ENTRY440**
bajo esta escena e intervalo. No queda aprobado ENTRY372 ni cualquier otra
postura por extensión. Esta validación no es una tarea instalada en Motion.

La autorización física continúa pendiente de:

1. Correspondencia y error total del registro de escena: la discrepancia entre
   imagen y nube y la cobertura parcial del entorno siguen sin resolver. Usar
   el proxy original evita aceptar el ajuste visual experimental como medición.
2. Las 54 interfaces nominales: hace falta demostrar su representación/contacto
   permitido en esta ruta. No incluyen abrazaderas, pero siguen siendo parte
   del modelo completo y no se eliminan automáticamente por ser interfaces.
3. Trayectoria aplicada, error de seguimiento y parada: ±1° es una hipótesis
   offline, no un límite demostrado para todos los ejes de ENTRY. La prueba
   evalúa interpolación articular afín, no certifica el interpolador Motion.

Por ello todos los informes mantienen `physical_approval=false`. Los tests de
software, las distancias nominales y un operador ante el E-stop no sustituyen
estas comprobaciones. No se conecta ningún publicador VLA ni se marca el
checkpoint o el ensayo físico como validados.

## Reproducción y conservación

Evidencia privada:
`../Humanoide-vla-evidence/20260914T092751Z_ENTRY-UNCERTAINTY-VALIDATION/`.
Incluye informes, comandos JSON, proxy original convertido, búsqueda numérica,
recomputación, backups previos, fuentes finales y manifiesto SHA256. Las fuentes
del dataset y la captura se conservan en las carpetas anteriores por hash.

Ejecutar el mismo comando de revisión anterior, con salida nueva, añadiendo:

```bash
--local-radius-bounds --directional-bounds --uncertainty-partition-nodes 512
```

Comandos completos: `candidate440-command.json`, `access-recovery-command.json`
y `probe-verification-command.json`. Son arrays para `subprocess.run`, no texto
a ejecutar con `eval`. No se requiere instalación en el robot.

Fuentes PC: nuevo `scripts/vla/entry_subdivided_scene_bounds.py` y su test;
ampliación de `review_vla_entry_error_bound.py` y
`review_entry_fixture_hypotheses.py`. Aplicación tras firmware: recuperar fuentes
y evidencia por hash, volver a verificar compatibilidad del modelo y calcular
offline. Reversión: restaurar sólo esos dos revisores desde `before/` y retirar
el módulo/test nuevos y las entradas documentales de esta intervención,
preservando cambios anteriores. Sin rollback remoto, commit o push.
