# Resumen del proceso para reconocer y recoger una botella

**Cruzr S2 con manos v4 · 15 de octubre de 2026**

## Objetivo y punto de partida

Conseguir que el robot reconozca una botella, localice su posición sobre una mesa y adapte el movimiento de una mano para recogerla y dejarla en un punto B fijo.

Empezaremos con una botella conocida, ligera, de pie y preferentemente opaca. El robot y la mesa permanecerán inmóviles. La posición de la botella podrá variar dentro de una zona cuyo alcance se haya comprobado.

La teleoperación PICO y la reproducción geométrica de movimientos ya se probaron en vacío. Quedan por desarrollar y validar la percepción de botella, la localización 3D y su conexión con el agarre. Grabar un movimiento permite repetirlo; adaptarlo a una botella desplazada requiere esos pasos adicionales.

## Proceso de trabajo

| Fase | Qué haremos | Cuándo avanzar | Si falla |
|---|---|---|---|
| 1. Preparar y capturar | Comprobar conexiones y cámaras. Guardar una imagen en color, profundidad y calibración con el robot quieto. | Imagen legible y datos completos, con tiempos compatibles. | Revisar conexión, formato de imagen y recepción de calibración. |
| 2. Reconocer la botella | Probar en el PC un modelo preentrenado con COCO, que incluye la categoría botella. Obtener su contorno en la imagen. | Identifica la botella correcta y la distingue del fondo. | Revisar luz, encuadre y modelo. Si sigue fallando, etiquetar imágenes propias y ajustar el modelo. |
| 3. Medir en 3D | Combinar el contorno con profundidad y calibración para calcular la posición. | La medida coincide con referencias físicas en varias posiciones. | Corregir escala, alineación entre color y profundidad o calibración. Una botella transparente puede requerir otra estrategia. |
| 4. Relacionar cámara y mano | Verificar cómo se transforma la posición de cámara a coordenadas del robot y dónde está el punto de agarre de la mano v4. | Las posiciones calculadas son coherentes en toda la zona prevista. | Calibrar las transformaciones y la geometría de la mano. |
| 5. Preparar el movimiento | Definir acercamiento, agarre, elevación, transporte y retirada. Calcular articulaciones y revisar límites y colisiones. | El plan completo es alcanzable, continuo y libre de colisiones. | Cambiar orientación, aproximación o zona de trabajo y recalcular. |
| 6. Ensayar y agarrar | Probar primero el recorrido en vacío. Después sujetar una botella ligera, elevarla poco y apoyarla cerca. | Movimiento repetible y sujeción comprobada sin deformación ni deslizamiento. | Revisar geometría y control de cierre antes de transportar. |
| 7. Completar y validar | Llevar la botella a B, depositarla, abrir la mano y retirarse. Repetir desde posiciones nuevas. | Recogida y depósito estables, con fallos registrados y recuperables. | Volver a la fase que origina el error y repetir la evaluación. |

## Capturas y uso de PICO

Primero basta **una captura estática** para comprobar la detección. Si funciona, la campaña inicial propuesta será:

- **135 pares color y profundidad:** 9 posiciones × 3 giros × 5 capturas.
- **10 capturas sin botella:** comprobar falsas detecciones.
- **60 pares reservados:** 4 posiciones nuevas × 3 giros × 5 capturas para evaluar sin ajustar parámetros con ellas.

Son **205 pares de evaluación**, no un mínimo garantizado de entrenamiento. Solo ampliaremos y etiquetaremos datos de entrenamiento si el modelo inicial lo necesita.

PICO servirá para demostrar aproximaciones y agarres. Se grabarán brazos y manos con el grabador completo y, por separado, imágenes y calibración para relacionar la demostración con la escena. La trayectoria demostrada se revisará antes de adaptarla a nuevas posiciones.

## Condiciones para las pruebas físicas

Antes de cada movimiento se comprobarán postura, manos y objeto, batería, cargador, ambos paros, ruedas, modo de trabajo, recorrido libre y persona junto al paro. Solo habrá un mando activo.

El cierre deberá validarse para la botella elegida: no se presupone que la mano aplique automáticamente la fuerza mínima necesaria. Ante una interrupción con botella sujeta, se comprobará el estado físico antes de recuperar; no se reiniciará el ciclo ni se enviará HOME automáticamente.

## Primer paso y documentación de ejecución

El siguiente trabajo es **capturar una imagen real del robot y comprobar que el modelo delimita correctamente vuestra botella**, sin mover el robot. Después se abordará la medición 3D.

Los comandos Linux, Docker y ROS, los prototipos y los criterios detallados están en el [plan completo](plan_botella.md), también disponible en [PDF](plan_botella.pdf). La integración de agarre adaptativo sigue siendo trabajo de desarrollo; no existe todavía una orden única que ejecute todo el proceso.
