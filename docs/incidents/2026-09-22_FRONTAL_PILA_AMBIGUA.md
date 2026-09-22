# Selección frontal: caja y soporte confundidos como empate

22-09-2026, Europe/Madrid. **Causa VERIFICADA; selector corregido e instalado;
recepción nativa de la selección VERIFICADA; agarre no ejecutado.**

## Causa de este intento

El operador ejecutó `force_escenario1.sh`. Goal de agarre
`38371422-5359-4834-a3c2-b4ecb5911f3e`, 08:45:46 UTC, termina en
`NoneException`/1101000/status6. Se prepararon cabeza y ambos brazos; no
suponer HOME después del fallo. El operador confirma inmóvil, caja apoyada,
abrazaderas vacías y sin contacto.

La sesión `/tmp/cruzr-front-sps-fkxwpauo/selection.jsonl` registra:
`Ambiguous frontal boxes; do not choose by height or list order`, etapa detect,
SPS UUID `7bf18835-8f0b-4946-8b99-1fdd59c4c695`.
Motion muestra `Goal was aborted` y `GetVisionBox type: grasp error` antes
de llegar a obtener una pose y comprobar alcance/IK. No fue el mismo rechazo
ClampBoxOutOfReach anterior ni un timeout del cliente. No consta retirada
Iceoryx en el intervalo consultado; no atribuir este fallo a middleware.

Vision eligió la captura `1790066750.362790000` con cinco candidatas. La imagen
original `1790066750.362790000_action_grasp.jpg` muestra una pila frontal con
la caja abierta arriba y detección de otra caja debajo, más una pila lateral.
Las candidatas frontales de cámara son aproximadamente
[-0,103037;0,385069;0,866509] y [-0,102508;0,575672;0,955598] m.
La sesión antigua no guardó TF/poses completas al rechazar: no atribuir un
ángulo base exacto a esa captura. La causa de rechazo sí está registrada.

El operador confirma expresamente el objetivo: **la caja abierta superior de
la pila frontal, aunque las pilas laterales tengan cajas más altas**.
No se cambia la intención a «escoger la caja más alta de toda la escena».

Los waypoints de esta ejecución difieren del ensayo anterior:
get1=(-0,01295981;−0,01714718;−3,09642307), put1=(-0,00893415;0,53716889;
1,58150295). El agente no los editó. Llegada get1 verificada por el script con
error 19,2/19,3 mm y 0,322°. No reutilizar la pose de caja X0,803542/Z0,389692
como si perteneciese a esta nueva disposición.

## Corrección BOX-01-FRONT-STACK

[Selector](../../scripts/box_handling/select_front_box.py): agrupa detecciones
frontales cuyos centros XY están próximos (diámetro completo ≤8 cm), exige
separaciones verticales consecutivas de 22±4 cm para las workbin de 22 cm,
y toma la detección superior dentro de cada grupo válido. Entre pilas sigue
eligiendo el menor ángulo horizontal absoluto, sector ±20° y ambigüedad 2°.
La altura de una pila lateral no le da prioridad. Se conservan rechazos por
pilas distintas igualmente frontales, geometría incompatible, duplicados y
cadenas que exceden el diámetro. No se filtra una caja frontal inalcanzable
para sustituirla por una lateral.

Estos umbrales describen una política de identificación para esta caja;
no son certificación de apilado, espacio libre ni viabilidad de agarre. La caja
superior detectada tampoco demuestra por sí sola que su recorrido esté libre.
No se ampliaron límites de alcance, fuerza, velocidad o IK ni se alteraron
trayectorias XML/YAML instaladas. La pose que recibe Motion sigue siendo la
pose original de cámara, conservando TF exacta y contrato de una sola selección.

Diagnóstico mejorado:

- [front_sps_native.py](../../scripts/box_handling/front_sps_native.py) registra
  captura y TF antes de seleccionar, incluidos rechazos.
- [probe_front_box.py](../../scripts/box_handling/probe_front_box.py) imprime
  poses y TF cuando el selector rechaza una consulta.
- [front_sps_session.py](../../scripts/box_handling/front_sps_session.py) muestra
  `FRONT_SPS_CAUSE` al terminar si hubo rechazo; no oculta la causa tras el
  `NoneException` genérico de Motion.

## Verificación

Consulta perceptiva sin trayectoria, UUID `a0a4bb4785bd443ba79399dade6d75da`,
stamp1790067218.447761000. TF del mismo instante:

| Candidata | X base (m) | Y base (m) | Z base (m) |
| --- | --- | --- | --- |
| Caja superior, índice0 | 0,783242 | 0,137329 | 0,793951 |
| Soporte, índice1 | 0,784089 | 0,132505 | 0,584720 |

Separación vertical≈0,20923 m; horizontal≈4,9 mm. Selector nuevo devuelve índice0
con pila [1,0], bearing9,9448°. Reejecutar el selector anterior offline sobre
**esa misma captura** reproduce el rechazo por ambigüedad. Las laterales quedan
fuera del sector frontal. Esta consulta no habilitó visión ni cambió postura;
Vision conserva sus imágenes diagnósticas habituales.

Pruebas: 62 tests iniciales pasan; tres regresiones posteriores añadidas y suite
local de41 tests pasa (65 tests distintos en total contando los de flujo, sin
cambios posteriores de implementación). Incluyen todas las permutaciones,
caja frontal inferior a lateral, tres niveles, tope inalcanzable, duplicados,
pilas distintas, cadenas, captura real y devolución de pose original por SPS.
Sintaxis y `git diff --check` correctos. Preflight físico instrumental: 20D
habilitados, velocidad0, error máximo consigna0,002330rad, paros0/0,
cargador desconectado, baterías50,3/52,3%, acción libre. No certifica HOME.

Prueba nativa `front_box_integration.py --check`: rc0, MetaLook detect_only
UUID13ad74a0-61da-4343-b895-5540c9058e86, SUCCEED1101001/status4.
Selecciona índice0, pila[1,0], X0,780342/Y0,134263/Z0,793721m;
pose original cámara[-0,101615;0,385736;0,864222]m. Transacción nativa
03d0115c-cd1e-4197-8336-ca15069071f2, visión05c7ae14debd418f8182c72f8d5adad2,
stamp1790067362.048521000. `CHECK_SPS_OK` confirma recepción nativa; no es
prueba de trayectoria ni agarre. Sesión `/tmp/cruzr-front-sps-epead75r` cerrada
por el supervisor; efecto runtime: actualización del historial perceptivo box/0.
No se envió HOME, navegación ni MetaClamp. No se restaura la caché antigua.


Verificación final tras añadir el caso del borde del sector: paquete
`74f5507e44addd71`, tarea47a17275-5b18-4ba8-bc77-b931e5e18ccb,
SUCCEED1101001/status4, sesión `/tmp/cruzr-front-sps-i5hfsl74`.
Selecciona índice0, pila[1, 0],
pose base X0.783537/Y0.135550/Z0.793584m;
SPS UUID6d0d96dd-8eb5-456f-8549-f308167c9d48, stamp_ns1790067565971696000.
La agrupación incluye cajas apenas fuera del sector para no escoger su soporte
interior por error; si la superior queda fuera, se rechaza esa pila. Regresión
específica pasa. El primer paquete `f3380fd77c3c21ea` también fue instalado y
probado en percepción, luego sustituido por este ajuste de borde; permanece
inactivo como evidencia, no es la versión vigente. Ambos recibos sin reinicios,
trayectorias ni sobrescritura de tareas. No se ejecutó agarre en ninguno.

## Instalación, activación y reversión

Paquete nuevo `74f5507e44addd71`, instalado de forma aditiva en Motion
192.168.11.2: host `/var/tmp/cruzr-front-box/74f5507e44addd71/`, contenedores
`walker-motion.manipulation_robot_app-1` y `walker-ros.ros2-1`, ambos en
`/opt/cruzr-front-box/74f5507e44addd71/`.
Aplicación reproducible: `python3 scripts/box_handling/front_box_integration.py --install`.
El constructor calcula ID/hashes y verifica dependencias nativas y tareas.
Recibo: `created_tasks=[]`, `originals_overwritten=false`, reinicios0,
órdenes de movimiento0. Las versiones originales del SDK permanecen intactas.
Los dos wrappers de escenario resuelven el paquete a partir de las fuentes
actuales, sin necesidad de cambiar sus trayectorias. No ejecutar el ciclo para
comprobar la selección: usar `--check-front` o el ensayo nativo `--check-sps`
con abrazaderas vacías; este último actualiza caché de percepción box/0.

Paquete anterior `a9eaf948512d2eb4` conservado. Backup externo del paquete,
fuentes previas, logs, consulta, foto original, receta y hashes:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922T084811Z_FRONT_NONE_EXCEPTION`.

Los manifiestos `final-bundle.json` y `SHA256SUMS` fijan fuentes y hashes exactos;
`before/` conserva trabajo local previo no reproducible sólo con Git. Para
revertir, restaurar únicamente los cuatro módulos modificados y sus tests
asociados desde `before/` (selector, probe, native y session); el ID resuelve
al paquete anterior, sin reiniciar ni restaurar estados transitorios. Revertir
selectivamente la documentación. El paquete nuevo puede quedar inactivo como
evidencia. No borrar paquetes ni sesiones ajenos.

Estado que conservar tras actualización: adaptación frontal por pilas y
comunicación sin SHM de la ficha COMM-01; reaplicar selectivamente con receta,
tras verificar dependencias. **Agarre, traslado y depósito no probados en esta
intervención.** Próximo ensayo debe partir del estado físico actual verificado,
no reiniciar el ciclo por rutina tras un fallo.
