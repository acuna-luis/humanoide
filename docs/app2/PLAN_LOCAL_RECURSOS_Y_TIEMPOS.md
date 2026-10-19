# app2 — plan completamente local, recursos y tiempos

**ID:** APP2-LOCAL-20261019. **Fecha/zona:** 19-10-2026, Europe/Madrid.
**Estado:** inventarios VERIFICADOS; CVAT y entorno de entrenamiento GPU
instalados/verificados en servidor. Dataset, entrenamiento de referencias y
despliegue app2 en robot pendientes.

**Trabajo desde ahora:** [guía de acceso/relevo](RETOMAR_APP2.md) y
[pasos de datos/entrenamiento](DATOS_Y_ENTRENAMIENTO.md). La
[rama publicada `vision-reconoce`](RETOMAR_APP2.md#recuperar-el-código-y-las-fotografías)
contiene el código y la documentación tras el commit/push solicitado. La
[copia privada de relevo](BACKUP_Y_MIGRACION.md) conserva una instantánea
anterior. Las fotos, evidencias, modelos, base de datos CVAT y credenciales
siguen fuera de Git; recuperarlos aparte cuando sean necesarios.

**Intervención posterior completada:** el usuario autoriza instalar el servidor.
[Estado y acceso de la instalación](SERVIDOR_LOCAL_INSTALACION.md). Ese informe
actualiza el estado operativo; los inventarios y presupuestos que siguen
corresponden a la planificación previa, sin convertir estimaciones en medidas.

## 1. Arquitectura elegida

Se adopta un flujo local y sin créditos de entrenamiento:

1. **CVAT Community:** etiquetado de imágenes con contornos por pieza.
2. **RF-DETR Seg Nano:** entrenamiento local con GPU propia y datos COCO.
3. **ONNX → TensorRT 8.6:** ejecución del reconocimiento dentro de Vision.

La **opción elegida para preparar el piloto** es poner CVAT, dataset y
entrenamiento en el servidor ofrecido por el usuario, accesible mediante
`ssh -p 2649 luisacuna@192.168.1.43`.
El PC accede al editor desde el navegador. El robot ejecuta la inferencia.
La alternativa es hacer el trabajo de preparación/entrenamiento en el PC actual.
El modelo final debe seguir siendo pequeño aunque el servidor sea potente.

El acceso SSH y el hardware del servidor se comprobaron el 19-10-2026,
12:11 Europe/Madrid. La ruta del PC usa `wlo1`, no el Ethernet del robot.
El inventario no determina su ubicación física. No se han trasladado
fotografías al servidor ni instalado herramientas durante esta consulta.

Se necesitarán descargas públicas iniciales de código, paquetes, imágenes y
pesos preentrenados. Después se verificará el flujo sin salida a Internet;
las fotografías y anotaciones se mantendrán en infraestructura propia.
Sin suscripciones/créditos de las herramientas seleccionadas; siguen existiendo
el coste del hardware, electricidad, almacenamiento y tiempo de trabajo.

## 2. Equipos observados y límite actual

| Equipo | Lectura o estado | Implicación |
|---|---|---|
| PC, CPU | Intel Core i7-14700HX, 20 núcleos/28 CPU lógicas | Adecuado para intentar el piloto; no se ha medido rendimiento de entrenamiento |
| PC, RAM | Clase 32 GB; ~31GiB utilizables y ~19GiB disponibles en captura | Probar CVAT y entrenamiento, evitando competencia innecesaria |
| PC, GPU | RTX 4070 Laptop, 8188 MiB; ~15MiB usados en captura | Empezar por Nano, resolución y batch pequeños; no garantiza que cualquier configuración quepa |
| PC, sistema | Ubuntu24.04.5,Python3.12.3,driver580.178.04 | Preparar entorno aislado con versiones compatibles, sin cambiar Python/driver del sistema |
| PC, Docker | Engine29.8.1,Compose5.5.1; runtime nvidia registrado | Existencia verificada; ejecución CUDA del entorno de entrenamiento pendiente |
| PC, disco | Un único NVMe montado; ~46GiB libres,95% ocupado | Ajustado para instalar y comparar varios entornos/modelos |
| PC, imágenes CVAT | No aparecen en el filtro cvat/* | No asumir que la descarga/instalación ya está hecha |
| Servidor, CPU | AMD Ryzen Threadripper PRO 5975WX, 32 núcleos/64 CPU lógicas, x86_64 | Margen amplio para preparación; empezar con 4–8 workers, sin monopolizar hilos |
| Servidor, RAM | 503,51 GiB utilizables;496,76 GiB disponibles en captura | Muy por encima del presupuesto inicial; no hace falta ampliar RAM |
| Servidor, GPU | NVIDIA RTX 6000 Ada Generation, 49140 MiB totales; 5500 MiB usados | Clase 48 GB;~42,6 GiB de VRAM libres en ese instante, compartida con otras cargas |
| Servidor, sistema | Ubuntu24.04.5,Python3.12.3,driver580.178.04 | Entorno aislado instalado posteriormente; driver del host conservado |
| Servidor, Docker | Engine29.8.1,Compose5.5.1; daemon accesible | Acceso GPU desde contenedor verificado; CVAT instalado |
| Servidor, raíz y /home | Volumen de~98GiB,77,71GiB disponibles | Evitar guardar aquí datasets/checkpoints crecientes |
| Servidor, SSD de Docker | Samsung 990 PRO 2 TB, montaje /var/lib/docker;~1,65TiB libres | Destino preferido de volúmenes para datos/entornos, sin editar internamente Docker |
| Robot, última lectura del día | AGX Orin 64 GB; CUDA 12.2/TRT 8.6.2.3; MemAvailable ~11,4 GiB | Sólo inferencia; comparte GPU con servicios existentes |

El inventario de Vision procede de la [inspección real anterior](VERIFICACION_ROBOT_Y_ELECCION_VISION.md),
no de una nueva conexión al robot en esta intervención. La GPU del PC tiene
memoria dedicada; la del Orin comparte RAM del sistema. No comparar ambas cifras
como si fueran reservas equivalentes.

## 3. Requisitos prácticos del servidor

Son **presupuestos de ingeniería para este proyecto**, no mínimos certificados
por CVAT/RF-DETR. El consumo exacto se decide con un piloto medido.

| Recurso | Para intentar un piloto pequeño | Recomendación de trabajo |
|---|---|---|
| GPU | NVIDIA CUDA con 8 GB; Nano y ajustes de memoria | Una GPU NVIDIA con 16–24 GB; preferible 24 GB si está disponible |
| RAM del sistema | 32GB, con margen para procesos activos | 64 GB para CVAT, preparación y entrenamiento |
| CPU | 8 núcleos razonablemente actuales | 8–16 núcleos con buen rendimiento por núcleo y SSD rápido |
| Disco libre de proyecto | ~50GiB, con retención controlada y margen adicional del sistema | 80–100GiB para comenzar; 200 GiB libres si se amplían tomas/experimentos |
| Disco y conexión | SSD; acceso privado al servidor | NVMe/SSD y Ethernet para transferir imágenes/modelos |

Más VRAM permite aumentar batch o resolución; **no determina por sí sola la
velocidad**. Además de VRAM, influyen la arquitectura y capacidad de cálculo de la GPU. Una CPU grande sin GPU CUDA no sustituye
la aceleración necesaria para un entrenamiento práctico de este modelo.
No hace falta plantear varias GPU para la primera etapa. El servidor leído
supera el presupuesto de GPU/RAM/CPU; no se justifica comprar otro para el
piloto. Esto no garantiza mayor precisión ni un número concreto de FPS en Orin.

**Reserva propuesta en el servidor:** 200 GiB del SSD grande para app2,
64 GB de RAM como presupuesto inicial de servicios/trabajo y una GPU disponible
durante el entrenamiento. No son cuotas ya aplicadas. Usar volúmenes Docker
con nombres propios para dataset/resultados y volúmenes de CVAT, que quedarán
en el SSD del DockerRootDir observado. No manipular sus directorios internos
manualmente. Si se prefieren rutas de host, descubrir y acordar primero una
ruta del disco grande: `/home/luisacuna` pertenece al volumen pequeño.
No emplear almacenamiento de otros proyectos ni detener sus procesos.

En el PC con 46 GiB libres, no desplegar todo sin revisar el presupuesto. Las
opciones son reservar más espacio interno o usar almacenamiento del servidor/
un SSD externo. Poner sólo las fotografías en otro disco no cambia dónde guarda
Docker sus capas: actualmente `/var/lib/docker` está en la misma raíz del PC.
No se ha borrado nada ni se han movido Docker, datasets o evidencias existentes.

## 4. Presupuesto de disco

Estimación para un usuario, 200–500 imágenes seleccionadas, un modelo pequeño
y pocas ejecuciones conservadas. No incluye grabar vídeo continuo o ROSbags
extensos. La variación depende de versiones, compresión y retención.

| Concepto | Presupuesto orientativo |
|---|---|
| CVAT: imágenes Docker, volúmenes y base de datos inicial | 10–20GiB |
| Entorno RF-DETR/PyTorch/CUDA de entrenamiento | 10–20GiB |
| Imágenes originales, copias de trabajo y exportaciones COCO | 3–10GiB |
| Checkpoints y resultados de unas pocas pruebas | 5–15GiB |
| Exportaciones ONNX/engine y validación | 2–5GiB |
| Cachés y temporales | 5–10GiB |
| Reserva libre para sistema y crecimiento | 20GiB o más |

El subtotal de trabajo oscila aproximadamente entre 35 y 80 GiB; con reserva,
la planificación cómoda es **80–100GiB libres**. Las categorías son un
presupuesto conjunto: si se usan 10 GiB de CVAT y 20 GiB de entrenamiento, no se
presupuestan además dos copias completas del mismo entorno sin necesidad.

Los PNG originales observados alcanzan varios MB por foto: calcular el tamaño
con la media de un lote real y multiplicar por originales+trabajo+backups.
Guardar checkpoints seleccionados, no todas las épocas indefinidamente.
Los artefactos y datos permanecerán fuera de Git, con versiones y SHA256.

Para el robot, reservar provisionalmente **10–20GiB de disco adicional** para
imagen app2, exportaciones y caché de compilación; es una estimación, no el
tamaño del modelo solo. Buscar un consumo adicional en ejecución de **2–4GiB
de RAM unificada como objetivo inicial**, que deberá medirse. Compilar un engine
puede requerir un pico mayor: limitar workspace y comprobar coexistencia.
No prometer que ese objetivo se cumplirá ni utilizar la RAM total como libre.

## 5. Configuración inicial de entrenamiento

Primera versión candidata: **rfdetr 1.11.2**, a fijar junto con Python/PyTorch
y sus dependencias después de comprobar la instalación. La documentación
latest puede describir una versión de desarrollo; conservar configuración y
versiones efectivamente utilizadas. El entorno de PC/servidor no se copia al
Orin: se exporta el modelo y se prepara otro ejecutor ARM64.

Empezar con RF-DETR **Seg Nano**, `resolution=312`, `multi_scale="off"`,
`amp_dtype="auto"` y `batch_size="auto"`, registrando batch y acumulación
efectivamente utilizados. Desactivar multi_scale hace que este piloto mida
312×312 fijo; el valor nominal solo no evita las escalas variables por defecto.
En el portátil, batch 1 es una alternativa si el ajuste automático no cabe.
La entrada 312 es para verificar memoria y establecer una referencia: si borra
los rasgos que distinguen referencias, habrá que aumentar resolución o usar
un recorte con más detalle. Nano requiere dimensiones compatibles con su
divisor 12; no elegir dimensiones arbitrarias. La VRAM adicional del servidor
permite probar más detalle, manteniendo como criterio la ejecución final en Orin.

Ejecutar 2–5 épocas de prueba antes de un entrenamiento largo. Medir:
VRAM máxima, RAM, tiempo por época, tiempo de validación y tamaño del checkpoint.
Si falla por memoria: reducir batch, cerrar únicamente cargas propias no
necesarias o usar el servidor; después revisar resolución/checkpointing. No
degradar la identidad de referencia sólo para conseguir que el proceso termine.

La instalación posterior verificó RF-DETR/CUDA en el servidor mediante
inferencia y un paso de entrenamiento sintético sin red. **El entrenamiento
de referencias reales sigue pendiente**. Tampoco se ha medido
que el entrenamiento quepa en los 8 GB del portátil. No producir un engine
TensorRT en RTX 6000 para copiarlo como si fuera portable a Orin/TRT 8.6:
exportar ONNX y compilar/validar allí el grafo exacto.

## 6. Fases y entregables

| Fase | Trabajo | Resultado para continuar |
|---|---|---|
| 0. Confirmar servidor y almacenamiento | Inventario y volúmenes propios en SSD grande preparados | Recursos suficientes;200GiB de presupuesto, sin cuota aplicada |
| 1. Preparar herramientas | CVAT local, entorno RF-DETR separado, pesos/dependencias y caché instalados | Acceso privado, GPU y smokes verificados; versiones registradas |
| 2. Piloto de datos | 30–50 escenas distintas, piezas aisladas/agrupadas, vacíos y confundibles | Clases verificadas o provisionales claras; imágenes originales conservadas |
| 3. Etiquetar y revisar | Un contorno por pieza visible; exportar COCO de instancias | Máscaras/clases correctas y particiones sin fuga entre sesiones |
| 4. Entrenar en pequeño | Prueba de memoria y primer ajuste; loggers locales | Checkpoint reproducible y medidas de recursos/tiempo |
| 5. Evaluar y ampliar | Imágenes reservadas, errores, desconocidos y referencias parecidas | Decidir si hacen falta mejores imágenes/etiquetas o más ejemplos |
| 6. Exportar y probar en Vision | ONNX, engine para TRT8.6, adaptador de imágenes SHM, sólo percepción | Paridad de máscaras/clases, latencia/memoria y coexistencia medidas |

El piloto permite comprobar el flujo, no certificar precisión industrial.
Después ampliar orientativamente a 200–500 imágenes diversas según errores,
con unidades y sesiones reservadas. Acordar falsa aceptación, rechazo y latencia
antes de declarar identificación conforme. Pose 3D, agarre y alimentación física
permanecen en las fases posteriores del [plan general](PLAN_Y_PREGUNTAS.md).

## 7. Tiempos para planificar

**Son estimaciones, no tiempos medidos ni compromiso de entrega.** Se supone
un usuario, instalación accesible, referencias disponibles y un modelo pequeño.
Se separa trabajo humano de cálculo, que puede quedar ejecutándose sin atención.

| Trabajo | Reserva orientativa |
|---|---|
| Preparación CVAT/entorno y comprobaciones iniciales | 1–3h de trabajo, más descargas; incidencias de drivers pueden ampliar |
| Captura de 30–50 escenas variadas | 0,5–1,5h, con preparación de piezas y referencias |
| Etiquetado/revisión de ese piloto | 2–6h según piezas por imagen y detalle |
| Prueba corta de memoria/tiempos | 15–45min como reserva inicial, a sustituir por la medición |
| Primer entrenamiento del piloto | 1–4h de cálculo orientativas |
| Entrenamiento de 200–500 imágenes, 50–100 épocas | Reservar 2–8 h por ejecución como hipótesis; reestimar con el piloto |
| Evaluación y análisis de errores | 1–3h de trabajo por ronda |
| Integración inicial de percepción en Vision | 1–3 jornadas adicionales si exportación/runtime son compatibles; incompatibilidades pueden ampliar |

La RTX 6000 Ada mejora especialmente el margen de VRAM respecto al portátil;
no reduce automáticamente captura o anotación. No se ha ejecutado el mismo
entrenamiento en ambos equipos: no se presupone una aceleración de 2x, 5x u
otra cifra. Las ventanas de 1–4 h y 2–8 h son reservas provisionales, no una
predicción medida de esta GPU. Sustituirlas tras la prueba corta.

Para recalcular GPU, cronometrar épocas estables con la misma resolución,
batch y frecuencia de validación. Por ejemplo: 90 s/época × 100 épocas = 2,5 h;
añadir evaluación final/exportación y un margen propio. No aplicar esa cifra
como benchmark a la GPU actual sin medirla.

Para anotación, usar:

```text
horas = imágenes × piezas_por_imagen × segundos_por_contorno / 3600
```

Ejemplo: 300 imágenes × 8 piezas × 45 s = **30 h**, antes de revisar/corregir.
Una bandeja con muchas piezas hace que el etiquetado domine el calendario.
Tras el primer modelo se puede estudiar preetiquetado local y corrección;
no se presupone su ahorro antes de comprobarlo.

Objetivo de organización: **1–2 jornadas de trabajo para un primer piloto en
PC/servidor**, sujeto a esos supuestos; luego integración en Vision. Un conjunto
representativo de 200–500 escenas puede requerir varias jornadas adicionales
de anotación. No es un plazo del ciclo de agarre ni garantía de producción.

## 8. Datos locales, respaldo y comprobación sin nube

CVAT Community es la edición gratuita autogestionada. Sus polígonos/máscaras
se exportan en COCO; verificar que cada instancia conserva su segmentación y
que los nombres de imágenes coinciden al preparar train/valid/test.
RF-DETR entrena con dataset local, sin usar el servicio de entrenamiento cloud.

Usar almacenamiento local, acceso privado al editor y cuentas locales; evitar
conectar almacenamiento cloud, APIs de anotación remotas o loggers externos.
Preparar pesos preentrenados y dependencias antes de comprobar el modo offline.
Que una dependencia incluya el SDK Roboflow no significa que este flujo deba
enviar imágenes: verificar tráfico y ejecución sin salida a Internet.
No se ha certificado ausencia de telemetría de todo el stack.

Mantener backups de originales, anotaciones, base de datos/volúmenes CVAT y
modelos seleccionados. Un tar en el mismo disco no protege de la pérdida del
disco; disponer de copia en otro almacenamiento propio. No reutilizar acciones
de limpieza global de Docker ni eliminar evidencias para hacer hueco por defecto.

Conservar licencias de las versiones/pesos. La familia RF-DETR Seg consultada
se publica bajo Apache 2.0; no extender esa afirmación a todos los modelos de
Roboflow o a variantes de detección con otras condiciones.

## 9. Estado y reanudación

Hecho: plan/presupuesto, inventarios y posterior instalación de CVAT y entorno
GPU en servidor; inferencia, entrenamiento sintético y ONNX/ORTCPU verificados.
[Informe, acceso y recetas](SERVIDOR_LOCAL_INSTALACION.md).
Pendiente: dataset y entrenamiento reales, exportación/paridad del modelo final,
compatibilidad y medición en robot. No se ha movido o cambiado el robot ni
creado una cuenta cloud. Los comandos siguientes son de consulta, no instalación.

Inventario y respaldo privados:
`../Humanoide-vla-evidence/20261019T100559Z_APP2_LOCAL_PLAN/`.
Comprobaciones de sólo lectura repetibles:

```bash
free -h
df -h . /var/lib/docker
nvidia-smi --query-gpu=name,memory.total,memory.used,driver_version --format=csv,noheader
docker compose version

# Servidor; consultas de lectura, sin instalar ni entrenar:
ssh -p 2649 luisacuna@192.168.1.43 'free -h'
ssh -p 2649 luisacuna@192.168.1.43 'df -h /home /var/lib/docker'
ssh -p 2649 luisacuna@192.168.1.43 'nvidia-smi --query-gpu=name,memory.total,memory.used,driver_version --format=csv,noheader'
```

**Siguiente paso:** abrir CVAT del servidor, capturar/etiquetar el piloto y
preparar sus particiones COCO. El entorno de entrenamiento ya está separado.
Hasta medirlo, los tiempos y consumos de
entrenamiento son hipótesis. Este plan sustituye como decisión vigente la
propuesta anterior de usar entrenamiento en nube, conservada como historia.

Fuentes primarias consultadas el 19-10-2026:

- [CVAT Community](https://docs.cvat.ai/docs/products/community/).
- [Formato COCO de CVAT](https://docs.cvat.ai/docs/dataset_management/formats/format-coco/).
- [Instalación CVAT](https://docs.cvat.ai/docs/administration/community/basics/installation/).
- [RF-DETR 1.11.2](https://github.com/roboflow/rf-detr/tree/1.11.2).
- [Parámetros de entrenamiento versionados](https://github.com/roboflow/rf-detr/blob/1.11.2/docs/learn/train/training-parameters.md).
- [Configuración RF-DETR 1.11.2, escalas y precisión mixta](https://github.com/roboflow/rf-detr/blob/1.11.2/src/rfdetr/config.py).
- [Entrenamiento local](https://rfdetr.roboflow.com/latest/learn/train/).
- [Exportación TensorRT](https://rfdetr.roboflow.com/latest/exports/tensorrt/).

Las fuentes justifican funcionalidades y parámetros; los presupuestos de RAM,
disco y horas son estimaciones propias pendientes del piloto.
