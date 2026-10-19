# app2 — plan de trabajo y preguntas pendientes

**ID:** APP2-PLAN-20261019.

**Fecha/zona:** 19 de octubre de 2026, Europe/Madrid.

**Estado:** plan incremental; infraestructura y fotografías observadas;
reconocimiento específico pendiente de implementación y validación.

**Alcance inmediato:** percepción de las piezas visibles, sin movimiento del robot.

## 1. Decisión de trabajo

Sí podemos avanzar ya con reconocer las piezas. El primer resultado será
**detectar cada pieza, separarla visualmente de sus vecinas y mostrar dónde
está en la imagen**. Esto no requiere conocer todavía el transportador o su PLC.

Se separan tres objetivos:

| Nivel | Resultado | Situación |
|---|---|---|
| A: detección de instancias | Contorno, ubicación en píxeles, cantidad visible y confianza por pieza | Siguiente hito; se puede preparar con las imágenes disponibles |
| B: identificación | Familia confirmada y referencia/material ID correcto frente al esperado | Requiere referencias etiquetadas, confundibles y criterio de aceptación |
| C: operación física | Pose métrica, agarre, entrega orientada, alimentación y caja vacía | Fases posteriores, con validación específica |

Durante A, una detección no tendrá un material ID inventado. La identificación
exacta permanecerá `NO_VERIFICADA` hasta contar con evidencia suficiente.

## 2. Requisitos y terminología

La lámina del cliente desarrolla **ITR Material Feed and Empty Container Handling**:
alimentar piezas, comprobar identificación antes de cargar, conservar orientación
y superficies, respetar cantidad/espaciado, comprobar disponibilidad del destino,
gestionar cartón vacío y registrar anomalías. La identificación debe registrar
resultado, `no-read`/`misread`, reintentos y excepción en la interfaz de la sección 7.
El contrato de esa interfaz no está disponible. Véase [el detalle](REQUISITOS_CLIENTE.md).

Se incorpora la aclaración aportada por el usuario:

| Sigla | Uso sectorial contrastado | Nombre de trabajo en español |
|---|---|---|
| ITR | Inner Tie Rod | Bieleta interior / rótula axial de dirección |
| OTR | Outer Tie Rod | Terminal exterior / rótula exterior de dirección |

La literatura citada emplea explícitamente ITR para inner tie rod y OTR para
outer tie rod. Esto respalda la terminología, **no identifica una referencia
concreta de nuestras fotografías**. [Park et al., 2014](https://onlinelibrary.wiley.com/doi/10.1155/2014/942645).

Las piezas alargadas son compatibles visualmente con la interpretación ITR
aportada por el usuario; se conserva como **INFERENCIA** hasta confirmación de
referencia por el cliente. El título OTR situado al final de la lámina podría
iniciar el apartado siguiente. Su posición no demuestra que las fotos sean OTR
ni que exista un error en el documento. El alcance detallado de OTR no se ve.

## 3. Evidencias conservadas

Se ha archivado la **lámina exacta de la fábrica real**, 2189×630, y cinco PNG
de las cámaras del robot, incluida la cabeza sin rectificar a 1920×1536.
Las copias se verifican mediante SHA256 y se mantienen fuera de Git.
Rutas, procedencia, resoluciones y copia empaquetada en [FOTOS_Y_FUENTES.md](FOTOS_Y_FUENTES.md).

Hechos observados el 19-10-2026:

- Cabeza rectificada: `/sensor/camera/stereo/color/raw`, 960×576, `bgr8`.
- Cabeza izquierda sin rectificar: `/sensor/camera/stereo_left/image/raw`,
  1920×1536, `yuv422`, convertida a PNG para inspección.
- Cintura y chasis: RGB 640×360. En la captura útil de cabeza, cintura sigue
  cortando la bandeja y no se elige como vista principal.
- El encuadre inicial mostraba sólo parte de la espuma. En las capturas
  posteriores se ve la bandeja completa de cartón con piezas metálicas alargadas
  próximas entre sí, sobre contenedor azul.
- ROI orientativa en la imagen rectificada conservada: x380–640/y320–505.
  No es un destino físico ni debe copiarse a otra resolución o postura.
- PC: RTX 4070 Laptop, 8188 MiB. Ruta a Vision por Ethernet `eno1`.
  Rendimiento del detector bajo carga todavía no medido.
- El detector del proveedor está especializado en cajas/workbin. No está
  demostrado que reconozca estas piezas.

Una imagen útil y su resolución no validan escala de profundidad, identidad,
exactitud milimétrica, pose de agarre o fuerza necesaria.

## 4. Hoja de ruta incremental

Los hitos se completan por evidencia. No se fija una duración de entrenamiento
sin conocer referencias, cantidad de muestras y criterios de aceptación.

| Hito | Trabajo y entregable | Si funciona | Si no funciona |
|---|---|---|---|
| H0 — conservar y describir | Fotos originales, manifiesto, requisitos y preguntas | Completado documentalmente; añadir originales futuros sin sobrescribir | Recuperar el fichero original; no sustituirlo por una imagen recreada |
| H1 — reconocimiento inicial | Dataset pequeño etiquetado, detecciones/contornos por pieza y visualización offline | Ampliar escenas y evaluar errores | Revisar encuadre, oclusión, separación, resolución o método |
| H2 — distinguir referencias | Clases verificadas y confundibles, matriz de confusión y resultado desconocido | Comparar ID esperado/observado con criterio acordado | Obtener rasgos visibles, otra vista o marcado; no forzar una clase |
| H3 — optimizar velocidad | Medidas de latencia y consumo; comparar modelos/exportación | Conservar la alternativa más rápida que cumpla precisión | Revisar recorte, transporte, copias y resolución; no perder detalles distintivos |
| H4 — observación en vivo | Salida continua con timestamps y rechazo de imágenes antiguas, sin publicar movimiento | Prueba prolongada en condiciones representativas | Resolver colas, pérdidas, deriva de escena y errores de lectura |
| H5 — pose y agarre | Calibración, TCP, profundidad/CAD, geometría y ejecutor específico | Ensayo posterior autorizado con comprobaciones físicas | Mantener sólo percepción, sin compensar con límites más laxos |
| H6 — alimentación completa | Integración con estación, orientación/espaciado, caja vacía e interfaz sección 7 | Validación del ciclo completo con cliente | Registrar excepción y detener la fase correspondiente |

H0 está completado para las referencias disponibles; H1–H6 siguen pendientes.
Una sola fotografía no demuestra que H1 o H2 estén resueltos.

## 5. Próximo hito: detectar cada pieza

1. Usar las fotos conservadas para acordar qué contorno visible pertenece a
   cada instancia. No inventar las partes ocultas por cartón u otras piezas.
2. Preparar una primera toma de imágenes variadas de la zona de trabajo:
   piezas aisladas, bandeja completa, huecos, solapamientos, bandeja vacía y
   objetos que no deban detectarse. Mantener originales y metadatos.
3. Para un prototipo, empezar con unas decenas de escenas distintas; después
   preparar aproximadamente 200–500 imágenes útiles como presupuesto inicial
   de etiquetado, ampliable según errores. No son un mínimo garantizado ni
   cientos de frames casi iguales del mismo vídeo.
4. Etiquetar contornos y asignar clase provisional neutral cuando falte la
   identificación confirmada. No llamar a todas las piezas un mismo material ID
   únicamente por estar en la misma caja.
5. Separar entrenamiento y prueba por sesión y, cuando haya varias unidades,
   por unidad física. Reservar escenas con cambios reales de aspecto y posición.
6. Comparar un segmentador pequeño con una referencia sencilla de contornos/
   geometría en escena controlada. Si esta última sólo reconoce objeto sobre
   fondo, no presentarla como identificación de referencia.
7. Guardar resultados dibujados, errores, tiempos y versión del modelo para
   que la siguiente sesión pueda continuar desde el mismo punto.

Candidatos de partida: variantes pequeñas n/s de YOLO de segmentación, con
YOLO26-seg como opción actualmente documentada. Se hará ajuste con datos propios:
una red COCO genérica no identifica automáticamente una referencia industrial
de dirección. No se han instalado ni descargado pesos app2 en esta intervención.
[Segmentación y entrenamiento](https://docs.ultralytics.com/tasks/segment/).

Una máscara puede servir para estimar un eje principal en píxeles; la orientación
de sus extremos puede seguir siendo ambigua. No se convierte en orientación 3D
o punto de agarre sin calibración y comprobación específicas.

## 6. Identificar referencias parecidas

El usuario ha confirmado que el sistema debe distinguir piezas parecidas.
Esta necesidad se conserva aunque el primer prototipo use una clase provisional.

Para H2 se necesitan ejemplos correctos y confundibles con referencia verificada.
Si los detalles que las distinguen no son visibles, primero se estudiará otra
vista, mayor resolución efectiva o un marcado legible. Añadir entrenamiento no
recupera información ausente de la imagen.

Si existe código o texto legible en la pieza, evaluar lectura y comprobación
visual conjunta. El ID de una etiqueta de caja aporta contexto, pero no prueba
por sí solo que cada pieza interior sea correcta. La validación de referencia
podrá usar un clasificador ligero sobre el recorte o puntos distintivos si las
confusiones lo justifican. Se probará antes de incorporarlo al flujo.

## 7. Velocidad y evaluación

**Actualización APP2-CLOUD-ONBOARD-20261019:** el usuario concreta que la
ejecución final debe estar dentro del robot. La nube se utilizaría para preparar
datos/entrenar; el destino de inferencia es Vision. Una comprobación offline en
PC puede ayudar durante el desarrollo, pero no sustituye la validación a bordo.

**APP2-VISION-RUNTIME-20261019 — comprobación real posterior completada:**
Vision es Jetson AGX Orin/aarch64, RAM61,37GiB, L4T36.3, CUDA12.2 y
TensorRT8.6.2.3; import TensorRT correcto. MemAvailable~11,4GiB y GPU compartida
con picos observados hasta99%, sin benchmark app2. Cuatro canales de imágenes
recibidos con timestamps crecientes; mensajes SHM del proveedor. Detalle,
contenedores, fuentes, errores de consulta corregidos y límites en
[la verificación real](VERIFICACION_ROBOT_Y_ELECCION_VISION.md).
La imagen actual Roboflow Jetson6.2 consultada usa CUDA>=12.6/TensorRT10.7:
no instalarla suponiendo compatibilidad. Mantener entrenamiento en nube y
descargar ONNX para un ejecutor propio compatible con la pila existente.
Primera prueba técnica propuesta: YOLO11n-seg pequeño, previa resolución de
licencia; RF-DETR-seg como alternativa a comparar. Ningún modelo nuevo ejecutado.
Antes de compilar o desplegar, reconfirmar el entorno si ha habido cambios;
no actualizarlo ni reutilizar un engine del PC/nube por suposición.

Valoración de plataformas, sin cuenta creada, datos subidos o modelos instalados:

| Opción | Encaje propuesto | Decisión pendiente |
|---|---|---|
| Roboflow | Primera candidata por el flujo de preparación de datos y entrenamiento; RF-DETR de segmentación figura entrenable/exportable y Apache2.0 | Descargar un modelo pequeño y comprobar exportación/runtime, precisión y coste de ejecución en Vision |
| Ultralytics Platform | Alternativa directa para entrenar YOLO de segmentación en nube y descargar pesos/ONNX | Comprobar licencia del modelo para el producto y medir una variante pequeña en el mismo Vision |
| NVIDIA TAO | Alternativa técnica de segmentación de instancias y despliegue NVIDIA | Mayor preparación del flujo; no se ha demostrado ventaja para este prototipo |

La preferencia por Roboflow es una valoración de facilidad, no un benchmark ni
una confirmación de compatibilidad UBTECH. La selección del modelo queda abierta:
comparar una variante pequeña RF-DETR-seg y una YOLO-seg con las mismas escenas
reservadas. Elegir por confusión entre referencias, máscaras, latencia y memoria
medidas en el robot. Evitar un modelo que sólo pueda consultarse mediante API
remota si no permite el despliegue propio necesario.

Fuentes primarias consultadas el 19-10-2026:
[modelos/exportación de Roboflow](https://docs.roboflow.com/models/supported-models),
[descarga de pesos](https://docs.roboflow.com/models/model-weights/download-roboflow-model-weights),
[entrenamiento/exportación Ultralytics](https://docs.ultralytics.com/platform/train/models),
[TAO Mask2Former](https://docs.nvidia.com/tao/tao-toolkit/7.2.0/text/cv_finetuning/pytorch/instance_segmentation/mask2former.html),
[compatibilidad de engines TensorRT](https://docs.nvidia.com/deeplearning/tensorrt/latest/inference-library/engine-compatibility.html).
Licencias/formato/exportación dependen del modelo; no suponer que una suscripción
de entrenamiento concede automáticamente derechos de despliegue cerrado.

Flujo previsto: fotos → entrenamiento en nube → pesos/ONNX → compilación compatible
con el destino → contenedor app2 separado en Vision → observación de cámaras.
Descarga de artefactos, dependencias y funcionamiento sin Internet deberán
verificarse antes de aceptar el despliegue. No hay inferencia app2 a bordo aún.

Usar imágenes directas de cámara, recorte de zona útil, batch1 y cola que conserve
la última imagen; conservar detalle de la referencia. Mantener app2 separado de
los contenedores de control, sin cambiar el SDK ni sustituir workbin.

Medir por separado captura/transporte, preprocesado, inferencia y postprocesado.
Registrar latencia imagen→resultado p50/p95, frecuencia, imágenes descartadas,
consumo y errores por escena. Los campos age_ms de las primeras capturas
incluyen procesamiento secuencial; no son un benchmark de la aplicación.

Después de validar precisión, comparar exportación TensorRT y precisión
numérica reducida en la GPU de destino. Mantener sólo mejoras que conserven los
criterios acordados. Un engine TensorRT no se trata como fichero portable entre
PC y Vision sin verificar hardware/runtime. [Exportación TensorRT](https://docs.ultralytics.com/integrations/tensorrt/).

Criterios a acordar, sin inventar porcentajes industriales:

- Detección: piezas omitidas, falsas detecciones, fusiones de dos instancias,
  fragmentaciones de una pieza y cantidad visible.
- Identidad: falsa aceptación de otra referencia, falso rechazo y desconocidos.
- Calidad espacial: máscaras y error de ubicación/orientación en imagen.
- Rendimiento: latencia p95 y estabilidad bajo la carga real.

## 8. Registro de preguntas

| ID | Pregunta | Estado / efecto |
|---|---|---|
| Q01 | ¿Cuál es el código de cada referencia objetivo y confundible? | Pendiente; bloquea afirmar ID exacto, no preparar detección genérica |
| Q02 | ¿Material ID significa referencia, lote, número de serie o combinación? | Pendiente; define etiquetas e interfaz |
| Q03 | ¿Qué pieza de la bandeja corresponde a cada referencia? | Pendiente; hace falta ground truth, no deducirlo por forma |
| Q04 | ¿Hay marcado legible en pieza o etiqueta en caja y qué contiene? | Preguntado, sin respuesta todavía; condiciona lectura de códigos |
| Q05 | ¿Se confirma que app2 desarrolla ITR y OTR es el apartado siguiente? | Interpretación aportada por usuario; confirmación cliente pendiente |
| Q06 | ¿Se trabajará con piezas parecidas o siempre idénticas? | Respondido: debe distinguir piezas parecidas |
| Q07 | ¿Cuántas referencias/unidades habrá, incluyendo mezclas y defectos? | Pendiente; define dataset y cobertura |
| Q08 | ¿Qué variaciones de bandeja, apoyo, luz, orientación y oclusión se esperan? | Pendiente; ya se observaron espuma inicial y cartón posterior |
| Q09 | ¿Qué falsas aceptaciones/rechazos y latencia son admisibles? | Pendiente; no elegir modelo sólo por FPS |
| Q10 | ¿Hay dimensiones, masa, CAD y superficies de agarre autorizadas? | Pendiente; relevante para H5, no bloquea H1 |
| Q11 | ¿Qué fuente proporciona el ID esperado: orden, estación, PLC/MES u otra? | Pendiente; necesaria para comparación de producción |
| Q12 | ¿Cuál es el contrato completo de la interfaz de la sección 7? | No aportado; no inventar API ni formato oficial |
| Q13 | ¿Qué cantidad aprobada, orientación y separación exige la entrega? | Pendiente; H6 |
| Q14 | ¿Cómo se conoce destino preparado, bloqueado, lleno o desalineado? | Pendiente; no asumir que una imagen sustituye señales de estación |
| Q15 | ¿Hay que plegar cartón o sólo retirarlo, y dónde se deposita? | Pendiente; la lámina remite al procedimiento definido |
| Q16 | ¿Qué apoyos manuales se admiten durante evaluación? | Cliente exige documentarlos; condiciones concretas pendientes |
| Q17 | ¿Se conserva la foto real de fábrica y la foto del robot? | Sí; originales diferenciados y hashes en el manifiesto |
| Q18 | ¿Dónde debe ejecutarse el reconocimiento final? | Respondido: dentro del robot, en Vision; la nube para preparación/entrenamiento |
| Q19 | ¿Se comprobó el runtime del robot real? | Sí: AGX Orin/L4T36.3/CUDA12.2/TensorRT8.6.2.3 y cuatro canales de imágenes; informe enlazado en sección7 |
| Q20 | ¿Qué modelo cumple precisión y latencia coexistiendo con servicios? | Pendiente de artefacto app2 y benchmark; no deducirlo del inventario |

Las Q01–Q05 no impiden organizar imágenes y probar detección de instancias;
sí impiden declarar identificación de material conforme. Q10–Q16 se mantienen
para fases posteriores y no deben bloquear innecesariamente H1.

## 9. Preparación de cámara y punto de reanudación

Se añadió al wrapper existente una comprobación de cabeza compatible con
abrazaderas y SPS. No es parte del detector:

```bash
./scripts/cruzr_blue_workbin_cycle.sh --check-head
```

El último check de esta intervención encontró Motion ocupado por la tarea
PICO v4 UUID27318de6-c1a6-4d86-a9c5-6f8b127df3da. El PC estaba STOP; esto no
termina la tarea nativa. Posteriormente el operador informó de encuadre útil
y las imágenes lo confirmaron. No inferir de esa secuencia una postura actual,
recuperación validada o permiso para cancelar/mover. Consultar
[el estado PICO](../teleoperation/CRUZR_S2_PICO_TELEOP_SOURCE_OF_TRUTH.md).

**Para retomar:** abrir este plan y el índice de fotos; verificar el archivo de
referencia; elegir/etiquetar instancias del encuadre útil y preparar un pequeño
conjunto de escenas variadas. Trabajar primero offline, guardar resultados y
actualizar la tabla de hitos/preguntas. No empezar por agarre, navegación o VLA.

## 10. Historial inicial

- Usuario solicita distinguir pieza de coche de otras parecidas.
- Se comprueban cámaras; primer encuadre insuficiente y posterior encuadre útil.
- Se conservan imágenes y se propone segmentación pequeña con medición real.
- Usuario aporta lámina del proceso de fábrica y aclaración ITR/OTR.
- Usuario asigna el nombre **app2** y pide conservar fotos, plan y preguntas.
- Se archivan originales, manifiesto, paquete y documentación. No se instala
  detector, no se entrena y no se envían movimientos en esta documentación.
- Usuario concreta ejecución dentro del robot; se comparan plataformas de nube.
- Se verifica Vision real y recepción de cuatro canales; se descarta asumir
  compatibilidad del contenedor actual Jetson6.2 con la pila CUDA12.2/TRT8.6.
  Roboflow nube + ONNX + ejecutor propio en Vision es la ruta propuesta;
  selección y rendimiento del modelo continúan pendientes de prueba.
