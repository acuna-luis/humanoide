# Preguntas abiertas para UBTECH — Cruzr S2

Fecha: 2026-08-06<br>
Alcance: preguntas derivadas exclusivamente de los tres paquetes inspeccionados. `P0` bloquea una decisión de viabilidad/seguridad; `P1` bloquea diseño o estimación; `P2` afecta industrialización/operación.

## 1. SDK y versiones

### Q01 — P0. ¿Cuál es la combinación exacta y homologada de firmware, sistema v0.2.0, ControlCenter, `sdk_controller`, `t800_mc_server`, efector e imágenes VLA para el número de serie que recibiremos?

- **Por qué:** los tres lotes se generaron en fechas distintas y mezclan nombres `utars`, `walker_s2`, `cruzr`, `s2` y `cruzr_s2`.
- **Evidencia local:** el manual es v2.1; `utars-udoke-config-v0.2.0_offline-001/images/{motion,vision}.tar` contiene integraciones del 2026-06-19; `cruzrss2_vla_pack-002/docker_images/*.tar` es del 2026-04-24.
- **Bloquea:** baseline reproducible, garantía, actualización y primera puesta en marcha.

### Q02 — P1. ¿Cuál de `cruzrss2_vla_pack-002/codes` y `codes-S2` es canónica, y qué significan exactamente las diferencias de lifter y poses XML?

- **Por qué:** sólo tres fuentes comunes difieren, pero el comportamiento cambia: S2 acepta joints de lifter ausentes como cero y luego descarta sus tres acciones.
- **Evidencia local:** `codes-S2/.../gr00t_inference.py:437-468`; `codes-S2/.../executor_node_sdk.py:37-43,272-295`.
- **Bloquea:** selección de código, control de altura y seguridad de ejecución.

### Q03 — P1. ¿Por qué el manual instala `ubt_robot` 1.0.0 y marca x86_64 como no abierto cuando el paquete entrega wheels 1.0.9 y bibliotecas x86_64?

- **Por qué:** una versión/API incorrecta puede fallar silenciosamente o quedar fuera de soporte.
- **Evidencia local:** `SDK/python/ubt_api_tiny_python.0624.tar.xz`; `SDK/c++/ubt_api_tiny_colcon.0624.tar.xz`; manual SDK secciones 6.1.2.
- **Bloquea:** lenguaje/arquitectura de la aplicación y soporte contractual.

## 2. Base móvil

### Q04 — P0. ¿Qué precisión y repetibilidad XY/yaw garantiza `NavTo` en llegada normal y en “precise positioning”, con robot cargado, y cuáles son las condiciones de suelo/mapa?

- **Por qué:** el robot debe quedar dentro del alcance y tolerancia del grasp sin reposicionamiento manual.
- **Evidencia local:** el manual define `A000002 NavTo` con `pose` o `targetId`, pero no aporta error ni repetibilidad.
- **Bloquea:** posibilidad de recoger/depositar cajas de forma autónoma.

### Q05 — P0. ¿Está permitido mover la base sosteniendo una caja; cuál es el payload dinámico, velocidad, aceleración, distancia de frenado y estabilidad máxima en esa condición?

- **Por qué:** el ciclo exige transportar la caja y el robot pesa 188 kg; no hay política combinada base-brazos.
- **Evidencia local:** el VLA sólo produce 20 joints de torso/brazos y no ruedas: `data/.../meta/info.json:86-112`; el tutorial exige posicionamiento previo manual.
- **Bloquea:** arquitectura del ciclo La Palma y evaluación de vuelco/deslizamiento.

### Q06 — P1. ¿Qué interfaces, estados, tolerancias, fallos y hardware requiere la recarga EVT4/Wi-Fi?

- **Por qué:** el runtime configura `recharge_task`, pero no hay API de usuario ni secuencia de recovery.
- **Evidencia local:** `utars-udoke-config-v0.2.0_offline-001/vision/.metafiles/nav.metafile.yml:15-30`; `system.metafile.yml:24-43`.
- **Bloquea:** operación prolongada y cálculo de disponibilidad.

## 3. Brazos

### Q07 — P0. ¿Existe un controlador cartesiano, de impedancia/admitancia o un planificador de movimientos soportado oficialmente para Cruzr S2? Facilitar API, frecuencia, frames y ejemplos bimanuales.

- **Por qué:** el paquete sólo ofrece FK/IK y control articular; no hay MoveIt, planning scene ni servo cartesiano.
- **Evidencia local:** manual SDK sección 5.11; `URDF/cruzr_s2_description.zip`; ausencia de MoveIt/OMPL en los árboles inspeccionados.
- **Bloquea:** pregrasp preciso, contacto, inserción y volcado controlado.

### Q08 — P0. ¿Cuáles son los límites homologados por joint de posición, velocidad, aceleración, jerk, esfuerzo y temperatura para control SDK, y qué límites aplica el firmware?

- **Por qué:** el ejecutor VLA sólo comprueba 6.28 rad/s global; los brazos están documentados a 30 rpm máximo, aproximadamente 3.14 rad/s.
- **Evidencia local:** `codes-S2/.../executor_node_sdk.py:88-166`; tabla de joints del manual SDK.
- **Bloquea:** validación del ejecutor y movimiento seguro con carga.

### Q09 — P1. ¿Cuál es el workspace, error de pose, repetibilidad y comportamiento de IK cerca de singularidades para cada brazo y ambos simultáneamente?

- **Por qué:** `CalcJointAnglesForEndPose` existe, pero no se documentan convergencia ni garantías.
- **Evidencia local:** manual SDK sección 5.11 y bibliotecas `/opt/walker/manipulation`.
- **Bloquea:** alcance a cajas/palés/cinta y diseño de estaciones.

## 4. Manos y pinzas

### Q10 — P0. ¿Qué efector exacto se suministrará: clamp/placas, PGC-140-50, mano v3 o v4? Facilitar `HW_TYPE`, CAD, masa, TCP, CoG, brida, cableado y payload reducido.

- **Por qué:** teleoperación admite cuatro configuraciones y el VLA se llama `utars_clamp`; no hay confirmación del hardware real.
- **Evidencia local:** manual SDK sección 7.1; `data/.../meta/info.json:2-3`; `codes-S2/.../s2_vla_pick_large_teleop_ready.xml:5-16`.
- **Bloquea:** diseño mecánico, agarre, payload, calibración y compra.

### Q11 — P0. ¿Cómo se agarra la caja de 600 × 400 × 220 mm del demo y qué acciona el “clamp”, dado que las acciones VLA no contienen pinza/mano?

- **Por qué:** la PGC abre sólo 50 mm; el checkpoint manda joints de brazos/cabeza/lifter/cintura, no efector.
- **Evidencia local:** manual SDK 7.3; `data/.../meta/info.json:86-112`; `codes-S2/.../s2_vla_pick_large_teleop_ready.xml:16`.
- **Bloquea:** interpretación del demo y factibilidad de caja sin asas.

### Q12 — P1. ¿Qué exactitud, repetibilidad, banda de control y vida útil tiene el mando de 0–100 N de la PGC, y cómo se calibra la detección `grip/dropped`?

- **Por qué:** el mensaje expone fuerza mandada y estados, pero no error, regulación ni ensayos.
- **Evidencia local:** manual SDK secciones 5.10.1–5.10.2.
- **Bloquea:** umbrales de agarre, daño de caja y detección de deslizamiento.

## 5. Payload

### Q13 — P0. Facilitar curvas de payload por brazo y bimanual frente a alcance, orientación del TCP, aceleración, lifter y centro de gravedad; aclarar si los 15 kg incluyen efectores.

- **Por qué:** sólo se publica “15 kg máximo con ambos brazos”; no basta para carga dinámica o volcado.
- **Evidencia local:** manual SDK, especificación general, “双臂最大负载 15kg”.
- **Bloquea:** peso máximo de caja, factor de seguridad y ciclo.

### Q14 — P0. ¿Cuál es la masa máxima ensayada de la caja del tutorial VLA y la tasa de éxito para cada masa/llenado/centro de gravedad?

- **Por qué:** el tutorial fija dimensiones y altura, pero omite peso y distribución del contenido.
- **Evidencia local:** manual SDK sección 7.3.1; dataset `utars_clamp_and_place_large_box...`.
- **Bloquea:** equivalencia con las cajas reales de La Palma.

## 6. Visión

### Q15 — P0. Entregar contrato completo del `box_pose_estimator_node`: topics/services, tipo de mensaje, frames, clases, modelo, rango, latencia, precisión y condiciones de iluminación/oclusión.

- **Por qué:** existe un contenedor configurado, pero no su interfaz ni model card.
- **Evidencia local:** `utars-udoke-config-v0.2.0_offline-001/vision/.metafiles/box_pose_estimation.metafile.yml:1-12`; etiqueta pose 6D 1.1.4 en `images/vision.tar`.
- **Bloquea:** decidir si se reutiliza la percepción UBTECH o se desarrolla una propia.

### Q16 — P0. ¿Por qué el estimador usa `pose_6d_estimation_640_400_byd.json` y `WALKER_PROJECT_ID=walker_s2` en un Cruzr S2? ¿Qué configuración/modelo corresponde al cliente?

- **Por qué:** su nombre sugiere variante/cliente distinto y puede no reconocer las cajas objetivo.
- **Evidencia local:** `vision/.metafiles/box_pose_estimation.metafile.yml:4-9`.
- **Bloquea:** compatibilidad de percepción y licencia del modelo.

### Q17 — P1. ¿Qué procedimiento oficial calibra intrínsecos, extrínsecos, hand-eye y TCP tras instalar un efector? ¿Qué tolerancia y periodicidad se garantizan?

- **Por qué:** hay CameraInfo, una cadena TF y un calibration node, pero no protocolo de aceptación métrico.
- **Evidencia local:** manual SDK sección 1.4.2; `vision/.metafiles/drivers.metafile.yml:63-68`; `system.metafile.yml:2-16`.
- **Bloquea:** error total de grasp/deposición.

## 7. Manipulación de cajas

### Q18 — P0. ¿Existe una skill oficial que integre navegación, detección 6D, grasp, cierre de efector, elevación, transporte y place, o el tutorial 7.3 sólo cubre movimiento de brazos?

- **Por qué:** la API define skills genéricas y el tutorial VLA, pero el runtime VLA no usa navegación ni pinza.
- **Evidencia local:** manual SDK secciones 6.2.1 y 7.3; `gr00t_inference.py:24-120`; `executor_node_sdk.py:37-43`.
- **Bloquea:** alcance real del SDK frente a desarrollo propio.

### Q19 — P0. ¿Está soportado volcar una caja cargada sobre cinta? Facilitar límites de ángulo, CoG, carga, velocidad, fuerzas, secuencia y pruebas de estabilidad.

- **Por qué:** no hay tarea, dato, modelo ni ejemplo de inclinación/vaciado.
- **Evidencia local:** las únicas tareas son cuatro pick/place de estante: `data/.../meta/tasks.jsonl:1-4`.
- **Bloquea:** función central del caso La Palma.

### Q20 — P1. ¿Qué estrategia recomiendan para cajas sin asas: placas pasivas bimanuales, dedos adaptados, vacío u otro end-effector? ¿Qué materiales/rigideces se han probado?

- **Por qué:** una PGC de 50 mm no abraza una caja de 600 mm; el clamp no está descrito mecánicamente.
- **Evidencia local:** manual SDK secciones 5.10 y 7.3.
- **Bloquea:** concepto de agarre y hardware adicional.

### Q21 — P1. ¿Cómo se coordinan base, lifter y ambos brazos sin perder estabilidad? ¿Existe interlock que impida mover la base en posturas/cargas peligrosas?

- **Por qué:** los módulos existen por separado y el VLA S2 descarta el lifter.
- **Evidencia local:** `executor_node_sdk.py:37-65,288-295`; `nav.metafile.yml`.
- **Bloquea:** arquitectura de la máquina de estados y safety envelope.

## 8. VLA y entrenamiento

### Q22 — P0. ¿Cuál es la tasa de éxito del checkpoint 40000 por tarea, con intervalos de confianza, y dónde están los conjuntos de validación/test y logs de evaluación física?

- **Por qué:** sólo hay split `train`, `best_metric=null` y `best_model_checkpoint=null`.
- **Evidencia local:** `data/.../meta/info.json:4-12`; `weight/checkpoint-40000/trainer_state.json`.
- **Bloquea:** decidir si el checkpoint es demostración o activo reutilizable.

### Q23 — P0. ¿Por qué `InferenceTask.action` asigna IDs 0=pick lower, 1=pick upper, 2=place lower, 3=place upper, mientras dataset/YAML asignan 1=place lower y 2=pick middle?

- **Por qué:** una orden puede ejecutar la conducta equivocada.
- **Evidencia local:** `codes-S2/.../InferenceTask.action:1-7`; `.../configs/utars_clamp_and_place_large_bio_box_lock_lifter.yaml:6-10`; `meta/tasks.jsonl:1-4`.
- **Bloquea:** cualquier ensayo físico seguro del VLA.

### Q24 — P0. ¿Cuál es la corrección oficial para que el action no llame `goal_handle.succeed()` tras un resultado fallido y no marque éxito después de excepciones sin chunks?

- **Por qué:** el supervisor recibiría éxito falso.
- **Evidencia local:** `gr00t_inference.py:240-251,345-380`.
- **Bloquea:** orquestación, recuperación y aceptación del software.

### Q25 — P1. ¿Por qué se registraron 12 señales F/T pero la inferencia sólo construye RGB + posiciones articulares? ¿Existe checkpoint multimodal que use fuerza?

- **Por qué:** el control de contacto robusto requiere feedback; el código actual lo ignora.
- **Evidencia local:** `meta/info.json:46-84`; `model_interface_general_ros2.py:187-246`.
- **Bloquea:** estrategia de compliance, slip y agarre adaptativo.

### Q26 — P1. ¿Qué GPU/VRAM, tiempo, almacenamiento y versiones exactas se requieren para fine-tuning; está soportado hacerlo en Orin o sólo en servidor externo?

- **Por qué:** el script soporta CUDA/multi-GPU pero no documenta modelo de GPU ni VRAM.
- **Evidencia local:** `gr00t_finetune.py:36-127,344-459`; checkpoint/modelo de ~7.6 GB más optimizador.
- **Bloquea:** presupuesto y arquitectura de entrenamiento.

### Q27 — P1. Entregar Dockerfile, commit Isaac-GR00T, lockfiles y hashes de imágenes/checkpoint/dataset.

- **Por qué:** la imagen clonó una rama externa y sustituyó todos los `==` por `>=`; no hay checksums.
- **Evidencia local:** historial interno de `docker_images/vla_inference_node_sdk.tar`; ausencia de manifiestos de integridad.
- **Bloquea:** reproducción, mantenimiento y supply-chain approval.

## 9. Teleoperación y demostración

### Q28 — P1. ¿Qué kit exacto está soportado para cada efector: Pico/VR, Xsens, exoesqueleto o guantes? Facilitar modelos, firmware, licencias, calibración, latencia y disponibilidad regional.

- **Por qué:** el manual enumera combinaciones, pero no se entrega hardware ni SOP Cruzr S2 Teleoperation.
- **Evidencia local:** manual SDK sección 7.1; `motion/.metafiles/motion.metafile.yml:11,31-45`.
- **Bloquea:** método de captura de demostraciones y coste.

### Q29 — P1. ¿Cómo se convierte un `.motion` grabado por `manipulation_outline_sdk record` a LeRobot Parquet/MP4 con sincronización, labels y F/T?

- **Por qué:** se entregan recorder/player/editor y un dataset LeRobot, pero no el puente entre ambos.
- **Evidencia local:** manual SDK 7.1.2.1–7.1.2.3; `data/.../meta/info.json`.
- **Bloquea:** pipeline de programación por demostración.

### Q30 — P2. ¿Existe guiado manual por gravedad/hand-guiding certificado o sólo teleoperación remota?

- **Por qué:** no se encontró modo de enseñanza por empuje físico del brazo.
- **Evidencia local:** manual SDK sólo documenta teleoperación y control articular.
- **Bloquea:** selección del método de teaching para planta.

## 10. Simulación

### Q31 — P1. ¿Existe paquete oficial Isaac Sim/Gazebo/MoveIt para estos URDF/USD, con dinámica, colisiones, actuadores, sensores y controlador Cruzr S2?

- **Por qué:** hay URDF/USD, pero el URDF no contiene transmission/ros2_control y no hay launch de simulación.
- **Evidencia local:** `SDK/URDF/cruzr_s2_description.zip`; `SDK/USD/*.zip`.
- **Bloquea:** desarrollo sin robot, validación de alcance/colisión y sim-to-real.

### Q32 — P2. ¿Qué licencia permite usar/modificar los USD y las mallas para una simulación comercial del cliente?

- **Por qué:** no hay licencia global adjunta.
- **Evidencia local:** `SDK/USD/Collected_cruzr_s2_v1.zip`; `SDK/USD/Collected_hand_v3_usd.zip`.
- **Bloquea:** compartir la célula virtual con integradores/clientes.

## 11. Despliegue

### Q33 — P0. ¿Está soportada la imagen VLA CUDA 12.6.3/cuDNN 9.3 sobre el host/runtime uDoke CUDA 12.2/cuDNN 8.9, y qué versión exacta de JetPack/driver exige?

- **Por qué:** hay dos stacks CUDA distintos en la misma Orin.
- **Evidencia local:** configuración/historial interno de `docker_images/vla_inference_node_sdk.tar` y `images/vision.tar`.
- **Bloquea:** arranque de inferencia y riesgo de incompatibilidad ABI/driver.

### Q34 — P1. ¿Cómo se integra VLA en uDoke con arranque ordenado, healthchecks, reinicio, logs y parada, en vez de cinco terminales manuales?

- **Por qué:** el tutorial arranca nodos/containers manualmente y no hay metafile VLA.
- **Evidencia local:** manual SDK 7.3.3–7.3.4; `utars-udoke-config.../*.metafile.yml`.
- **Bloquea:** industrialización y recuperación automática.

### Q35 — P1. Entregar procedimiento oficial de backup, actualización y rollback, incluidas firmas y criterios de compatibilidad.

- **Por qué:** los scripts modifican kernel, GRUB, systemd, GPU, red y TF; no hay rollback/checksums.
- **Evidencia local:** `replace.json:2-37`; `shells/rt_patch_x86.sh`; `shells/trim_service.sh`; ausencia de firmas.
- **Bloquea:** mantenimiento seguro y recuperación ante fallo.

## 12. Seguridad

### Q36 — P0. Facilitar arquitectura de seguridad funcional del robot: categorías/PL/SIL, cadena del E-stop, STO, distancias de parada y señales disponibles para safety PLC.

- **Por qué:** sólo se documenta botón físico y fallos de servo; no hay interfaces/certificados de célula.
- **Evidencia local:** manual SDK secciones 2.1–2.5 y tabla de fallos.
- **Bloquea:** risk assessment y uso industrial legal/seguro.

### Q37 — P0. ¿Cómo debe protegerse el modo SDK cuando desactiva el control interno? ¿Qué watchdog, deadman y transición segura están soportados?

- **Por qué:** UBTECH advierte que al tomar motores sale el control de movimiento y el desarrollador asume todos los joints.
- **Evidencia local:** manual SDK, advertencia tras `cc.api.sdk.switch_mc_mode`.
- **Bloquea:** uso de `/mc/sdk/robot_command` y del ejecutor VLA.

### Q38 — P0. ¿Qué solución oficial ofrece detección de colisión/self-collision y límites de fuerza durante VLA?

- **Por qué:** el ejecutor sólo comprueba velocidad global y no observa E-stop, F/T, torque, posición, aceleración o colisión.
- **Evidencia local:** `executor_node_sdk.py:88-166,210-248,342-376`.
- **Bloquea:** cualquier prueba con carga/personas cerca.

### Q39 — P1. ¿Cómo se autentican y restringen ControlCenter 51000, rosbridge, web backend y servicios de host network? ¿Se pueden activar TLS, tokens y ACL ROS 2?

- **Por qué:** el token de API puede estar vacío y varios servicios usan host network/puertos expuestos.
- **Evidencia local:** manual SDK sección 6.1.1.2; `vision/.metafiles/system.metafile.yml:71-86`; `web.metafile.yml:1-40`.
- **Bloquea:** aprobación de ciberseguridad de planta.

### Q40 — P1. Confirmar si `shells/cmd_proxy.sh` está soportado o debe eliminarse; explicar threat model del FIFO que ejecuta `eval` como servicio root.

- **Por qué:** supone ejecución arbitraria local y no aparece en `replace.json`.
- **Evidencia local:** `utars-udoke-config-v0.2.0_offline-001/shells/cmd_proxy.sh:1-183`, especialmente `:63-74`.
- **Bloquea:** aceptación del paquete offline por seguridad IT/OT.

## 13. Licencias

### Q41 — P0. Facilitar licencia comercial y de redistribución para SDK, bibliotecas, mensajes, dataset, checkpoint, modelos de pose/nav, imágenes Docker, URDF/USD y teleoperación.

- **Por qué:** hay licencias parciales Apache/BSD, pero no licencia superior ni derechos sobre datos/pesos/binarios UBTECH.
- **Evidencia local:** `gr00t_finetune.py:1-14`; package.xml de mensajes; ausencia de `LICENSE` global.
- **Bloquea:** contrato, entrega al cliente y modificación/redistribución.

### Q42 — P1. ¿Qué funciones requieren licencia de pago, suscripción cloud, dongle o soporte anual (VLA, pose 6D, navegación, teleop, actualizaciones)?

- **Por qué:** se incluyen binarios cerrados y referencias a servicios internos/cloud sin lista de entitlements.
- **Evidencia local:** `images/vision.tar`, `images/motion.tar`; `system.metafile.yml:47-70`.
- **Bloquea:** coste total y continuidad operativa.

## 14. Soporte

### Q43 — P1. ¿Qué SLA, canal técnico, ventana de versiones y política de CVE/patches se ofrece para un despliegue industrial en España, EE. UU. y Polonia?

- **Por qué:** el manual sólo muestra un canal general y no un proceso LTS/industrial.
- **Evidencia local:** manual SDK FAQ final; imágenes con múltiples componentes versionados.
- **Bloquea:** plan de mantenimiento y compromisos al cliente.

### Q44 — P1. ¿Proporcionará UBTECH fuente o símbolos/documentación de los componentes cerrados necesarios para diagnosticar `t800_mc_server`, `sdk_controller`, navegación y pose 6D?

- **Por qué:** los componentes clave sólo aparecen como binarios dentro de imágenes.
- **Evidencia local:** etiquetas internas de `images/motion.tar` y `images/vision.tar`.
- **Bloquea:** capacidad de resolver incidencias sin dependencia total del fabricante.

## 15. Formación

### Q45 — P1. ¿Qué formación oficial incluye commissioning, SDK/ROSA, navegación, calibración, teleop/VLA, mantenimiento y seguridad, y sobre qué versión exacta?

- **Por qué:** el material es tutorial parcial y contiene inconsistencias de versión/flujo.
- **Evidencia local:** manual SDK v2.1 y SOPs entregados.
- **Bloquea:** planificación del equipo y calendario de integración.

### Q46 — P2. ¿Puede UBTECH realizar una sesión hands-on con el efector exacto y entregar ejercicios/logs de fallos y recovery?

- **Por qué:** no hay procedimientos de recovery de misión ni tests automatizados.
- **Evidencia local:** `gr00t_inference.py:240-251,345-380`; ausencia de suite de integración.
- **Bloquea:** curva de aprendizaje y preparación de FAT/SAT.

## 16. Prueba “lifting box process testing”

### Q47 — P0. Solicitamos una prueba presenciada de proceso completo: ¿puede UBTECH demostrar pick bimanual, lift, transporte de base, place, inclinación/vaciado y retorno de caja vacía con la caja real del cliente?

- **Por qué:** el material sólo prueba conceptualmente pick/place de una caja dimensionalmente fija sobre estante y requiere posicionar la base manualmente.
- **Evidencia local:** manual SDK 7.3.1–7.3.4; `meta/tasks.jsonl:1-4`.
- **Bloquea:** decisión go/no-go de La Palma.

### Q48 — P0. ¿Qué protocolo de aceptación propone UBTECH para esa prueba: al menos 100 ciclos por variante, masas/llenados, tasa de éxito, tiempo de ciclo, precisión, incidentes, recuperaciones y vídeo+rosbag+logs?

- **Por qué:** no se entregan métricas de evaluación física ni test split.
- **Evidencia local:** `meta/info.json:4-12`; `trainer_state.json` sin best metric/checkpoint.
- **Bloquea:** comparación objetiva con requisitos del cliente y garantía de rendimiento.

### Q49 — P0. ¿La prueba incluirá fallos inducidos de pose, iluminación, caja deformada, agarre parcial, deslizamiento, persona/obstáculo, pérdida de cámara y reinicio de nodo?

- **Por qué:** no hay evidencia de recuperación; el action incluso puede reportar éxito falso.
- **Evidencia local:** `gr00t_inference.py:240-251,303-380`; `executor_node_sdk.py:135-166`.
- **Bloquea:** robustez y análisis de riesgos.

### Q50 — P1. ¿UBTECH firmará un informe que relacione cada resultado con versión, número de serie, efector, calibraciones, checkpoint/hash y parámetros?

- **Por qué:** hoy no hay hashes ni baseline inequívoca.
- **Evidencia local:** ausencia de firmas/checksums y coexistencia de variantes `codes`/`codes-S2`.
- **Bloquea:** trazabilidad contractual del FAT y transferencia al sitio.

## Las 15 preguntas que deben enviarse primero

1. Q47 — demostración completa con la caja real.
2. Q13 — curvas de payload dinámico por brazo/bimanual.
3. Q10 — efector exacto y CAD/TCP/CoG.
4. Q11 — mecanismo real de clamp del demo.
5. Q04 — precisión/repetibilidad de navegación.
6. Q05 — transporte de caja con base móvil.
7. Q19 — soporte y límites de volcado/vaciado.
8. Q15 — contrato/métricas del estimador de pose 6D.
9. Q07 — control cartesiano/fuerza/planificación oficial.
10. Q08 — límites dinámicos homologados por joint.
11. Q36 — arquitectura de seguridad funcional y señales safety.
12. Q38 — colisión/self-collision y fuerza bajo VLA.
13. Q23 — corrección de IDs de tarea contradictorios.
14. Q33 — compatibilidad CUDA/JetPack/driver.
15. Q41 — licencias comerciales y de redistribución.
