# Contraste offline del montaje corregido — 07-09-2026

## Resultado

### Referencias del manual SDK revisadas

Se leyó el DOCX local `SDK/Cruzr S2 优必选SDK二次开发文档【对外】6.24.docx`
(SHA-256 `649a46dd4edd80d2ae738c285d1e563ef4e71aaac8f827793584a1f5783d3d86`).
La sección 1.3 declara los ejes con articulaciones a cero. Se inspeccionó
directamente su figura `word/media/image7.png`, SHA-256
`5d559910e0a9771a43ee8c39f1251ab04f200cbdc52a061f5a2d434a631997ad`:
muestra manos articuladas, no el soporte pasivo actual. No resuelve la
correspondencia del montaje negro de las fotos.

La tabla de parámetros de sensores incluye filas L_sixforce_link y
R_sixforce_link con ceros. **No son el offset de las abrazaderas**: no trasladar
esos ceros al contrato de montaje. La sección de pinzas PGC también describe
otro efector. No se modificó el SDK ni ejecutó ningún ejemplo del documento.

**Siguiente dato físico mínimo:** imagen que identifique una referencia no
simétrica del sensor (por ejemplo, conector/salida de cable o marca de orientación)
y su relación con la parte fija de la muñeca y el soporte. Las cotas A–F,
las patitas hacia dentro y las vistas del patrón central ya están registradas.
No repetirlas ni mover articulaciones para conseguir otra vista. Sólo obtener
la imagen si la referencia es visible desde fuera de la envolvente, sin tocar
ni desmontar nada; si está oculta, registrar esa limitación. Un conector visible
será una referencia candidata que deberá contrastarse, no aprobación automática.

Esta dependencia no se resuelve ejecutando más veces el ajuste simétrico ni
eligiendo la solución con unas millonésimas menos de residuo. Quedan además
el soporte completo, incertidumbre y validación de recorridos/arranque.

### Ajuste numérico de las dos fotografías (offline)

**Búsqueda de referencia no simétrica:** en los contornos z=0 ya extraídos
hay candidatos distintos del patrón de seis: centro de un contorno de ~3,5 mm
en L `(12,0)` mm / R `(-12,0)` mm, y pareja de contornos exteriores en
L `(-30,5, ±10,5)` mm / R `(30,5, ±10,5)` mm. Son coordenadas CAD, no cotas
que deba repetir el operador. Esos candidatos podrían discriminar giro si
se demostrara su identidad física; en las fotos revisadas no queda establecida
esa correspondencia. No asumir que cualquier tornillo exterior es esa pareja,
ni retirar tapas o desmontar el sensor para buscarla. Conservar la incertidumbre
es distinto de afirmar que todo el sensor sea simétrico a 120°.

**VERIFICADO computacionalmente, no metrología:**
`scripts/audit_clamp_photo_correspondence.py` ensaya doce correspondencias por
lado (seis desplazamientos cíclicos, dos sentidos), entre los seis contornos
CAD candidatos y centros de seis cabezas visibles localizados manualmente.
Puntos aproximados y escalas del visor quedan explícitos en
`config/clamp_photo_landmarks.json`; los originales se comprueban por SHA-256.
No se editan imágenes ni se exportan transformaciones 3D.

| Lado | RMS de los seis mejores ajustes 2D | RMS de los otros seis |
|---|---:|---:|
| Izquierdo | ~0,852 píxeles originales | ~46,831 píxeles |
| Derecho | ~1,022 píxeles originales | ~48,518 píxeles |

**INFERENCIA limitada:** el patrón fotografiado es compatible en proyección
con el candidato CAD. No identifica cuál tornillo corresponde a cuál: tres
orientaciones por sentido de recorrido dan prácticamente el mismo ajuste.
Los dos sentidos son hipótesis de correspondencia 2D, no dos montajes 3D
físicamente válidos ni permiso para reflejar matrices de rotación.
Los residuos son de los puntos usados en el ajuste, no una validación
independiente, tolerancia física o distancia de seguridad en milímetros.

La orientación absoluta no puede resolverse sólo con este patrón. Antes de
asignar R/t se necesita vincular una referencia no simétrica del sensor físico
con el CAD (no simplemente la forma del soporte negro, ausente como pieza
identificada en el URDF). No se justifica pedir de nuevo A/B/C/D/F ni repetir
las mismas fotos: esos datos ya están disponibles. Hasta resolver esa
correspondencia y completar el volumen del soporte, las rutas siguen sin
calificar, incluidos HOME y rearme interno.

Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260907_clamp_photo_correspondence.json`.
Reproducción (archivo de salida nuevo, nunca sobrescribe):

```bash
python3 scripts/audit_clamp_photo_correspondence.py \
  --cad-report /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260907_clamp_sensor_bolt_pattern.json \
  --output /ruta/a/un/informe_nuevo.json
```

Resultado `PHOTO_CAD_HYPOTHESES_ONLY_NO_3D_REGISTRATION`; pruebas sintéticas
comprueban homografía conocida, ambigüedad de patrón y rechazo de entradas
degeneradas. Cero conexiones al robot y cero movimientos.

### Actualización: vistas inferiores y ambigüedad CAD

**OBSERVADO / declarado por operador:** últimas dos fotos recibidas en el
chat, primera brazo izquierdo del robot, segunda derecho. El operador aportó
después sus rutas; originales abiertos e inspeccionados directamente:

| Lado | Original | SHA-256 |
|---|---|---|
| L | `/home/lacuna/Imágenes/1.jpeg` | `30052b8cbab874a4aabb133b2e5ae888fe4840c7eec58a5c5359f59a17a9e377` |
| R | `/home/lacuna/Imágenes/2.jpeg` | `a584276dd7088b856b636629802160076544d5b15829b9f3a915341685c222c3` |

No confundirlas con las seis fotos anteriores de las 08:11. Se observan seis
cabezas de tornillo en la pieza central plateada y fijaciones exteriores
distintas en el soporte negro. Las patitas aparecen a la derecha en L y a la
izquierda en R, del lado del torso en estas vistas. Esta observación respalda
el reporte de orientación interior en la postura fotografiada, no establece
ejes ROS. El soporte prolongado y sus ventanas aportan una referencia visual
asimétrica, pero no se ha identificado su malla pasiva en el URDF: no permiten
por sí solos asignar un ángulo absoluto respecto del sensor CAD. Las marcas
verdes de pintura tampoco son índices de orientación CAD demostrados.

**VERIFICADO offline:** el nuevo análisis de bordes de triángulos coplanares
z=0 extrae seis contornos cerrados de aproximadamente 4,2 × 4,2 mm en cada
sensor. El conjunto se repite al rotarlo 120° y 240° (residuo máximo al punto
más próximo ~0,0000064 mm, redondeo CAD); a 180° el residuo es ~7,6484 mm.
Este resultado describe esos contornos, no todas las características del sensor.
Los centros R son los negativos XY de L en este CAD; no es una autorización
para reflejar o copiar la transformación de la herramienta física.

**PENDIENTE:** demostrar que esos contornos corresponden a las fijaciones
visibles (no a otra tapa/plano), e identificar una característica no simétrica
para registrar orientación y plano. Coincidir en seis tornillos no basta.
Las rutas originales ya están recibidas y registradas; no falta esa entrega
ni se solicitan nuevas cotas de placa. Falta la correspondencia geométrica,
no la identificación izquierda/derecha. El registro fotográfico será evidencia auxiliar, no certificación de
distancias libres ni aprobación de trayectorias.

Evidencia reproducible:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260907_clamp_sensor_bolt_pattern.json`,
generada por `scripts/audit_clamp_sensor_reference.py`. Pruebas unitarias cubren
extracción de contorno eliminando diagonal interior y detección de simetría.
Estado permanece `CAD_REFERENCE_CANDIDATE_ONLY`: cero conexiones al robot,
cero comandos de movimiento. Los bloqueos locales no interceptan HOME interno
de arranque; no se autoriza rearme ni movimiento con este resultado.

**VERIFICADO en archivos:** el URDF suministrado tiene una sola variante
`cruzr_s2_description/urdf/cruzr_s2_v1/cruzr_s2_v1.urdf`. En ambos lados:

| Unión | Traslación XYZ (m) | RPY (rad) |
|---|---|---|
| wrist_roll → sixforce | `0, 0.07712, 0` | `-1.5708, 1.5708, 0` |
| sixforce → pgc_base | `0, 0, 0` | `0, 0, 1.5708` |

La segunda unión es de **PGC**, no una transformación demostrada del soporte
pasivo. Los 77,12 mm no son longitud ni desplazamiento de la placa. No copiar
esa unión ni asumir traslación cero para el clamp real.

Se enumeraron los miembros de los ZIP URDF y USD Cruzr: ninguno contiene
`clamp` en su nombre. Esto corrobora la ausencia nominal, no demuestra que un
activo con nombre genérico no pueda representarlo. El contrato E4.1F existente
ya documenta la ausencia de CAD específico identificado.

SHA-256 ZIP URDF: `7cb7f856223ce99a86d44349be475a2b5925d57ca694ee069a96c808802e297e`.
SHA-256 ZIP USD: `7380c52227a9ca99c69121effbbbaff18b9807e72e8759ee3376bd47ac3f4c30`.
No se modificaron los originales ni se extrajo o ejecutó software del proveedor.

## Evidencia fotográfica

Originales en `/home/lacuna/Descargas/WhatsApp Image 2026-09-07 at … .jpeg`
(sin espacio entre el sufijo horario y `.jpeg`). Hashes calculados localmente:

| Sufijo horario | SHA-256 |
|---|---|
| `08.11.15` | `31d3eec3df249c43eaecc0beaec8d487f26c7ec1cc405e0a8d9dad7902687d3c` |
| `08.11.14 (1)` | `d0eb36504829fffc41314b76a6e80272aea730e1dec17b2dc5f38342540110fa` |
| `08.11.14` | `703060b723a8bcca608b527ca97affccaebcadf073bbb5bff0a0b62f94f98bad` |
| `08.11.13 (1)` | `bff565df97495453204b00e25397e729cfbbea702bd1315c01a94c01ede99c10` |
| `08.11.13` | `51aefd69b21eeee87036185a4d7be885cc89a5dce5629f87ec40478950dc1763` |
| `08.11.12` | `3b54bffbe9f78c0783b609ee18d341cda3f8121f1ba64161d78c96829afe3497` |

**OBSERVADO:** placas rectangulares con almohadillas, dos patillas salientes,
soporte lateral con refuerzos triangulares y desplazamiento respecto al sensor.
Las vistas permiten identificar las piezas; no son imágenes calibradas ni
incluyen una escala coplanar. No se dedujeron milímetros de píxeles ni se asignó
un marco ROS a un lado sólo por su posición en una fotografía. Hay separación
visible en las vistas aportadas, no una medida de holgura durante movimiento.
La restitución a fábrica se conserva como declaración del operador, no como
certificación obtenida por comparación con estas fotos.

## Cotas pendientes y cómo evitar repetir medidas

### Actualización con medidas aportadas por el operador

Ambos lados: A=95 mm, B=45 mm, C=55 mm; dos patillas de 12 mm
desde el borde por clamp. El operador volvió a medir directamente la altura
total y confirmó **100 mm**. Esta altura sustituye la lectura aproximada
anterior de 105 mm para la placa; no redefine automáticamente toda la
envolvente del soporte. El operador aclaró después la referencia: B/C=45/55
desde la unión real; desde el centro serían 50/50. Se acepta esa aclaración
como medida reportada bilateral y se cierra la pregunta de referencia.

La ilustración generada dejó la línea discontinua por debajo de la unión
sensor–soporte. Se advirtió en el chat y la aclaración posterior resuelve la
referencia: el plano de unión está 5 mm por encima del centro de altura de
la placa. No convertir ese desplazamiento en un eje ROS sin determinar su
orientación; tampoco se deduce de él el espesor total de todo el soporte.
Los salientes se añaden al contorno **lateral**, nunca a A; dos patillas en
el mismo borde no implican sumar 24 mm al ancho. Puede envolverse todo ese
borde hasta la punta con un volumen conservador, evitando medir cada curva,
pero aún hace falta ancho/posición lateral y espesor/envolvente del soporte.

Registro numérico: `config/clamp_mount_requalification.json`, sección
`reported_dimensions`, separada de `mounts`. Se mantienen R/t y bounds en
null hasta demostrar su correspondencia al sensor. La altura total medida
no justifica centrar la placa ni reflejar automáticamente el montaje.

Se conservan las lecturas históricas aproximadas `120 × 52 × 105 mm` y el
espesor local `33 mm`. No sustituirlas por dimensiones PGC. Esas lecturas
describían una envolvente de un extremo y **no** su posición ni equivalencia
bilateral después de cambiar el montaje.

Las referencias físicas identificables son el **eje central del sensor
plateado**, el **plano de unión del soporte negro debajo del sensor** y la
**cara exterior de las almohadillas**. Primeras cotas útiles, por cada brazo
identificado desde el propio robot:

1. Distancia perpendicular desde el eje del sensor al plano de las almohadillas.
2. Distancias desde el plano de unión del soporte hasta los bordes superior e
   inferior de la placa, indicando qué borde queda de cada lado del plano.

**A/B/C ya contestadas: no repetir estas solicitudes.** Siguiente dato manual:
ancho del rectángulo de la placa sin patillas y ubicación lateral respecto
al eje del sensor. Las patillas añaden 12 mm en el borde correspondiente:
ancho exterior de la placa con dos patillas en el mismo borde = ancho +12 mm,
no +24 mm. Ese ancho no equivale a la envolvente completa del soporte.

Además deben quedar acotados los extremos laterales respecto al eje, incluidas
las patillas, si las cotas históricas no los localizan. Son cotas de posición,
no una petición de repetir todas las dimensiones. Las fotos laterales
`08.11.14 (1)` y `08.11.13` muestran el soporte; las vistas de almohadillas
`08.11.14` y `08.11.12` muestran sus extremos. Falta enlazar sin ambigüedad
estas referencias externas al origen/orientación de `sixforce_link`; no asumir
que el plano visible coincide con z=0 del STL.

**No se solicita mover muñecas, desmontar, tocar brazos ni introducir una
cinta cerca de mecanismos energizados.** La medición por una persona requiere
una condición de aislamiento y estabilidad verificada por personal competente;
el E-stop por sí solo no se trata como aislamiento de todas las energías.

## Estado de cierre

### Referencia de sensor: inspección offline posterior

`scripts/audit_clamp_sensor_reference.py` inspecciona el STL binario original
en su ZIP, valida origen/escala de colisión y calcula bounds y sumas de áreas
de triángulos de z constante. No extrae ni modifica el SDK. Resultado:
`20260907_clamp_sensor_reference.json`, `CAD_REFERENCE_CANDIDATE_ONLY`.
En ambos sensores, z=0 suma aproximadamente 2946,945 mm² de triángulos
planos; es una referencia candidata, no una cara externa de fijación
identificada físicamente. Bounds de malla: x≈±38,617 mm, y≈±26 mm,
z≈−26,5…+19 mm. No convertir esos extremos en cotas del soporte negro.

El URDF sigue conectando PGC al sensor, no proporciona el soporte pasivo.
La vista inferior de cada unión, con tornillos y contorno completo visibles,
es la evidencia siguiente para contrastar posición angular y plano de montaje.
No se requieren nuevas cotas A–F en este paso. La fotografía no garantiza
resolver por sí sola la correspondencia métrica; servirá para identificarla
o precisar el dato que falte. Tomarla sólo desde fuera de la envolvente, sin
introducir manos/cabeza debajo del brazo ni moverlo/desmontarlo para obtenerla.

No hubo conexión ni comando al robot. Las cinco regresiones previas siguen
aprobadas; la inspección CAD no es un barrido de trayectoria ni habilita HOME.

### Actualización posterior: espesor confirmado y volumen parcial

El operador confirmó F=34+2=36 mm y medidas iguales en ambas abrazaderas.
No repetir F ni A/B/C/D. El auditor deriva ahora placa+almohadillas de
70×100×36 mm; desde el eje hacia las almohadillas ocupa 59…95 mm (A−F…A).
La altura respecto al plano sigue −55…+45 mm y el ancho sin patillas −35…+35.
Un prisma que rellene también las patillas sería 82×100×36 mm **sólo si** éstas
quedan dentro del intervalo de profundidad de la placa; se conserva como
candidato, no como inclusión demostrada de todo el efector.

Estas coordenadas son distancias descriptivas, no un frame ROS ortonormal
identificado ni una malla instalada. Falta incluir soporte/fijaciones,
incertidumbre y correspondencia al sensor en ambos lados; no se ha ejecutado
barrido de colisiones. Las referencias de muñeca/PGC del proveedor no se
reutilizan como si fueran las del soporte real.

Ejecución offline: cinco tests aprobados, incluidos rechazo de F ausente,
no finito, negativo, booleano y profundidad que cruza el eje sin revisión.
`20260907_clamp_plate_volume_36mm.json` fuera de Git conserva resultado
`BLOCKED_MOUNT_INPUTS` (salida 3 esperada), cero conexiones y cero comandos.
Registro: `config/clamp_mount_requalification.json`; cálculo:
`scripts/audit_clamp_mount_requalification.py`. Sin cambios remotos, commit o
push; no se levantó ningún bloqueo de movimiento.

### Actualización: ancho y orientación de patillas

Operador: rectángulo de 70 mm centrado en el eje de giro, ancho exterior
82 mm con patillas. Ambas tienen patillas **hacia el interior del robot en
la postura actual**. En un marco descriptivo con u hacia las patillas y v
hacia el borde superior, la envolvente frontal reportada es
u=[−35,+47] mm, v=[−55,+45] mm. No se asignan estos ejes al URDF: la
dirección hacia el torso cambia con la postura de la muñeca. En esta postura,
las puntas alcanzan 47 mm hacia el interior desde el centro lateral de la placa,
no 35 mm. No es una medida de distancia a la carcasa ni demuestra contacto.

El auditor ahora deriva ese rectángulo envolvente 2D rellenando conservadoramente
todo el borde hasta las puntas; así no hace falta medir los radios y alturas
individuales de ambas patillas para esta aproximación. No incluye todavía
profundidad del soporte, tornillos ni incertidumbre. Cuatro tests locales
aprobados; el auditor conserva `BLOCKED_MOUNT_INPUTS`, sin movimiento.
Evidencia fuera de Git: `20260907_clamp_front_profile_82mm.json`; la dirección
interior fue declarada después de generar ese archivo y está en el contrato
actual, no se reescribió el artefacto histórico.

Próxima comprobación de dimensión: espesor total de placa más almohadillas,
perpendicular a la cara de contacto. La lectura histórica de 33 mm no tiene
referencia suficientemente inequívoca para reutilizarla como ese espesor.
También faltan transformación al sensor y volumen completo del soporte;
completar el espesor no autorizará por sí solo HOME.

Fotos recibidas y contrastadas: completo. Transformación métrica bilateral:
pendiente. Barrido continuo y HOME interno: pendientes. Ningún PASS físico,
publicador, conexión al robot, cambio remoto o movimiento en esta revisión.
El bloqueo local permanece intacto. Reanudar en la obtención de cotas de
montaje y su correspondencia al frame; no repetir un ensayo HOME para medir.
