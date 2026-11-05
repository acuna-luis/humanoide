# APP2 — contraste con T-Spec HR-001, revisión 001

**Fecha de análisis:** 19-10-2026, Europe/Madrid.\
**Estado:** VERIFICADO documentalmente; cumplimiento del sistema PENDIENTE.\
**Intervención:** lectura local del DOCX y contraste de su XML, sin conexión al
robot ni modificación de servicios, configuración o controles.

Este documento registra requisitos y límites de la fuente aportada. La lista
única de trabajo y preguntas se mantiene en
[PLAN_Y_PREGUNTAS.md](PLAN_Y_PREGUNTAS.md); esta matriz no sustituye esa lista ni
declara que las funciones estén implementadas.

## 1. Fuente, identificación y alcance

Fuente aportada: `TE-MQXXXXX-Humanoid_rev001 (2).docx`. Portada:
**T-Spec HR-001 — Last Mile Material Distribution Humanoid Deployment**,
Global Manufacturing Development; Published Date **08/25/2026**; revisión **001**.

- [Original privado conservado](../../../Humanoide-vla-evidence/app2/specifications/2026-10-19/TE-MQXXXXX-Humanoid_rev001_2.docx).
- SHA256 del DOCX: `261f5e378c4edfd79cad190d0bfc9a1caf6dc274e2cce0895a4ed763c16605f5`.
- La propia especificación identifica como controlada la versión almacenada
  en el sitio de ingeniería del cliente; esta copia adjunta no acredita que
  sea la revisión vigente de todas las normas referenciadas.
- La tabla de revisiones contiene la fecha literal anómala `08/2025/2026`.
  Se conserva la diferencia; no se corrige ni interpreta como una segunda fecha.

**El Word contiene tres operaciones, no solamente APP2.** En §9, Equipment
Requirements → OPERATION DESCRIPTIONS, aparecen en este orden:

| Orden en el Word | Título exacto | Alcance específico |
| --- | --- | --- |
| Primera | Harness Box 31XX Material Replenishment | Sacar cajas del bulk pack, identificar material y cargar un rack creform; controlar FIFO, cantidad y ubicación. |
| Segunda | ITR Material Feed and Empty Container Handling | Sacar componentes ITR de una caja, identificar material, alimentar transportador/punto de presentación y gestionar la caja de cartón vacía. |
| Tercera | OTR Line-Side Replacement Station Replenishment | Recoger componentes OTR de la estación de reposición y abastecer el rack creform asignado. |

**APP2 es el nombre interno acordado para la segunda operación, ITR.** Los
títulos de operaciones del Word no llevan numeración automática de aplicación
ni usan los términos `app1`, `app2` o `app3`. Esa correspondencia por orden no
debe presentarse como un código contractual confirmado por el cliente.

El bloque fotográfico situado tras el texto ITR pertenece estructuralmente a
ese apartado: está en el párrafo XML p463, entre el final de los requisitos ITR
(p462) y el título OTR (p465). El título OTR que aparece debajo en la captura
inicia el siguiente apartado; no es un pie que identifique como OTR las fotos
anteriores. Esto aclara su posición documental; la referencia exacta de las
piezas sigue sin estar identificada por número de parte.

Las siglas ITR/OTR no se desarrollan en el DOCX. Su interpretación como Inner
Tie Rod / Outer Tie Rod procede del contexto y de fuentes del sector, no de
una definición explícita de este contrato.

**Cómo localizar las referencias:** `pNNN` indica el índice, comenzando en cero,
de todos los elementos `w:p` en orden de aparición en `word/document.xml`,
incluidos párrafos vacíos, tablas e imágenes. Es un localizador reproducible de
esta copia, no una página ni un número de cláusula del cliente. Las secciones
§3–§9 se contrastaron con la numeración XML y el índice del documento.

## 2. Matriz de requisitos específicos de APP2 / ITR

Todos estos requisitos proceden de §9, ITR Material Feed and Empty Container
Handling. Una cita breve sirve de localizador; el resto es resumen del requisito.

| ID de esta matriz | Referencia y cita breve | Requisito y consecuencia para APP2 |
| --- | --- | --- |
| APP2-R01 | p442, “take ITR components from the supplied box” | El alcance completo incluye recogida, identificación, alimentación y depósito de la caja vacía. Reconocer piezas es un primer hito de ese alcance. |
| APP2-R02 | p442, “Manual support may be used” | Se admite apoyo manual durante evaluación de desarrollo si se documenta como condición de apoyo o excepción. No equivale a demostrar ejecución autónoma. |
| APP2-R03 | p445, “ready to accept material” | Comprobar material ITR correcto y disponibilidad del transportador o posición de alimentación antes de cargar. |
| APP2-R04 | p446, “one at a time or in the approved handling quantity” | Cantidad de manipulación aprobada, orientación conservada y protección de superficies funcionales. No hay cantidad numérica fijada. |
| APP2-R05 | p447–448, “required orientation and spacing” | Colocar con orientación y separación requeridas y vigilar bloqueo, llenado o desalineación. Esas dimensiones y tolerancias no aparecen definidas. |
| APP2-R06 | p449, “collapse or handle the empty cardboard box” | El tratamiento de cartón y su destino deben definirse. El texto permite plegar o manejar la caja según lo acordado; no obliga por sí solo a una técnica de plegado concreta. |
| APP2-R07 | p450, “Document the replenishment cycle” | Conservar ciclo y anomalías para validación del flujo y futuro trabajo estándar. |
| APP2-R08 | p452, “expected versus actual ITR material ID” | Confirmar ID esperado frente a real **antes** de cargar; registrar lectura, no-read/misread, reintentos y excepción hacia la interfaz de §7. Una etiqueta visual genérica «pieza ITR» no prueba referencia exacta. |
| APP2-R09 | p454, “Part number, container label, and feed location” | Verificar número de parte, etiqueta de contenedor y ubicación de alimentación. Con la aclaración del operador recogida en §6, puede plantearse verificar la referencia mediante la etiqueta de la caja y un contrato de asociación confirmado. No se deduce una obligación de leer un ID o serial individual en cada pieza. Faltan ejemplos y reglas reales de correspondencia. |
| APP2-R10 | p455, “reversed, damaged, or incorrectly oriented” | Evitar liberar componentes invertidos, dañados o mal orientados. Detectar presencia no demuestra inspección de daño ni orientación correcta. |
| APP2-R11 | p456, “additional ITR loading shall be inhibited” | Inhibir carga si destino lleno, bloqueado o en fallo hasta corregir la condición. Señales, responsables y handshake aún deben acordarse. |
| APP2-R12 | p458–459, “required clearances” | Definir aproximación, orientación, método de carga, recorrido del cartón vacío y holguras; validar manejo repetitivo sin daño, interferencia de embalaje o riesgo ergonómico. |
| APP2-R13 | p460, “abnormal condition handling” | Contemplar suministro vacío, bloqueo, material incorrecto, pieza dañada y contenedor de vacíos lleno. |
| APP2-R14 | p462, “validation evidence” | Documentar secuencia, supuestos de recogida, carga, cartón vacío, condiciones de imagen/etiqueta, anomalías, campos de datos y evidencias. |

## 3. Requisitos transversales que también afectan a APP2

| ID de esta matriz | Sección / localizador | Requisito y límite de interpretación |
| --- | --- | --- |
| APP2-T01 | §3, p119–122 | Compra para desarrollo, ensayo y evaluación interna. La aprobación de este equipo no es liberación para producción; esa aprobación futura es independiente. |
| APP2-T02 | §3–§4, p139–143, p219–225 | Aplican las especificaciones del cliente salvo excepción escrita. La lista incluye SD-1061 Machine Vision Application Requirements. El contenido de esa norma y de las otras normas referenciadas no viene incorporado al DOCX y sigue pendiente de obtención/revisión. |
| APP2-T03 | §5, p245–246 | **Lectura de códigos/etiquetas e identificación de material mediante visión integrada del humanoide**, por aplicación. Confirmación de lectura, mala lectura, interfaz y trazabilidad requeridas. Un lector externo separado requiere justificación y aprobación escrita. |
| APP2-T04 | §5, p246 | Evidencia de validación por posición de etiqueta, distancia de lectura, iluminación, orientación, lectura correcta, no-read/misread y salida de datos; debe incluirse en FAT/SAT. No se especifican aquí simbología, tamaño de etiqueta, distancia ni precisión mínima. |
| APP2-T05 | §5, p239, p247–250 | Concepto de seguridad, evaluación de riesgos, paros, recuperación, límites operativos, formación, acceso y respaldo. Son requisitos por demostrar; no se presume certificación del robot por disponer de sensores o paros. |
| APP2-T06 | §6, p255–261 | Arquitectura eléctrica/integración documentada; PLC Allen Bradley/Siemens según planta, OPC UA, MQTT, Ethernet/IP y protocolos adicionales necesarios. Deben concretarse interfaces, tags y mensajes; mencionar los protocolos no demuestra implementación. |
| APP2-T07 | §6, p258, p262–264 | Documentar red/IP, arquitectura, estructuras de mensajes, propiedad/retención de datos, acceso y lógica de identificación, pass/fail, reintentos y excepciones. Salidas para MES/trazabilidad/digital twin/analítica. |
| APP2-T08 | §6, p263 | Cloud, VPN del proveedor, acceso remoto y comunicaciones inalámbricas requieren aprobación escrita del cliente antes de activarse en su alcance de despliegue. Es una condición de integración del cliente, no una instrucción para cambiar ahora la red o el laboratorio local. |
| APP2-T09 | §7, p286–290 | Interfaz o exportación documentada; método, propiedad, retención, buffer local, frecuencia, backup/recuperación y códigos únicos de excepción. No exige PC/cabinet/monitor/switch/UPS dedicado salvo petición escrita. |
| APP2-T10 | §7, p291–295 | Datos por aplicación, diccionario y registros de ejemplo; revisar/exportar eventos, identificación y transferencia en FAT/SAT. La confianza o métrica equivalente se solicita **si está disponible**; no hay umbral numérico contractual fijado. |
| APP2-T11 | §8, p299, p378–388 | Plan de validación, riesgo, protocolos FAT/SAT y evidencia MQ1/MQ2; demostrar configuración, identificación material/ubicación, trazabilidad, estados, excepciones, paros, intervención y tiempo de ciclo. Se requieren criterios, pero no aparecen valores de aceptación numéricos para esas métricas. |
| APP2-T12 | §8, p338–348 | Documentación electrónica, inglés como mínimo y configuración aprobada vigente antes de MQ1/MQ2/SAT/cierre; incluir arquitectura, operación, seguridad, visión, datos, versiones y backup/restore. Documentación en español del laboratorio no cubre por sí sola la entrega requerida en inglés. |
| APP2-T13 | §8, p364–374 | Cronograma, revisiones semanales, informe mensual y seguimiento de acciones con responsable, fecha, riesgo y evidencia. Arquitectura de controles/red/datos y software deben revisarse con el cliente. |

Los requisitos del Word se tratan como información para analizar y planificar.
No autorizan instalar software, activar interfaces, subir imágenes, modificar
seguridad, conectarse a terceros ni mover el robot desde esta revisión.

## 4. Contrato mínimo de datos descrito en §7

p295 enumera estos campos mínimos, sin fijar todavía esquema, tipos, transporte,
frecuencia ni política temporal de sincronización:

1. Nombre de aplicación.
2. Timestamp.
3. Task ID.
4. Location o rack ID.
5. Material ID esperado.
6. Material ID reconocido.
7. Resultado de visión/barcode.
8. Estado pass/fail.
9. Número de reintentos.
10. Indicador no-read/misread.
11. Código de excepción.
12. Estado de intervención del operador.
13. Estado de paro de seguridad o protective stop.
14. Tiempo de ciclo.
15. Versión software/firmware del robot.
16. Estado de finalización.

p291 añade confianza de lectura o métrica de calidad equivalente cuando esté
disponible. p290 pide códigos únicos para no-read, misread, material incorrecto,
camino bloqueado, paro, intervención manual, tarea incompleta y recuperación
fallida. El conjunto definitivo y la distinción entre `actual material ID`
(§6) y `recognized material ID` (§7) requieren acordar un diccionario explícito.

## 5. Fechas y aceptación

| Elemento | Texto explícito y localizador | Estado de planificación |
| --- | --- | --- |
| MQ1 | §3, p149: readiness en proveedor antes del **13-11-2026**. §8, p379: revisión de preparación en proveedor antes de autorización de envío. | Fecha documental; confirmar vigencia contractual, alcance y criterios con el cliente. |
| MQ2 | §3, p151: evaluación completada antes del **18-12-2026**, Plant 3, Saginaw, Michigan. §8, p380: evaluación y evidencias en cliente, denominada MQ2/SAT. | No confundir con puesta en producción. |
| Revisión previa | §8, p373: revisiones eléctrica, seguridad, lógica, software/datos, visión y zonas al menos **cuatro semanas antes de MQ1**, salvo acuerdo distinto. | Si se aplica al 13-11-2026, el cálculo da **16-10-2026**; esta última es fecha derivada, no otra fecha literal del documento. |
| Seguimiento | §8, p367–369: informe el primer día de cada mes y reuniones semanales desde kickoff hasta MQ1; posible continuidad hasta MQ2/SAT. | Organización y confirmación pendientes. |
| Envío | §8, p391: MQ1 completado, críticos resueltos/dispuestos, documentos de envío/importación y aprobación escrita. | No basta con que la demo funcione. |
| Retención | §8, tabla p321–324: cuatro semanas de evaluación post-SAT y cierre/disposición de críticos/documentación/evidencia. | Hito comercial separado de éxito técnico inicial. |

La tabla comercial de §8 contiene cuatro fases **30% / 30% / 30% / 10%**:
aprobación de protocolos de riesgo y FAT/SAT, MQ1 y autorización de envío, SAT y
evidencias aprobadas, y retención final. Se registra para conservar contexto;
no supone aceptación comercial por parte de este proyecto.

**No se han encontrado valores de aceptación explícitos para** tasa de acierto
de referencia, falsos positivos, no-read/misread, mAP, latencia, FPS, tiempo
máximo de ciclo, tolerancia de pose, masa/dimensiones de la ITR, distancias de
cámara, cantidad de piezas por toma o política máxima de reintentos. El documento
pide definir o validar varios de ellos, pero no proporciona sus valores.
Cualquier cifra propuesta por el equipo será objetivo interno provisional
hasta acordarla; no debe citarse como umbral del cliente.

## 6. Efecto sobre la estrategia actual y datos por aclarar

Se mantiene útil el primer hito de segmentar y distinguir las piezas visibles
en las cámaras actuales. El DOCX amplía el objetivo: se necesita además
identificación de referencia/etiqueta, decisión esperado frente a real,
no-read/misread y trazabilidad. Un segmentador puede localizar la pieza o la
etiqueta; por sí solo no prueba lectura de barcode ni cumplimiento completo.

**Aclaración del operador, 19-10-2026 — OBSERVADO:** «la id vendría en la caja».
Es información aportada en la conversación, no una nueva cláusula del Word.
La fuente de identificación prevista es la **etiqueta de la caja de origen**;
no se ha indicado que cada pieza lleve un ID o número de serie individual.
Falta confirmar si el dato identifica referencia de material, lote o ambos,
así como su formato y simbología.

Como propuesta de implementación pendiente de validar, la lectura de esa caja
puede proporcionar el contexto de material para las piezas extraídas de ella.
Hay que acordar y probar cómo se conserva la asociación pieza–caja y cuándo
se invalida ese contexto —por cambio de caja o pérdida de asociación, por
ejemplo—, y cómo se detectan o gestionan mezclas de piezas. Una etiqueta leída
no prueba por sí sola que todo el contenido corresponda a ella. Son cuestiones
de diseño y validación de esa asociación, no nuevos requisitos contractuales
ni una exigencia de serialización individual añadida por este análisis.

La selección de clases, método de lectura y evaluación queda condicionada a
recibir números de parte/variantes, muestras de etiquetas de caja y simbologías,
ubicación real de esas etiquetas, ejemplos de material incorrecto/dañado y
condiciones de cámara. También falta acordar señales del destino, orientación,
espaciado, datos, seguridad, métricas y criterios FAT/SAT. Esas preguntas y su
seguimiento pertenecen a [la lista única del plan](PLAN_Y_PREGUNTAS.md), junto
con la confirmación de revisión documental y calendario.

La conservación y análisis de este adjunto **no modifica el estado instalado**
de CVAT/RF-DETR ni demuestra un detector de piezas entrenado, lectura de códigos
en el robot, integración PLC o manipulación APP2. El punto de reanudación técnico
permanece en [RETOMAR_APP2.md](RETOMAR_APP2.md) y
[DATOS_Y_ENTRENAMIENTO.md](DATOS_Y_ENTRENAMIENTO.md).
