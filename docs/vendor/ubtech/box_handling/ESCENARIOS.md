# Escenarios del procedimiento de cajas

Fuente: apartados 2 y 3 de los DOCX chino/español de esta carpeta. Son
especificaciones del proveedor, no medidas nuevas del robot ni prueba de la
distribución usada para entrenar checkpoint-40000. Distancias en centímetros.

## 1. Estantería dinámica / rodillos

XML identificado por secuencia: utars_task_canada_wrc_20250930_start.xml.

| Parámetro | Valor documental |
| --- | --- |
| Estantería | Una de dos niveles |
| Nivel inferior, extremo 1 | 85 cm; regulación ±10 cm (75–95) |
| Nivel inferior, extremo 2 | 99 cm; ajustable y fijable, rango no indicado |
| Inclinación inferior | 10° |
| Nivel superior | 129 cm en un extremo (85+14+30), inclinación 10°; otro extremo no especificado |
| Cajas | 9, de 60×40×23 cm |
| Palés | 2, de 80×60×26 cm según el texto |
| Mesa de destino | 91,5 cm de altura |
| Distancia lateral caja–estantería | ≥164 cm desde lado izquierdo de la caja |
| Separación mesa–estantería | ≥45 cm |
| Caja de get3 | Centrada en nivel superior |

| Punto | Referencia de colocación |
| --- | --- |
| get1 | Centro rueda derecha a 59 cm del frente de caja; lateral caja derecha–rueda derecha 16 cm |
| put1 | Centro rueda derecha a 90 cm de parte inferior de estantería y 20 cm de centro de pata niveladora derecha |
| get2 | Centro rueda derecha alineado con lado derecho de caja de pila izquierda, a 51,5 del frente; original omite unidad, cm inferidos por contexto |
| put2 | Centro rueda derecha a 87 cm de parte inferior de estantería y 90 cm de centro de pata niveladora derecha |
| get3 | Centro rueda derecha a 74 cm de parte inferior de estantería y 57 cm de centro de pata niveladora derecha |
| put3 | A 56 cm del frente de mesa, centrado; referencia exacta en robot no explicitada |

La figura get1 coloca la rueda derecha **por fuera del lateral derecho de la
caja**, no16cm hacia su centro. Los59cm son la componente longitudinal desde
el centro de rueda. Con base780mm y lateral exterior, el operador aportó un
ensayo get1 exitoso. Los780mm son su medida, no una cota literal del SOP.
[Ensayo y tareas siguientes](../../../box_handling/GET1_PROVEEDOR_ENSAYO_20260916.md).

Secuencia: extraer lateralmente hacia la derecha la caja superior derecha
(get1→put1); levantar directamente la caja superior izquierda (get2→put2);
recoger caja del nivel superior y llevarla a la mesa (get3→put3).
El texto llama «inferior derecha» a ambos depósitos put1/put2 aunque sus puntos
difieren. No inventar una corrección. No se especifica altura exacta de la base
de las cajas superiores de las pilas ni peso de carga.

## 2. Dos estanterías

XML identificado por secuencia: utars_task_zhucheng_env_20260428_start.xml.

| Parámetro | Valor documental |
| --- | --- |
| Estanterías | Dos, cada una 150 cm largo ×50 ancho ×150 alto |
| Estantería 1 | Nivel inferior 70 cm, superior 125 cm |
| Estantería 2 | Nivel inferior 90 cm, superior 125 cm |
| Cajas | Dos, de 40×30×23 cm |
| Alineación | Centrado y perpendicular, sin desviación angular |
| Referencia de distancias | Saliente inferior, centro de banda anticolisión; no centro de rueda |
| get1 | 12,5 cm; recoger caja cargada abajo en estantería 1 |
| put2 | 31 cm; depositar esa caja abajo en estantería 2 |
| get2 | 12 cm; recoger otra caja vacía arriba en estantería 2 |
| put1 | 33,5 cm; depositar esa caja arriba en estantería 1 |

Secuencia: get1→put2, después get2→put1. No se vacía la primera caja;
se devuelve otra que ya estaba vacía. El proveedor ha indicado por separado
que el vaciado debe desarrollarse. No aparece operación de dumping en estos XML.

### Diferencias respecto al XML del escenario 2

| Campo literal | XML | Documento |
| --- | --- | --- |
| boxSize | [0.4,0.3,0.22] en todos los usos | 40×30×23 cm |
| targetPos inferior | [0,0.0,0.7] | Nivel inferior de origen 70 cm |
| putHeight inferior | 0.7 | Nivel inferior de destino 90 cm |
| targetPos superior | [0,0.0,1.2] | Nivel de origen 125 cm |
| putHeight superior | 1.2 | Nivel de destino 125 cm |

Las magnitudes sugieren metros, pero no equiparar targetPos/putHeight con la
altura del tablero sin resolver sus marcos y semántica en el backend. Las
coordenadas de navegación pertenecen al mapa, no están expresadas en este XML.

## Activación descrita y alcance

Web: construir mapa y registrar puntos. Mando: G derecha y volver inicia el
flujo configurado tras selección/localización; E abajo y centro, seguido de G,
repite tras recolocar las cajas. El documento no muestra cómo seleccionar el
XML en la web. A termina después del siguiente punto, no es un paro inmediato.

Consulta 16-09-2026: los XML están almacenados, pero está seleccionado el árbol
placeholder default_task_config.xml. Esta carpeta no cambia esa selección.
Las confirmaciones físicas y éxitos de HOME→READY→ENTRY propios del proyecto
no constituyen una prueba de estos flujos completos de proveedor.
