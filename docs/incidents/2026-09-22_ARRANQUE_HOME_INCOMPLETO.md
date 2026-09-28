# Arranque: HOME incompleto tras liberar E-stop

**22-09-2026 14:12 CEST — HOME-V8-CANDIDATE-01: prueba física completada.**
Una ejecución de la tarea separada devuelve SUCCEED/status4; HOME medido en los
20 ejes, velocidad cero, máximo absoluto 0,002876 rad. Operador confirma recorrido
normal, sin contacto, tirones ni ruidos anormales, y estabilidad final.
Tiempo observado desde inicio del árbol hasta último MetaMove: 15,059 s;
nominal 13,45 s conservado. Hubo 202 rechazos iniciales de consigna durante
0,402 s antes de entrar en el límite del hombro; no se modificaron protecciones.
Instalada, cargada y probada desde esta postura concreta; no recuperación general.
HOME automático sigue en v7; sin reinicio ni rearme de Control Center.
Salida de su Fault previo NO verificada. [Prueba, evidencia y límites](../teleoperation/CRUZR_HOME_V8_CANDIDATA.md).

**22-09-2026 — HOME-V8-CANDIDATE-01 instalada de forma aditiva, sin movimiento.**
Tarea separada home_v8_early_roll_CANDIDATE reparte apertura−0,05/−0,15rad
con el primer ajuste de codo; mantiene13,45s nominales y destinos finalesv7.
No es condicional ni recuperación general. Lectura actual y barridos501,
3tests offline correctos; sincronización/seguimiento y prueba física pendientes.
HOME automáticov7 intacto; sin reinicios, task_list ni acciones. Candidata
instalada, carga nativa pendiente. [Fuentes, límites, backup y receta](../teleoperation/CRUZR_HOME_V8_CANDIDATA.md).

22-09-2026, Europe/Madrid. OBSERVADO en logs y VERIFICADO por muestra20D.
Motion boot_id a6b50ffe-b1c2-4a8a-bd8a-00bdc92135bf, contenedor manipulación
StartedAt11:49:19Z, RestartCount0. No confundir errores del arranque anterior
incluidos en docker logs con la causa de esta instancia.

CC observa liberación a11:51:52Z. Autodiagnóstico passed=true/error0 a11:52:05Z;
StartMotion arranca, HOME interno goal e53c95a2-90a2-4080-955c-bb33367efad7,
árbol cruzr/home iniciado11:52:15Z. Motion rechaza repetidamente left_arm
2-th position cmd0,116678 fuera de[-1,85873;0,0987266]rad. Exceso0,0179514rad
(≈1,03°). No equiparar directamente el signo/índice interno con el raw motor:
existen convenciones de componente distintas. IsReached informa fallo del
brazo izquierdo; árbol FAILURE. CC11:52:18Z: LimbMotion/StartMotion fallan,
reason19 Limb motion failed; transición aFault.

Muestra posterior /mc/actuator_state stamp1790078097 (consulta QoS
best_effort/volatile y tipo explícito):20ejes completos, errores0 y status0x1237.
MEASURED_HOME=0; máximoabsposición1,477990rad, brazos0,401328rad, velocidad
máxima0,001047rad/s, deltaconsigna máximo0,001951rad. Ejemplos fuera de cero:
cabeza pitch−0,344762; elevador11004/11003/11002=0,876478/1,477990/0,578982;
muñeca pitch izquierda0,401328 y derecha0,338818rad. No es HOME completo,
aunque no haya fault de servo en esta muestra. El error de consigna/límite
explica el rechazo observado; origen físico de la postura fuera del intervalo
PENDIENTE, sin atribuir daño, contacto o descalibración sin evidencia.

Diagnóstico exclusivamente de lectura: inventario/logs de ambos hosts y muestra
articular. Sin HOME, rearme, apagado, reinicio ni cambios remotos. Se solicita
confirmación presencial de estabilidad, abrazaderas vacías y ausencia de contacto;
pendiente al registrar. No reejecutar HOME ni el ciclo de cajas automáticamente.
No apagar ni rearmar como prueba; definir recuperación según postura/entorno.

Evidencia y consultas reproducibles: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922T115456Z_BOOT_FAILURE`.
Incluye read-boot.py, logs, actuator-read.py, actuator-state.json y
posture-report.txt. Clasificación reproducible:
`python3 scripts/lib/cruzr_home_posture_gate.py < actuator-state.json`.
Sólo documentación PC modificada; backup before/ y after/, SHA256SUMS.
Reversión documental selectiva; no se cambia la configuración de arranque.


## Revisión del HOME instalado y primera etapa — 22-09-2026

Operador confirma robot estable, abrazaderas vacías y sin contacto. Autoriza
revisión; no movimiento. Redescubrimiento y lectura del XML remoto verifican
SHA1e6e2fb7ddc598dc3793d093c283c82063507df0e53b70a18e161cab883a6f03,
idéntico a cruzr_internal_home_body_first_v7_13s.xml. libmeta_move.so conserva
SHAbfeab1c7a295b58cd96fddd20916fc3f7fe16bd8c8ad1e77720f48aad34ccc69.
No hubo sustitución de tarea/biblioteca por esta revisión.

**VERIFICADO:** el primer tramo izquierdo es delta_joint_angles
[0;0;0;−0,03;0;0;0] en1s, no la apertura de hombro que viene después.
El objetivo registrado en coordenadas de componente es
[−0,0670158;0,116678;0,010642;−0,100851;0;0,401328;0,00431432].
Mantiene el roll del hombro fuera de su máximo0,0987266. Se contaron500 rechazos
ValidateCmdWithLimit del segundo ángulo; IsReached deja error de codo0,0299041rad,
prácticamente todo el desplazamiento solicitado. El brazo derecho sí termina
su paso de codo SUCCESS. El fallo izquierdo interrumpe el paralelo: lifter,
waist y head pasan aAborted, sin completar3,75s. No alcanza las etapas de
bajada y cierre. El signo del motor4002 (−0,116870 en la muestra posterior)
no contradice el signo positivo del componente; no intercambiar sus convenciones
para generar una recuperación.

Es la misma limitación documentada en
[el incidente18-09](2026-09-18_HOME_V7_ARRANQUE_HOMBRO_FUERA_LIMITE.md).
Allí una corrección puntual del hombro permitió después HOME, con revisión
geométrica y supervisión específicas. Ese XML declara uso para aquella postura;
no está validado para la actual. La postura anterior al apagado de HOY no se
ha reconstruido, por lo que no se atribuye el origen del exceso a un contacto,
paro, caída o descalibración específicos.

Conclusión: HOMEv7 se cargó según lo previsto, pero su etapa de codo presupone
que los restantes ejes del brazo estén dentro de límites. No cubre este estado.
Siguiente trabajo posible: valorar una recuperación puntual del hombro con
muestra fresca, convenciones/límites y barrido del efector actual; sólo después
validar HOME desde el estado resultante. Cambiar el orden o reutilizar la receta
histórica sin esa validación no constituye una solución general.
No se preparó ni ejecutó una orden de recuperación en esta revisión.

Evidencia reproducible read.py/read.jsonl, home.txt, meta.txt, log.txt y
backups before/after con SHA256SUMS: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260922T115935Z_HOME_REVIEW`.
Cambios únicamente documentales PC; reversión selectiva, sin rollback remoto.
