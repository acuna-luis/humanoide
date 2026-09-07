# Auditoría de contactos y daños: PICO, HOME y arranque v0.2.0

**Fecha:** 2026-09-07. **Unidad:** WAE001UBT60000669.
**Estado:** auditoría documental y de logs realizada; causa raíz completa,
inspección material y revalidación física **ABIERTAS**.
**Alcance de esta intervención:** lectura remota de logs/configuración y trabajo
local; cero órdenes de movimiento, ROS, rearmados, reinicios o cambios remotos.

## 1. Dictamen ejecutivo y corrección de la explicación anterior

1. **VERIFICADO:** el 04-09 el arranque ejecutó internamente `cruzr/home`.
   No fue sólo energización ni una deriva pasiva. El brazo izquierdo recibió
   objetivo articular cero, se registró fuerza excesiva y la tarea abortó.
2. **VERIFICADO:** el siguiente arranque volvió a ejecutar `cruzr/home` y
   terminó con éxito. «No enviamos HOME desde el PC» **no** equivale a
   «el robot no ejecutó HOME». Se corrige expresamente esa explicación previa.
3. **OBSERVADO/TESTIMONIO:** hubo contacto clamp–torso y daños posteriores.
   La secuencia comunicada por el propietario es: primer contacto de la foto 3,
   perforación/marca de la foto 1 y, después, rayado/agrietamiento bilateral,
   posiblemente al volver a HOME. El propietario confirmó durante esta auditoría
   que **los problemas de las fotos ocurrieron el 4 de septiembre cerca de las
   14:00 de España** (Madrid, UTC+02), compatible con el fallo de las 13:58 y
   el segundo HOME de las 14:20. El 28-08 es sólo antecedente, no origen atribuido
   a estas fotos. No hay vídeo sincronizado que feche cada marca.
4. **INFERENCIA FUERTE, NO CAUSA ÚNICA DEMOSTRADA:** invertir las clamps pudo
   situar las patillas dentro de la trayectoria del cuerpo. El cambio de montaje
   fue confirmado por el propietario, pero no conocemos su hora exacta ni
   disponemos de transformaciones medidas antes/después para atribuir cada daño.
5. **VERIFICADO EN CÓDIGO:** la comprobación geométrica E6.0K heredó el centro
   del proxy; no midió la transformación de ambas herramientas reales. Su PASS
   matemático no valida el montaje invertido ni certifica el montaje de fábrica.
6. **NO DEMOSTRADO:** que el checkpoint causara este contacto. La transición
   E6.1C fue rechazada antes del goal y el incidente está asociado al HOME de
   arranque. No confundirlo con E6.0Y anterior: allí sí hubo inferencia y un
   publicador transitorio, pero se registraron cero frames enviados.

No es correcto resumirlo como «imprevisibilidad del VLA» ni sólo como «clamps al
revés». Fallaron las garantías de integración: montaje real no verificado,
trayectoria de retorno no cualificada para esa postura y una ruta automática
de arranque que no pasaba por nuestros bloqueos del PC.

## 2. Evidencias, integridad y límites

### 2.1 Conservación

Directorio sellado local:

`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260907T053541Z_CONTACT-AUDIT`

- 108 logs Motion (41.904.291 bytes) y 21 Vision (2.143.565 bytes).
- Fechas seleccionadas: 25–28 de agosto y 3–4 de septiembre, archivos
  `robot_app`, `rosa_control_node`, `cc_main`, `ecat_err_handler_service`.
- SHA-256 por archivo calculado al leerlo remotamente y contrastado localmente;
  tar originales, manifests, colector y metadatos conservados. 137 artefactos
  locales verificados. Los hashes prueban integridad desde la captura, no
  autenticidad histórica ni ausencia de archivos borrados/rotados.
- Colector: [audit_contact_evidence.py](../../scripts/audit_contact_evidence.py).
- Analizador offline: [analyze_contact_evidence.py](../../scripts/analyze_contact_evidence.py).
- Resultado vigente: directorio hermano `20260907_CONTACT-AUDIT-analysis-v2`,
  con `timeline.tsv` (2.995 entradas clasificadas), `event_counts.json`,
  `analysis.json`, copia del analizador y `analysis.sha256`.
  La v1 se conserva, pero su patrón omitía avisos `over of range`; usar v2.

El índice es una selección reproducible, no sustituye a los logs originales;
limita a tres ejemplos por archivo los avisos repetitivos de rango/colisión/bus.
Los recuentos incluyen todos los matches. Un mismo renglón puede tener varias
categorías: 2.995 no significa 2.995 incidentes.

### 2.2 Relojes y referencias

Los logs del robot usan hora +08:00; la tabla muestra también Madrid (+02:00).
Se restan seis horas, **sin corregir** el desfase histórico PC↔robot de unos
22–23 segundos observado en E6.0Y. Los tiempos subsegundo se comparan dentro
del mismo origen; correlaciones entre hosts no prueban latencias exactas.

Referencias siguientes relativas al directorio sellado:

| ID | Archivo original |
|---|---|
| M28 | `motion/etc/walker/log/motion/robot_app.20260828-130436.64.log` |
| M27 | `motion/etc/walker/log/motion/robot_app.20260827-145718.66.log` |
| M4A | `motion/etc/walker/log/motion/robot_app.20260904-143741.64.log` |
| M4F | `motion/etc/walker/log/motion/robot_app.20260904-194905.65.log` |
| R4F | `motion/etc/walker/log/motion/rosa_control_node.20260904-194904.65.log` |
| C4F | `vision/etc/walker/log/system/cc_main.20260904_194736.79.log` |
| M4S | `motion/etc/walker/log/motion/robot_app.20260904-201849.65.log` |
| C4S | `vision/etc/walker/log/system/cc_main.20260904_201725.80.log` |

Las tres fotos de este mensaje se inspeccionaron visualmente en el chat. No
se han recibido rutas a **estos originales** ni EXIF y no se incluyen sus bytes
en el manifest. Las fotos del fixture E6.1B no son fotos del daño. Queda abierta
su incorporación con hash, lado anatómico y referencia de escala. La fecha
04-09 alrededor de las 14:00 España proviene del testimonio del propietario;
no es una fecha EXIF ni demuestra el instante individual de cada lesión.

### 2.3 Registro de daños, sin inventar diagnóstico material

| ID | Evidencia del propietario | Qué permite afirmar | Qué falta |
|---|---|---|---|
| D1 | Foto 3: clamp izquierda contra lateral | contacto visible; presión informada por operador | instante exacto, fuerza de contacto y punto que inició la lesión |
| D2 | Foto 1: pequeña marca/orificio aparente | discontinuidad visible de superficie; perforación reportada | inspección de profundidad e interior para confirmar perforación |
| D3 | Fotos 1 y 2: líneas a altura de manos | marcas bilaterales visibles; aparición posterior reportada | distinguir pintura rayada de grieta, fecha y tarea causante de cada lado |

Una foto del daño final no demuestra qué trayectoria lo produjo. Tampoco un
`SUCCEED`, ausencia de fault o retorno a HOME descarta roce o daño oculto.

## 3. Cronología reconstruida

| Fecha/hora robot (+08) | Madrid (+02) | Evento | Evidencia/certeza |
|---|---|---|---|
| 27-08 16:24:28 | 10:24:28 | inicia tarea PICO; después fuerza excesiva izquierda a 16:25:59, valores −305,644/−306,965/−306,638 | M27:27534,28313–28315; antecedente, no atribuir fotos actuales |
| 28-08 15:46:51 | 09:46:51 | tarea PICO; termina antes del intento de retorno | M28:21302; log previo contiene avisos de autocolisión |
| 28-08 16:00:18.168 | 10:00:18.168 | `cruzr/open_arm_before_home`, goal `54f7beb2-ffd2-45bd-86e6-07559fae709b` | M28:26161; salida PC aportada por operador |
| 28-08 16:00:19.931 | 10:00:19.931 | fuerza izquierda −370,944; tarea acaba fallando | M28:26190,26223–26227; caso distinto al del 04-09 |
| 04-09 14:59:00.723 | 08:59:00.723 | READY vendor E6.0Y | M4A:492; evidencia PC `20260904T085921_E6.0Y-READY` |
| 04-09, run PC 09:19:28 | hora PC, sin conversión | inferencia E6.0Y: primer punto rechazado; 0 frames | evidencia histórica `20260904T091928_E6.0Y`; no confundir con E6.1C |
| 04-09 15:26:55.057 | 09:26:55.057 | recovery exacto E6.0 | M4A:564; run PC `20260904T092716_E6.0Y-RECOVERY` |
| 04-09 19:05:31.727 | 13:05:31.727 | nuevo READY vendor para E6.1C | M4A:636; run PC `20260904T130344_E6.1C-READY` |
| 04-09, antes del primer arranque fallido | — | E6.1C ENTRY aborta en preflight `WaitStartMotion`; se decide ciclo completo | fuente global/historial PC; no aparece start de tarea ENTRY en logs seleccionados |
| 04-09 19:57:38.977 | 13:57:38.977 | E-stop liberado; arranque sale de espera | C4F:114–138 |
| 04-09 19:57:51.186 | 13:57:51.186 | self-check pasa; empieza `StartMotion` | C4F:147–153 |
| 04-09 19:58:01.981 | 13:58:01.981 | **HOME automático inicia**, UUID `a6c4f346-336f-4596-8bc6-bdff8ef89ed7` | M4F:618,628 |
| 04-09 19:58:02.436 | 13:58:02.436 | objetivo izquierdo `[0 0 0 0 0 0 0]` en 6 s; aviso de límite | M4F:639–640 |
| 04-09 19:58:04.108–.128 | 13:58:04.108–.128 | fuerza excesiva izquierda −305,521 → −310,717 → **−317,787** | M4F:1976,1982,1989 |
| 04-09 19:58:04.522 | 13:58:04.522 | tarea detenida por FT anormal; `StartMotion` falla, razón 19 | M4F:2102; C4F:166–171 |
| 04-09 19:58:09–14 | 13:58:09–14 | 4004/4003 `0x1003`, 4004 `0x2006`, SAFEOP ERROR | R4F:156–180; posterior al FT en los registros |
| 04-09 20:01:09.296 | 14:01:09.296 | E-stop registrado accionado | C4F:181; no describir su accionamiento como «instantáneo» |
| 04-09 20:03:30–40 | 14:03:30–40 | apagado lógico | C4F:202–219; luego confirmaciones físicas del operador |
| 04-09, apagado | — | contacto aliviado; KEY1, brazos estables/asimétricos; chasis apagado y nuevo arranque | testimonio/fotos; no convertir descenso sin potencia en recuperación validada |
| 04-09 20:19:51.073 | 14:19:51.073 | se libera E-stop en el segundo arranque | C4S:87 |
| 04-09 20:20:14.279 | 14:20:14.279 | **otro HOME automático**, UUID `12986f37-add6-4ffa-9e57-c1a7024dc674` | M4S:166,176 |
| 04-09 20:20:21.359 | 14:20:21.359 | HOME termina; StartMotion pasa y llega JoystickMode | M4S:423; C4S:140–149; no prueba ausencia de rayado |
| 04-09 20:53:42–56 | 14:53:42–56 | nuevo apagado registrado | C4S:226–298; invalida tratar aquel HOME como estado vivo actual |

Los valores FT se conservan tal como los imprime el firmware, asociados a
componentes de fuerza (N nominales). **No se afirma Force-X**: el mensaje usa
`1-th dimension` y la convención/transformación del sensor no está homologada
aquí. No son una medición de presión sobre la carcasa ni necesariamente el
pico físico real. Hay 0,414 s entre primera alerta FT y mensaje de halt en M4F;
eso **no mide** el tiempo total de parada mecánica.

## 4. Qué movimiento se ordenó realmente

Lectura remota del 07-09 del contenedor descubierto
`walker-motion.manipulation_robot_app-1`, bajo
`/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/`:

| Tarea | XML leído | Implicación |
|---|---|---|
| `cruzr/home` | `Parallel threshold=5`: elevador, ambos brazos, cintura y cabeza a cero en 6 s | no separa primero el efector del cuerpo; varios grupos se mueven concurrentemente |
| `cruzr/open_arm_before_home` | primera fase paralela de 3 s, brazos con segundo ángulo −0,332024/−0,348983 y resto cero, cintura/elevador cero; segunda fase HOME paralela 2 s | su nombre no garantiza una retirada cartesiana ni seguridad desde PICO/READY/contacto |

SHA-256 de los XML leídos: HOME
`50d819d6d6190280c6efee1dc275877362c3f7c807ec733fbc3c7ed217daed88`;
open-arm `ec2c187c2217ca2dc1767179fba570677f062527fa7070729e81b05141f8980c`.
Son hashes actuales, no una prueba de que los bytes fueran idénticos el 04-09.
Los objetivos/duraciones HOME sí están documentados entonces por M4F/M4S.

La cadena observada es:

`liberación E-stop → self-check → StartMotion/LimbMotion → cruzr/home → objetivos articulares → FT excesivo → abort/fault`.

Pasar self-check verifica disponibilidad/estado, no garantiza una trayectoria
libre de autocolisión. Tener cero publicadores **VLA** tampoco impide una tarea
de manipulación invocada por Control Center.

## 5. Hipótesis y hallazgos de barreras

| ID | Hallazgo / hipótesis | Estado y límite |
|---|---|---|
| H1 | HOME automático desde postura próxima al torso desencadenó el sobreesfuerzo del 04-09 | VERIFICADO: task, consignas, FT y fallo; ubicación del contacto por foto/operador |
| H2 | patillas invertidas interfirieron con el lateral | INFERENCIA fuerte: montaje invertido reportado y contacto compatible; no probado como causa única de D2/D3 |
| H3 | segundo HOME produjo rayas bilaterales | POSIBLE: HOME bilateral confirmado y testimonio; sin vídeo/inspección entre ciclos no puede atribuirse cada marca |
| H4 | VLA generó esa trayectoria | SIN EVIDENCIA para este incidente; HOME de arranque explica la orden. E6.0Y anterior sí cargó checkpoint, pero 0 frames |
| H5 | Wi-Fi o EtherCAT originó la colisión | NO DEMOSTRADO: EtherCAT falla después del FT; no consta orden VLA por Wi-Fi en ese tramo |
| H6 | se superaron límites articulares durante HOME | AVISOS VERIFICADOS: M4F:640 `left_arm 2-th` 0,10316 frente a máximo 0,0987266; M4S:204 cabeza −0,696906 frente a mínimo −0,688727. Falta determinar tratamiento interno; no afirmar límites desactivados |
| H7 | `MetaMove.yaml` ausente / defaults ocasionaron el daño | PENDIENTE: aparecen también en arranque exitoso; no atribución causal por mera presencia |
| B1 | el wrapper de HOME impide cualquier HOME peligroso | FALSO como afirmación global: sólo intercepta sus llamadas; no Control Center/arranque ni otros clientes |
| B2 | E6.0K validó la envolvente real | INSUFICIENTE: tamaño de una clamp, uso bilateral asumido, centro x/y heredado, z fijado; no montaje 6D medido |
| B3 | aceptación de límites de velocidad/aceleración garantiza no contacto | FALSO: velocidad reducida no corrige intersección ni presión sostenida |
| B4 | todos los runners están bloqueados tras el incidente | NO: E6.1C conserva entry/recover y E6.0Y conserva recover; añadir una frase humana no es un enclavamiento central |
| B5 | timeout/fin del cliente cancela la acción | NO DEMOSTRADO: E6.1C usa `timeout 60 rosa action send_goal`; no hay confirmación de cancelación por UUID en ese fallo |
| B6 | muestra previa a confirmación sigue fresca al enviar | DEUDA: E6.1C toma muestra/gate antes de esperar al operador, sin nuevo gate tras la espera |
| B7 | hash de task-list prueba bytes ejecutados | INCOMPLETO: `assert_runtime` E6.1C verifica lista/inicio del contenedor, no ambos XML vivos en ese punto |

B5–B7 son defectos potenciales detectados por inspección, **no causas** del
contacto del 04-09: esa transición no llegó a ejecutarse.

El servicio Vision `cruzr-v020-boot-guard.service` se observó activo/habilitado
el 07-09. Su código permite reiniciar Control Center para una carrera concreta
y enviar `move_head_home`. La consulta journal del intervalo del incidente
devolvió «No entries»: no prueba intervención ni ausencia de intervención.
Debe incluirse en la revisión de rutas de arranque; no se modificó aquí.

## 6. Qué falló en nuestra evaluación y qué ya se contuvo

Se sobreinterpretó una prueba de tamaño con colocación asumida como garantía
geométrica; se trató el retorno a HOME tras reinicio como una recuperación sin
trayectoria; se confió demasiado en que el endurecimiento del wrapper cubría
también los caminos internos. Debemos corregir esas tres conclusiones, no
trasladar toda la responsabilidad a la orientación elegida por el operador.

**Contenciones históricas observadas:** paro, apagado supervisado, contacto
aliviado sin manipulación directa reportada, clamps vacíos y reanudación
supervisada. Estas acciones limitaron el incidente, pero el segundo ciclo
incluyó otro HOME y no constituye una solución preventiva universal.

**Contención documental vigente:** no reanudar HOME/READY/ENTRY/PICO/VLA ni
ciclos de rearme como ensayo desde esta condición hasta cerrar A1–A5 abajo.
No confundir esta restricción con un bloqueo técnico ya desplegado. Esta
auditoría no ha apagado el robot, deshabilitado servicios ni cambiado XML.
El estado físico actual debe confirmarse aparte; no se infiere del chat.

## 7. Plan de cierre y criterios de aceptación

**Actualización posterior del 07-09:** el operador confirma perforación a las
13:58 y rayados durante el segundo arranque/HOME; inspección indica daño sólo
en carcasa y ningún daño interior observado; ambas clamps restituidas.
La cronología y la inspección ya tienen respuesta del operador. La tabla
siguiente conserva el estado de la auditoría inicial: consulte la
[recalificación y contención implementada](2026-09-07_REQUALIFICACION_CLAMPS.md)
para su actualización. A3 tiene ahora bloqueo local parcial probado, no
protección del arranque interno. A2/A4 siguen sin transformación medida ni
barrido aprobado; no confundir esa deuda con falta de confirmación del montaje.

| Acción | Prioridad / responsable propuesto | Criterio verificable | Estado |
|---|---|---|---|
| A1 Inspección de D1–D3 | CRÍTICA / técnico mecánico competente | fotos originales fechadas con escala/lado; determinar perforación vs rayado vs grieta; inspeccionar cubierta, soportes, fijaciones y elementos internos afectados; dictamen y reparación si procede | PENDIENTE; no declarar daño cosmético |
| A2 Fijar montaje bilateral | CRÍTICA / integración mecánica | orientación y fijación documentadas; transformación muñeca/sensor→clamp izquierda/derecha, patillas y tornillos incluidos; incertidumbre medida; identificación de perfil y fotos coincidentes | PENDIENTE; «fábrica» verbal no basta |
| A3 Enclavamiento de incidente y cobertura de rutas | CRÍTICA / software + integración robot | pruebas offline demuestran rechazo de todos los runners; matriz explícita PC/UI/PICO/Control Center/arranque; ningún reinicio interno puede iniciar una trayectoria no cualificada. No anular paros ni FT | PROPUESTO, NO DESPLEGADO |
| A4 Recalificar geometría y retorno | CRÍTICA / planificación | modelo real y margen justificado; barrido desde postura 20D medida, ambos efectores/cuerpo/entorno, incertidumbre, interpolación y frenado; rechaza contacto inicial, montaje desconocido, trayectoria no libre | PENDIENTE; no sustituirlo por abrir brazos a ciegas |
| A5 Robustecer ejecutor | CRÍTICA / software | hashes XML y perfil vivos; exclusión de clientes; muestra fresca después de autorización; cancelación con UUID y confirmación ante pérdida de red/timeout; sin reintento y estado incierto bloqueado | PENDIENTE; probar con dobles/mocks, no provocar fallos en hardware |
| A6 Recalificación física de movimientos auxiliares | CRÍTICA / equipo de ensayo | tras A1–A5, protocolo aprobado, sin caja, sin contacto y sin avisos de rango/fuerza; registro de trayectoria/FT y vídeo; progresión planificada, no `home` universal | NO AUTORIZADA por esta auditoría |
| A7 Reanudar checkpoint | ALTA / VLA | escena y entrada 20D ligadas al perfil físico; shadow nuevo, objetivos aprobados y luego autorización específica; diferenciar READY/HOME de frames VLA reales | BLOQUEADA por A1–A6 |

Pruebas offline mínimas para A3–A5: montaje invertido; izquierda/derecha
intercambiadas; desplazamiento de herramienta; patilla omitida; postura
asimétrica; inicio ya en contacto; muestra envejecida durante confirmación;
XML distinto con task-list idéntica; reinicio del controlador; cliente
concurrente; timeout antes y después de aceptar goal; cancelación sin ACK;
desconexión de red. Cada caso debe **rechazar sin ordenar recuperación
automática** o demostrar una parada validada, no generar un nuevo HOME.

E6.0J/K/Q y E6.1A/B/C conservan sus resultados históricos, pero sus conclusiones
geométricas dependientes de la colocación asumida no habilitan este montaje.
No borrar ni reescribir evidencia anterior; vincular el nuevo perfil/versiones
y repetir los gates afectados. El cambio a orientación nominal tampoco cierra
por sí solo las trayectorias de arranque y retorno.

## 8. Pendientes de trazabilidad que no se pueden resolver sólo con software

- Cuándo se invirtió/restauró **cada** clamp y orientación durante cada ciclo.
- Qué fotos/vídeos existen entre primer contacto, apagado y segundo HOME.
- Si D2 atraviesa la pieza y si D3 es pintura, fisura o deformación.
- Cadena física exacta patilla→superficie y calibración/transformación FT.
- Completitud de logs históricos rotados; esta captura no es un rosbag continuo.

No se promete «no volverá a ocurrir» con esta auditoría. Se establece qué
barreras fallaron y qué evidencia debe cerrar cada una antes de mover otra vez.

## 9. Reproducción offline y entrega

Desde el repositorio, el analizador se puede repetir con `--output` apuntando
a un directorio nuevo. Rechaza evidencia alterada y no realiza conexiones.

```bash
python3 scripts/analyze_contact_evidence.py \
  /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260907T053541Z_CONTACT-AUDIT \
  --output /home/lacuna/proyectos/Robots/Humanoide-vla-evidence/CONTACT-AUDIT-revision-nueva
```

Cambios de esta auditoría: colector/analizador locales, este informe y
correcciones documentales. No se tocaron SDK, configuraciones del robot,
servicios ni ejecutores físicos. No hubo commit/push. La reversión de los
documentos no corrige el riesgo físico ni invalida la evidencia conservada.

Verificación local: `git diff --check` sin errores; dos regresiones de
`scripts/test_contact_audit.py` aprobadas (conversión de hora, detección de
`over of range`, reproducibilidad, rechazo de sobrescritura y evidencia alterada).
Los cuatro hashes de `analysis.sha256` validan. Estas pruebas validan la
trazabilidad del análisis, **no** la seguridad de una trayectoria física.
