# Seguimiento de solicitudes a UBTECH — Cruzr S2

Actualizado: 2026-08-11<br>
Fuente: historial del grupo de soporte aportado por Luis. Este documento distingue entre lo solicitado, lo respondido parcialmente y lo que todavía no consta como enviado. Las consultas realizadas por email deben incorporarse cuando se disponga de su texto o asunto exacto.

## Estados

- **Respondido:** existe una respuesta concreta suficiente para continuar.
- **Parcial:** hubo respuesta, pero no cubre todos los puntos solicitados o falta ejecutar/programar la asistencia ofrecida.
- **Pendiente de respuesta:** la pregunta consta en el chat y no aparece respuesta posterior.
- **No consta solicitado:** es una necesidad identificada, pero no aparece formulada explícitamente en el historial aportado.

## Solicitudes ya enviadas

| Tema | Solicitud realizada | Respuesta recibida | Estado | Acción siguiente |
|---|---|---|---|---|
| Soporte y formación inicial | UBTECH anunció ayuda para desembalaje, operación, prueba de elevación de cajas y posventa. | Viki presentó a Mr. Zhu y Lucio; posteriormente ofreció organizar una reunión online. No consta fecha ni sesión realizada. | **Parcial** | Pedir fecha, duración, asistentes y agenda de la sesión práctica. |
| SDK y herramientas | Se pidieron paquete de desarrollo, documentación, API, ejemplos, lenguajes soportados, simulador y herramientas de prueba. | Viki compartió una carpeta de Google Drive. No respondió expresamente qué lenguajes están soportados ni si existe simulador/herramienta oficial. | **Parcial** | No volver a pedir el paquete; pedir únicamente los elementos y aclaraciones que faltan. |
| Descarga y desembalaje | Se pidió el procedimiento aprobado, equipos, puntos de elevación, liberación de brazos/base, precauciones y supervisión técnica. | Se remitió el manual de producto y se ofreció una reunión online. No consta confirmación de supervisión ni respuesta separada a cada punto. | **Parcial** | Registrar si el desembalaje ya se completó; mantener pendiente la formación de operación/commissioning. |
| Aplicación móvil | Se preguntó si existe una aplicación de teléfono para usarlo como mando. | No consta respuesta. | **Pendiente de respuesta** | Reclamar confirmación expresa: nombre, Android/iOS, enlace oficial, versión y funciones. |
| Contraseña Wi-Fi | Se pidió la contraseña del hotspot del Cruzr S2. | Mr. Zhu respondió: `Ubtrobot` seguido de los cuatro dígitos que coinciden con el nombre Wi-Fi. | **Respondido** | Documentar el SSID y la contraseña concreta de esta unidad sin publicarlos externamente. |
| Usuario y contraseña web | Tras recibir la contraseña Wi-Fi se preguntó `user and pass?` para `http://192.168.11.3`. | Las credenciales ya están disponibles, según confirmación posterior de Luis. | **Respondido/resuelto** | No volver a solicitar las credenciales; documentar y cambiar la contraseña según la política interna. |
| Baterías/BMS | Se remitieron SOC, voltaje, corriente, temperatura, números de serie, diferencia de SOC, truncamiento de SN y diagnósticos; se pidieron criterio de parada/carga, SOC gobernante y necesidad de balance/calibración/firmware. | No consta respuesta. | **Pendiente de respuesta — crítica** | Solicitar respuesta escrita del responsable técnico/BMS y conservar las lecturas originales. |
| Documentación de conformidad | Se comunicó la ausencia de `Certificate of Conformity ×1` y `Factory Inspection Report ×1`. | No consta respuesta. | **Pendiente de respuesta** | Solicitar copias digitales, originales y correspondencia con el número de serie entregado. |
| Instalación de manos | Se pidió el SOP oficial de instalación y, si fuera posible, guía online durante el montaje y primer encendido. | No consta respuesta. | **Pendiente de respuesta — crítica** | No conectar las manos hasta recibir modelo/generación, izquierda/derecha, montaje, par, cableado, `HW_TYPE`, drivers y calibración. |

## Necesidades de Antonio que no constan todavía como preguntas explícitas

| Tema | Pregunta que debe enviarse a UBTECH | Motivo |
|---|---|---|
| Método óptimo de programación | ¿Cuál es el flujo oficial recomendado: web/no-code, skills, behavior trees, teleoperación, programación por demostración, VLA o SDK? | Evitar tratar una plataforma moderna como una colección de órdenes articulares manuales. |
| Enseñanza por demostración | ¿Puede el operador teleoperar con Pico/VR, Xsens, exoesqueleto o guantes, grabar una demostración y convertirla en una tarea reutilizable? | Esto es lo que Antonio denomina “enseñar” al robot. |
| Generalización de una demostración | ¿La tarea grabada sólo reproduce una trayectoria o puede localizar una caja que haya cambiado de posición y adaptar el agarre mediante visión/VLA? | Una reproducción de movimiento no equivale a una política adaptativa. |
| Pipeline de aprendizaje | ¿Cómo se convierte una grabación `.motion` en datos de entrenamiento LeRobot/VLA, cómo se etiqueta y dónde se realiza el fine-tuning? | El SDK contiene grabación/reproducción y un paquete VLA, pero no documenta el puente completo entre ambos. |
| Hardware de teleoperación | ¿Qué equipos, modelos, licencias y calibración se requieren y cuáles vienen incluidos en la compra? | El SDK menciona Pico/VR, Xsens y otros dispositivos, pero no confirma el kit suministrado. |
| Voz | ¿Qué comandos de voz están disponibles, cómo se activan y qué idiomas admite el ASR/TTS y los avisos del sistema? | Sólo se ha documentado la palabra de activación `Walker, Walker`; el TTS español instalado funciona mal. |
| Aplicación/web | ¿Existe una interfaz oficial de operación y programación de bajo código, además de la aplicación móvil ya preguntada? | La web actual exige credenciales que todavía no se han facilitado. |
| Reconocimiento de objetos | ¿Cómo se activa/configura el estimador de cajas u objetos, qué clases reconoce y cómo se enseña un objeto nuevo? | Hay componentes de visión instalados, pero no una demostración funcional end-to-end. |
| Pick and place adaptativo | Demostrar cómo enseñar o configurar “coger aquí y dejar allí” y qué ocurre si la caja cambia de posición. | Debe aclararse qué parte resuelve percepción, planificación, agarre y recuperación. |
| Cámaras | ¿Qué visor oficial permite ver todas las cámaras y consultar campo de visión, profundidad y calibración? | Los topics están disponibles, pero falta el flujo operativo destinado al usuario. |
| Navegación y obstáculos | ¿Cómo se crea/activa el mapa, se localiza el robot y se valida la evitación de obstáculos con los dos LiDAR? | Los sensores y servicios existen, pero no se ha hecho commissioning de navegación. |
| Recarga automática | ¿Está soportado el regreso autónomo al cargador, qué hardware requiere y cómo se configura/prueba? | El runtime contiene una acción de recarga, pero todavía no se ha validado. |

## Interpretación técnica de “programación por demostración”

El SDK documenta teleoperación de medio cuerpo mediante Pico/VR y funciones para grabar, reproducir y editar archivos `.motion`. Esto permite capturar y repetir una demostración y, por tanto, constituye una forma básica de programación por demostración.

No está demostrado que una grabación `.motion` enseñe automáticamente una tarea adaptable. Si la caja cambia de posición, una reproducción de trayectoria puede fallar. Para generalizar hacen falta percepción de la pose del objeto y una política/planificador que adapte el movimiento; alternativamente, un pipeline VLA entrenado con muchas demostraciones. El paquete incluye dataset, checkpoint y código de fine-tuning/inferencia, pero no explica cómo convertir las grabaciones de teleoperación en el dataset VLA ni cómo desplegar de forma soportada el resultado.

Esta distinción debe ser uno de los puntos principales de la reunión con UBTECH.

## Consulta previa por email confirmada por Luis

Por email se preguntó si el robot puede enseñarse mediante guantes o sensores, qué método de teleoperación/programación por demostración recomienda UBTECH y si el hardware necesario está incluido en el suministro. No se ha recibido una respuesta técnica completa. Antes de cerrar el seguimiento deberán añadirse al registro la fecha, destinatarios y asunto del correo original.
