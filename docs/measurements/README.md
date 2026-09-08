# Guía de medición de las abrazaderas

Fecha: 2026-09-08. Estado: VERIFICADO como herramienta visual local;
geometría real y recuperación PICO→HOME PENDIENTES.

Abra `abrazadera_mediciones_3d.html` en un navegador. No necesita servidor,
sin dependencias externas y sin conexión al robot.

1. Seleccione izquierda o derecha y una de las doce mediciones.
2. Arrastre el dibujo para girar, use la rueda para ampliar o las vistas predefinidas.
3. Registre medida, unidad, referencia, instrumento, incertidumbre y fotografía.
4. Descargue la ficha JSON antes de cerrar: los datos sólo permanecen en memoria.

Las entradas no cambian el dibujo. El JSON contiene ambas fichas y conserva
`geometry_validated:false` y `motion_authorized:false`; no es una trayectoria.
No hay importador de fichas en esta versión.

## Fotografías con cinta

Con el aislamiento y la estabilidad resueltos por el técnico antes de acercarse,
tome por cada lado vistas general, frontal, lateral y posterior de las zonas
accesibles. No mueva el robot para conseguir las fotos.

Coloque la cinta extendida, legible y en el mismo plano de lo que se mide;
encuadre lo más perpendicular posible a ese plano. Identifique izquierda/derecha
y tres referencias comunes no alineadas P1/P2/P3 sobre piezas rígidas. Añada vistas
oblicuas solapadas para relacionar caras. No tape contornos ni puntos de medida.
Una escala en otro plano introduce error de perspectiva. Las fotografías permiten
estimar cotas visibles, pero no prueban superficies ocultas, holguras mínimas ni
la transformación al marco cinemático del robot. Registre lo desconocido.

## Alcance y comprobación

La placa azul representa dimensiones nominales declaradas de 70 × 100 × 36 mm.
Sensor, soporte, patitas y muñeca son ilustrativos; su colocación no reproduce
el montaje real. O/X/Y/Z son referencias de trabajo que debe definir el técnico,
no ejes ROS. No usar el dibujo para recortar envolventes de colisión.

Verificado: sintaxis JavaScript con `node --check`; apertura y revisión visual
con Chrome headless; prueba de los doce paneles, independencia y conservación
en memoria de campos L/R y selección de vistas. Sin prueba de movimiento ni
cambios en robot/servicios. Para deshacer la herramienta basta retirar estos
archivos locales y sus referencias documentales.

Aclaración 2026-09-08: leyenda visible de O y ejes X/Y/Z; marcas fotográficas
renombradas P1/P2/P3 para distinguirlas de las longitudes A/B/C y T.

Actualización 2026-09-08: ocho cotas declaradas precargadas en L/R, sin asumir
confirmación en ninguno de los lados. Cada campo distingue pendiente, declarado
pendiente de confirmar e introducido pendiente de verificar. JSON v2 incluye
valores originales y estados, también para paneles que no se hayan abierto.

Cada campo incluye ahora definición, extremos/dirección cuando es una distancia,
ejemplo de texto y situación de partida. Los ejemplos no rellenan valores.
P1/P2/P3 piden identificar puntos físicos, no inventar coordenadas. El resumen
de pendientes distingue referencias, patitas, soporte, contacto y holguras.

La vista principal se reduce a cinco apartados por lado: posición del montaje,
orientación, límites completos, incertidumbre y evidencia/inspección. Referencia
objetivo L/R_sixforce_link pendiente de registro físico. Unidades explícitas:
mm, grados con convención o matriz de rotación sin unidades; conversión a metros
para el modelo robot. Las doce fichas están en un desplegable de apoyo opcional.
JSON v3 conserva la ficha mínima, su definición y las fichas detalladas; ningún
campo introducido valida automáticamente geometría ni movimiento. Una envolvente
conservadora puede rechazar recorridos válidos; entonces se refina con evidencia.
No existe aprobación universal de trayectorias mediante esta ficha estática.

Ejemplos numéricos: cinco bloques visibles separados de los datos introducidos,
exportados bajo illustrative_examples con usable_for_motion=false. Los límites
descriptivos se derivan de dimensiones declaradas; traslación, rotación y error
son sólo ejemplos de formato. Las fotos 1/2.jpeg no permiten estimar esos valores
respecto al sensor. No rellenan campos ni cambian la geometría del dibujo.

Comparación didáctica: `orientacion_R_ejemplos.html` muestra identidad y giro de
+90 grados alrededor de Z con sensor fijo y cámara sincronizada. Se incrusta en
el apartado de orientación de la ficha: conservar ambos HTML en la misma carpeta
para ver la comparación integrada. Cada archivo funciona localmente sin red.
Los ejemplos son ficticios y no afectan las medidas ni la aprobación de rutas.
Verificados sintaxis JavaScript y renderizado visual en Chrome.

Comparador ampliado a cuatro vistas: identidad y giros independientes +90°
sobre X, Y y Z fijos del sensor. Todas comparten la cámara, con explicación de
la regla de mano derecha y de los cambios de dirección de las piezas.

Ficha mínima precargada con orientaciones bilaterales aproximadas confirmadas
cualitativamente por el técnico según usuario, dimensiones declaradas y evidencia.
Traslación/errores/límites en el nuevo marco siguen pendientes. Los datos se ven
antes de los ejemplos; exportación conserva estado de precarga y marca ediciones.

Corrección del renderer principal: placa y patitas giradas por lado mediante
Ry(±90°), de modo que el eje de fijación queda paralelo al plano de almohadilla.
Los desplazamientos usados para dibujar siguen siendo arbitrarios, sin valor
metrológico, y no se copian a las fichas. 70/100 se denominan lado corto/largo;
no reutilizar asignaciones antiguas ancho/alto o flechas A/B/C/T sin registro.
