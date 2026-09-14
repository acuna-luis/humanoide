# ENTRY: datos actuales y separación de las tolerancias

2026-09-14, Europe/Madrid. VLA-01. **OBSERVADO y VERIFICADO offline;
movimiento físico no aprobado.** Continúa la petición de cerrar ENTRY y se
incorpora la instrucción de adaptar el error de 2 mm. No se envían movimientos,
paradas o reinicios, ni se modifican controladores, filtros o límites del robot.

## Adaptación del error de escena

Los **2 mm del certificador son separación geométrica mínima**, definida en
`prepare_vla_entry_bundle.py`; no son una especificación verificada de exactitud
de la cámara, ni la distancia completa necesaria para detener el robot.
Tampoco se sustituyen los errores de montaje/contorno declarados anteriormente
por el técnico por una supuesta exactitud del sensor.

Se añade un perfil explícito exclusivamente offline:
[`entry_scene_uncertainty_review.json`](../../config/vla/offline/entry_scene_uncertainty_review.json).

| Concepto | Valor y alcance |
|---|---|
| Incertidumbre traslacional de escena para explorar | **50 mm**, provisional |
| Aplicación | Ampliar cada caja de escena 50 mm por cara |
| Separación geométrica mínima existente | 2 mm, conservada |
| Error articular del escenario | ±1°, hipótesis offline conservada |
| Error angular de registro | Sin cota validada |
| Recorrido de parada | Sin cota validada |

Los 50 mm se redondean por encima de los 43,565 mm de discrepancia máxima
observada en el contraste anterior. **No constituyen un error total demostrado,
un óptimo industrial o una recomendación de UBTECH.** La ampliación cubre una
hipótesis de traslación; no convierte un residual de unas muestras en una cota
de toda la escena, sus dimensiones, orientación o partes ocluidas.

`review_entry_fixture_hypotheses.py` acepta
`--scene-uncertainty-profile config/vla/offline/entry_scene_uncertainty_review.json`.
Rechaza combinarlo con `--padding-mm`, valores inválidos o perfiles que pretendan
autorizar ejecución/modificar los 2 mm. Conserva el hash del perfil en la salida.
Las opciones anteriores mantienen sus valores por defecto; ningún ejecutor
físico lee ni aplica este perfil.

**Resultado con ENTRY440 y los sólidos del ajuste visual ampliados 50 mm:**
acceso y retorno vacío dan 1017 pares certificados, 54 avisos nominales y **1
par sin demostrar: abrazadera derecha–caja**. Sin timeout; 20,72 y 24,83 s.
El testigo del acceso está al 75 % de READY→ENTRY: distancia inferior calculada
28,434 mm, frente a cota isotrópica requerida 88,384 mm. No es una colisión
demostrada. La partición adicional de incertidumbre no lo certifica.

Esta hipótesis usa el ajuste visual archivado y no reemplaza la escena original
que pasó el análisis anterior. Permitir más incertidumbre requiere más espacio
libre; no se resta el error a las distancias ni se acepta penetración del modelo.

## Comprobaciones nuevas en el robot, sólo lectura

Captura pasiva de Motion iniciada a las **09:53:26 UTC / 11:53:26 Europe/Madrid**:
356 mensajes completos, ambos paros observados en 0, sin incidencias del
analizador, sin muestras de fault o actuador deshabilitado. Todos los ejes
observados tienen velocidad 0; discrepancia solicitada–medida máxima
0,000958738 rad. No hubo transición de paro: **esta captura en reposo no mide
seguimiento dinámico ni distancia/latencia de parada**.

Se redescubren contenedores Motion y Vision. Vision tiene dos contenedores con
sufijo `ros2-1`; se selecciona el `walker-ros.ros2-1` observado, sin asumir que
el otro contenedor de escritorio sea equivalente. La primera selección ambigua
se detuvo localmente antes de consultar. Ningún contenedor se instala o reinicia.

Nueva captura pasiva RGB/nube/CameraInfo y TF:

- RGB y nube comparten exactamente la marca de origen
  `1789379932427157000 ns`; el TF se consulta en ese instante.
- RGB 960×576, nube 8990 puntos, 8103 finitos dentro del intervalo óptico
  0,1–4 m usado sólo para analizar. K y TF coinciden con los anteriores.
- CameraInfo tiene marca 0 y llega como configuración latched: no se declara
  nueva calibración. Coincidencia de marcas RGB/nube no certifica el reloj
  físico del sensor ni su precisión métrica.
- TF cámara→base: traslación `[0.157298,0.036528,1.506770] m`, cuaternión XYZW
  `[0.600126,-0.590726,0.383595,-0.379140]`.

El nodo de captura se crea y destruye dentro del contenedor ROS existente,
mediante `python -c`, sin copiar archivos ni publicar órdenes de movimiento.
Las imágenes y datos permanecen en evidencia privada. No se infiere zona libre
ni autorización física a partir de esta imagen.

## Registro: comparación en los mismos puntos

Se añade `compare_entry_scene_registration.py`. Evalúa la distancia perpendicular
firmada de los mismos puntos del tablero al plano obtenido por ajuste visual;
evita confundir diferencia de altura entre lugares distintos con error de plano.

| Evidencia | Puntos compatibles con plano de nube | Mediana firmada al plano visual | Percentil95 absoluto |
|---|---:|---:|---:|
| Captura anterior | 117 | 33,451 mm | 40,290 mm |
| Captura nueva con marcas coincidentes | 135 | 33,893 mm | 38,835 mm |

En la nueva captura, el residual95 de la propia nube respecto a su plano es
4,598 mm. Las normales de los planos difieren 4,549°. La discrepancia persiste
en las nuevas observaciones; aún no se puede atribuir a una única causa ni
afirmar exactitud de 2 mm. Anotaciones de esquinas, dimensiones declaradas,
calibración y proyección requieren contraste; el nuevo margen exploratorio
no declara corregida ninguna de ellas.

Para reproducir los puntos: decodificar los campos FLOAT32 `x/y/z` de la nube,
con sus offsets y `point_step`; filtrar valores finitos y 0,1<Zóptico<4 m;
calcular `uv = (K @ xyz)[:2] / Zóptico` y `p_base = R_tf @ xyz + t_tf`.
Los arrays `uv` y `points_base` quedan en `current-points.npz`; los polígonos
visibles del tablero, revisados sobre el RGB nuevo, en `current-annotations.json`.
No se usan índices de una nube no organizada como coordenadas de imagen.

## Última interfaz y contrato de movimiento

Se optimiza el demostrador de fronteras con `entry_relative_kinematics.py`:
cancela la cadena común y calcula sólo la transformación relativa necesaria.
128 comparaciones con FK completa en estados aleatorios, incluidas ramas
distintas e inversión de pareja, pasan con tolerancia numérica 2e-14.
Una opción separada usa distancia FCL directa: 192 comparaciones contra el
método de colisión+distancia, incluidas 98 intersecciones, dan diferencia 0.
Valores FCL no positivos siguen siendo frontera no separada.

La unión elevador2–torso **continúa sin demostración continua**: dos análisis
de hasta 180 s agotan presupuesto después de 100321 y 120185 consultas,
respectivamente. No se convierte ese agotamiento en contacto ni en aprobación.
No cambia la revisión de los 13 cruces CAD ya presentes en HOME/PICO.

Las trazas previas mantienen cobertura incompleta de los ejes de ENTRY.
`cmd_pos` es consigna solicitada sin límites aplicados, según la definición
archivada, y no se observó ninguna parada nueva. No se asigna una cota de parada
inventada para completar el certificado.

## Referencias técnicas y alcance

La documentación de [Universal Robots sobre funciones de seguridad](https://www.universal-robots.com/manuals/EN/HTML/SW5_25/Content/prod-usr-man/complianceUR3e/H_g5_sections/safetyFunctionsAndinterfaces/configurable_functions.htm)
exige considerar el movimiento posterior a iniciar una parada. Sus prestaciones
numéricas pertenecen a sus robots y **no se trasladan al Cruzr**. La documentación
de [MoveIt CollisionRobot](https://docs.ros.org/en/lunar/api/moveit_core/html/classcollision__detection_1_1CollisionRobot.html)
distingue padding geométrico y pares de colisión permitida. Estas referencias
apoyan separar conceptos; no proporcionan una tolerancia óptima universal ni
una lista de interfaces permitidas para esta unidad. Consultadas el 14-09-2026.

## Conservación y reproducción

Evidencia privada:
`../Humanoide-vla-evidence/20260914T095214Z_ENTRY-FINAL-GATES/`.
Incluye captura y análisis pasivos, descubrimiento de contenedores, captura
RGB/nube/TF, comparación de registro, informes de frontera, regresión FCL,
perfil de 50 mm, comandos, fuentes finales, backups y manifiesto SHA256.

Cambios PC: módulo FK relativo y test; revisor de fronteras ampliado;
capturador pasivo `capture_entry_scene_readonly.py`; comparador de planos y
tests; perfil offline y su carga en `review_entry_fixture_hypotheses.py`.
**11 tests pasan**, además de la regresión FCL citada y la captura real pasiva.
La sintaxis del capturador se valida también en el contenedor ROS existente.
Un intento de procesamiento local usó el Python sin SciPy y se repitió con
`.venv/general-home`; no se instalaron paquetes.

Reproducción: `boundary-command.json`, `boundary-distance-only-command.json`,
`registration-command.json`, `current-registration-command.json` y
`scene50-command.json` contienen arrays de argumentos para ejecución offline
desde la raíz, siempre con salidas nuevas. `scene-command.json` identifica
host, contenedor y hash del código de sólo lectura enviado. Captura Motion:
`python scripts/teleoperation/capture_home_motion_trace.py --seconds 10
--output-dir /ruta/privada/nueva`; no mueve ni detiene el robot.

Tras actualización, recuperar fuentes y evidencia por hash y verificar de nuevo
modelo, contenedores, tipos, frames y endpoints antes de capturar. No instalar
el perfil de hipótesis como configuración de ejecución. Reversión: restaurar
sólo los revisores/tests modificados desde `before/` y retirar los módulos,
perfil y anotaciones nuevos, preservando trabajo anterior. No hay cambios
remotos persistentes que restaurar. Sin commit/push.
