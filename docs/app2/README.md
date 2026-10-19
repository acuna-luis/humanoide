# app2 — identificación visual y alimentación de piezas de dirección

Nombre acordado con el usuario el **19-10-2026**, Europe/Madrid.
Fase actual: **preparación del reconocimiento visual, sin manipulación**.

- **[Primer lote real de piezas: CVAT y cómo empezar a anotar](PILOTO_PIEZAS_REALES.md).**
- [Especificación completa rev001: APP2/ITR, requisitos y fechas](ESPECIFICACION_REV001.md).
- [Recorrido local reproducible y validación de infraestructura](VALIDACION_FLUJO_LOCAL.md).
- **[Empezar o retomar desde otro PC/agente](RETOMAR_APP2.md).**
- [Datos, etiquetado, splits y entrenamiento: comandos y límites actuales](DATOS_Y_ENTRENAMIENTO.md).
- [Paquete privado de relevo, backup y migración](BACKUP_Y_MIGRACION.md).
- [Plan vigente: todo local, servidor, disco, memoria y tiempos](PLAN_LOCAL_RECURSOS_Y_TIEMPOS.md).
- [Instalación del servidor: estado, acceso al editor y verificaciones](SERVIDOR_LOCAL_INSTALACION.md).
- [Plan, estado y preguntas pendientes](PLAN_Y_PREGUNTAS.md).
- [Verificación del robot real y elección de visión](VERIFICACION_ROBOT_Y_ELECCION_VISION.md).
- [Fotografías originales y archivo de fábrica](FOTOS_Y_FUENTES.md).
- [Requisitos del cliente e interpretación de ITR/OTR](REQUISITOS_CLIENTE.md).
- [Manifiesto de imágenes y checksums](manifest_fotos.json).

Las imágenes originales están en el archivo privado externo al repositorio,
enlazado en el índice de fotografías. Hay copias de las cámaras del robot y
de la lámina aportada con fotografías de la fábrica real. No confundirlas.

No existe todavía un detector app2 entrenado ni una operación de agarre app2
validada. Las comprobaciones de cabeza/teleoperación son herramientas de
preparación, no el reconocimiento de las piezas.

Decisión vigente: CVAT Community y entrenamiento RF-DETR Seg Nano en el
servidor consultado (RTX6000 Ada48GB); inferencia final en Vision/Orin.
La comparación anterior de plataformas cloud se conserva como historia.
CVAT y el entorno GPU ya están instalados y verificados en el servidor,
incluida exportación ONNX de prueba. Dataset/entrenamiento de referencias y
compatibilidad del modelo final con TensorRT8.6 todavía pendientes.
