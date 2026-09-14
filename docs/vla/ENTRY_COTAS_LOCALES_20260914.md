# ENTRY: cotas locales, alternativas y estado de aprobación

Fecha: 2026-09-14, Europe/Madrid. Ficha: VLA-01. Estado: **VERIFICADO en
análisis del modelo; aprobación física PENDIENTE**. No se envió movimiento,
no se instaló nada en Motion/Vision ni se arrancó el VLA. Los cambios son
herramientas Python del PC; no alteran el ejecutor, SDK, geometría runtime,
protecciones ni el escenario angular predeterminado de 5°.

## Resultado vigente

Se conserva el escenario explícito ±1° por articulación y el margen de 2 mm,
sin eximir ninguno de los 1072 pares. ±1° sigue siendo una hipótesis offline:
las trazas no cubren todos los ejes de ENTRY ni demuestran consigna aplicada
ni desplazamiento durante parada.

| Revisión HOME → READY → ENTRY372 | Certificados del modelo afín | Avisos nominales | Sin resolver | Tiempo |
|---|---:|---:|---:|---:|
| Radios globales y sólidos afinados, revisión anterior | 997 | 54 | 21 | 54,807 s |
| Radios locales y consultas selectivas | 1016 | 54 | 2 | 8,840 s |
| Además, cajas de cinemática por intervalos | 1016 | 54 | 2 | 11,527 s |

Los dos pendientes son `L_hand_link#0` y `R_hand_link#0` frente a
`scene:tabletop_inferred`. No son contactos observados. Los 54 avisos
nominales conservan sus identidades y no se borran por estar también en HOME.
La separación geométrica afín no demuestra el interpolador real de Motion.

ENTRY430 se contrastó con el frame 0 del parquet y RGB originales, sin mezclar
articulaciones de episodios. La revisión completa vía READY con ±1° deja
1010/54/8 en 4,916 s: empeora el resultado y no sustituye ENTRY372. Su preparación
nominal con presupuesto de 15 s agotó el tiempo; esos resultados parciales
quedan archivados como tales. Las rutas alternativas `body_first` y `direct`
mostraron avisos adicionales y tampoco se aprueban.

Se revisaron también los extremos de las **69 entradas erguidas originales**
preseleccionadas por el censo nominal. Ninguna resuelve todos los pares a ±1°:
13 dejan un pendiente, 35 dejan dos, una deja tres y 20 dejan ocho. Todas
conservan los 54 avisos nominales y ninguna agotó su presupuesto. Es un censo
de extremos con error, no de las 69 rutas completas ni una validación VLA.

Una búsqueda numérica reproducible dentro de ±1° en ENTRY372 encontró distancia
del modelo de **2,107371 mm entre abrazadera derecha y tablero**, frente al
margen exigido de 2 mm; izquierda: 32,527420 mm. En ENTRY440 encontró
12,670921 mm entre abrazadera derecha y caja. Se guardan las 20 articulaciones
exactas de cada ejemplo. La búsqueda no es una minimización global demostrada,
no certifica holgura y no demuestra contacto físico. La diferencia de sólo
0,107371 mm respecto al margen en el ejemplo derecho no justifica ejecutar
contra una escena inferida cuya incertidumbre total está pendiente.

## Qué cambió en el cálculo

`entry_local_displacement_bounds.py` añade una cota de rotación finita en cada
centro de intervalo. Para un semiancho angular h y radio perpendicular r,
el desplazamiento se acota por `2*r*sin(min(h, pi)/2)`. Se suman las
contribuciones exclusivas de las dos ramas de la cadena; los ancestros
comunes aplican una misma transformación rígida y cancelan en la distancia.

Justificación: se descompone el cambio de articulaciones desde las proximales
a las distales. Cuando cambia una articulación, las descendientes todavía
conservan sus valores nominales; los cambios de ancestros han movido rígidamente
su eje y el sólido juntos. Por ello el radio perpendicular nominal acota ese
paso completo. La suma triangular acota perturbaciones simultáneas finitas;
no es una linealización de Jacobiano ni una conclusión basada en muestreo.
Los vértices de las cajas locales contienen los sólidos e incluyen su error
geométrico. Una cota local que exceda la global independiente provoca rechazo.

El semiancho usado en cada tramo incluye **error más recorrido hasta el extremo
del intervalo**, no sólo el error. El margen por par mostrado en el informe es
el máximo de los centros evaluados; se etiqueta como tal y no como constante
global. Cada certificado usa la cota correspondiente al intervalo completo.

Las consultas selectivas conservan exactamente el algoritmo de distancia de
`RobotGeometry`: AABB lejana o sólido próximo. Sólo calculan pares pendientes;
los pares con testigo o sin resolución siguen registrados como no certificados.
El afinado de superficies se aplica sólo a los índices solicitados, manteniendo
las comprobaciones de coherencia entre cotas. Esto elimina gran parte del coste
sin eliminar pares del informe.

`entry_interval_boxes.py` propaga intervalos de ángulos mediante Rodrigues y FK,
con redondeo hacia fuera y extremos trigonométricos. Una coordenada que separa
las cajas barridas del sólido y la escena puede demostrar separación en todo
el intervalo. No resuelve por sí sola los dos casos restantes. Los límites
numéricos, URDF y sólidos siguen siendo los del modelo local, no una certificación
industrial del sistema físico.

## Lecturas remotas y confirmación física

Consultas acotadas de sólo lectura a Motion y Vision, después de comprobar
Docker activo para evitar activación por socket. Contenedores redescubiertos;
Motion y ROS activos. Ambos contenedores VLA detenidos. Se consultaron estados,
locks, extremos ROS y una captura pasiva RGB/nube, sin servicios de movimiento.

- HOME medido: máximo absoluto 0,002780340178 rad; velocidades cero.
- Sin faults de actuador; máxima discrepancia consigna–posición del mismo orden.
- Baterías 90,4000015 % y 90,5 %; ambos paros liberados; cargador desconectado.
- RobotCommand: cero writers, dos readers; action server de manipulación presente.
  La presencia de un cliente de acciones no demuestra actividad ni inactividad;
  no se capturó en esta ronda el estado de una acción concreta.
- Locks libres. `walker_mode=false` se conserva como dato bruto, sin atribuirle
  semántica no comprobada. Netdata de Vision figuraba unhealthy; no se intervino.
- Cámara BGR8 960×576, intrínsecos coincidentes con los anteriores; la caja sigue
  parcialmente recortada por abajo en la imagen. Nube pasiva con 376 muestras.
  No demuestra los límites completos actuales de mesa/caja ni sus incertidumbres.

El usuario declara HOME, paro liberado, abrazaderas vacías, cargador desconectado,
ningún mando, persona disponible y mesa de 80 cm delante con caja apoyada. Su
respuesta no explicita ruedas bloqueadas ni todo el volumen barrido libre.
No se convierten esas omisiones en confirmaciones. Tampoco se reutiliza esa
confirmación indefinidamente después de cambiar escena o modo.

## Verificación y reproducción

25 pruebas unitarias pasan: 11 del certificador, cinco de afinado, cinco de
cotas locales y cuatro de intervalos. Regresión adicional sobre geometría real:
3216 distancias completas y 291 consultas de subconjuntos coinciden con el
algoritmo original a 1e-12 m en HOME/372/440; 60 perturbaciones de 20 articulaciones
quedan contenidas por los intervalos de todos los vértices de las cajas de los
sólidos del robot. Son regresiones, no sustitutos de la justificación analítica.

Dependencias: `.venv/general-home` ya existente; no se instalaron paquetes.
El contraste de parquet/RGB usa `.venv/vla-scene` y las dependencias ya disponibles.

```bash
VLA_EVIDENCE_ROOT=/home/lacuna/proyectos/Robots/Humanoide-vla-evidence
.venv/general-home/bin/python scripts/vla/review_vla_entry_error_bound.py \
  --access-review "$VLA_EVIDENCE_ROOT/20260914T055526Z_VLA-ENTRY80-OFFLINE/review-filtered/access-review.json" \
  --selection "$VLA_EVIDENCE_ROOT/20260914T055526Z_VLA-ENTRY80-OFFLINE/review-filtered/selection.json" \
  --obstacles "$VLA_EVIDENCE_ROOT/20260911T114330Z_VLA-ENTRY-SCENE/recentered/obstacles.json" \
  --error-degrees 1 --subdivision-depth 10 --budget-seconds 90 \
  --local-radius-bounds \
  --refine-unresolved-from "$VLA_EVIDENCE_ROOT/20260914T065216Z_TRACKING-SENSITIVITY/scenario-1.json" \
  --output /tmp/entry-local-review-new.json

.venv/general-home/bin/python scripts/vla/screen_entry_uncertainty.py \
  --survey "$VLA_EVIDENCE_ROOT/20260914T055526Z_VLA-ENTRY80-OFFLINE/endpoint-survey.json" \
  --obstacles "$VLA_EVIDENCE_ROOT/20260911T114330Z_VLA-ENTRY-SCENE/recentered/obstacles.json" \
  --error-degrees 1 --output /tmp/entry-upright-error1-new.json
```

Las salidas deben ser nuevas. El censo comprueba hashes del estudio previo,
entradas y modelo; el revisor comprueba además identidad de candidato, ruta,
orden articular y conjunto de pares. Los informes no habilitan movimiento.

Evidencia privada de esta intervención:
`../Humanoide-vla-evidence/20260914T072438Z_ENTRY-LOCAL-BOUNDS/`.
`before/` conserva el estado al empezar; `selective-sources/`, `interval-sources/`
y `final-sources/` conservan versiones y `evidence.sha256` los hashes. Los comandos,
logs, selección430, censo69, captura pasiva y búsqueda numérica están archivados.
El primer intento de radio local agotó 90 s; su versión intermedia exacta no
se preservó antes de la siguiente mejora y queda **PENDIENTE de reconstrucción**.
No se usa ese intento como prueba reproducible de aprobación. El primer arranque
del censo rechazó `max_depth=0` antes de calcular; se corrigió a1 y la ejecución
completa posterior es la conservada. Los resultados terminados sí identifican
fuentes exactas y entradas.

Aplicación: recuperar las fuentes PC de esta ficha y ejecutar las recetas.
No hay install/reload remoto. Rollback: restaurar sólo los tres revisores
modificados desde `before/`, retirar los cinco archivos nuevos de esta intervención
(cotas locales, intervalos, sus dos tests y censo), conservando trabajo previo y
posterior; actualizar estas entradas documentales. No restaurar indiscriminadamente
el repositorio ni sus cambios ajenos. Evidencia privada fuera de Git; sin commit/push.

## Punto de reanudación y límites de cierre

No ejecutar ENTRY ni conectar VLA físico a partir de estos informes. Lo pendiente
no se cierra cambiando `physical_approval` o aumentando la tolerancia:

1. Resolver la separación con la **escena actual**, incluyendo registro y contornos
   con incertidumbre acotada. La imagen actual recortada y dos obstáculos archivados
   no son una medición completa. No se recomienda una distancia de desplazamiento
   de mesa/robot a partir de esta búsqueda.
2. Mantener identificados los 54 avisos de interfaces del modelo: no equivalen a
   54 contactos reales, pero hace falta justificar su dominio permitido o corregir
   la representación. La revisión previa encontró contraejemplos que impiden una
   exclusión global derivada únicamente de HOME/PICO.
3. Demostrar el seguimiento/interpolación y parada para los ejes y trayecto usados,
   o disponer de un procedimiento y límites del fabricante que acoten el ensayo.
   Las trazas actuales sólo excitan ocho ejes; la presencia de un operador junto
   al paro no aporta por sí sola la distancia recorrida antes de detenerse.

La compatibilidad de mesa de 80 cm, pose y siguientes chunks del VLA sigue
separada de la entrada geométrica. No se declara éxito de agarre, shadow actual
ni aprobación del flujo completo por haber mejorado este cálculo.
