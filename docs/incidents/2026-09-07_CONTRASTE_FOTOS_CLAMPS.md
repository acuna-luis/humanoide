# Contraste offline del montaje corregido — 07-09-2026

## Resultado

### Cota de orientación para evitar elegir por apariencia

`audit_clamp_orientation_bound.py` calcula la esfera centrada en el origen
descriptivo, no en el centro de la caja: radio `sqrt(47²+55²+95²)=119,411 mm`.
La norma es invariante bajo rotación. Esta es una alternativa condicional al
registro del ángulo para un filtro preliminar, **no un registro físico**.
Requiere demostrar la correspondencia del origen (intersección del eje del
sensor con el plano de referencia de B/C) al frame sixforce y las referencias
ortogonales. Los campos de centro L/R, errores y radio seguro son nulos.

Si se acotan error de centro y error geométrico, sus radios pueden sumarse al
nominal por desigualdad triangular; aquí no se asignó ninguno. Volumen dinámico
de parada sigue aparte. Una intersección de la esfera es inconclusa: no
descartar un escenario real por ese solapamiento conservador. Ninguna ruta
se evaluó con esta esfera, ni se exportó objeto ROS.

Tres tests verifican fórmula, esquinas rotadas e inválidos; la prueba no valida
metrología. Suite completa v4 correcta, evidencias externas
`20260907_clamp_orientation_bound.json` y
`20260907_requalification_regressions_v4.json`. El bloqueo concreto restante
de esta alternativa es el **centro y sus errores**, no exigir de nuevo A–F/T ni
un CAD de abrazadera inexistente. No se ha resuelto ese centro con las fotos.

### T y contención nominal cerrados por declaración del operador

El 07-09 se recibe «T=130, no sobresale nada fuera de los otros márgenes».
El contrato conserva esa cita, fuente y alcance bilateral basado en la igualdad
de piezas previamente declarada. Se genera envolvente nominal 82×100×130 mm,
profundidad `95−130=−35` hasta +95 mm. No es el espesor F=36 de la placa.
Evidencia externa `20260907_clamp_nominal_T130/`, ocho tests del generador
correctos. No se exige ya medir soporte para este cierre nominal, ni CAD de
fabricante. No se ha establecido incertidumbre ni R/t y no se aprobó trayectoria.

### Continuación: integridad y medida práctica

Se corrigió el auditor local para no presentar límites de un lado cuando su
evidencia falta o no coincide con el hash, y para rechazar resultados no finitos
por desbordamiento numérico. No se detectó un movimiento asociado a este detalle:
el resultado global ya permanecía bloqueado. Test nuevo rechaza el esquema del
modelo parcial como entrada de montaje. Modelo y asimetría se incorporan a la
suite fija, evidencia externa `20260907_requalification_regressions_v3.json`.

La [ficha de cotas pendientes](2026-09-07_COTAS_PENDIENTES_SOPORTE.md) sustituye
una petición genérica de más vistas por T (profundidad total desde almohadillas)
y comprobaciones de contención con bordes existentes. Datos todavía pendientes;
no se eligieron valores, márgenes ni transformación y no se tocó el robot.

### Modelo propio: no se exige CAD de fabricante inexistente

**CORRECCIÓN, 07-09:** el plano del fabricante no es un prerrequisito exclusivo.
Una representación propia con envolventes verificadas es una alternativa.
Las seis nuevas vistas del brazo izquierdo recibidas en chat muestran placa,
sensor, soporte inferior y riostras; no se dispone de rutas originales para
hashearlas. No se reclama una transformación métrica a partir de esas vistas.

**VERIFICADO offline:** `scripts/build_clamp_simplified_model.py` consume el
contrato existente y genera `model.json` y `plate_projections.svg`. Evidencia:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260907_clamp_simplified_model/`.
El JSON incluye el SHA-256 del contrato. PNG auxiliar obtenido con Inkscape e
inspeccionado visualmente. Cuatro tests en `test_clamp_simplified_model.py` pasan.

| Componente | Representación | Límite de evidencia |
|---|---|---|
| Placa y almohadillas | Caja 70×100×36 mm; u −35/+35, v −55/+45, profundidad 59/95 mm | Cotas nominales del operador; incertidumbre pendiente |
| Dos patitas | Reserva de todo el borde u +35/+47 mm | Condicionada a que ambas estén dentro de altura y profundidad de la placa |
| Soporte, riostras, tornillería | Componente explícito sin límites numéricos | No se omite silenciosamente ni se supone contenido en 0–59 mm |
| Montaje L/R | Sin transformación ROS | Igualdad de piezas no implica iguales transformaciones |

**PENDIENTE concreto:** extremos mínimos/máximos del soporte y tornillería
respecto a las mismas referencias, contención de las patitas, incertidumbre y
registro de coordenadas al sensor. Una foto adicional sin escala/referencia no
cierra automáticamente estos datos. No repetir A–F ni pedir otra ronda de
ángulos genéricos. Estas coordenadas son descriptivas, no un sistema ROS ni
una terna dextrógira físicamente registrada.

El resultado es `PARTIAL_MODEL_NOT_REGISTERED`, no una nueva comprobación de
colisión. El generador termina con código 0 por creación de artefactos, nunca
como gate de autorización. No exporta geometría ROS. No se ha ejecutado barrido
ni modificado contrato de montaje, bloqueos, robot o servicios. Quedan además
pendientes equivalencia de interpolación, margen de parada y HOME de arranque.

### Cierre de observabilidad de los diez puntos

**VERIFICADO, sólo para los puntos seleccionados:** el auditor exterior v2
comprueba reflexión `(x,y)→(x,−y)` y obtiene residuo de vecino más próximo
**0 mm** en los conjuntos central, exterior y combinado, en L y R. Por eso
los puntos adicionales distinguen la orientación del eje largo, pero no
eliminan el empate entre dos sentidos de correspondencia. No afirmar que
toda la malla tenga esta simetría: el test sólo usa los centros seleccionados.
No confundir reflexión 2D con una rotación 3D físicamente válida.

La expresión previa «dos orientaciones candidatas» debe entenderse como
**dos correspondencias 2D**, no evidencia de dos montajes mecánicos posibles.
El ensayo no ha resuelto signo de normal/cara visible. Repetirlo, redondear
distinto o volver a fotografiar la misma cara sin una referencia adicional
no justifica elegir una solución ni completar la transformación métrica.

La unión fija URDF `wrist_roll→sixforce` se reinspeccionó: ambos lados tienen
`xyz=0 0.07712 0`, `rpy=-1.5708 1.5708 0`. Esto relaciona frames **del CAD**,
pero no identifica por sí solo cuál cara real del sensor o plano del soporte
se ve en la fotografía; no es una verificación independiente del montaje.

Evidencia nueva, preservando v1:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260907_clamp_outer_correspondence_v2.json`.
Seis tests pasan; el nuevo test distingue un rectángulo simétrico de un
conjunto con un punto asimétrico y rechaza entradas inválidas. Cero red,
conexiones, comandos, despliegues o cambios de límites.

**Bloqueo concreto:** para continuar hacia una cualificación física se
necesita identificar independientemente cara, plano y orientación de unión
sensor–soporte, además de acotar el soporte completo y su incertidumbre.
Vías posibles: plano de montaje referenciado al frame del sensor, o registro
metrológico de la unión realizado por personal competente con aislamiento
verificado. No se ha obtenido ninguno aquí. No solicitar más fotos genéricas,
repetir medidas A–F ni considerar solucionado este bloqueo mediante otra
suite offline. Una inspección de daños de carcasa tampoco proporciona ese
registro geométrico. HOME interno exige además su propia protección/validación.

### Continuación: fijaciones exteriores, sin nuevas fotos

**VERIFICADO CAD / OBSERVADO en fotos / INFERENCIA de correspondencia:**
`scripts/render_clamp_sensor_cad.py` generó cuatro SVG ortográficos desde el
STL original (L/R, vistas desde ±Z). Dos previews PNG L se rasterizaron con
Inkscape y se inspeccionaron. No son dibujos generativos ni fotos editadas.
El algoritmo de pintado por profundidad media sólo ilustra: no certifica
visibilidad, superficies externas ni geometría de colisión.

Las vistas muestran base alargada, contorno central lobulado, fijaciones
exteriores y una abertura rectangular. **No equiparar esa abertura con las
dos ventanas del soporte negro**, que es otra pieza. Tampoco asignar las
marcas verdes a ejes CAD. Los originales L/R ya registrados se abrieron de
nuevo; no hubo manipulación del robot para obtener otras vistas.

El análisis de triángulos z=4 mm extrae cuatro contornos de ~3,3 mm centrados
en (±28,±17,5) mm. Se anotaron manualmente cuatro cabezas exteriores visibles
en el soporte negro, separadas del patrón central, en
`config/clamp_outer_photo_landmarks.json`, con los mismos lienzos y hashes
originales que `config/clamp_photo_landmarks.json`.

`scripts/audit_clamp_outer_correspondence.py` mantiene el ajuste basado sólo
en seis puntos centrales, proyecta los cuatro candidatos exteriores y ensaya
las 24 asignaciones a las cuatro observaciones. No reajusta el modelo usando
los exteriores. La identidad física de dichos tornillos con los contornos
CAD continúa siendo hipótesis, no hecho demostrado.

| Lado | Dos hipótesis destacadas: RMS exterior | Otras cuatro con buen RMS central |
|---|---:|---:|
| L | 10,205 píxeles originales | 141,902–142,967 px |
| R | 21,170 píxeles originales | 155,547–156,085 px |

El RMS central de estas seis sigue ~0,852 px L/~1,022 px R. Las restantes seis
del conjunto de doce ya tenían mal ajuste central (~47–49 px) y no se
rehabilitan por su residuo exterior. No se fijó un umbral de aceptación; las
dos destacadas siguen indistinguibles bajo este contraste rectangular y los
sentidos de recorrido 2D no equivalen a matrices R físicamente válidas.

**Límite importante:** la homografía se extrapola como si todos los puntos
fueran coplanares; CAD central y contornos exteriores están en distintas cotas
y las cabezas fotografiadas añaden alturas desconocidas. El residuo no es
una precisión métrica ni una prueba de montaje. No demuestra por sí solo
cara visible, signo de normal, offset, orientación de herramienta o soporte
completo. No eliminar incertidumbres de `clamp_mount_requalification.json`.

Evidencia externa (salidas exclusivas nuevas):

- `20260907_sensor_cad_views/manifest.json`: hash ZIP y cuatro SVG;
  los PNG son previews auxiliares no incluidos en ese manifiesto.
- `20260907_clamp_outer_correspondence.json`: puntos, hashes, doce hipótesis,
  predicciones y asignaciones exteriores; estado
  `OUTER_FEATURE_SCREEN_ONLY_NOT_REGISTERED`.

Cinco tests de homografía pasan, incluidos proyección de puntos no usados
en ajuste y rechazo de probes inválidos; esto prueba cálculo, no hardware.
Sin red, ROS, movimiento, despliegue, commit ni push. El robot no se consultó.
Rollback de esta extensión: revisar/revertir sólo sus scripts, anotaciones y
documentación; no cambia las rutas bloqueadas ni exige rollback remoto.

**Reanudación:** resolver cara/normal y correspondencia del plano de fijación
con las referencias CAD visibles, conservando las dos hipótesis y el efecto
de distintas alturas. No pedir otra foto genérica ni ejecutar HOME para
distinguirlas. Si las fuentes no permiten cerrar esta identidad, hace falta
plano de montaje o registro metrológico cualificado, no elegir por intuición.

### Revisión vigente: no se solicita otra fotografía genérica

El operador ha aportado repetidamente la vista inferior solicitada y una
vista oblicua adicional en el chat. Se reconoce que el dibujo orientativo
no aclaró la referencia necesaria. **No falta cumplir esa solicitud:** no
pedir otra vez la misma vista, A–F, ni buscar un conector cuya existencia o
visibilidad no se haya identificado. No desmontar ni mover para fotografiar.
La imagen oblicua sólo consta en el chat, sin original local/hash asignado;
no se inventa procedencia ni identificación lateral para ella.

**VERIFICADO offline:** `scripts/audit_clamp_sensor_asymmetry.py` relee el
ZIP/URDF/STL original (origen/escala comprobados por el auditor de referencia).
Para cada giro alrededor de z busca un vértice rotado fuera de la AABB
original. Una salida positiva demuestra que el conjunto no se conserva
bajo ese giro; una salida cero NO demuestra simetría. No es un registro de
foto ni un cálculo de holgura física.

| Geometría CAD, igual resultado L/R | Giro 120°: exceso fuera de AABB | Giro 240° |
|---|---:|---:|
| Malla completa del sensor | 13,289273 mm | 13,291598 mm |
| Triángulos coplanares z=0 | 10,995556 mm | 10,995558 mm |

Identidad 0° da exceso cero. Estos milímetros describen **el test CAD contra
sí mismo**, no error de montaje, distancia al torso ni tolerancia aceptada.
La simetría del patrón central no debe extrapolarse a toda la pieza.
Esto deja abierta una vía de registro por contorno/fijaciones exteriores,
pero NO demuestra que el contorno visible sea el externo del STL, que z=0
sea la cara fotografiada o que las zonas discriminantes no estén cubiertas.
Las marcas verdes no tienen correspondencia CAD demostrada.

Evidencia exclusiva, sin sobrescribir informes previos:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260907_clamp_sensor_asymmetry.json`.
Contiene hashes y vértices testigo. Tres tests dirigidos pasan (rectángulo
asimétrico, cero que no prueba simetría, entradas inválidas).
Estado `CAD_ASYMMETRY_ONLY_PHOTO_REGISTRATION_UNRESOLVED`; cero conexiones,
cero movimientos, `physical_authorized=false`. Sin cambios remotos.

**Punto de reanudación técnico:** contrastar la forma completa y fijaciones
exteriores del CAD con las fotos existentes, manteniendo explícitas las
oclusiones y las distintas caras/planos. No elegir R/t sólo por semejanza ni
por el menor RMS de seis puntos. Si no se identifica una correspondencia
inequívoca, se necesita un plano de montaje referido al sensor o un registro
metrológico realizado en condiciones de aislamiento por personal competente;
no una nueva foto genérica ni un movimiento de prueba. Esa obtención no se ha
realizado ni autorizado aquí. Registrar el montaje tampoco cierra por sí solo
el soporte completo, incertidumbre, trayectoria continua y HOME de arranque.

Rollback local: retirar únicamente los dos scripts nuevos de asimetría y esta
actualización documental mediante revisión de diff; no cambia ningún bloqueo
ni requiere rollback en el robot. Sin commit ni push.

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

**Solicitud anterior, sustituida por la revisión vigente de arriba:** imagen que identifique una referencia no
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
