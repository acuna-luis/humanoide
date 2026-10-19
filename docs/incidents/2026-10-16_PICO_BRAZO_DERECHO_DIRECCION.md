# PICO: respuesta hacia fuera del brazo derecho

Fecha: 16-10-2026, Europe/Madrid. Estado: OBSERVADO por operador; causa PENDIENTE.
Identificador: `PICO-RIGHT-DIRECTION-20261016`.

## Observación y estado

El operador comunica: «en teleoperacion cuando movía el brazo derecho hacia
dentro este se iba hacia afuera». Falta distinguir si la mano completa se
desplazaba en sentido contrario o si se abría el codo mientras la mano seguía
al mando. Se solicita esa aclaración, sin pedir repetir el movimiento.

Lectura inicial: backend STOP (`operation_type=1`), tracking activo
(`vr_status=1`), USB ADB presente, conexión XR loopback63901 y ruta Ethernet
eno1/.11.250. No procesos pico_control en la lectura posterior. El agente no
envía STOP, START, HOME, modo, consigna, reset, reinicio ni cambio de parámetros.
No se infiere estado físico de carga, contacto o postura desde estos datos.

## Hallazgos verificados por lectura

- El YAML v4 conserva SHA256
  `01a5ca8acba16bbe136a3bdbcb4a593667d672f8ee9613b98631699fc429b582`.
  No cambió respecto al perfil comprobado antes del ensayo. Escalas de rotación
  1,0 en ambos brazos, cintura/elevador0, colisión activa y topics de cada brazo
  con sus nombres correspondientes. Esto no demuestra que la transformación
  compilada sea correcta en todas las referencias.
- `tele_mode.limb_mode=2`, declarado por el perfil como EndMapTele: controla
  el objetivo del extremo del brazo; el YAML no prescribe copiar la posición
  humana del codo. La solución de articulaciones puede adoptar otra postura.
- En un fragmento de 600 kB del último robot_app se cuentan **297 errores de
  IK derecha**, de 18:41:25.297 a 18:41:31.129 en el reloj nativo del log.
  Cero errores del mismo patrón de IK izquierda en ese fragmento. No son
  recuentos completos de la sesión ni prueban ausencia de otros errores.
- Ejemplos de objetivos fallidos xyzrpy:
  `[0.4079,-0.5488,-0.2019,1.8414,-1.4703,3.0722]` y
  `[0.5499,-0.7247,-0.2345,1.5626,-1.2738,-2.5375]`.
  **Son objetivos rechazados por IK**, no posiciones medidas ni prueba del
  recorrido físico de la mano.
- El registro nativo actualiza varias referencias `right_joy_eef_init` y
  `right_limb_eef_origin` al salir de NotTele. El fragmento no contiene una
  captura sincronizada suficiente de intención humana, poses de mando,
  objetivos y movimiento físico para demostrar inversión de signo.

## Interpretación y siguiente paso

Los fallos IK indican que el solver no encontró una solución para algunos
objetivos de posición/orientación del brazo derecho. Son un hallazgo relevante,
pero no demuestran por sí solos la causa del movimiento contrario comunicado.

Si sólo se abre el codo, distinguir retargeting del extremo de copia de postura
humana. Si la mano completa se mueve en sentido opuesto, revisar referencia de
coordenadas del visor, orientación inicial y correspondencia mando→objetivo.
Estas posibilidades son INFERENCIA, no un diagnóstico confirmado. No corregir
invirtiendo un eje ni alterando límites o colisión sin comparar datos.

Próximo trabajo: resolver la aclaración visual y comparar poses/transformaciones
mediante captura pasiva o análisis offline, sin habilitar actuadores. Esta
intervención no autoriza otra prueba física. Si hubo contacto, fuerza anormal
o fallo de servo, aplicar la [guía de recuperación](../guides/CRUZR_S2_RECUPERACION_TRAS_CONTACTO_TELEOP.md)
antes de cualquier acción; no enviar HOME para probar.

Como contexto externo, el [servicio oficial de XRoboToolkit](https://github.com/XR-Robotics/XRoboToolkit-PC-Service)
documenta poses del visor y de los mandos en su propio sistema de coordenadas.
Ese contrato genérico no acredita cómo las transforma la integración nativa
UBTECH de esta unidad; no se instala el ejemplo de otro robot para resolverlo.

## Evidencia y cambios

`../Humanoide-vla-evidence/20261016T104612Z_PICO_RIGHT_ARM_DIRECTION_READONLY/`:
perfil, inventario de contenedores, robot-app-tail.json, fragment-summary.json,
PC rtm tail, estado de procesos y copias documentales before/after con hashes.
Log original: `/etc/walker/log/motion/robot_app.20261016-162425.65.log` en Motion.
Consultas de sólo lectura; cambios únicamente en documentación del repositorio.
Sin cambios de sistema que revertir, sin commit ni push.
