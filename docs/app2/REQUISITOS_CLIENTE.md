# app2 — referencia del cliente y aclaración ITR/OTR

**Fuente:** lámina gráfica adjuntada por el usuario el 19-10-2026.
Se conserva el PNG original de 2189×630, sin reencodificar, en el
[archivo de fotografías](FOTOS_Y_FUENTES.md). Documento original, revisión y
sección 7 completa: pendientes de recibir. Lo siguiente es una transcripción
resumida en español, no un reemplazo del documento contractual completo.

## Requisito visible: ITR Material Feed and Empty Container Handling

El humanoide debe retirar componentes ITR de la caja suministrada, confirmar
identificación mediante visión integrada, alimentar el transportador o punto
designado y llevar el cartón vacío a la ubicación asignada para contenedores
vacíos. El apoyo manual se permite sólo durante evaluación de desarrollo si
queda documentado como condición de apoyo o excepción.

Secuencia descrita:

1. Confirmar material ITR correcto disponible y destino preparado para recibirlo.
2. Retirar piezas una a una o en cantidad aprobada, manteniendo orientación
   y evitando daño en superficies funcionales.
3. Colocar en orientación y espaciado requeridos para el proceso posterior.
4. Comprobar bloqueo, llenado o desalineación antes de añadir material.
5. Al vaciar la caja, plegarla o manejarla según el procedimiento definido
   y colocarla en el contenedor de vacíos asignado.
6. Registrar ciclo de reposición y anomalías para evaluar proceso y tarea.

## Identificación visual

Antes de cargar el transportador o presentación, comparar el material ID
esperado con el observado. Registrar en la interfaz de desarrollo de la sección 7:

- resultado de lectura;
- condición `no-read` o `misread`;
- número de reintentos;
- estado de excepción.

No se especifican en el fragmento OCR, QR, DataMatrix, modelo de visión,
protocolo de la interfaz ni objetivos cuantitativos de precisión/latencia.
Estas decisiones siguen abiertas y no se atribuyen al cliente.

## Fotografías de la fábrica real

Las cinco fotografías forman parte de la **lámina del cliente**, no de las
capturas de nuestro robot:

| Referencia descriptiva | Contenido visible |
|---|---|
| Fábrica F01 | Cartones sobre un carro amarillo junto a la línea |
| Fábrica F02 | Bandejas de cartón apiladas, abiertas y con separadores |
| Fábrica F03 | Vista superior de piezas alargadas organizadas en cartón; flecha roja |
| Fábrica F04 | Zona de alimentación junto a un transportador y otra bandeja con piezas |
| Fábrica F05 | Contenedor/estructura metálica con ruedas; finalidad concreta pendiente de confirmar |

El documento gráfico también muestra el título
*OTR Line-Side Replacement Station Replenishment* debajo del bloque de fotos.
Sólo se ve ese título, no su secuencia detallada. Puede comenzar un apartado
siguiente; no se considera que las fotos sean OTR sólo por su posición.

## Aclaración de nomenclatura aportada por el usuario

El usuario propone ITR como *Inner Tie Rod* y OTR como *Outer Tie Rod*, y explica
su relación con los extremos interior/exterior del conjunto de dirección.
La terminología sectorial está respaldada por
[Park et al.](https://onlinelibrary.wiley.com/doi/10.1155/2014/942645).
La página de [ZF sobre tie rods](https://www.zf.com/products/en/cars/products_65853.html)
se conserva como referencia general adicional aportada por el usuario.

La correspondencia de las piezas concretas fotografiadas con ITR es una
interpretación compatible con su forma y contexto, no una identificación de
material ID ni una confirmación de cliente. Tampoco se conocen lote/serie,
dimensiones, masa o superficies de agarre de estas unidades.
