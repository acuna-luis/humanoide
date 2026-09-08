# READY → HOME: ejecución y cierre de ida/vuelta

Fecha: 2026-09-08. VERIFICADO: recuperación SUCCEED/status=4 y HOME medido.
OBSERVADO por el operador: recorrido correcto y estado estable/libre de contacto.
Resultado: `PASS_READY_TO_HOME_PHYSICAL_AND_OPERATOR_CONFIRMED`.

## Autorización y comprobaciones

Solicitud: «Ahora ejecuta mientras lees todo lo necesario: READY a HOME».
Se conserva la revocación del bloqueo anterior por el propietario. El operador
confirmó «sí» a condiciones actuales: abrazaderas vacías/libres de contacto,
recorrido sin caja/mesa/personas, cargador desconectado, ruedas bloqueadas,
ambos paros liberados, sin otro mando activo y persona junto al paro.
Se revisaron XML/YAML, runner histórico y contraste de rutas antes de la acción.
No se modificaron ni eliminaron bloqueos compartidos ni protecciones de Motion.

- Docker ya activo y contenedores redescubiertos en ambos hosts.
- Preflight E6.0G/canónico PASS; HW_TYPE=cruzr_s2_v1, paros 0/0, cargador 0,
  baterías 61,7/91,5 %, actuadores habilitados y acciones listas.
- Última transición de CC observada JoystickMode. Action server 1 y tipo
  /mc/manipulation/action = mc_task_msgs/action/ArmTask redescubierto.
- READY fresco completo: brazos error máximo 0,001842 rad, velocidad cero;
  cabeza, cintura y elevador contrastados; salud de actuadores aprobada.
- XML recovery instalado/local SHA-256
  9e47b6ee37f83f75036c203b809e9a93284d459316764615496a872ca3b4fbcc.
- YAML recovery instalado/local SHA-256
  bd5f588a4e69c3f5fc38796cccc1adffded293bc5355b67ee18d54f321b6e3b0.
- Task-list 224c6fca…fac1b, proceso posterior al archivo;
  s2_vla_e6_0_exact_recovery registrado, Reverse=false/TimeRatio=1.0.

## Acción y medidas posteriores

Tarea: s2_bio_vla/s2_vla_e6_0_exact_recovery, yaml_args={}.
Ruta: READY B→A→staging→HOME; cabeza y cintura a cero en la última etapa.
Goal único: fc84badc-971b-42d0-b8a6-5f59a0f10849.
Resultado SUCCEED/status=4, state=1101001; salida SSH 0.
No hubo reintento, checkpoint, cambio de modo ni orden adicional de movimiento.

HOME final:

| Comprobación | Resultado |
|---|---|
| 20 ejes de cuerpo/brazos | Presentes, HOME por actuadores y joints nombrados |
| Máximo absoluto de posición | 0,002684466 rad |
| Máximo de brazos | 0,000959 rad |
| Velocidad final | 0 rad/s |
| Error de actuador/estado | Sin faults, habilitados |
| Delta máximo consigna−posición | 0,002684 rad |
| VLA | exited/exited |
| /mc/sdk/robot_command | writers 0, readers 2 |
| Confirmación visual posterior | Operador: «todo bien» ante pregunta sobre recorrido, estabilidad y ausencia de contacto |

## Lecturas durante la maniobra

Se lanzó una suscripción pasiva acotada de whole_joint_states en paralelo con
la acción. Guardó 2.251 mensajes JSON completos, sin cola JSON truncada, con
sellos desde 1788850018.000640134 hasta 1788850022.500602740 (4,500 s de muestras).
El rc=124 corresponde al timeout deliberado de 7 s de la captura, NO a un fallo
de la acción, que terminó con rc=0 y SUCCEED.

La primera muestra ya tenía máximo articular 0,892681 rad, por tanto la captura
no demuestra cobertura desde el inicio de READY. La última da 0,002780 rad.
Velocidad máxima muestreada entre ejes no rueda: 2,049366 rad/s. Es un dato
reportado por joints durante esta tarea vendor; no equivale a validar los
límites de diseño offline de 0,15 rad/s ni aceleración/frenado. No se cambió
TimeRatio ni se aplicó el candidato lento. No se capturó FT continuo ni se
implementó un monitor que ordenara parada. La protección runtime existente
y la supervisión física se conservaron. No hay monitor persistente.

## Validación conjunta y reanudación

La [ida anterior](2026-09-08_READY_AUTORIZADO_PROPIETARIO.md) y esta vuelta
constituyen un ciclo HOME→READY→HOME completado con el montaje actual, ambos
extremos medidos y confirmaciones del operador sin problemas/contacto.
Estado: **PASS físico de ida y vuelta para este ensayo**.

No transforma en PASS los cálculos geométricos inconclusos, registro del útil,
incertidumbre, equivalencia exacta de curvas o respuesta de parada. No autoriza
repetición desatendida, movimiento desde postura arbitraria, ENTRY ni VLA.

Estado final documentado: HOME estable/libre de contacto. Revalidar estado
antes de la siguiente acción; no repetir recuperación por ver una nota antigua.
Cambios persistentes: documentación y evidencia local; ningún archivo/servicio
remoto, XML, YAML o protección cambiado. No hay rollback de configuración.
Los wrappers históricos conservan su bloqueo técnico; esta ejecución específica
se envió por SSH/ROSA bajo autorización vigente con los gates anteriores.

Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260908T064550Z_OWNER-READY-HOME/`, con manifiesto SHA-256,
preflight, configuración, muestras, captura, comando, goal/resultado y confirmación.
