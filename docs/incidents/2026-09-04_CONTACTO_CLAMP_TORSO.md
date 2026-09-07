# Informe de incidente: contacto clamp–torso durante `StartMotion`

> **CORRECCIÓN 07-09:** informe preliminar superado por la
> [auditoría de logs originales](2026-09-07_AUDITORIA_CONTACTOS_HOME.md).
> StartMotion ejecutó `cruzr/home` en ambos arranques, no sólo reenergización.
> La inversión de clamps es una hipótesis contribuyente fuerte, no causa única
> demostrada. No está fechado qué movimiento produjo cada marca. El texto
> histórico siguiente no debe usarse como diagnóstico final ni autorización.

Fecha: 2026-09-04  
Estado: **PRELIMINAR SUPERADO**, con montaje invertido reportado y alcance material
pendiente de inspección.

## Resumen ejecutivo

Durante las pruebas de manipulación de cajas se invirtieron deliberadamente
las abrazaderas porque esa orientación ofrecía un agarre más favorable. La
modificación cambió la envolvente física del efector, especialmente la
posición de sus patillas, pero no se incorporó al URDF, a una malla de
colisión ni a un perfil distinto de herramienta. Los movimientos estándar
continuaron operando con la geometría nominal/de fábrica implícita.

El incidente ocurrió al liberar el E-stop con el robot en READY. El self-check
terminó correctamente y la secuencia interna propietaria `StartMotion`
reenergizó los brazos. La clamp izquierda contactó con el torso; después se
registraron fallos 4003/4004 y EtherCAT `SAFEOP ERROR`. Las fotografías
posteriores muestran rayado y una marca/orificio aparente en la cubierta. El
alcance cosmético, estructural o funcional todavía no ha sido inspeccionado.

El checkpoint, el publicador VLA y la transición ENTRY **no se ejecutaron**.
Por tanto, no hay evidencia para atribuir este incidente a una inferencia de
IA o al checkpoint.

## Causa y factores contribuyentes

- **Causa inmediata observada:** movimiento/reenergización interna
  `StartMotion` desde READY con holgura insuficiente entre clamp izquierda y
  torso.
- **Factor contribuyente principal confirmado:** orientación invertida de las
  abrazaderas, adoptada para mejorar la manipulación de cajas.
- **Fallo de integración:** esa configuración no se trató como una geometría
  de herramienta diferente y no fue incorporada al modelo de colisiones ni a
  los gates de montaje.
- **Limitación del proveedor:** no se dispone de CAD/mesh de colisión ni de una
  referencia geométrica inequívoca para estas clamps pasivas.
- **Limitación de observabilidad:** `StartMotion` es una secuencia interna y su
  trayectoria exacta no se expone como preview antes del rearmado.
- **Fallo preventivo interno:** se verificaron estado articular, paros y salud
  del sistema, pero esos checks no podían detectar una envolvente mecánica
  modificada no representada.

La “imprevisibilidad” relevante no fue aleatoriedad del VLA. Fue
**imprevisibilidad operativa residual**, creada por combinar una geometría
física modificada y no modelada con una secuencia interna propietaria cuya
trayectoria no podía previsualizarse con los artefactos disponibles.

## Respuesta y estado posterior

Se accionó el E-stop y se completó un apagado controlado. Al retirar potencia,
el contacto se alivió. Un segundo arranque supervisado desde brazos libres
recuperó `JoystickMode`; el preflight aprobó y se midió HOME en los 20 ejes,
con velocidad cero y sin enviar un goal HOME desde el PC; los logs revisados
el 07-09 demuestran que el arranque sí ejecutó HOME. Esto demuestra recuperación
funcional inmediata, pero no descarta daño material oculto.

## Acciones correctivas

1. Restaurar, marcar y fotografiar la orientación de fábrica de ambas clamps.
2. Prohibir la orientación invertida en movimiento automático mientras no
   tenga un perfil de herramienta, envolvente/mesh y procedimiento propios.
3. Añadir doble verificación visual del montaje y holgura bilateral antes de
   reenergizar o ejecutar HOME/READY.
4. Mantener bloqueado HOME→READY y sustituirlo por validación escalonada,
   lenta y con un solo brazo centinela antes del movimiento bimanual.
5. Inspeccionar y registrar la profundidad de la marca/orificio, la cubierta,
   cableado, sensores y ausencia de deformación; no clasificar el daño como
   cosmético antes de esa inspección.
6. Conservar logs, fotografías y hashes de configuración como evidencia del
   incidente y de las correcciones.

## Texto breve para dirección

Las abrazaderas se invirtieron deliberadamente porque esa orientación
mejoraba el agarre de las cajas. El cambio alteró la envolvente física del
efector, pero no estaba representado en el modelo de colisiones del robot. Al
liberar el E-stop desde READY, una rutina interna `StartMotion` —anterior a
cualquier ejecución del VLA— reenergizó los brazos y la clamp izquierda
contactó con el torso, causando el rayado y la marca/orificio aparente. La
protección detuvo el sistema, pero lo hizo después del contacto. La lección no
es que el VLA actuara aleatoriamente, sino que una modificación mecánica no
modelada introdujo una zona de colisión que los checks de software no podían
ver y que coincidió con una secuencia propietaria no previsualizable. Se ha
establecido como requisito restaurar y verificar la geometría de fábrica, y
se bloquea cualquier uso automático de la orientación invertida hasta disponer
de modelo, perfil y validación específicos. El robot recuperó HOME medido;
queda pendiente inspeccionar y clasificar formalmente el daño físico.
