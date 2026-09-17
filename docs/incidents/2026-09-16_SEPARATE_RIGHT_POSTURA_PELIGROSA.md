# Incidente de postura peligrosa durante separate_right

Fecha: 2026-09-16, Europe/Madrid. Estado: **INCIDENTE HISTÓRICO; ENSAYO POSTERIOR EXITOSO**.
El operador corrigió la base a780mm y el lateral a160mm hacia fuera. Aportó
SUCCEED/status4 y éxito físico de get1. El bloqueo inicial del script ya fue
sustituido por el usuario. [Ensayo y estado vigente](../box_handling/GET1_PROVEEDOR_ENSAYO_20260916.md).
El cuerpo de este informe conserva hallazgos y contención del intento anterior;
no atribuirle por sí solo una causa única ni extenderlo a cualquier disposición.
Tarea: `Singapore/separate_right_cruzr`, v0.2.0, abrazaderas.
Registro de cambios: BOX-01-EXEC. La suspensión sustituye la recomendación
anterior de volver a ejecutar tras habilitar visión.

## Situación física comunicada y estado posterior

El operador informa que el robot se inclinó peligrosamente y casi introdujo
la cabeza en una caja; accionaron el E-stop y retiraron las cajas. La fotografía
muestra la flexión pronunciada del torso. No permite cuantificar contacto,
daño, fuerza, distancia de parada ni ángulos articulares.

Durante el diagnóstico el operador comunica que completaron un reinicio y
que el robot está en HOME con E-stop liberado. La lectura nueva lo corrobora:
20 ejes corporales, posición absoluta máxima 0,001821602 rad, velocidad cero,
20 actuadores corporales con error_code=0/status=4663 y diferencia máxima de
consigna 0,001821602 rad. Ambos paros=0, cargador=0, un servidor de acciones,
cero writers en `/mc/sdk/robot_command`. No repetir HOME: ya está en esa postura.
No se enviaron movimientos, rearme, apagado o reinicio por el agente en esta
intervención. El reinicio y HOME son acciones del operador/arranque interno.

## Secuencia reconstruida

Los tiempos siguientes son los escritos en los logs del robot. El reloj del
PC difiere del reloj del robot: no presentar estos valores como UTC del PC.

| Hora del log | Evidencia |
| --- | --- |
| 16:34:49.200 | Goal `1266497b-a14f-42df-acea-7c24dfa7ae78`: habilitar transport vision |
| 16:34:49.891 | Habilitación termina en SUCCESS |
| 16:34:51.745 | Goal `dfc1d414-79b0-4908-ae40-591cad32c30b`: separate_right |
| 16:34:55.426 | Cabeza y ambos brazos terminan los MetaMove iniciales |
| 16:34:55.638 | Comienza `MetaClamp wrc/separate_right_cruzr` |
| 16:34:56.580 | Visión devuelve una pose y Motion la acepta |
| 16:34:56.591 | Se inicia la trayectoria calculada |
| 16:35:03.706 | Control Center registra E-stop=1 |
| 16:35:06.751 | Error articular registrado 3,1411 supera umbral 3,14 |
| 16:35:06.831 | `ClampJointTrackingError`, 7101108, status=6 |
| 16:43:58.758 | En el nuevo arranque se registra HOME completado |

El error 7101108 aparece aproximadamente 3,125 s DESPUÉS de que Control Center
registre el paro. Los últimos registros de posición de la mano izquierda
permanecen iguales mientras crece la diferencia con la consigna. Esto es
compatible con consignas calculadas después de detener físicamente el robot.
No demuestra que el robot siguiera moviéndose esos tres segundos ni mide su
distancia de parada. No atribuir la inclinación previa al código final.
No llegó a ejecutarse `wrc/separate_bodyback_cruzr` en este goal.

## Visión y trayectoria efectivamente utilizadas

El primer intento anterior, goal `99277662-f57f-4c77-a26c-79ebc1391e7e`, había
fallado porque `Transport vision is not running`. Habilitarlo corrigió ese
prerrequisito, pero no comprobó la seguridad de MetaClamp. Fue incorrecto
recomendar otro ensayo físico basándose solamente en esa corrección.

La captura RGB-D guardada por el propio detector durante el segundo intento
muestra las dos cajas superiores. La pose seleccionada coincide con la caja
de la derecha en la imagen anotada; no hay evidencia para atribuir este
incidente a que eligiera la caja izquierda. No se usó el VLA/checkpoint.

Datos del registro de Motion, posiciones en metros:

| Dato | X | Y | Z |
| --- | ---: | ---: | ---: |
| Caja en cámara | 0,2233 | 0,6284 | 0,9735 |
| `X_BaseBox` | 0,7730 | −0,1986 | 0,5329 |
| Mano izquierda: punto VISION con offset | 0,5089 | −0,0980 | 0,5240 |
| Mano derecha: punto VISION con offset | 0,7520 | −0,5492 | 0,5418 |

Los puntos iniciales ABSOLUTE de ambas manos tenían Z=1,0 m. El tramo siguiente
las lleva hacia Z≈0,52–0,54 m en el marco usado por Motion, acompañado de
desplazamiento hacia delante y asimetría lateral. El descenso procede de la
trayectoria calculada; no es sólo inclinación de cabeza para ver la caja.

Esas Z no deben llamarse automáticamente alturas desde el suelo. En el mismo
instante, Vision escribe una traslación de cámara con Z=1,63681 mientras Motion
escribe `X_WCamera` con Z=1,5099. Antes de atribuir los 126,91 mm de diferencia
a una calibración errónea hay que identificar los orígenes y los marcos de
ambas transformaciones. No añadir ese offset a la trayectoria a ciegas. La
base de caja a 570 mm comunicada por el operador no es directamente comparable
con el centro geométrico o los puntos de los efectores sin esta comprobación.

## Configuración relevante y límites del diagnóstico

Se leyeron las versiones instaladas y coinciden con el archivo del proveedor:

- XML separate_right: `4ba2515ba030f7f1483eed704ce68e0d888ac29754bef1645908fb9f96345e0b`.
- YAML separate_right: `648c713e286b1602dabcb538b755fe780bdbe9513618b3cc5133955c6eaec2ec`.
- YAML bodyback: `a3b25e1cfd0abbd4fa179e09cd161ebb9b1d46786bacf06192cc5c434af34dc6`.
- Task stack: `bd8f5c38ac97c2a9ff19097b2bae43b0ab59827e377fd601ddfcfc1709da0e33`.

El task stack `task_stack_cruzr_separate_manipulability.yaml` contiene objetivos
de ambas manos y una restricción de centro de masa; en segundo nivel contiene
límites de hombros y optimización de manipulabilidad. No aparece una tarea
explícita para mantener/acotar la postura del torso ni un límite de distancia
cabeza–caja. La mera clave `torso` en el YAML de parámetros no demuestra que
haya un objetivo activo de torso en el stack. El solver usa 18 dimensiones.

El YAML contiene `enable_self_collision_check: false` y
`enable_abnormality_determination: [none]`. Además, el parser en ejecución
registra `self_collision_detect=false` y `collision_detect=false` por defecto.
El chequeo articular registra umbral 3,14 rad. Son condiciones encontradas,
no ajustes aplicados por el agente en este diagnóstico; tampoco prueban que
todas las protecciones de hardware estén desactivadas.

**Conclusión:** se ejecutó una trayectoria bimanual con libertad de torso y
sin evidencia de separación de cabeza/cuerpo respecto a esta escena. La
aceptación visual y el ajuste de distancias del SOP no bastaron. La cadena
explica un mecanismo compatible con la postura observada, pero sigue pendiente
reconstruir el barrido corporal y confirmar la semántica de coordenadas. No se
declara una causa única de calibración, selección de caja o firmware.

## Contención y siguiente trabajo

En la contención inicial, `scripts/force_separate_right_cruzr.sh` terminó con código78 antes de SSH,
Docker o ROSA. La versión ejecutable anterior se conserva únicamente como
evidencia privada; no usarla como rollback operativo. El bloqueo local no retira
la tarea del robot ni impide que la web/otros clientes la llamen. El escenario 1
completo también contiene get1 y reintentos: su ejecución queda suspendida para
esta configuración; no usar el árbol completo para saltar la suspensión.

Antes de otra ejecución: identificar los marcos de cámara/base y puntos de
agarre; reproducir offline los objetivos con caja/pila/palé y el modelo corporal;
incorporar restricciones efectivas de torso y separación de cabeza/cuerpo;
revisar semántica de parada/cancelación y ejecutar por etapas sólo después de
comprobar esos cambios. Un timeout del cliente CLI no cancela necesariamente
una acción aceptada. No resolverlo aumentando el umbral de seguimiento, bajando
la velocidad o cambiando a otra tarea sin revisar su recorrido.

## Evidencia y reproducción del cambio local

Evidencia privada y backup previo:
`../Humanoide-vla-evidence/20260916T084847Z_SEPARATE_RIGHT_INCIDENT/`.
Incluye logs Motion/Vision, configuración viva, extracto sin ANSI, imagen RGB
y anotación de agarre del instante del goal, copias before/ y SHA256SUMS.
Estado posterior leído:
`../Humanoide-vla-evidence/20260916T085041Z_ESTOP-AVAILABLE/results.json`.

Fuente reproducible de la suspensión: el propio script, salida 78 antes de
cualquier cliente remoto, sin instalación o recarga en el robot. Verificación
offline: sintaxis Bash y ejecución con clientes remotos sustituidos por
sentinelas, sin invocar ninguno. Conserva los archivos y cambios previos del
usuario. Reversión operativa = mantener la suspensión hasta sustituir la ruta
por una revisada; la copia before/ sirve para análisis, no para volver a operar.
No se hizo commit ni push.
