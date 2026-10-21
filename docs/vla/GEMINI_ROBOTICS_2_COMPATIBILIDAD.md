# Gemini Robotics 2 y CRUZR S2 / Y1

**ID:** GR2-COMPAT-20261021. **Fecha:** 21-10-2026, Europe/Madrid.
**Alcance:** revisión documental y estática de repositorios públicos; seguimiento
de acceso mediante consultas de metadatos de Google. Ninguna instalación,
inferencia, transferencia de imágenes privadas, conexión al robot,
cambio de modo o movimiento. GR2 aquí significa Gemini Robotics 2 de Google;
no es el GR00T de NVIDIA que contiene el paquete VLA recibido de UBTECH.

## Dictamen de ingeniería

**INFERENCIA:** el S2 ofrece las interfaces necesarias para desarrollar una
integración con **Gemini Robotics ER 2 como orquestador**, manteniendo el control
de cada habilidad en los controladores locales. No exige sustituir el VLA ni
entrenar un modelo de movimiento para empezar a analizar imágenes y resultados.
Esto no demuestra todavía una integración ejecutada ni una manipulación nueva.

**PENDIENTE:** usar **GR2 VLA u On-Device 2** para generar movimientos nuevos
requiere acceso al modelo y adaptación de su contrato de observación/acción al
robot. La ruta pública de ajuste On-Device 2 no incluye S2/Y1. La ejecución
local en la Orin del S2 no queda demostrada por disponer de 64 GB de RAM.

Para **Y1**, la integración como orquestador es conceptualmente equivalente,
pero no se dispone aquí de su SDK ni de una unidad verificada. No asumir que
reutiliza los mensajes, controladores o configuración del S2. No confundir
Cruzr Y1 con Rainbow RB-Y1 ni CRUZR S2 con Walker S2.

## Evidencia pública revisada

| Elemento | Resultado y alcance |
|---|---|
| [Gemini Robotics SDK](https://github.com/google-deepmind/gemini-robotics-sdk/tree/26b49f1a15b96f1e65b05160f5b991d6167aba74) | VERIFICADO: revisión fijada en `26b49f1a15b96f1e65b05160f5b991d6167aba74`, commit 12-10-2026, versión `2.156.0`; árbol completo de 239 archivos descargado para lectura, sin ejecutar. |
| [CLI, selector v2](https://github.com/google-deepmind/gemini-robotics-sdk/blob/26b49f1a15b96f1e65b05160f5b991d6167aba74/safari_sdk/flywheel/flywheel_cli.py#L296) | VERIFICADO: `gemini_robotics_on_device_v2` usa `--embodiment` con `trossen`, `so101`, `dexmate`, `fr3_duo`. S2/Y1 no figuran. Modificar ese enum no demuestra aceptación por el servicio remoto ni un checkpoint adaptado. |
| [Entrenamiento](https://github.com/google-deepmind/gemini-robotics-sdk/blob/26b49f1a15b96f1e65b05160f5b991d6167aba74/safari_sdk/flywheel/flywheel_cli.py#L740) | VERIFICADO: el CLI construye la configuración y llama `orchestrator().startTraining(...)`. Tener un servidor GPU propio no convierte esa ruta en entrenamiento local autónomo. |
| [Serving On-Device 2](https://github.com/google-deepmind/gemini-robotics-sdk/blob/26b49f1a15b96f1e65b05160f5b991d6167aba74/safari_sdk/flywheel/flywheel_cli.py#L1077) | VERIFICADO: hay cliente LOCAL y CLI que prepara y lanza Docker. La imagen de serving, checkpoint, configuración y, cuando corresponde, licencia son artefactos externos. Contempla pesos cifrados o directorios sin cifrar, pero no los incluye. Tener el cliente/CLI no proporciona el modelo completo. |
| [Ejemplo de policy](https://github.com/google-deepmind/gemini-robotics-sdk/blob/26b49f1a15b96f1e65b05160f5b991d6167aba74/examples/model/gemini_robotics_policy_example.py#L41) | VERIFICADO: define ALOHA/Trossen y Franka Duo. Franka tiene dos vectores de siete articulaciones y dos valores de agarre; el ejemplo usa entradas simuladas. No es un driver físico S2. |
| [Interfaz de robot agente](https://github.com/google-deepmind/gemini-robotics-sdk/blob/26b49f1a15b96f1e65b05160f5b991d6167aba74/safari_sdk/agent/framework/embodiments/embodiment.py#L41) | VERIFICADO: permite implementar streams y herramientas propios. El adaptador concreto ALOHA usa FastAPI y vídeo. Esta extensibilidad sustenta la viabilidad de una capa S2; no adapta por sí sola la política de movimiento. |
| [Ejemplos públicos ER](https://github.com/google-gemini/robotics-samples/tree/c51cbab6e6efffff8738ecf9ce41ba85034d9654) | VERIFICADO estáticamente: commit `c51cbab6e6efffff8738ecf9ce41ba85034d9654`, 04-08-2026. Servidor con Spot/Tinybot/humano; `robot_url` apunta a un backend HTTP. Hace falta un adaptador Cruzr, no sólo cambiar la URL. Sin pesos de GR2 en este código cliente. |
| [REAF](https://github.com/google-deepmind/reaf) | VERIFICADO documentalmente: framework para entornos y adaptadores de acciones/observaciones. Puede estructurar un entorno nuevo; no aporta un checkpoint ni un controlador Cruzr. |

El SDK declara licencia Apache-2.0 para su código y advierte que no es un
producto con soporte oficial de Google. La mayoría de sus funciones requieren
el programa Trusted Testers. La licencia del código no establece por sí sola
las condiciones de uso, distribución o ajuste de los pesos restringidos.

En robotics-samples, [la interfaz de embodiment](https://github.com/google-gemini/robotics-samples/blob/c51cbab6e6efffff8738ecf9ce41ba85034d9654/live-api/agent/embodiment/base.py#L11)
separa streams, herramientas y `execute_action()`. El adaptador Spot usa una
cámara propia y herramientas fijas. Aunque hay un helper de OpenAPI, su
`initialize()` no lo activa en este commit: no se ha demostrado descubrimiento
automático para un robot nuevo. El
[servidor](https://github.com/google-gemini/robotics-samples/blob/c51cbab6e6efffff8738ecf9ce41ba85034d9654/live-api/agent/server.py#L693)
selecciona ER 2 streaming, mientras el README conserva un valor anterior;
contrastar el código y la API vigente antes de reproducir una receta.

## Tres productos con contratos diferentes

1. **ER 2:** servicio público en preview, con endpoints
   `gemini-robotics-er-2-preview` y `gemini-robotics-er-2-streaming-preview`.
   Analiza entradas y solicita herramientas definidas por la aplicación.
   [Documentación de la API](https://ai.google.dev/gemini-api/docs/robotics-overview).
2. **GR2 VLA:** modelo de visión/lenguaje a acciones, en private preview.
   El anuncio reserva VLA y On-Device a participantes de acceso anticipado.
   [Página VLA](https://deepmind.google/models/gemini-robotics/vla/) y
   [anuncio 30-07-2026](https://deepmind.google/blog/gemini-robotics-2-brings-whole-body-intelligence-to-robots/).
3. **On-Device 2:** ejecución local, distribución sólo a Trusted Testers.
   Su ficha declara limitaciones con muchos grados de libertad y evaluación
   principalmente sobre manipulación bimanual con el robot parado; los riesgos
   de movilidad/control corporal completo quedan fuera de su alcance actual.
   [Ficha del modelo](https://deepmind.google/models/model-cards/gemini-robotics-on-device-2/).

La guía streaming especifica JPEG de hasta 1 FPS, texto/audio y salida de texto
mediante WSS. Las acciones físicas se declaran como llamadas `BLOCKING` y se
devuelve su resultado. Eso encaja con ordenar habilidades y observar progreso;
no constituye un lazo de control articular de 200/500 Hz.
[Contrato streaming](https://ai.google.dev/gemini-api/docs/robotics-streaming).

## Qué se puede reutilizar del S2

El [inventario real de Vision del 19-10](../app2/VERIFICACION_ROBOT_Y_ELECCION_VISION.md)
documenta Jetson AGX Orin ARM64, clase 64 GB, CUDA 12.2, TensorRT 8.6 y cámaras
accesibles. Sólo había unos 11,4 GiB de MemAvailable en las instantáneas con
servicios activos: no son 64 GB libres ni una reserva para otro modelo.
No se ha repetido la consulta en esta intervención.

La [revisión del SDK](../reports/HUMANOID_SDK_TECHNICAL_REVIEW.md) y la
[guía de datos VLA](CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md) describen cámaras, estados,
controladores y separación Vision/Motion. También existen grabaciones y
reproducciones PICO, incluidas manos v4, cuya captura necesita conservar los
canales correctos. Son componentes aprovechables; no son automáticamente datos
de ajuste compatibles con GR2.

Hay un trabajo concreto de conversión: el inventario de Vision identifica
`shm_msgs/Image2m` BGR8 para RGB rectificada de cabeza y `Image6m` YUV422 para
la vista raw. No basta suscribirse suponiendo `sensor_msgs/Image` RGB. La
[captura completa v4](../teleoperation/PICO_MANOS_V4_20261015.md) conserva señales
de manos que el `.motion` nativo no representaba con movimiento de posición.
La sincronía entre RGB y estados/órdenes sigue necesitando validación; las
frecuencias nominales de los canales no la demuestran.

Una adaptación tendría que fijar nombres/orden/unidades de articulaciones,
frames, calibración, sincronización, acción absoluta o relativa, frecuencias,
consignas y retorno del efector. Las 14 acciones ALOHA significan seis ejes y
una pinza por lado; los 14 ejes de brazo S2 son siete por lado. Igual dimensión
no significa igual representación. Tampoco las abrazaderas pasivas equivalen
a pinzas accionadas o a manos v4.

No se localizó una especificación pública de inferencia On-Device 2 que confirme
ARM64/Orin, versión de CUDA, RAM mínima o latencia. El hardware TPU descrito en
la ficha corresponde al entrenamiento. PENDIENTE obtener runtime/modelo y medir
su compatibilidad y consumo antes de decidir si va en robot o servidor externo.

## Decisión y punto de reanudación

### GR2-ACCESS-20261021 — comprobación de acceso y requisitos actuales

**VERIFICADO por consultas HTTPS GET de metadatos:** las credenciales existentes
en `GOOGLE_API_KEY` y `GEMINI_API_KEY` obtuvieron HTTP 200 del catálogo
`generativelanguage.googleapis.com/v1beta/models`. Cada respuesta contenía 63
modelos sin siguiente página; los únicos nombres relacionados con robótica
eran `gemini-robotics-er-2-preview` y `gemini-robotics-er-2-streaming-preview`.
Esto verifica credenciales reconocidas y visibilidad del catálogo; no se probó
generación, cuotas, facturación ni inferencia streaming.

Con esas mismas credenciales, la consulta de descubrimiento a
`roboticsdeveloper.googleapis.com/$discovery/rest?version=v1` devolvió HTTP 403,
`PERMISSION_DENIED`, motivo `SERVICE_DISABLED`. Es una evidencia del servicio
deshabilitado para los proyectos asociados a las credenciales consultadas;
no demuestra rechazo al programa Trusted Testers. Habilitar una API tampoco
demostraría por sí solo permiso para un modelo restringido concreto.

No se encontraron credenciales Safari en las variables `API_KEY_SAFARI` o
`API_KEY_GEMINI`, ni en los archivos conocidos bajo `~/.config/safari_sdk` y
`/opt/safari_sdk`. El código distingue esas credenciales de las variables Gemini
ordinarias; ver [auth.py](https://github.com/google-deepmind/gemini-robotics-sdk/blob/26b49f1a15b96f1e65b05160f5b991d6167aba74/safari_sdk/auth.py#L98).
No se imprimieron ni conservaron claves, identificadores de proyecto o respuestas
privadas completas. No se habilitaron servicios ni solicitaron nuevos accesos.

**VERIFICADO localmente:** no se localizó adaptador Cruzr–Gemini, checkpoint GR2
o evaluación GR2 en `docs/scripts/config`. Los paquetes Safari/GDM/GenAI no
aparecen en los metadatos de los Python revisados (sistema, general-home y
vla-scene). Esto no inventaría otros equipos, contenedores o cuentas. El VLA y
las pruebas shadow existentes corresponden a NVIDIA GR00T del proveedor.

**Resultado:** no se puede dar por cumplida la condición conjunta de acceso al
modelo de acciones, adaptación Cruzr y evaluación del control. ER 2 está visible
en el catálogo, pero la integración y su inferencia siguen sin probarse. La
aprobación Trusted Testers y los artefactos de modelo/runtime permanecen
PENDIENTES, no rechazados ni disponibles por inferencia.

Evidencia saneada y copias antes/después:
`../Humanoide-vla-evidence/20261021T093438Z_GR2_ACCESS_METADATA/metadata-check.json`.
La comprobación no transmitió imágenes/instrucciones al modelo ni contactó con
el robot o servidor GPU. Sólo metadatos de servicios Google y lectura local.

**GR2-LOCAL-REQ-20261021 — aclaración vigente del usuario:** ejecución dentro del
Ubuntu del robot, sin API de Internet. La propuesta anterior de comenzar con
ER 2 por API no cumple este requisito y se descarta para este flujo. No se
presupone disponibilidad de un simulador ni se ha creado uno.

La variante Gemini candidata para esa arquitectura es **On-Device 2**, mediante
pesos y servidor de inferencia local compatibles con Vision/Orin ARM64. Su
paquete de ejecución y acceso siguen sin estar disponibles o acreditados en el
entorno revisado: no hay hoy una instalación completa comprobada que ejecutar.
El CLI sí contempla lanzar un contenedor local, pero eso no aporta los
artefactos restringidos ni demuestra compatibilidad Jetson.

**INFERENCIA de arquitectura, no implementación:** cámaras y estados S2 →
On-Device 2 en Vision → adaptador de acciones/supervisión → controladores Motion
existentes. La adaptación incluye formato y sincronía de entradas, contrato de
acciones, efector y, según soporte del checkpoint, ajuste con demostraciones de
esta cinemática. No es suficiente renombrar articulaciones ni instalar el SDK.

Cuando se disponga del modelo, la primera evaluación puede usar imágenes y
estados grabados para guardar sus salidas sin publicarlas a actuadores. Esto
es evaluación offline sobre grabaciones, no una simulación física ni prueba de
control real. Una orden de alto nivel no implementa por sí sola pose, trayectoria
y agarre de una pieza nueva. No se ha creado ni ejecutado el adaptador.

El plan APP2 local CVAT/RF-DETR permanece vigente. On-Device 2 sigue condicionado
a acceso, soporte del embodiment, runtime y evaluación. No se propone sustituir
la ejecución interna por un servidor externo o servicio cloud.

Las demostraciones de adaptación rápida de Google no permiten fijar aquí el
número necesario de ejemplos, coste, éxito o plazo para las piezas ITR, S2/Y1
y sus efectores. No se ha probado inferencia ni precisión ni control físico.
Las funciones de seguridad del robot tampoco quedan acreditadas por GR2.

## Evidencia, verificación y reversión

Evidencia privada reproducible:
`../Humanoide-vla-evidence/20261021T091906Z_GR2_SOURCE_REVIEW/`.
Incluye fuente fija, recibo por archivo, backup documental anterior y revisión.
Tar de fuente SDK: 682744 bytes, SHA256
`cb26d96628c8344ed39a6ea9020b7ee1aa4561fe0a02103a656684ee9b721115`.
Para contrastar los hallazgos usar los permalinks anteriores y ese commit;
una versión posterior exige repetir la revisión de CLI/runtime/embodiments.

Cambios de esta intervención: copia local de fuentes para auditoría y documentos
del repositorio. Seguimiento de acceso: consultas de metadatos registradas en la
evidencia GR2_ACCESS_METADATA. No hay paquetes, modelos, servicios, red o control instalados,
cargados o probados físicamente. Reversión documental selectiva desde `before/`,
preservando cualquier revisión posterior. Sin commit ni push.

## Prueba temporal posterior de nube — excepción autorizada

El usuario autorizó posteriormente probar ER 2 cloud y enviar una captura real
guardada. Dos inferencias completadas, incluida detección de8 instancias en9,401 s.
[Prueba, alcance y receta](GEMINI_ER2_PRUEBA_NUBE.md). Esto acredita acceso de
inferencia ER2, sin extenderlo a GR2 VLA/On-Device ni validar control físico.
La restricción de ejecución local para producción se conserva.
