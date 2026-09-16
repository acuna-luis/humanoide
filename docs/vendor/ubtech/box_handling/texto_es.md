# Procedimiento UBTECH — es

Extracción textual; figuras y formato en el DOCX saneado. Credenciales omitidas.

Cruzr S2 - Procedimiento de traslado de cajas

1. Creación del mapa y definición de puntos

    La creación del mapa y la definición de puntos se realizan desde la interfaz web.

[Credenciales omitidas / Access credentials redacted]

Entre en la pantalla de creación del mapa.

Recorra una vuelta completa por la zona mientras observa la pantalla de visualización. Mantenga el robot lo más bajo posible, sin que toque el suelo, y empújelo para realizar el escaneado.

Pulse «Guardar mapa».

Pulse «Gestión de mapas».

Defina un punto, registre la posición actual, introduzca su nombre y guárdelo. Repita la operación.

Para los nombres concretos de los puntos, consulte los siguientes escenarios de traslado de cajas.

2. Proceso de traslado de cajas con estantería dinámica

2.1 Preparación de los elementos:

Estantería dinámica ×1. Especificaciones: estantería de dos niveles. Nivel inferior: altura de 85 cm en un extremo, inclinación de 10° y regulación vertical de ±10 cm; el otro extremo tiene 99 cm de altura y puede desplazarse verticalmente y fijarse. Nivel superior: altura de 129 cm en un extremo (85 + 14 + 30), con una inclinación de 10°.

Cajas retornables ×9. Dimensiones: 60 × 40 × 23 cm.

Palés ×2. Dimensiones: 80 × 60 × 26 cm.

Mesa ×1. Altura: 91,5 cm.

2.2 Requisitos de los puntos

Como se muestra en la imagen, en get1 el centro de la rueda derecha queda a 59 cm del frente de la caja, y el lado derecho de la caja queda a 16 cm del lado derecho de la rueda.

put1: el centro de la rueda derecha queda a 90 cm de la parte inferior de la estantería y a 20 cm del centro de la pata niveladora derecha.

get2: el centro de la rueda derecha debe quedar alineado con el lado derecho de la caja situada a la izquierda de la pila, a una distancia de 51,5 respecto al frente de la caja.

put2: el centro de la rueda derecha queda a 87 cm de la parte inferior de la estantería y a 90 cm del centro de la pata niveladora derecha.

get3: el centro de la rueda derecha queda a 74 cm de la parte inferior de la estantería y a 57 cm del centro de la pata niveladora derecha.

put3: a 56 cm del frente de la mesa, alineado con el centro de la mesa.

El lado izquierdo de la caja debe quedar, como mínimo, a 164 cm de la estantería.

La mesa debe quedar, como mínimo, a 45 cm de la estantería.

La caja de get3 debe colocarse en el centro exacto del nivel superior de la estantería.

2.3 Descripción del proceso

La primera vez que se ejecute el proceso completo después de encender el robot, desplace el interruptor G del mando hacia la derecha y devuélvalo a su posición. Cuando el robot solicite configurar el mapa y anuncie que la localización de navegación se ha realizado correctamente, comenzará a ejecutar las siguientes tareas.

El robot navegará primero hasta el punto get1 para desapilar. Extraerá hacia la derecha la caja retornable situada arriba a la derecha hasta sujetarla de forma estable; después navegará hasta put1 y colocará la caja en la parte inferior derecha de la estantería dinámica.

A continuación, navegará hasta get2, sujetará directamente y levantará la caja retornable superior del lado izquierdo; después navegará hasta put2 y colocará la caja en la parte inferior derecha de la estantería dinámica.

Después navegará hasta get3, levantará la caja retornable situada en la parte superior de la estantería dinámica, navegará hasta put3 y colocará la caja sobre la mesa.

3. Proceso de traslado de cajas entre estanterías de dos niveles

3.1 Preparación de los elementos:

Estanterías de dos niveles ×2. Dimensiones: 150 cm de largo × 50 cm de ancho × 150 cm de alto. En la primera, el nivel inferior está a 70 cm y el superior a 125 cm; en la segunda, el nivel inferior está a 90 cm y el superior a 125 cm.

Cajas retornables ×2. Dimensiones: 40 × 30 × 23 cm.

3.2 Requisitos de los puntos

El robot debe quedar centrado frente a la estantería. La distancia desde el saliente inferior (centro de la banda anticolisión) hasta el centro de la estantería será:

get1: 12,5 cm

put1: 33,5 cm

get2: 12 cm

put2: 31 cm

Asegúrese de que el punto del robot quede exactamente centrado respecto a la estantería, sin desviación angular (controle el robot con el mando desde un punto alejado sobre la línea central perpendicular a la estantería hasta acercarlo a ella).

3.3 Descripción del proceso

La primera vez que se ejecute el proceso completo después de encender el robot, desplace el interruptor G del mando hacia la derecha y devuélvalo a su posición. Cuando el robot solicite configurar el mapa y anuncie que la localización de navegación se ha realizado correctamente, comenzará a ejecutar las siguientes tareas.

El robot navegará primero hasta get1, extraerá la caja retornable con carga del nivel inferior de la estantería 1; después navegará hasta put2 y colocará la caja en el nivel inferior de la estantería 2.

A continuación, navegará hasta get2, extraerá la caja retornable vacía del nivel superior de la estantería 2; después navegará hasta put1 y colocará la caja en el nivel superior de la estantería 1.

4. Precauciones

Inicie la creación del mapa una vez activado el control de movimiento.

Evite en lo posible acercarse a paredes blancas u otros entornos sin características visuales distintivas.

Cuando haya finalizado una ejecución y sea necesario continuar, desplace el interruptor E del mando hacia abajo y devuélvalo al centro; después desplace el interruptor G hacia la derecha y devuélvalo a su posición. El robot continuará la ejecución. Antes de continuar, vuelva a colocar las cajas retornables en sus posiciones iniciales.

Durante una tarea no es posible controlar el avance del robot con el mando. Pulse la tecla A: el robot navegará hasta el siguiente punto y detendrá la tarea. A partir de ese momento se puede tomar el control mediante el mando y desplazar el robot. Para volver a ejecutar la tarea será necesario reiniciar el robot.

[ADVERTENCIA ESPECIAL] No active el control de movimiento cuando el robot esté en la base de carga o conectado a un cargador por cable. Debe impedirse cualquier movimiento, ya que podría dañarse el hardware y quemarse los transistores MOSFET.
