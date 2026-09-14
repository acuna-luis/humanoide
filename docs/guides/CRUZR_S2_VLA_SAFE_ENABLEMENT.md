# Integración segura del VLA suministrado para Cruzr S2

**Relevo para la próxima sesión — 2026-09-14:** leer primero el [estado consolidado y secuencia de reanudación](../vla/RELEVO_VLA_20260914.md). HOME→READY→ENTRY está probado por el operador; shadow funciona. TRIAL_02 abortó por timeout al cambiar a SDK, con cero frames y sin acuse; el controlador final es desconocido. Prioridad: consultar controlador y logs antes de reintentar. No repetir ensayos ni asumir estado físico a partir del historial.


**2026-09-14 — Corregida la selección de controlador del ensayo mínimo (VLA-01).**
El intento `ENTRY410_ONE_POINT_TRIAL_01-6l8y73xw` publicó 134 consignas en
1,33 s, con brazos inmóviles, y terminó por `Tracking error: R_shoulder_pitch_joint`.
ROSA nativo confirmó `manipulation_controller=running` y ambos SDK `initialized`:
el ejecutor anterior omitía el cambio de controlador. La captura posterior
coincide con el inicio. Se añadió inventario nativo, cambio mediante
`/mc/motion_sdk/switch_to_vla` sólo en `--run`, respuesta positiva y feedback SDK
20D fresco antes de publicar. Conserva chasis y mantiene explícitamente los
seis ejes fuera de los brazos. Sin aumento de tolerancias, reinicio, HOME ni
reintento automático; al acabar conserva SDK activo. Diecisiete tests locales
pasan; --check y --observe en vivo pasan sin activación ni publicador.
**Cambio de controlador y ejecución corregida pendientes de prueba física.**
Plan vigente: `controller-fixed-plan`; el plan anterior queda obsoleto por hash.
[Detalles, comando y reversión](../vla/ENSAYO_MINIMO_PUNTO_VLA_ENTRY410.md).


**2026-09-14 — Corregidos directorio de evidencias y admisión del ensayo mínimo.**
El intento guardado terminó antes de crear el publicador; la segunda invocación
falló por directorio existente. Ahora cada nueva invocación conserva el anterior
y obtiene una ruta única. El diagnóstico identificó pequeñas variaciones de
encoders de rueda; se usa velocidad≤0,01rad/s más deriva≤0,002rad, y admisión
articular≤0,01rad/s con posición inicial≤0,002rad durante1s. No se cambian
trayectoria ni límites de seguimiento. Quince tests pasan; --observe pasó en
vivo con cero publicadores creados. Plan regenerado: admission-fixed-plan.
Ensayo físico del prefijo todavía no ejecutado por el agente.
[Comando vigente, evidencia y reversión](../vla/ENSAYO_MINIMO_PUNTO_VLA_ENTRY410.md).


**2026-09-14 — Ensayo mínimo VLA preparado, aún no ejecutado.**
Replay parcial del primer punto del chunk2 desde ENTRY410: ambos brazos,
25 % de la transición, máximo 1,396°, 4 s; no agarre ni chunk completo.
El punto completo mantiene un par mano derecha/mesa sin resolver; el prefijo
conserva 1018 pares certificados y los 54 avisos internos históricos, sin nuevos
fallos geométricos. Trece tests y --check pasan. Ejecutor SDK con lectura de
salud/paros/cargador/postura, seguimiento y llegada; sin reintentos ni HOME.
No requiere instalar XML, recargar o reiniciar. Scripts del operador intactos.
[Comando, límites, reproducción y estado pendiente](../vla/ENSAYO_MINIMO_PUNTO_VLA_ENTRY410.md).


**Continuación vigente — 2026-09-14: ENTRY medido y shadow task 0 completado.**
98 muestras inmóviles, error final máximo 0,1593° respecto a ENTRY410. Seis
propuestas y seis aceptaciones por el perfil shadow existente de 14 ejes de
brazos; primer cambio máximo 6,1643° (umbral shadow 0,35 rad), sin envío físico.
Inferencia caliente mediana 0,436 s; arranque exterior 79,394 s. Caja completa
visible en la cámara. Sesión cerrada: ambos contenedores VLA exited y cero
publicadores de movimiento. No se cambiaron tareas ni umbrales. Siguiente:
adaptar el ejecutor físico a ENTRY410 y resolver entrada al primer punto;
no repetir HOME/READY/ENTRY ni confundir aceptación shadow con agarre probado.
[Ensayo, tiempos, reproducción y evidencia](../vla/ENSAYO_READY_ENTRY410_20260914.md).


**Actualización vigente — 2026-09-14: READY→ENTRY410 probado físicamente,
5/5 etapas con éxito según el operador y sus cinco resultados Motion SUCCEED.**
HOME→READY nuevo y READY→ENTRY410 quedan completados para los ensayos comunicados.
Se conserva `force_entry.sh` del operador. Siguiente: lectura fresca y propuestas
VLA task 0 en shadow desde ENTRY; el agarre VLA aún no se ha probado.
[Registro del ensayo, Goal ID y evidencia](../vla/ENSAYO_READY_ENTRY410_20260914.md).


**Actualización vigente — 2026-09-14: HOME→READY nuevo probado físicamente,
5/5 etapas con éxito.** El propietario aporta los cinco resultados Motion
`SUCCEED` (state 1101001, status 4) y confirma el ensayo exitoso desde HOME.
Se cierra el pendiente de primera ejecución del acceso
`ready410_h63_access_01..05_forward` para este ensayo. Se registra lentitud:
122 s nominales; duración real no cronometrada. La ejecución fue mediante ROSA
directo con un `force_ready.sh` modificado por el operador; el agente conserva
ese archivo. ENTRY/VLA y el monitor Python no quedan probados por este ensayo.
Esta actualización prevalece sobre los estados históricos de READY pendiente.
[Resultados, cinco Goal ID, alcance y evidencia](../vla/ENSAYO_HOME_READY_NUEVO_20260914.md).


**2026-09-14 — ENTRY410 instalada en Motion y contenedor recargado una vez; paro mantenido.**
Diez XML y registro82ac1bc8…d2e434e verificados; respaldo copiado y comprobado en PC.
Principal1 verificado antes de instalar/recargar. Motion reiniciado13:32:04UTC;
hashes intactos. No se envió ninguna tarea o movimiento. Control Center queda
en WaitStartMotion y el guard responde not_initial_boot_release: NO liberar
paro ni repetir recarga. Pendiente recuperación de arranque supervisada, carga
efectiva y ensayo. VLA-01; recibos/backups en la ficha enlazada.
[Instalación, recarga y recuperación](../vla/EJECUTOR_ENTRY410_POR_ETAPAS.md).

**2026-09-14 — Instalación ENTRY410 preparada; pendiente paro principal pulsado.**
Instalador en disco con respaldo, preservación literal de registro y reversión
ante fallo; no recarga ni ejecuta. Plan vivo sin conflictos para diez tareas,
registro c4873861…78c84f1 →82ac1bc8…d2e434e. Quince tests pasan. No se ha instalado
ni movido; requiere E-stop principal activo antes de aplicar. VLA-01.
[Plan, receta y límites](../vla/EJECUTOR_ENTRY410_POR_ETAPAS.md).

**2026-09-14 — Ejecutor específico ENTRY410 implementado; integración física pendiente.**
Una etapa por invocación, XML/extremos/hashes comprobados, extremo20D fresco,
trazas, cancelación solicitada ante fallo y sin reintentos. Paquete aditivo de
diez XML preparado sólo en PC. Once tests y diez etapas reales verificados.
Consulta pasiva confirma ArmTask y servidor ROS2; Motion usa SWIG sin rclpy,
por lo que admisión de archivos queda en Motion y cliente en contenedor ROS.
Sin goal enviado, instalación o recarga. Contrato de habilitación basado en
evidencia, instalación/carga y prueba del transporte/monitor aún pendientes;
no se genera autorización automática ni se usa el ejecutor040 retirado. VLA-01.
[Ejecutor, comandos y pendientes](../vla/EJECUTOR_ENTRY410_POR_ETAPAS.md).

**2026-09-14 — Condiciones físicas confirmadas; preflight vivo correcto, ensayo ENTRY410 no ejecutado.**
Operador confirma HOME, abrazaderas vacías/sin contacto, ruedas bloqueadas,
cargador desconectado, sin otros mandos, recorrido libre y persona junto al paro.
Auditor vivo sólo lectura: batería83,1/83,6%, paros0/0, velocidad0, control exclusivo
y preflight canónico correctos. ENTRY410 sólo dispone de generador de borradores;
el ejecutor E6.1C antiguo es de ENTRY040 y su auditor está retirado con salida78.
La confirmación física no transforma esos borradores en un ejecutor validado.
No se instaló, recargó ni movió. Evidencia:
`../Humanoide-vla-evidence/20260914T125702Z_ENTRY410-PHYSICAL-PRECHECK/`.
Reproducir lectura con `scripts/vla/audit_vla_live_preflight_e6_0g.sh --check --expect-released`.
No hay cambio remoto que revertir; respaldo documental en `before/`. VLA-01.


**2026-09-14 — Reutilización de cálculos de trayectorias documentada.**
Separados métodos, pruebas reutilizables por inclusión de dominio y resultados
que dependen de escena/ejecución. Incluye matriz de cambios, flujo de reutilización,
recetas, uso de cámaras y recuperación tras firmware. Los 220 mm, ±1° y50 mm no
son valores universales; las exclusiones de ENTRY no se generalizan. Cambio sólo
documental, sin modificar modelos, filtros, tareas o robot. ANL-01 / VLA-01.
[Guía de reutilización](../vla/REUTILIZACION_CALCULOS_TRAYECTORIAS.md).

**2026-09-14 — Retroceso confirmado a unos 220 mm: margen externo recuperado en el modelo.**
Recalculados acceso y retorno de ENTRY410, también desde nueva lectura pasiva:
1018 pares certificados, 54 marcas internas y cero pendientes. Pasa abrazadera
derecha–tablero bajo las hipótesis ±1°/+50 mm. 361 muestras inmóviles, paros0/0,
sin errores observados. Etapas offline75 s revisadas, sin instalar o mover.
Exclusiones internas del propietario conservadas; incertidumbre física total y
ensayo de ejecución/parada siguen separados del resultado geométrico. VLA-01.
[Resultados y reproducción](../vla/REVISION_ENTRY410_MESA725_20260914.md).

**2026-09-14 — ENTRY410 anclada a separación medida de 160 mm desde punta del chasis.**
Modelo de escena desplazado −59,71 mm en X, conservando giros estimados por cámara.
Registrada la exclusión offline solicitada de 13 pares internos, sin alterar
protecciones ni informes brutos. Nuevo contraejemplo verificado: abrazadera
derecha frente al tablero expandido 50 mm, con error articular máximo 0,956°.
No es contacto físico observado; impide aprobar el margen externo de esta
configuración. Seis tests pasan, sin movimiento ni cambios remotos. VLA-01.
[Medida, recálculo y reproducción](../vla/REVISION_ENTRY410_MESA725_20260914.md).

**2026-09-14 — Diagnóstico adicional ENTRY410: no corregir la extrínseca con el residuo RGB/nube.**
El desacuerdo de 25,70 mm se conserva bajo la transformación común cámara–robot.
El plano de profundidad depende fuertemente de la región: extrapola fondos de
65,5–80,0 cm frente a los 84 cm asumidos. No se cambió calibración ni geometría.
Localizadas las 13 interfaces pendientes: diez uniones directas y tres pares
entre elevador/cintura/torso/cabeza; ninguna con abrazaderas, sin exenciones nuevas.
Nueva herramienta offline, siete tests pasan. Sin intervención remota. VLA-01.
[Diagnóstico y receta](../vla/REVISION_ENTRY410_MESA725_20260914.md).

**2026-09-14 — ENTRY410 recalculada para la escena de 72,5 cm.**
Acceso y retorno: 1018 intervalos certificados y 54 infracciones del margen del
modelo, sin intervalos pendientes. Once separaciones continuas de superficies
CAD demostradas en el dominio410; 13 interfaces móviles con intersecciones aún
sin justificación mecánica. Preparadas cinco etapas (75 s READY→ENTRY) y sus
inversas, sólo borradores. Nueva lectura inmóvil y hashes Motion contrastados.
RGB y profundidad discrepan 25,70 mm de mediana en el tablero: registro físico,
cobertura completa y ejecución/parada siguen pendientes. 16 tests pasan.
Sin movimiento, instalación, recarga ni VLA físico. VLA-01.
[Resultados, reproducción y pendientes](../vla/REVISION_ENTRY410_MESA725_20260914.md).

**2026-09-14 — Mesa ajustada por el operador a 72,5 cm; ENTRY410 se conserva.**
Confirmación «72,5, hecho»: dimensión suelo–superficie del tablero, precisión no
aportada. Perfiles offline actualizados y selección repetida para 0,725 m.
Nueva captura pasiva en Vision: RGB completo de caja/mesa y nube de 9179 puntos,
marcas imagen/nube coincidentes. No demuestra zona libre ni postura articular.
La escena cambió: revisiones geométricas con mesa de 80 cm quedan históricas;
registro y revisión de la nueva escena pendientes. No se ha movido, instalado,
recargado o cambiado ninguna protección del robot. VLA-01.
[Registro del ajuste](../vla/SELECCION_ENTRY410_20260914.md#actualización-mesa-confirmada-a-725-cm).

**2026-09-14 — ENTRY410 seleccionada como base de adaptación para mesa de 80 cm.**
Comparadas 360/380/410 con sus parquets y primeros fotogramas originales.
Posturas prácticamente equivalentes: diferencia máxima de muñeca 0,701 mm.
Apoyo de entrenamiento inferido: 64,18 / 64,17 / 72,65 cm; 410 queda más cerca
bajo hipótesis comunes, sin certificar alturas. Las tres conservan acceso y
retorno con 1018 pares certificados y 54 avisos. Selección sólo offline:
config/vla/offline/selected_entry_adaptation.json; ENTRY runtime sin cambios.
Conservar trabajo de360 como referencia, sin heredar automáticamente su validación.
Sin consulta o movimiento del robot, instalación o cambio del checkpoint. VLA-01.
[Comparación y decisión](../vla/SELECCION_ENTRY410_20260914.md).

**2026-09-14 — ENTRY360 por etapas y once fronteras CAD resueltas de forma continua.**
Nuevo método de órbitas resuelve lifter2/torso; las otras diez parejas sin cruce
se prueban por subdivisión angular. Permanecen trece interfaces con cruces CAD,
sin exenciones. Propuesta offline READY→360 en cinco etapas, 75 s nominales:
1018 pares certificados, mismos 54 avisos, sin timeout; incluye 90/90 contra escena.
Hashes actuales de YAML/URDF/cúbica coinciden; seis límites de cabeza/cuerpo
comprobados con ±1°. Comparar suelo/tablero en una captura da 75,47–82,11 cm:
no establece cota metrológica ni justifica recolocar la mesa. Borradores no
instalados; seguimiento, parada y correspondencia mecánica siguen pendientes.
18 tests pasan. Sin movimiento, instalación, recarga ni cambio de protecciones. VLA-01.
[Resultados, límites y reproducción](../vla/ENTRY360_ETAPAS_E_INTERFACES_20260914.md).

**2026-09-14 — ENTRY360 revisado para ensayo; todavía no habilitado físicamente.**
Vector original task0/frame0 verificado. Acceso/retorno recalculados desde la
captura actual: 1018 pares certificados, mismos 54 avisos, 0 pendientes; 90/90
contra escena con hipótesis 50 mm y ±1°. Interfaces360: 30 invariantes y 24
móviles, 696 muestras, sin contactos CAD nuevos fuera de cajas de referencia;
no prueba continua. Captura pasiva354 mensajes, velocidad0, sin fallos,
paros0/0; RGB/nube nuevos con marcas iguales. Ejemplo360: altura inferida
64,18 cm (62,25–66,03 cm sólo por variación de píxeles), compatibilidad80 cm
no demostrada. Propuesta READY→360 de65 s, no instalada/validada en Motion.
Auditor antiguo040 retirado, salida78. Faltan registro físico/interfaces y
contrato de ejecución/seguimiento/parada; separar del agarre VLA. 15 tests pasan.
Sin movimientos, instalaciones o recargas. VLA-01.
[Revisión, evidencia y reproducción](../vla/REVISION_PRUEBA_ENTRY360_20260914.md).

**2026-09-14 — ENTRY440 con escena ampliada 50 mm: contraejemplo demostrado.**
El par pendiente abrazadera derecha–caja intersecta el modelo al 98,83 % del
acceso y también en el extremo, con perturbaciones menores de 1° y dentro de
límites. Ambos testigos se recomputaron. En el extremo: separación sin ampliar
71,39 mm nominal y 49,90 mm perturbada; una traslación hipotética de 49,95 mm
produce contacto del modelo. No es contacto físico ni error real observado.
Se examinan 113 extremos alternativos: ENTRY360/380/410 pasan acceso y retorno
con 1018 pares certificados, los mismos 54 avisos y 0 pendientes. Los 90 pares
contra escena pasan en las seis rutas. Cambian altura/alcance: compatibilidad
con mesa de 80 cm e imagen VLA pendiente; no se cambia el ejecutor.
Buscador, verificador, selector y vista 3D offline; 11 tests pasan. Cero consultas
u órdenes al robot; VLA físico pendiente. VLA-01.
[Demostración, límites y reproducción](../vla/CONTRAEJEMPLO_ENTRY50_20260914.md).

**2026-09-14 — Error de escena separado del margen geométrico; perfil de 50 mm.**
Por petición del usuario se añade hipótesis offline de registro traslacional
50 mm, ampliando sólidos; los 2 mm siguen siendo separación geométrica mínima,
no exactitud exigida/demostrada de cámara. No es un óptimo ni una cota validada.
ENTRY440 acceso/retorno con ajuste visual+50 mm: 1017 certificados, 54 avisos,
1 par derecho–caja sin demostrar. Captura pasiva actual válida: 356 muestras,
velocidad 0, sin faults, paros 0/0; no parada observada. RGB/nube nuevos con
marca coincidente y TF de ese instante: discrepancia de plano mediana33,9 mm.
Elevador2–torso sigue pendiente tras ampliar cálculo; no se eximen interfaces.
11 tests y 192 comparaciones FCL pasan. Sin órdenes de movimiento, instalación,
recarga o cambio remoto persistente. [Ficha y reproducción](../vla/CIERRE_Y_TOLERANCIAS_ENTRY_20260914.md). VLA-01.

**2026-09-14 — Los 54 avisos internos de ENTRY440 se desglosan.**
30 pares invariantes con base/auxiliares fijos; 10 pares con fronteras CAD
continuamente separadas; 13 con cruces ya presentes en referencias HOME/PICO;
1 (elevador2–torso) separado en muestras, prueba continua pendiente por presupuesto.
Ninguno incluye abrazaderas. En 696 configuraciones no se encontró contacto CAD
validado fuera de las cajas de referencia; es muestreo, no prueba de ausencia.
No deben interpretarse los 54 avisos como 54 choques físicos. Sin eximir pares,
reducir márgenes, aprobar movimiento o modificar el robot. Seis tests pasan.
VLA-01: [diagnóstico, límites y reproducción](../vla/INTERFACES_ENTRY440_20260914.md).

**2026-09-14 — ENTRY440: separación de acceso y retorno validada offline.**
La subdivisión de la caja articular resuelve el par derecho–caja pendiente:
1018 pares certificados (90 contra escena, 928 internos), 54 avisos nominales,
0 sin demostrar, sin timeout. También pasan el acceso desde la captura con
cabeza bajada y el retorno vacío hasta HOME20D. Escena original, ±1° y margen
2 mm conservados. Treinta tests pasan. Esto sustituye el pendiente numérico de
ENTRY440 del informe anterior, no aprueba movimiento físico: registro de escena,
54 interfaces y seguimiento/parada continúan pendientes. Cero órdenes remotas.
VLA-01: [alcance, evidencia y reproducción](../vla/VALIDACION_ENTRY440_20260914.md).

**2026-09-14 — Revisión ampliada de ENTRY; aprobación física pendiente.**
Contraejemplo recomputado: ENTRY372 intersecta la mesa del modelo al 88,17 % de
READY→ENTRY con perturbación máxima 0,9932°, dentro de límites. No es contacto
físico observado. ENTRY440 original verificado evita ese par, pero conserva
un par sin demostrar contra la caja: 1017 certificados, 54 avisos nominales,
1 pendiente, sin timeout. El ajuste visual experimental pasa la separación
con escena ampliada 20 mm, pero su registro difiere de la nube varios centímetros
y no se ha adoptado. Nuevas cotas direccionales sin recortar sólidos/márgenes;
28 tests y 3216 comparaciones pasan. Sin consultas o comandos remotos nuevos.
VLA-01: [resultados, reproducción y límites externos](../vla/CIERRE_GEOMETRICO_ENTRY_20260914.md).

**2026-09-14 — Interpretación de los2,11mm corregida con evidencia geométrica.**
El ejemplo corresponde a separación horizontal contra el frente del proxy de mesa,
no holgura vertical real. Ajuste de117puntos observados: el proxy llega49,9mm por
encima del centro de la zona y46,8mm por delante del punto más cercano; no implica
esos excesos en todo el perímetro. Cotas83,8×84×3,8cm ya registradas. Tres tests
nuevos pasan. Sin recortar geometría, aprobar ENTRY ni nuevas órdenes remotas.
[Datos, límites y receta](../vla/REGISTRO_MESA_ENTRY_20260914.md). VLA-01.

**2026-09-14 — Cabeza en observación, movimiento limitado completado.**
`--prepare-vision --yes`, tarea existente `cruzr/move_head_lower`, SUCCEED/status4.
Final pitch−0,430665rad/yaw−0,000383rad, velocidades0; restantes ángulos sin
variación entre extremos. Brazos/cuerpo HOME, **no HOME20D completo**. RGB y
nube nueva10231puntos muestran caja completa y borde cercano del tablero;
mediciones regionales exploratorias no sustituyen contornos/error completos.
Sin ENTRY, agarre, VLA físico, instalación o recarga. MOT-04/VLA-01.
[Acción, postestado, evidencia y pendientes](../vla/OBSERVACION_ENTRY_20260914.md).

**2026-09-14 — Captura actual y preparación de observación, sólo lectura.**
RGB estéreo nuevo960×576 y376puntos: base de caja y borde cercano del tablero
fuera de encuadre; escena completa sigue sin medir. Preflight canónico pasa:
20D inmóviles, discrepancia≤0,002780rad, baterías83,6/83,0%, paros0/0,
cargador desconectado, abrazaderas `cruzr_s2_v1`. Se revisó rama existente
`cruzr_blue_workbin_cycle.sh --prepare-vision`: sólo tarea de cabeza instalada,
no se ejecutó. Pendiente confirmación de ruedas/zona cabeza/control/operador.
Cero movimiento, instalación o cambios remotos. Evidencia privada:
`../Humanoide-vla-evidence/20260914T081839Z_ENTRY-CAMERA-CHECK/` (VLA-01).
La captura usa `/opt/ros/humble/setup.bash` en `walker-ros.ros2-1`; intentos
previos con setup nativo fallaron por imports y no modificaron contenedores.

**2026-09-14 — Simulada mesa/caja−20mm; ENTRY continúa pendiente.**
Misma ruta372,±1°/2mm:1016certificados,54avisos y2pendientes intactos.
En la postura derecha antes hallada, distancia modelo2,107→3,408mm: mejora1,301mm,
no20mm. Opción PC `--scene-z-offset-mm` conserva procedencia y distingue escenarios;
20tests pasan. Sin consulta/cambio/movimiento remoto ni modificación física de mesa.
[Resultados, receta y reversión](../vla/ENTRY_MESA_MENOS20MM_20260914.md). VLA-01.

**2026-09-14 — ENTRY, cotas locales y alternativas; sin aprobación física.**
A ±1°/2 mm, ruta372: 1016 certificados del modelo, 54 avisos nominales retenidos
y dos pendientes abrazadera–mesa en 11,527 s (antes21). Ninguno de los69 extremos
erguidos queda completamente resuelto;430 empeora a ocho pendientes. Búsqueda
numérica encuentra 2,107 mm abrazadera derecha–tablero en372 dentro de±1°;
no es cota global ni contacto físico.25 tests pasan y regresión con geometría real.
Lecturas remotas: HOME inmóvil, baterías≈90%, paros liberados, VLA detenido;
captura pasiva con caja recortada. Sin movimiento/instalación remota. VLA-01.
[Resultados, fuentes, receta, rollback y pendientes](../vla/ENTRY_COTAS_LOCALES_20260914.md).

**2026-09-14 — Escenario±1° afinado sólo offline:** distancias de sólidos en
pares pendientes dejan997certificados,54avisos nominales intactos y21pendientes
(10resolución/11incertidumbre), frente a23. Sin reducir±1°/2mm ni excluir pares.
Dieciséis tests pasan; sin consulta remota, movimiento o cambio de límites.
[Receta, evidencia y pendientes](../vla/ERROR_ARTICULAR_TRAZAS_20260914.md#afinado-posterior-del-escenario-1). VLA-01.

**2026-09-14 — Trazas y escenarios de error revisados, sólo offline.**
Diez capturas inventariadas con hashes correctos; seis comparables, dos móviles.
H01/H02: máximos de discrepancia consigna solicitada–posición0,444207°/0,433667°;
no consigna aplicada ni cota de parada. Sólo ocho ejes con movimiento significativo.
Escenarios±0,1/0,5/1/5° dejan3/11/23/325pares sin resolver y54avisos nominales
retenidos. ±0,1° no contiene lo observado; ±1° prioritario para estudio, sin
cambiar límites ni aprobar ejecución. Cinco tests nuevos pasan. Sin consulta,
instalación o movimiento remoto; VLA físico0/4, shadow calificado0/5. VLA-01.
[Datos, cobertura, comparación y reproducción](../vla/ERROR_ARTICULAR_TRAZAS_20260914.md).

**2026-09-14 — Error5° de acceso ENTRY372: causas separadas, sin movimiento.**
Corregida repetición de cálculo en pares ya no certificables; permanecen
rechazados. Nuevo revisor de una ruta archivada, sin IO del robot. Profundidad6
termina en26,490s:693pares certificados,54avisos nominales,280sin demostrar
por cota de incertidumbre y45por resolución. No hay aprobación física ni
reducción de error5°/margen2mm. La cota global acumulada exige≈1,015m en algunos
pares de abrazadera: es una cota conservadora, no movimiento observado.
Once tests pasan. No repetir sólo más tiempo: ajustar rigurosamente la cota,
resolver interfaces y escena/compatibilidad antes de activar. VLA-01.
[Detalle, receta y reversión](../vla/ENTRY_Y_RECUPERACION_20260914.md#segunda-revisión-separar-tiempo-resolución-e-incertidumbre).

**2026-09-14 — ENTRY y acceso revisados sin movimiento; aprobación física pendiente.**
Censo completo:150 entradas task0;69 erguidas sin avisos adicionales respecto a
HOME ni avisos con los dos obstáculos archivados en el extremo. Tras descartar
ENTRY46 por interferencias del modelo con el tablero, candidata ENTRY372
(2,845°), cotejada con parquet/RGB original. Tres rutas nominales por intervalos:
1.018 pares certificados y54 avisos retenidos, sin pares nuevos; no aprobación
completa. Escenario5° sin certificar por presupuesto agotado. Recuperación vacía
incluye tramo final a HOME20D, no sólo cabeza en observación. Altura de soporte
inferida≈75,3cm sin incertidumbre total acotada: compatibilidad80cm pendiente.
Lectura nueva: HOME máximo0,002876214rad, velocidades0, RobotCommand writers0,
ambos VLA detenidos. K estéreo coincide con el archivo; caja parcialmente
recortada en RGB. Consultas solamente, sin instalación/reinicio/movimiento.
Dos herramientas PC, diez tests nuevos y ocho de ranking aprobados; sin nuevas
dependencias. No se cambian ENTRY activa ni gates; shadow calificado0/5.
[Resultados, reproducción y pendientes](../vla/ENTRY_Y_RECUPERACION_20260914.md).

**2026-09-11 — Petición de agarre VLA en15min: avance offline; agarre NO ejecutado.**
Quince inferencias nuevas (episodios40/430/438, frame0, cinco semillas) pasan
continuidad inicial de14brazos en sus escenas originales: máximos0,033086,
0,031726 y0,032916rad. No son shadow actuales ni éxito físico.
Modelos completos de extremos conservan54avisos con margen canónico, sin
nuevos pares respecto a HOME; no se han eximido. Runner E6.1C retirado sigue
bloqueando antes de movimiento. Estimación exploratoria de soporte430/438
≈89,6/90,4cm bajo premisas explícitas, sin incertidumbre total acotada; no
queda demostrada la equivalencia con80cm ni se ordena cambiar la mesa.
Tres herramientas PC nuevas; contenedor CUDA temporal network=none, exit0,
retirado junto a staging después de exportar resultados. Sin cambio remoto
persistente, movimiento ni arranque de los VLA persistentes. Shadow calificado
0/5 y tareas físicas0/4. Validación de acceso/recuperación/escena pendiente.
[Detalle, reproducción y reanudación](../vla/DECISION_ENTRY_VLA_20260911.md).

**2026-09-11 — VLA task0 probado en shadow con mesa80:2 propuestas rechazadas.**
Se corrigió e instaló sólo el adaptador de evidencia en Vision: Image2m usa
shm_msgs/String en frame_id/encoding; ahora se serializan según size.
SHA173b55da…cce67b81, backup remoto y receta selectiva en VLA-01;9 tests pasan.
Primer intento0chunks por ese fallo; segundo2chunks/10,009s y capturas RGB+20D
verificadas. Ambos rechazados por salto inicial en12ejes: máximo1,414390rad
(81,039°), límite0,1rad. No se ejecutó el flujo físico ni se ampliaron límites.
Estado observado final igual al inicial: brazos/cuerpo HOME numérico y cabeza
−0,430857rad, velocidad0; VLA exited/restart=no y RobotCommand publishers0.
Es diagnóstico desde postura actual, no validación ENTRY ni de altura80cm.
Pruebas calificadas0/5, tareas físicas0/4; acceso/recuperación/ENTRY pendientes.
La petición del usuario ya autoriza avanzar al cumplir los controles técnicos.
[Resultado, reproducción y reversión](../vla/PRUEBA_VLA_MESA80_20260911.md).

**11-09 — E6.1 retomado sin robot:** [revisión ENTRY](../vla/REVISION_ENTRY_ERGUIDA_20260911.md).
150 entradas task0 comparadas:113 cumplen filtro exploratorio≤5° y límites
articulares; ENTRY40 da31,196°. Candidatos438/430, sin cambiar contrato/XML
ni fixture. Faltan RGB/fixture y trayectorias del candidato; cinco shadow0/5,
VLA físico0/4. Ocho tests pasan. Estados del08-09 inferiores son históricos.

**08-09, HOME tras finalizar el ensayo ENTRY:** [registro](../incidents/2026-09-08_HOME_TRAS_ENTRY.md).
READY→HOME SUCCEED/status=4; HOME 20D máximo 0,002780 rad, velocidad cero,
actuadores sanos. Último estado medido HOME sustituye READY; confirmación visual
posterior pendiente. Revisión de ENTRY por inclinación y shadow 0/5 pendientes.

**08-09, retorno ENTRY→READY completado:** [registro](../incidents/2026-09-08_RETORNO_ENTRY_READY.md).
Último estado medido READY: SUCCEED/status=4, error brazos 0,001633 rad,
cuerpo en READY, velocidad cero y actuadores sanos. Operador confirma estabilidad, ausencia de contacto y postura adecuada del torso. ENTRY sigue pendiente de revisión por inclinación; shadow 0/5.
Esta actualización sustituye ENTRY como último estado medido.

**08-09, observación posterior del propietario:** señala inclinación del torso
muy pronunciada y aporta fotografía. OBSERVADO: postura visual inclinada;
no confirma aceptación física de ENTRY ni estabilidad/ausencia de contacto.
La ejecución y el gate articular siguen verificados, pero la idoneidad de esta
postura queda PENDIENTE de revisión antes de avanzar con fixture/shadow.
El XML solicita lifter_pitch_1 = −0,834773 rad (−47,83°) y lifter_pitch_3 =
0,291265 rad (16,69°): son ángulos articulares, no medición del torso respecto
al suelo. La fotografía no demuestra el estado físico actual ni las holguras.
No se ha enviado movimiento ni modificado el objetivo por esta observación.

**08-09, HOME→READY→ENTRY ejecutado:** [evidencia y estado](../incidents/2026-09-08_READY_ENTRY_AUTORIZADO.md).
Ambas acciones SUCCEED/status=4; ENTRY 20D error 0,003835 rad, velocidad 0,
actuadores sanos. Captura completa de la transición: pico reportado 0,107861 rad/s.
Último estado ENTRY, VLA detenido/writers 0. Confirmación visual posterior
pendiente; retorno ENTRY→READY y cinco shadow (0/5) pendientes.
Esta actualización prevalece sobre los estados históricos HOME/ENTRY pendiente.

**08-09, plan reanudado en E6.1:** [gates y preparación](../incidents/2026-09-08_REANUDACION_PLAN_E6_1.md).
HOME↔READY deja de ser bloqueante pendiente de ensayo. ENTRY XML/aceptación
cotejados; error proyectado al frame 40 de 0,001055 rad. Auditor nuevo identifica
relaciones rígidas y calcula barrido condicionado de útiles (4.096 celdas);
no validación física completa de ENTRY. Perfil P14 faltante añadido a ambos
hosts; validador Motion/inferencia Vision actualizados con backup y sin arrancar
contenedores. --check ahora verifica hashes de código y pasa. Seis tests nuevos,
shadow local correcto; HOME medido, VLA exited/restart=no. No nuevo movimiento.
Siguen pendientes ENTRY físico, fixture actual y cinco shadow (0/5).

**Actualización vigente 08-09 — ciclo HOME→READY→HOME satisfactorio:**
[Retorno y validación conjunta](../incidents/2026-09-08_HOME_DESDE_READY_AUTORIZADO.md). Ambas acciones autorizadas por
el propietario terminaron SUCCEED/status=4, con extremos medidos y confirmación
visual posterior sin problemas/contacto. Estado final HOME: máximo 20D
0,002684 rad, velocidad 0 y actuadores sanos; VLA detenido, writers 0.
PASS físico de ida y vuelta con montaje actual para este ensayo. Captura parcial
del retorno: 2.251 estados, pico de velocidad reportada 2,049366 rad/s; no valida
el candidato offline lento ni frenado. Geometría continua/registro pendientes.
No monitor persistente ni habilitación ENTRY/VLA. El texto siguiente conserva
los resultados históricos de cada análisis; no anula el ensayo autorizado.
Los wrappers locales antiguos no fueron editados y conservan sus restricciones.

> **07-09 — E6.1C offline retirado:** el wrapper (--check/--run) y analizador
> directo devuelven salida 78, `BLOCKED_RETIRED_UNREGISTERED_CLAMP_GEOMETRY`.
> No generan nuevos PASS con el proxy antiguo. Los informes históricos se
> preservan pero no habilitan pruebas actuales. No protege HOME interno.

> **07-09 — contención local implementada:** [estado de recalificación](../incidents/2026-09-07_REQUALIFICACION_CLAMPS.md).
> Doce variantes de lanzamiento rechazadas en tests sin conexión; no cubre
> HOME interno del arranque, UI/PICO ni el guard instalado en Vision.
> E-stop mantenido; no liberar ni reiniciar para probar. Inspección reportada:
> daño sólo en carcasa; clamps restauradas. Geometría bilateral y barrido
> pendientes; E6.0K retirado para nuevos PASS. No hubo despliegue ni movimiento.

## Restricción prioritaria del 07-09-2026

La [auditoría de contactos/HOME](../incidents/2026-09-07_AUDITORIA_CONTACTOS_HOME.md)
demuestra HOME automático dentro de StartMotion y fuerza excesiva en el
incidente del 04-09. No fue una orden E6.1C ni evidencia de movimiento del
checkpoint. E6.0Y anterior sí ejecutó inferencia, pero transmitió cero frames.

Los PASS de E6.0K y barridos derivados **no cualifican la geometría instalada**:
se heredó el centro del proxy en vez de medir la transformación de ambas
clamps. Se conservan resultados offline/históricos, pero su uso como gate físico
queda suspendido hasta recalificación de montaje, trayectoria y arranque.
También deben inspeccionarse los daños antes de reanudar.

No existe todavía enclavamiento central de incidente: los runners E6.1C y la
ruta `--recover` de E6.0Y conservan ramas físicas. Una frase de confirmación no
cierra ese riesgo. No ejecutarlas para probar el incidente. Véanse A1–A7 del
informe; esta auditoría no cambió el runtime ni reinició servicios.

Para preparar el PICO 4 Ultra Enterprise, diseñar sesiones, capturar episodios
y decidir entre continuar este checkpoint o crear un nuevo perfil, consulte
[Cruzr S2 v0.2.0: teleoperación, captura de datos y evolución del VLA](../vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md).

## Estado verificado

El checkpoint GR00T N1.5 suministrado está instalado y puede cargarse sobre el
sistema v0.2.0. La inferencia se ha ejecutado de forma aislada y ha generado
chunks con la estructura esperada:

- 20 dimensiones en el orden oficial del perfil S2;
- 10 puntos por chunk;
- valores finitos y dentro de los rangos del checkpoint;
- cámara estéreo activa;
- estado de los 20 ejes recibido desde `/mc/whole_joint_states`;
- cero publicadores en `/mc/sdk/robot_command` durante toda la prueba.

La prueba shadow desde `home` generó dos chunks, pero ambos fueron rechazados
antes de cualquier ejecución física. El primer punto difería de la postura real
en ocho articulaciones de brazo, con diferencias máximas próximas a 1,35 rad.
Esto demuestra que el VLA no debe activarse directamente desde `home`.

Una segunda ejecución de task 0 el 2026-08-28, desde una postura y escena que
no se documentaron, produjo dos chunks adicionales. Ambos fueron rechazados por
siete violaciones del primer punto; la máxima fue
`R_shoulder_yaw_joint=1,339886 rad` con límite `0,35 rad`. La duración real fue
`10,063076 s` para un máximo solicitado de 8 s. Se mantuvieron cero
publicadores, STOP dejó ambos contenedores detenidos y no hubo movimiento. Este
run es `PASS_SHADOW_SAFETY_ONLY`, no evidencia de que task 0 pueda hacer PICK.

Al reanudar la campaña el 2026-08-28, el propietario informó que el robot ya
estaba encendido y en `home`. Un check fresco de sólo lectura confirmó
Motion/Vision, acciones listas, paros `0/0`, cargador desconectado y
`ACTUATORS_OPERATION_ENABLED=1`, pero el gate no pudo certificar la postura 20D
porque la muestra omitió los IDs `2001/2002/2003/3001`. No se envió movimiento.
VLA permaneció con ambos contenedores `exited` y cero publicadores. El siguiente
paso sigue siendo E1.0/E1.3 de medida física fuera de la envolvente; `home`
informado no autoriza repetir shadow desde una entrada nominal ni ejecutar VLA.

Para reducir carga operativa, el propietario cerró E1.0 con las medidas
`1,80 × 0,80 × 1,00 m`, cuatro esquinas a 1 m, rigidez/estabilidad y más de
1,5 m de separación; las fotos y marcas se difieren a E4. E1.3 conserva la
geometría medida de B0 `0,603 × 0,397 × 0,217 m` y difiere masa/colocación real
a E4/E6. Esta dispensa sólo libera shadow OOD. E2.1 task 2, run
`20260828T105547_E2.1`, generó dos chunks en `10,065012 s`; ambos fueron
rechazados por siete saltos del primer punto, máximo
`R_shoulder_yaw_joint=1,376502 rad` frente a `0,35 rad`. STOP dejó ambos
contenedores `exited`, publicadores `0` y hashes válidos. Es
`PASS_SHADOW_SAFETY_ONLY`, no evidencia de PICK medio ni autorización física.

E2.3 se redujo por decisión del propietario a un piloto 2+2. Task 0, run
`20260828T110217_E2.3-task0`, produjo cuatro chunks rechazados por las mismas
siete discontinuidades; duraciones `10,006055…10,039981 s` y máximo delta
`1,361919…1,367893 rad` en `R_shoulder_yaw_joint`. Task 2, run
`20260828T110617_E2.3-task2`, produjo otros cuatro rechazos equivalentes;
duraciones `10,005578…10,006689 s` y máximo `1,372170…1,379845 rad`. Cada
repetición confirmó STOP y los parents terminaron `exited/exited/publishers:0`;
ambos manifests validan. Es `PASS_PILOT_2X2_SHADOW_ONLY`: demuestra
repetibilidad del runtime/rechazo OOD, no capacidad de PICK ni seguridad para
publicación física.

E2.2 ya cubre los tasks PLACE 1 y 3 sin crear una postura HELD en el robot. El
run `20260828T112730_E2.2` cargó `checkpoint-40000` en un contenedor transitorio
con `--network none`, sin ROS ni mensajes de mando, y reprodujo frame 0 de los
episodios 465 y 265. Produjo dos chunks 10×20: MAE `0,007283609` para task 1 y
`0,011394879` para task 3, sin violaciones conservadoras de rango o primer
salto. El holdout es una partición local del último 15 % por task; no es un
split del proveedor y puede haber formado parte del entrenamiento. El resultado
es `PASS_OFFLINE_INFERENCE_ONLY`: valida el camino de inferencia, no PLACE
físico, generalización ni seguridad de ejecución. El cierre confirmó
`exited/exited/publishers:0` y cero acceso al estado del robot.

E3.0, run `20260828T114346_E3.0`, evaluó offline cinco episodios y fases por
cada task 0–3, con 20 muestras y 36 inferencias. Las MAE medias por task fueron
`0,004908891`, `0,006516288`, `0,009686776` y `0,008983554`; las cinco
ejecuciones seed 0 de cada task fueron idénticas. Dos baselines violaron el
rango de `lifter_pitch_1_joint`: task 2/episodio 270/frame 0 en un punto y
task 3/episodio 287/frame 0 en siete puntos, hasta `0,060465574` frente al
máximo `0,000336618`. Por ello el resultado es
`PASS_OFFLINE_CAMPAIGN_WITH_CONSERVATIVE_VIOLATIONS`, no candidato ejecutable.
El split local 424/76 no se solapa, pero no demuestra episodios inéditos para
C0. Hashes completos del checkpoint sin cambios y cierre
`exited/exited/publishers:0`; sólo queda autorizado continuar con E3.1 offline.

E3.1, run `20260828T120228_E3.1`, mantuvo el mismo aislamiento y evaluó 26
variantes de imagen sobre dos frames fijos de tasks 0/2. Las tres parrillas
fueron desplazamiento horizontal del frame, zoom global y perspectiva
trapezoidal global; **no** representan x, profundidad o yaw métrico de la caja.
Las 26 salidas fueron `ACCEPT_STRUCTURAL`, sin violaciones conservadoras, y los
nominales repetidos fueron exactos. El máximo cambio del chunk fue `0,040258`
rad para task 0 y `0,053590` rad para task 2, ambos bajo zoom. El checkpoint
conservó sus hashes y el cierre fue `exited/exited/publishers:0`. La prueba
métrica permanece bloqueada porque el dataset no contiene RGB-D, calibración,
máscara/pose 6D ni geometría de repisa. Sólo se autoriza E3.2 con sink offline;
no se habilita movimiento.

E3.2, run `20260828T121832_E3.2`, añadió un sink local puro y una fault suite
reproducible. Aceptó dos chunks de control y rechazó 32/32 inválidos, incluidos
NaN/Inf, orden/dimensión, estado/imagen/chunk obsoletos, rango, primer salto,
velocidad, timeline, IDs duplicados/regresivos, cancelación, STOP, deadman y
doble cliente. La auditoría AST encontró cero imports ROS/red, símbolos de
mando o llamadas de publisher/action. Los perfiles 14–20 tienen tests de
máscara y hold no nulo, pero el run certificado sólo cubre `P20_AHLW/low` con
pose sintética, no VLA-ready física. VLA permaneció
`exited/exited/publishers:0`; no hubo estado ni movimiento. Como el perfil no
incluye un límite certificado de aceleración, el gate de ejecutor físico no
está cerrado. Sólo se permite E3.3 offline.

E3.3, run `20260828T124011_E3.3`, ejecutó 22 casos en un scheduler Python
puramente local. Demostró para el contrato candidato: 10 puntos a 80 ms,
horizonte 0,72 s, cero replay en huecos, timeout inter-chunk a 0,5 s, purge
inmediato ante cancel/STOP/pérdida de imagen o estado, rechazo de overlap y
dispatch tardío, y fin sólo tras cinco flags consecutivos. El AST no contiene
ROS, red, publisher/action ni topic de mando; el VLA quedó
`exited/exited/publishers:0` antes/después y no se leyó ni movió el robot.

Ese PASS es sólo local. La fuente Vision suministrada infiere a 0,2 Hz y
termina con un único `flag_pred > 0,1`; el YAML declara cinco flags pero el
Python no lee el parámetro. El chunk declara 0,72 s, mientras las dos copias
del ejecutor suministrado interpolan a 9 s (`src`) y 6 s (`install`). Por ello
la semántica física continúa sin resolver, Gate VLA-3 permanece abierto y el
único siguiente paso permitido es E4.0 de inspección read-only.

E4.0, run final corregido `20260901T075728_E4.0`, resolvió pasivamente la primitiva instalada
`clamp_s2_joints_trajectory`: hash `7722b734…7f6`, dos goals 14D y
`1,5 + 1,0 s`. Su `back`, hash `ee39039c…389`, usa dos goals 14D y
`2,0 + 3,0 s`, pero no es la inversa exacta de la secuencia completa. El task
S2 suministrado `s2_bio_vla/s2_vla_pick_large_teleop_ready` no está instalado
ni registrado, tampoco aparece en el upgrade v0.2.0 entregado; los ready
existentes tienen otra semántica. La revisión v2 reordenó correctamente
hombro/codo, pero su intercambio de muñecas fue descartado por E6.0A: el orden
directo coincide con task 0/frame 0 a `0,002112805 rad`, frente a
`0,614627484 rad` con swap. También resolvió el segundo valor de
cintura como `waist_yaw=0`, porque el URDF S2 sólo tiene ese eje. El XML no
fija los tres lifter: los hereda, el ejecutor S2 descarta sus índices 16–18 y
los 500 episodios abarcan múltiples configuraciones. No hay límites runtime
explícitos, swept volume ni recovery completo. Estado
`PARTIAL_RESOLUTION_BLOCKED_NOT_READY_FOR_E4_1_OR_PHYSICAL_USE`; E4.2 offline
es el siguiente análisis permitido, nunca movimiento. El VLA terminó
`exited/exited/publishers:0`, sin estado ni movimiento.

E4.2, run `20260901T081210_E4.2`, se limitó a artefactos locales y rechazó la
premisa de una altura única por task. A `0,05 rad`, los perfiles nombrados
no-S2 que aparecen en tasks 0/1 son 55/70/85 y en tasks 2/3 son 100/115, con
muchos episodios sin perfil nombrado. Además, task 0/2 y task 1/3 contienen
pares de episodios con elevadores prácticamente iguales
(`0,000124356/0,000206182 rad`), por lo que ni los tres ángulos ni su FK
resuelven el nivel del estante o `platform_in_base`. Tasks 2/3, episodios
90/91, sólo quedan correlacionados offline con la plataforma SDK de 1 m/perfil
100; el XML 100 es no-S2 y no constituye calibración. Estado
`PARTIAL_HEIGHT_FAMILIES_RESOLVED_SINGLE_HEIGHT_MAPPING_REJECTED`; no hubo red
al robot, inferencia, publicador ni comando de movimiento. Siguen bloqueados
todos los gates físicos.

Por autorización posterior del propietario se ejecutó únicamente la parte
métrica de E4.1, sin terceros ni movimiento. El run válido
`20260901T084855_E4.1` capturó CameraInfo/TF, 20 posiciones estables del tag
113 y reconstruyó el borde de B0 del episodio 90. Los rayos
`(307,293)…(713,293)` producen `0,603128627 m` frente a `0,603 m`; la pose
candidata es `platform_in_base=(0,261844987,-0,027738106,0,870000000,
0,0,-1,545870035)`. `D_BUMPER_PLATFORM=-0,092859226 m` es firmado: revela
solape de proyecciones, no autorización para poner la mesa allí. La
incertidumbre es aproximadamente ±16,84/13,30/10,00 mm y ±0,868°. E4.1 queda
`METRIC_FIXTURE_CANDIDATE_RESOLVED_PHYSICAL_GATES_OPEN`; E4.0, colisiones,
swept volume y recovery mantienen todo movimiento bloqueado.

E4.1C cerró la primera comprobación de colisiones offline y se repitió con el
orden de muñecas corregido en `20260903T093408_E4.1C`. El analizador versionado
reconstruyó 121 muestras de
`preposition→forward→back`, con elevador del episodio 90, y transformó los
meshes URDF de 46 links al fixture E4.1. De 60 candidatos AABB, 32 se
confirmaron por intersección triángulo/plano contra la superficie de un tablero
sólido; afectan doce links de muñeca, sensor y efector. B0 quedó libre en la
criba AABB y no se colocó. Resultado
`SOLID_TABLETOP_CANDIDATE_REJECTED_BY_VENDOR_URDF_SWEEP`: no hacen falta aún
medidas de patas o espesor porque el plano superior de espesor cero ya falla.
El run `20260901T090235_E4.1C` queda descartado por el mapping anterior.
E4.1D cerró la duda de identidad, pero no la falta de CAD, en
`20260903T093440_E4.1D`: el SDK asocia PGC-140-50 con
`HW_TYPE=cruzr_s2_v1_gripper`; esta unidad lleva abrazaderas laterales pasivas
con `HW_TYPE=cruzr_s2_v1`. El mecanismo no es el mismo y no existen cotas/CAD
locales que validen `pgc/finger` como envolvente sustituta. La partición de
E4.1C atribuye 10 cruces a PGC/dedos y 22 a muñecas/sensores de fuerza. Estos
22 bastan para mantener rechazado el tablero sólido sin el efector PGC. Sólo
se autoriza diseñar offline huecos u otra pose. No se conectó al robot, no
hubo inferencia/publicador/movimiento y E4.3/E4.4 siguen bloqueados.

E4.1E ejecutó el siguiente cálculo permitido en
`20260903T093443_E4.1E`, también completamente local. Muestreó 401 estados,
seccionó muñecas/sensores en `z=-10/0/+10 mm` y aplicó 55 mm de margen XY.
Con B0 y su apoyo fijos, una búsqueda de tablero sólido en ±5° obtuvo 128.386
colocaciones con apoyo y cero libres de colisión. La referencia global a
`+76,5°`/`0,856 m` queda rechazada por salir de la alineación calibrada. Las
muescas frontales candidatas son izquierda
`[-0,720,-0,470]×[0,000,0,200] m` y derecha
`[0,400,0,650]×[0,000,0,170] m`. No invaden el apoyo de B0, pero omiten la
geometría de las abrazaderas reales, patas/espesor, entrada y recovery. No se
autoriza fabricar, acercar la mesa, colocar B0 ni mover. E4.1F agotó después
las especificaciones oficiales sin exigir medición manual.

E4.1F (`20260903T085912_E4.1F`) verificó por hash manual SDK/producto,
USD/URDF, XML ready y metadatos VLA. Las fuentes publican B0
`0,60×0,40×0,22 m`, plataforma `1,00 m`, carga bimanual global `15 kg` y PGC
`0,1385×0,075×0,075 m`/carrera `0,05 m`. La PGC requiere
`cruzr_s2_v1_gripper` y no representa las placas `cruzr_s2_v1`. Aunque el
manual enumera `clamp hands`, no publica envolvente, TCP, masa, CoG ni CAD; los
modelos contienen sólo PGC. No se infieren dimensiones ni se exige medirlas.
Los gates físicos siguen cerrados y sólo se libera E5.0 offline.

E5.0 completó ese gate local en `20260903T090355_E5.0`. Pasaron las 16
combinaciones de ocho perfiles por `low/middle`: 544 casos, 32 válidos
aceptados, 512 inválidos rechazados y 16 probes de máscara/hold. Los holds son
midpoints sintéticos, no estado articular vivo. El código auditado no usa ROS,
red, publicadores ni comandos físicos y el robot no fue consultado ni movido.
Por tanto se autoriza sólo E5.1 shadow; canary y ejecutor físico siguen
bloqueados por los gates de ready, fixture, recovery, aceleración y contrato
vendor.

E5.1 se ejecutó después como shadow-replay local, run
`20260903T091319_E5.1`. Las 20 inferencias C0 ya congeladas en E3.0 se
compararon bajo los ocho perfiles, sin repetir el modelo por una variable que
sólo existe en el ejecutor: 160 bundles, 148 aceptados, 12 rechazados de forma
segura y 160/160 máscaras correctas. Los 12 rechazos habilitan elevador y se
explican por límites de `lifter_pitch_1/3_joint`; los perfiles sin `L`
aceptaron 80/80. No hubo conexión ni estado vivo del robot. Se libera sólo
E5.2 offline; esta evidencia no autoriza mover ni seleccionar definitivamente
un perfil físico.

E5.2 (`20260903T091901_E5.2`) aplicó una regla explícita de parsimonia: menor
perfil dentro de `max(0,0001 rad,1 %)` del mejor MAE con 5/5 aceptaciones.
Seleccionó `P14_A` para las cuatro tasks. H no mejoró materialmente, W empeoró
ligeramente y L empeoró claramente, además de 12/80 rechazos en perfiles que
lo habilitan. Esta selección sólo vale para replay del dataset. E6.0 permanece
bloqueado; no se deriva autorización física de P14.

`E6.0-CHECK` vigente (`20260903T123041_E6.0-CHECK`) separó los gates por escenario.
E4.4 y la envolvente clamp/fixture no aplican al canary sin caja cuando
plataforma y B0 están retiradas, pero siguen bloqueando E7+. E6.0A
`20260903T093145_E6.0A` confirmó ready B dentro del soporte del checkpoint y
definió hold fresco de H/L/W; el run `092935` se descarta por usar el swap de
muñecas antiguo. E6.0J `20260903T120626_E6.0J`, por decisión del propietario,
adopta un proxy documental por clamp de `0,145×0,142×0,330 m`: unión de las
mallas PGC vendor más 25 mm por cara derivados de su carrera de 50 mm. Pasó
1.201 estados sin contacto externo; es un supuesto para el canary sin caja,
no CAD ni certificación del clamp real. E6.0L
`20260903T122501_E6.0L` fija el contrato temporal propio del canary: sólo
punto 0, una vez, sin replay y sin `end_flag`. E6.0M
`20260903T122502_E6.0M` empaqueta la secuencia exacta de ida y retorno, pero no
la instala ni la valida físicamente. Para E6.0 quedan tres requisitos:
recovery supervisado, transporte físico/STOP revisado y límite de aceleración
certificado. La auditoría y el frontend
`run_cruzr_vla_canary.sh --check` son locales; `--one-point`, `--one-chunk`,
`--window` y `--stop` todavía se rechazan antes de acceder al robot.

E6.0B (`20260903T094547_E6.0B`) muestreó 401 estados del camino exacto
`preposición→A→B→A→preposición`. Con FK vendor y OBB/SAT sobre 46 links
obtuvo cero violaciones URDF y cero solapes entre links a distancia cinemática
mayor que tres. Los 58 pares cercanos reportados no se clasifican: falta la
SRDF/matriz de colisiones permitidas, y la geometría PGC no representa las
abrazaderas pasivas instaladas. Es un PASS parcial de broad phase, no un PASS
de autocolisión ni una autorización física.

E6.0C (`20260903T095600_E6.0C`) clasificó los 58 pares: 40 directos, 12
estáticos ajenos al mando P14, 2 PGC no instalados y 4 móviles upstream. El
narrow phase BVH/STL descartó todos los candidatos a nivel de AABB de
triángulos y produjo cero intersecciones en 401 estados; cuatro self-tests
validaron el SAT coplanar/3D. El resultado es válido sólo para las mallas
vendor upstream; falta geometría clamp, holgura con tolerancias, política
runtime revisada y validación física. El gate permanece cerrado.

E6.0D (`20260903T101730_E6.0D`) midió la holgura exacta entre esas cuatro
parejas sobre los mismos 401 estados. El mínimo vendor muestreado fue
`0,016377700 m` (hombro derecho/torso, muestra 100); los codos/muñecas
mantuvieron unos `0,03488 m`. No es un margen físico certificado: el barrido
es discreto y siguen ausentes clamp, tolerancia de modelo/calibración/flexión,
aceleración y fuerza. El contrato derivado limita el canary a un punto y
calcula delta efectivo como `min(delta, velocidad × 0,08 s)`, pero queda
`SPECIFICATION_ONLY_FAIL_CLOSED`, sin publicador y con aceleración/margen
físico nulos.

E6.0E (`20260903T102652_E6.0E`) implementó el guard de preview de un solo
punto: pasó 35 casos de mensajes y 7 de manipulación del contrato. Sólo dos
previews nominales fueron aceptados; ninguno autorizó ejecución y el módulo no
contiene ROS, red, topic ni publicador. E6.0F (`20260903T102931_E6.0F`)
congeló el preview no aplicado de instalación/rollback del task ready y agotó
el inventario local. El loader vendor no debe ejecutarse desatendido porque es
interactivo y puede reemplazar el directorio y `task_list`.

La siguiente frontera es física o requiere valores certificados. El primer
escenario es `NO_BOX_READY_EMPTY_CELL`: caja, mesa/plataforma y AprilTag fuera
de un radio de 1,5 m; clamps instalados, vacíos y firmes; robot estable y home
verificado; ruedas bloqueadas y cargador fuera; dos personas, una junto al
paro; PICO/UI/teleoperación cerrados y VLA inicialmente detenido. Preparar el
escenario no autoriza movimiento.

E6.0G (`20260903T104309_E6.0G`) confirmó en vivo y sólo en lectura un E-stop
principal accionado, servo E-stop liberado, cargador fuera, baterías >79 %, VLA
detenido y cero publicadores. El task/XML ready estaba ausente. Con el paro
activo no hubo `/mc/whole_joint_states`, servidor de acción ni muestra de
actuadores, por lo que no se demostró inmovilidad instrumental.

Tras liberar el E-stop principal sin movimiento inesperado, el run intermedio
`20260903T105539_E6.0G` confirmó que Motion seguía en `WaitStartMotion`; una
pulsación exterior produjo sólo `Power click`. Se completó después el apagado
y reinicio supervisados prescritos por el manual. El arranque pasó
`WaitEStopRelease→SelfChecking→JoystickMode`, con self-check y `StartMotion`
exitosos.

El run E6.0G vigente `20260903T113216_E6.0G` corrigió además el falso cero de
`ros2 action info` usando `rosa action info`: demostró un servidor de
manipulación, proceso Motion posterior al task list, ready cargado en runtime,
preflight canónico aprobado y robot inmóvil. Paros `0/0`, cargador fuera y VLA
`exited/exited/publishers:0`; no hubo movimiento ni autorización física.

E6.0H (`20260903T104552_E6.0H`) creó un backup fresco e instaló de forma
atómica sólo el XML ready hash-matched y una entrada en `task_list.yaml`. No
recargó ni reinició el task manager, no inició VLA y mantuvo cero publicadores.
El task quedó inicialmente sólo **en disco**; el reinicio completo posterior
inició Motion después del task list y E6.0G demostró su carga runtime. El
readiness anterior mantenía cinco gates no-preflight; E6.0J redujo el vigente
a cuatro bajo el supuesto geométrico documentado. `--check` reconoce el
estado instalado sin reescribir. Esta constatación no autoriza ejecutar la
tarea ni iniciar VLA.

E6.0I vigente (`20260903T115129_E6.0I`) añadió el tramo que faltaba en los
barridos anteriores: `home` fresco a preposición vendor y su retorno. El run
inicial `114811` paró correctamente ante un nuevo solape OBB
`R_shoulder_yaw_link↔torso_link`; el analizador se amplió para resolverlo por
malla exacta. Sobre 101 muestras de entrada y 601 estados compuestos no hubo
intersecciones ni límites URDF violados. El mínimo vendor muestreado bajó a
`0,011169662 m`. Sigue sin modelar abrazaderas pasivas, tolerancias,
continuidad o dinámica; por tanto el gate físico permanece cerrado.

E6.0J vigente `20260903T120626_E6.0J` cubrió la misma trayectoria completa con
un proxy documental deliberadamente sobredimensionado por extremo
(`0,145×0,142×0,330 m`). No encontró solapes fuera de su cadena de montaje ni
intersecciones exactas. El resultado sólo satisface el gate geométrico del
canary `NO_BOX_READY` bajo la instrucción expresa del propietario; no extiende
esa aceptación a caja, mesa, carga, fuerza o operación industrial.

E6.0K `20260903T121338_E6.0K` registró una lectura manual aproximada de las
fotos con cinta: `120×52×105 mm`; con 10 mm por cara se adoptó
`140×72×125 mm`. El volumen queda contenido en el proxy E6.0J en ambos lados
bajo la hipótesis de clamps iguales o reflejados, por lo que el barrido mayor
lo cubre. Las fotos no están versionadas y la lectura no reemplaza CAD ni
certificación mecánica.

E6.0L `20260903T122501_E6.0L` pasó 36/36 expectativas del control core. El
archivo de compatibilidad `cruzr_s2_vla_physical_executor.py` es
deliberadamente transport-neutral: produce como máximo un intent en memoria y
declara `physical_transport_implemented=false`. Esto separa la decisión
temporal —ya determinada por el proyecto— de la futura implementación ROS/STOP,
que sigue siendo gate bloqueante.

E6.0M `20260903T122502_E6.0M` verificó que el nuevo MetaMove local recorre
`B→A→staging` con los goals/duraciones inversos y que el XML termina brazos,
cabeza y cintura en home numérico. `cruzr_vla_ready_pose.sh --check` y
`--dry-plan` son locales; `--install`, `--run-ready`, `--run-recover` y
`--stop` terminan con código 3 antes de cualquier acceso al robot.

La primera preparación física posterior quedó detenida antes de instalar:
aunque la confirmación textual indicaba E-stop principal accionado, el auditor
vivo y el preflight canónico leyeron `ESTOPS=0,0`. El operador enclavó después
el pulsador de nuevo. E6.0G `20260903T123632_E6.0G` confirmó entonces
`ESTOP_KEY=1`, cargador fuera, VLA detenido y cero publicadores. El valor
`SERVO_ESTOP_KEY=0` no corroboró por software el paro de chasis también
declarado. Con el E-stop principal activo, la ausencia de estado articular y
action server fue esperada y no se interpretó como inmovilidad instrumental.

E6.0N `20260903T123940_E6.0N` instaló **sólo en disco** el recovery exacto:
XML `45359d49…cd3c`, MetaMove `bd5f588a…e3b0` y una única entrada en el task
list, cuyo hash pasó de `e4ac5e43…4def7` a `0d24122c…64957`. El backup está en
`/home/walker/cruzr-vla/backups/20260903T123940_E6.0N`; el check posterior y
las nueve entradas de `evidence.sha256` pasaron. No hubo reload/restart,
arranque VLA, publicador ni movimiento. Como Motion inició antes de esta
modificación, la tarea todavía no está cargada en runtime. El gate de recovery
no se cierra hasta cargarla mediante un procedimiento separado y validarla
físicamente de forma supervisada; los otros gates continúan iguales.

E6.0O `20260903T124843_E6.0O` recargó sólo el contenedor dedicado
`manipulation_task_manager/robot_app`, no el control Motion completo. El
E-stop principal permaneció activo antes/después y no se llamó ninguna tarea.
El nuevo proceso arrancó después del task list y conservó una entrada y todos
los hashes exactos; cargador fuera, VLA detenido, cero publicadores y cero
movimiento. `SERVO_ESTOP_KEY=0` continuó sin corroborar el paro de chasis. El
log de arranque muestra únicamente la espera de `ListControllers` esperable
bajo E-stop, sin fatal/crash/YAML. Un error posterior de quoting en la captura
de log fue corregido y revalidado por lectura, sin segunda recarga. La carga
por orden temporal está demostrada; el action server y la trayectoria todavía
deben validarse tras un levantamiento controlado del paro.

`E6.0-CHECK` vigente (`20260903T125333_E6.0-CHECK`) consume E6.0N/O y mantiene
tres gates: recovery físicamente validado, transporte/STOP físico revisado y
límite de aceleración aceptado. No autoriza movimiento.

Tras liberar el E-stop principal, los topics reportaron `0/0`, pero siguieron
ausentes el estado articular y el action server. El log de Control Center
resolvió la ambigüedad: no registra `onServoEstopState=1`; el principal causó
`JoystickMode/Ready→WaitStartMotion` y su liberación produjo
`onEstopState=0`, sin un `ButtonStartMotion` posterior. El software es por
tanto consistente con ambos paros liberados y rearme pendiente. El preflight
terminó sin goal ni movimiento. Las fotos posteriores confirmaron que esta
revisión no tiene un botón separado identificable como START Motion: blanco es
`KEY1`, aro verde es Power/Start exterior y metálico es alimentación del
chasis. La prueba histórica demuestra que una pulsación verde sólo genera
`Power click`. No se debe pulsar ninguno para improvisar el rearme; corresponde
el ciclo completo supervisado de la sección 5.3.3 y repetir después el auditor.

El reinicio completo siguiente resolvió ese estado. E6.0G
`20260903T132151_E6.0G` demostró de nuevo actuadores habilitados, action server,
acciones listas, paros `0/0`, cargador fuera y VLA detenido con cero
publicadores. El primer `ready` físico se lanzó desde home medido, pero el XML
vendor falló de forma determinista: su acción de cintura contiene dos valores
`-0.0; 0.0` y el S2 v0.2.0 sólo expone `waist_yaw`. Esa rama falló antes de
emitir `MoveTo` y el paralelo abortó cabeza/brazos tras un avance pequeño. El
robot quedó quieto, sin force/collision/fault; `cruzr/home` se usó una sola vez
para invertir ese avance conocido y terminó `SUCCEED/status=4`. La medida final
fue cuerpo `0,002589 rad`, brazos `0,000671 rad`, velocidad cero.

E6.0P `20260903T133300_E6.0P` corrigió únicamente esa dimensión en una copia
versionada: `joint_angles="0.0"`. El XML S2 tiene hash
`c767f7396a325d375752fbce2351837e7f5e0c750902e4815ddd7acb24e2a9b2`; el
vendor intacto permanece en el repositorio con hash `f4025124…d8323`. El XML
vivo se sustituyó atómicamente con backup
`/home/walker/cruzr-vla/backups/20260903T133300_E6.0P`, sin recarga, tarea,
inferencia, publicador ni movimiento.

E6.0Q `20260903T135236_E6.0Q` validó físicamente READY→HOME sin caja. READY
terminó `SUCCEED/status=4` y quedó estacionario, sin fault y a menos de
`0,001843 rad` de sus consignas nativas. El primer recovery abortó antes de
movimiento: E6.0N había puesto el YAML nombrado bajo la raíz de
`manipulation_task_manager`, pero `MetaMove` lo busca bajo
`manipulation_meta_tasks`. El fatal `GetRequestFromYamlNode` reinició una vez
el contenedor y las articulaciones siguieron en READY. Se movió el YAML a la
ruta runtime correcta y se corrigió también el último remanente 2D de cintura
en el XML recovery (`joint_angles="0.0"`); XML `9e47b6ee…4fbcc`, backup
`/home/walker/cruzr-vla/backups/20260903T134947_E6.0Q`. El arreglo no recargó,
invocó ni movió. El segundo recovery terminó `SUCCEED/status=4` y la medida
final fue HOME en 20 ejes: cuerpo `0,002589 rad`, brazos `0,000959 rad`,
velocidad cero. VLA permaneció detenido y sin publicadores. El gate
ready/recovery queda cerrado; el canary del checkpoint continúa bloqueado por
transporte/STOP físico y aceleración.

El auditor local se regeneró como `20260903T140006_E6.0-CHECK`: recovery
figura `PASS` y quedan exactamente dos gates `BLOCKED`, transporte/STOP físico
y límite de aceleración. No se habilitó ningún modo activo.

Al cierre de la jornada, E6.0R `20260903T142823_E6.0R` ya aporta el adaptador
SDK P14 de un punto y STOP fail-closed, verificados offline en 51/51 casos.
E6.0T autoritativo `20260903T143529_E6.0T` confirmó sólo en lectura que esta
unidad consume `/mc/sdk/robot_command` (`RobotCommand`) y publica estado en
`/mc/sdk/robot_state`; no existen los topics directos alternativos de brazos.
No se creó ningún publicador y los dos contenedores VLA permanecieron
detenidos. E6.0S `20260903T144344_E6.0S` verificó 2.028 trayectorias minimum-
jerk con la envolvente provisional de proyecto `delta<=0,1 rad`,
`|v|<=0,15 rad/s`, `|a|<=0,5 rad/s²`. Esta envolvente no es certificación del
fabricante y aún no tiene aceptación del propietario.

E6.0U `20260904T073609_E6.0U` completó el monitor de estado medido y pasó
152 casos más 8 alteraciones de contrato. Comprueba READY y estacionariedad,
los 14 ejes de brazo, los seis ejes H/L/W bloqueados, frescura, velocidad y
aceleración; ante cualquier fallo solicita STOP una sola vez y queda
enclavado. No es una validación dinámica del robot: fue una campaña in-memory.

E6.0V `20260904T073852_E6.0V` resolvió la fuente viva sin publicar ni mover:
`/mc/sdk/robot_state` estaba anunciado pero no entregó muestra en 3 s;
`/mc/whole_joint_states` sí entregó 22 nombres, posiciones y velocidades y
quedó seleccionado con QoS RELIABLE. Los dos consumidores de
`/mc/sdk/robot_command` anuncian BEST_EFFORT y no había publicador de comando.

E6.0W `20260904T074537_E6.0W` añadió el runtime y proceso ROS explícito de un
punto: 24 casos funcionales y 3 gates de activación pasaron. La creación del
publicador es perezosa, posterior a READY fresco y a un chunk válido; sólo se
consume el punto 0, H/L/W se mantienen en su medida fresca y STOP destruye el
publicador. La plantilla del repositorio permanece desactivada y rechaza
`--run` antes de importar ROS.

E6.0X `20260904T075519_E6.0X` registra la aceptación del propietario de la
envolvente provisional sólo para `NO_BOX_READY`, task 0/P14 y un punto. No es
una certificación ni una autorización de movimiento. Después de un rearme
completo, E6.0G `20260904T084316_E6.0G` volvió a demostrar `ESTOPS=0,0`,
cargador fuera, estado/action disponibles, HOME medido, VLA detenido y cero
publicadores.

E6.0Y implementa el launcher activo por etapas sin habilitarlo por defecto.
`--ready` exige HOME medido; `--one-point` exige READY medido y crea un grant
efímero ligado por hashes a preflight, READY, aceptación y límites;
`--recover` sólo admite READY medido. El proceso crea el publicador de comando
de forma perezosa después de recibir un chunk válido y lo destruye ante STOP o
fallo. Nunca arranca el ejecutor vendor. El auditor offline
`20260904T085243_E6.0Y-OFFLINE` pasó sin acceder al robot. El primer punto
físico sigue sin ejecutarse y necesita una confirmación actual propia.

La primera etapa física HOME→READY se completó una sola vez en
`20260904T085921_E6.0Y-READY`, con `SUCCEED/status=4`. La comprobación inicial
rechazó por error la postura porque usaba coordenadas crudas de actuador: en
esta unidad algunos signos no coinciden con los joints ROS del checkpoint. La
muestra independiente `20260904T090051_E6.0V` confirmó por nombres los 14
objetivos READY con error máximo `0,001842 rad` y velocidad cero; la muestra
cruda confirmó actuadores sanos y delta posición–consigna ≤`0,001842 rad`.
El gate ahora usa `/mc/whole_joint_states` para postura y mantiene
`/mc/actuator_state` sólo para salud, velocidad cruda y consigna latente. La
regresión offline `20260904T090403_E6.0Y-OFFLINE` pasó. No se repitió READY,
no se arrancó inferencia y no apareció publicador de comando; los contenedores
siguen `exited/exited`. En ese momento aún faltaba confirmar visualmente READY
estable antes de autorizar por separado `--one-point`.

El intento `20260904T090909_E6.0Y` arrancó sólo inferencia y completó dos
preflights READY, pero no ejecutó el punto: Motion rechazó el grant con
`grant_not_current` antes de importar ROS. El PC estaba 22 s adelantado y el
`issued_at` basado en el PC aún era futuro para Motion. No se creó publicador,
no se envió trigger ni hubo movimiento; el cleanup dejó ambos contenedores
detenidos y `publishers:0`. El launcher obtiene ahora el epoch fresco de
Motion justo antes del grant, registra el skew y aborta si supera 60 s. La
regresión `20260904T091614_E6.0Y-OFFLINE` prueba grant válido, E-stop inválido,
desfase inválido y los gates READY. La postura posterior sigue
`MEASURED_READY=1` con error máximo `0,001842 rad` y velocidad cero. El intento
no debe repetirse sin una autorización nueva.

El nuevo intento `20260904T091928_E6.0Y` superó el gate temporal
(`GRANT_CLOCK_SOURCE=motion-host-epoch`, skew 23 s), y task 0 produjo tres
chunks. El primer punto se rechazó antes de emitir comandos porque el eje 2
superaba el delta máximo aceptado de `0,1 rad`:
`transport:arm:target_delta:2`. Se publicaron cero frames y no hubo movimiento.
El backend ROS sí llegó a construirse brevemente antes de que el planificador
rechazara el punto; STOP lo destruyó y el estado final fue `publishers:0`,
`exited/exited`. El runtime se corrigió para ejecutar
`plan_minimum_jerk(...)` y validar delta/velocidad/aceleración antes de crear el
backend, y para no imprimir 500 estados iguales por segundo. E6.0R y las
regresiones E6.0W `20260904T092245_E6.0W` y E6.0Y
`20260904T092246_E6.0Y-OFFLINE` pasan. El robot siguió en READY medido a
`0,001842 rad`, velocidad cero. El siguiente trabajo es analizar en shadow el
primer punto respecto del estado fresco; no aumentar `0,1 rad`, no repetir y
no recuperar automáticamente.

Tras comprobar visualmente READY, el recovery autorizado
`20260904T092716_E6.0Y-RECOVERY` llamó una sola vez a
`s2_bio_vla/s2_vla_e6_0_exact_recovery` y obtuvo `SUCCEED/status=4`. El gate
posterior midió HOME en 20 ejes: cuerpo ≤`0,002780 rad`, brazos
≤`0,000959 rad`, velocidad cero y delta posición–consigna ≤`0,002780 rad`.
No se arrancó inferencia; VLA terminó `exited/exited`, `publishers:0`. La
confirmación visual final se registró a continuación. El siguiente trabajo
técnico es shadow/análisis de la discontinuidad del eje 2, no otro movimiento.

El operador confirmó después HOME visual estable, brazos y cabeza sin
contacto, clamps vacíos y ningún movimiento inesperado. El ciclo E6.0 físico
queda cerrado en HOME. No queda autorización de movimiento vigente; el paso
siguiente es únicamente shadow/offline.

E6.0Z `20260904T094803_E6.0Z` resolvió ese análisis sin ROS, publicador ni
movimiento. Las 20 acciones del checkpoint son posiciones absolutas
(`absolute=true` en metadata), no deltas. En los 150 episodios task 0, la
acción del frame inicial está a como máximo `0,003134013 rad` de su propio
estado; un salto `>0,1 rad` no es el arranque normal demostrado. Los brazos
del READY histórico estaban muy cerca de una entrada task 0, pero los 20 ejes
no: el vecino más cercano queda a `0,834773183 rad`, dominado por
`lifter_pitch_1_joint=0` en vivo frente a `-0,834773183 rad` en el dataset.
Task 0 pide recoger una caja grande de la repisa baja y se ejecutó con
`NO_BOX_READY`; una muestra visual de seis familias de entrada confirma que
las demostraciones muestran un contenedor grande apoyado. No se puede asignar
causalidad exclusiva a escena o elevador, pero ambos contratos estaban
incumplidos. El target exacto histórico no quedó en el log anterior; la nueva
instrumentación conserva estado, primer target y deltas completos.

El contrato versionado `cruzr_s2_vla_task_entry_contract_e6_0z.json` y
`check_vla_task_entry_state.py` exigen para calificar shadow: escenario propio
de la tarea, los 20 ejes dentro del soporte observado y a `<=0,01 rad` de un
mismo frame 0 del task. Después hacen falta cinco chunks frescos desde esa
misma escena/entrada, cada uno con primer delta `<=0,1 rad`; el chunk que
pudiera llegar a una ruta activa se validaría otra vez. No se acepta aumentar
el límite, recortar/proyectar el target ni convertir una posición absoluta en
delta. Este PASS nunca autoriza movimiento.

Como cierre fail-closed, E6.0Y ya no contiene la ruta activa: `--ready` y
`--one-point` abortan localmente antes de red y se eliminaron el trigger, el
grant y el proceso publicador del launcher. Sólo quedan STOP y recovery
READY→HOME. La regresión `20260904T100258_E6.0Y-OFFLINE` confirma el cierre
con 10 checks estáticos y cero acceso al robot. El sucesor se implementará con otro contrato sólo después de
resolver escena `SUPPORTED_LOW`, entrada 20D, transición/recovery y cinco
shadow frescos. El cargador está conectado durante este trabajo offline, por
lo que cualquier movimiento está adicionalmente bloqueado.

El candidato inicial para ese diseño offline es `episode_000040`, por ser el
frame task 0 más cercano a la entrada histórica: H/L/W
`[-0,431336224, 0, -0,834773183, -0,000958738, 0,291264594, 0,024639565] rad`.
Su primer target sólo cambia `0,000326395 rad`. La imagen muestra un
contenedor plástico gris grande, abierto y vacío sobre una superficie blanca;
no habilita sustituirlo sin validación por una caja de cartón. El episodio es
un candidato de ingeniería para HOME→ENTRY→HOME, no un fixture congelado ni
una autorización física.

E6.1A auditó ese candidato completamente offline en el run autoritativo
`20260904T103516_E6.1A`. La transición 20D minimum-jerk necesita `23,59 s` por
sentido con los valores de diseño `0,15 rad/s` y `0,5 rad/s²`; su mayor
recorrido es `1,887083978 rad` en `L_shoulder_yaw_joint`. En 401 muestras no
hubo violaciones URDF, intersecciones exactas de los pares monitorizados ni
intersecciones de los proxies documentales clamp. El PASS es muestreado, no
certifica una trayectoria continua y esos valores dinámicos no están
aceptados para movimiento E6.1.

La reconstrucción desde el RGB congelado y la cámara calibrada sitúa la
superficie `SUPPORTED_LOW` a `0,774597 m` del suelo, rango
`0,768191–0,780828 m` con ±4 píxeles. El soporte de referencia
`0,75 × 0,50 × 0,04 m` y el volumen exterior de caja
`0,60 × 0,40 × 0,22 m` dieron cero candidatos OBB en 16 variantes. Esta pose
es inferida y requiere confirmación física; el tamaño de referencia no es un
máximo impuesto al VLA. La mesa T1 de `1,80 × 0,80 × 1,00 m` no queda
calificada para HOME→ENTRY de este frame: difiere `0,225403 m` en altura y su
tablero produce 159 alertas OBB si se simula a la altura candidata. El modelo
no demuestra contacto real ni descarta la mesa para otros escenarios o shadow.

Se reproduce únicamente en local con:

```bash
./scripts/vla/audit_vla_task_entry_path_e6_1a.sh --check
./scripts/vla/audit_vla_task_entry_path_e6_1a.sh --run
```

El wrapper no usa robot, red, ROS, contenedores ni publicadores. El run previo
`20260904T103323_E6.1A` queda superado: aún mezclaba el volumen PGC del URDF
con el proxy clamp; el autoritativo excluye correctamente PGC y conserva el
PASS.

E6.1B queda implementado offline y revalidado en
`20260904T121621_E6.1B`. El contrato fija los 20 ejes de
`episode_000040/frame 0`; los XML ENTRY/recovery sólo son previews sin
instalador ni modo `--run`. El checker exige fixture medido/fotografiado,
estado fresco a `<=0,01 rad`, velocidad `<=0,01 rad/s` y los 20 ejes
presentes, sin defaults. El orquestador de cinco shadow vuelve a medir ENTRY
antes de cada repetición, obliga a usar task 0/P14, conserva el RGB y estado
exactos entregados al checkpoint, verifica primer delta `<=0,1 rad` y exige
STOP, contenedores detenidos y cero publicadores después de cada sesión. No
despliega el perfil automáticamente y nunca ejecuta ENTRY/recovery.

La mesa medida por el propietario (`0,838 × 0,84 m`, superficie a `0,77 m`)
puede calificarse para **shadow estacionario**. El espesor medido es `0,038 m`;
se declaró inmovilizada y B0 azul quedó rígida, vacía, abierta y en la pose
nominal. Las dos fotos originales locales validan por SHA-256 y el fixture
`TABLE_77_B0_20260904` queda congelado con incertidumbre manual conservadora
`±0,005 m`. El color es
una variación registrada, no un requisito de la instrucción. No se declara
inútil ni equivalente al
soporte reconstruido. El OBB conservador marcó 20 candidatos usando 5 mm de
espesor supuesto, 44 usando 40 mm y 44 con los 38 mm medidos; son avisos contra proxies de clamp, no
contactos físicos demostrados. ENTRY/recovery con la mesa presente permanecen
fail-closed hasta una comprobación más precisa o prueba incremental separada.
No se usa AprilTag: no es una entrada de este checkpoint ni aparece en el
frame congelado. No existe autorización física.

E6.1C reduce el movimiento de entrada usando el READY vendor ya observado. El
run offline autoritativo corregido `20260904T130901_E6.1C` demuestra que los 14 ejes de
brazo del READY están a `0,000959 rad` como máximo del frame congelado y por
ello no deben volver a comandarse. El preview de 12 s sólo ajusta cabeza,
elevador y cintura; el cambio dominante es `0,834773183 rad` en
`lifter_pitch_1_joint`. Bajo la ley minimum-jerk auditada alcanza como máximo
`0,130433310 rad/s` y `0,033469203 rad/s²`. En 401 muestras hubo cero límites
URDF, cero contactos exactos robot/proxy clamp, cero solapamientos entre clamps
y cero candidatos OBB contra la mesa/caja reconstruidas. La inversa vuelve al
READY observado antes de reutilizar el recovery READY→HOME ya validado.

Este PASS es todavía de diseño: los XML son previews, no están instalados ni
registrados, y no se ha demostrado que el interpolador runtime de `MetaMove`
sea idéntico al minimum-jerk muestreado. Los límites `0,15 rad/s` y
`0,5 rad/s²` no son certificación UBTECH y la aceptación previa E6.0 no se
extiende automáticamente a E6.1C. No existe launcher ni autorización física
hasta una aceptación explícita y una instalación/recarga separadas bajo
E-stop.

El único HOME→READY físico `20260904T130344_E6.1C-READY` terminó
`SUCCEED/status=4` con brazos inmóviles en la medida posterior. El resultado
probó el orden runtime `MetaMove head=yaw;pitch`; el preview anterior tenía el
orden documental invertido, pero nunca fue instalado ni ejecutado. El gate
falló antes de ENTRY, se corrigieron ambos previews y la auditoría offline
volvió a dar cero límites/contactos/candidatos. READY fue confirmado
visualmente estable; ninguna ENTRY está autorizada todavía.

La aceptación local `20260904T131403_E6.1C-ACCEPTANCE` fija el alcance
cabeza/elevador/cintura, `0,15 rad/s` y `0,5 rad/s²`, sin certificación UBTECH
y sin autorizar ENTRY/publicador. Existen ahora instalador atómico, recarga
bajo E-stop y runner READY↔ENTRY con gates 20D; ninguno se ha aplicado aún al
robot.

Deploy realizado bajo E-stop: `20260904T132339_E6.1C-INSTALL` instaló los dos
XML y task list con backup/rollback; `20260904T132423_E6.1C-RELOAD` reinició
sólo el task manager. Hashes/runtime exactos, `ESTOP_KEY=1`, cargador fuera,
VLA detenido, cero publicadores, tareas invocadas y movimiento. ENTRY sigue
requiriendo liberación supervisada, READY fresco y autorización de corrida.

Intento posterior: el propietario autorizó READY→ENTRY, pero el runner se
detuvo antes de crear el goal porque el preflight canónico no estaba
disponible. La comprobación de sólo lectura confirmó
`CONTROL_STATE=WaitStartMotion`, `/mc/manipulation/action` con cero servidores
y ausencia de `/mc/whole_joint_states`. No hubo movimiento, inferencia ni
publicador. En esta unidad el siguiente gate es el ciclo completo supervisado
de v0.2.0; después deben repetirse READY 20D y la autorización específica.

Ese ciclo reveló un gate nuevo: al liberar el E-stop desde READY, el self-check
pasó pero `StartMotion` terminó `reason:19 Limb motion failed`; la clamp
izquierda quedó contra el torso, 4003/4004 fallaron y EtherCAT pasó a
`SAFEOP ERROR`. ENTRY, checkpoint y publicador nunca arrancaron. Un segundo
ciclo desde brazos libres recuperó `JoystickMode` y HOME 20D sin goals. El
propietario confirmó después que las abrazaderas se habían invertido
deliberadamente para mejorar la manipulación de cajas. Esa geometría distinta
no estaba representada en URDF/CAD/mesh ni en un perfil de herramienta, por lo
que es el factor contribuyente principal al contacto; la causa inmediata
observada sigue siendo el `StartMotion` interno desde READY. HOME→READY queda
bloqueado hasta demostrar orientación de fábrica y holgura bilateral con la
envolvente real. La configuración invertida queda prohibida para movimiento
automático mientras no exista modelo de colisión, perfil y procedimiento
específicos validados.

E6.0X `20260904T075519_E6.0X` registra la aceptación del propietario sólo para
E6.0, celda vacía, task 0/P14 y un punto: delta objetivo `<=0,1 rad`, velocidad
medida `<=0,15 rad/s`, aceleración medida `<=0,5 rad/s²`, muestreo de `10 ms`,
H/L/W inmóviles. No es certificación del fabricante ni autorización de
movimiento.

El consolidado histórico `20260904T075648_E6.0-CHECK` dejó el ejecutor en
`PASS_CODE_OFFLINE_ACTIVATION_GATED`, la aceptación en `PASS` y cero gates
estáticos. Su continuación de celda vacía fue ejecutada y queda superada por
E6.0Z: no repetir ese preflight ni crear otro grant `NO_BOX`. VLA permanece
detenido y `E6.0_PHYSICAL_AUTHORIZED=0`.

La fase A del preflight de hoy es `20260904T075947_E6.0G`. Con los paros
declarados accionados, comprobó sólo en lectura: principal `ESTOP_KEY=1`, señal
servo/chasis `0`, cargador fuera, baterías `45,8/48,5 %`, READY S2 correcto,
VLA detenido y cero publicadores. La señal `0` no corrobora el paro físico de
chasis; se conserva la comprobación física del operador. Bajo E-stop no había
estado articular ni action server, por lo que el siguiente gate es liberar
ambos paros bajo supervisión y repetir `--expect-released`. No pulsar
Power/KEY1/Start durante esa transición.

Después de liberar físicamente ambos paros, software confirmó `0/0/0`, pero
whole-state y el servidor de manipulación continuaron ausentes. El preflight
liberado falló cerrado. El guard correcto, ejecutado en Vision y sólo en modo
`--check`, obtuvo x86 3/3, cámaras 2/2 y seguridad `0 0 0`, pero
`CONTROL_STATE=unknown`; no reinició ni movió. Se requiere el ciclo completo
supervisado v0.2.0 antes de retomar E6.0. No usar Power/KEY1/Start aisladamente.

## Incompatibilidades corregidas en el overlay

El paquete original no arrancaba tal como fue entregado:

1. El ejecutor SDK instalado estaba incompleto y cargaba un perfil de 17 ejes.
2. `/mc/sdk/robot_state` se anunciaba, pero no emitía muestras. Se usa como
   alternativa read-only `/mc/whole_joint_states`, activo a unos 500 Hz.
3. La imagen no contenía la variante GR00T que define
   `Utars_1RGBDataConfig` ni el argumento `eagle_path`. Se monta el árbol GR00T
   suministrado por UBTECH, verificado mediante hashes.
4. El staging inicial omitía `experiment_cfg/metadata.json`; ahora incluye los
   dos metadatos necesarios para inferencia, pero no los 8,5 GB del optimizador
   de entrenamiento.

Ninguna de estas correcciones modifica el firmware base. Los dos contenedores
VLA siguen con política `restart=no` y quedan detenidos al terminar.

## Uso en shadow mode

Los runs no deben construirse concatenando una variable que proceda de otro
shell. Para medidas o herramientas futuras, crear la salida en el mismo bloque:

```bash
VLA_RUN_DIR="$(./scripts/vla/new_vla_evidence_run.sh --experiment ID)"
```

E1.1 y E1.2 disponen de wrappers que crean y validan esa ruta internamente:

```bash
./scripts/vla/audit_vla_experiment_e1_1.sh
./scripts/vla/audit_vla_experiment_e1_2.sh
```

Para un smoke autocontenido de task 0 o 2, con directorio propio, STOP ante
fallo y exportación de evidencia:

```bash
./scripts/vla/run_vla_shadow_smoke.sh --task-id 0
```

Para repetir E2.2 offline con tasks PLACE 1 y 3:

```bash
./scripts/vla/run_vla_offline_place_e2_2.sh --check
./scripts/vla/run_vla_offline_place_e2_2.sh --run --seed 0
```

Esta orden no sustituye una prueba física: no usa estado vivo ni comprueba que
una caja se deposite correctamente.

Para repetir la campaña E3.0 completa:

```bash
./scripts/vla/run_vla_offline_campaign_e3_0.sh --check
./scripts/vla/run_vla_offline_campaign_e3_0.sh --run
```

Las violaciones se conservan como resultado y nunca se envían al robot.

Para repetir la auditoría E4.0 de sólo lectura:

```bash
./scripts/vla/audit_vla_ready_e4_0.sh --check
./scripts/vla/audit_vla_ready_e4_0.sh --run
```

Un resultado parcial/bloqueado no autoriza E4.1 ni instalar o ejecutar el task.

Para repetir E4.2 sin red al robot:

```bash
./scripts/vla/audit_vla_heights_e4_2.sh --check
./scripts/vla/audit_vla_heights_e4_2.sh --run
```

Su resultado actual demuestra familias y rechaza una altura escalar; tampoco
autoriza una prueba física.

Después de que E1.0, E1.3 y E2.1 liberen el gate, cinco repeticiones E2.3 se
ejecutan sin mezclar logs/chunks y con STOP entre runs:

```bash
./scripts/vla/run_vla_shadow_repetitions.sh --task-id 0 --repetitions 5
```

La secuencia manual de bajo nivel continúa disponible para diagnóstico:

```bash
./scripts/vla/run_ubtech_vla_shadow.sh --deploy
./scripts/vla/run_ubtech_vla_shadow.sh --start-shadow --shadow-duration 300
./scripts/vla/run_ubtech_vla_shadow.sh --start-inference
./scripts/vla/run_ubtech_vla_shadow.sh --status
./scripts/vla/run_ubtech_vla_shadow.sh --trigger --task-id 0 --inference-duration 8
./scripts/vla/run_ubtech_vla_shadow.sh --stop
```

Si la secuencia ya terminó pero no se conservaron los logs locales, se pueden
extraer desde los contenedores detenidos sin arrancarlos:

```bash
VLA_RUN_DIR="$(./scripts/vla/new_vla_evidence_run.sh \
  --experiment RECOVERED-SHADOW)"
./scripts/vla/run_ubtech_vla_shadow.sh --export-evidence "$VLA_RUN_DIR"
```

El script aborta si detecta un publicador en `/mc/sdk/robot_command`. El
validador no importa `RobotCommand` y no crea publicadores ROS.

Los identificadores suministrados son:

- `0`: recoger caja grande del nivel inferior;
- `1`: depositar caja grande en el nivel inferior;
- `2`: recoger caja grande del nivel medio;
- `3`: depositar caja grande en el nivel medio.

## Condición para diseñar el sucesor físico de E6.0

E6.0Y/`NO_BOX_READY` está retirado y no puede volver a armarse. Su `--ready` y
`--one-point` abortan antes de red. Antes de escribir un launcher físico nuevo
deben existir juntos:

1. Escenario `SUPPORTED_LOW` coherente con task 0: contenedor grande vacío
   apoyado y visible en la repisa/plataforma baja; no una celda vacía.
2. Un único frame 0 task 0 elegido como referencia conjunta de los 20 ejes.
   No se permite formar una postura mezclando rangos de episodios distintos.
3. Transición HOME→ENTRY y recovery ENTRY→HOME deterministas, con barrido,
   límites y estado final comprobados offline antes de cualquier movimiento.
4. Medida fresca 20D dentro de los rangos del task y a `<=0,01 rad` del mismo
   frame de referencia, evaluada por `check_vla_task_entry_state.py`.
5. Cinco chunks shadow frescos de esa misma escena y entrada. Todos deben
   conservar estado, target y delta por eje y cumplir primer delta P14
   `<=0,1 rad`, sin clipping ni proyección.
6. Revisión del chunk real nuevamente antes de construir el publicador, más
   preflight y autorización física exclusivos de esa corrida.

La tolerancia `0,01 rad` es un gate conservador del proyecto, no un límite
certificado. Pasar los puntos 1–5 sólo permite crear y revisar el diseño del
sucesor; no concede movimiento. El cargador puede seguir conectado durante el
trabajo offline/shadow, pero debe desconectarse y verificarse por software
antes de cualquier transición física.

## 2026-09-14 — VLA-01: comprobación posterior al arranque completo

VERIFICADO: el preflight vivo con paros liberados termina correctamente;
20 articulaciones, velocidad máxima cero, baterías75,5/77,1%, cargador
desconectado, ambos paros0, servidor de manipulación disponible, sin otros
publicadores de control y contenedores VLA detenidos. Los diez XML instalados
y el registro conservan los hashes del recibo después del reinicio. Esto
verifica archivos persistentes, no la identidad efectiva de tareas cargadas.
HOME es la postura comunicada ahora por el usuario; este preflight no demuestra
por sí solo coincidencia de las20 posiciones con el extremo HOME.

PENDIENTE: el ejecutor de cinco etapas comienza en READY. El wrapper
`scripts/vla/cruzr_vla_ready_pose.sh` mantiene bloqueado HOME→READY y exige
validación independiente. No ejecutar etapa1 desde HOME. También sigue sin
emitirse la habilitación de ensayo documentada en el ejecutor ENTRY410.
No se enviaron movimientos, no se reinició ningún servicio y no se modificó
el robot en esta comprobación. El arranque correcto no elimina estos pendientes.
Evidencia: `../Humanoide-vla-evidence/20260914T135826Z_ENTRY410-POSTBOOT/`,
con preflight, hashes posteriores al arranque y respaldo documental.
Punto de reanudación: resolver el acceso HOME→READY y la habilitación del
ensayo, conservando el robot en su estado actual; no repetir el ciclo de
encendido para resolver un requisito del ejecutor.

## 2026-09-14 — VLA-01: acceso medido a READY calculado por grupos

OBSERVADO: captura pasiva posterior al arranque, 14:07:23–14:07:33 UTC,
347 muestras articulares, ambos paros0, sin incidencias del analizador.
VERIFICADO OFFLINE: `scripts/vla/prepare_home_ready_access.py` genera cinco
tramos desde la última postura medida hasta el READY exacto del informe410.
Comprueba identidad de traza, ausencia de movimiento/fallos en toda la traza,
variación articular≤0,002rad, identidad del modelo y fuentes inmutables durante
el cálculo. Genera diez XML DRAFT para ambos sentidos; no instala ni publica.

Resultado bajo las hipótesis del informe GAP220:1018 pares con intervalos
geométricos certificados,54 con violación del margen del modelo,0 pendientes
y sin timeout. Los54 pares son exactamente los mismos del informe de etapas
ENTRY410; no se convierten en aprobados ni se eliminan del resultado. La
correspondencia de pares no transfiere automáticamente pruebas de otro tramo.
Duración propuesta136s: cabeza20, cintura1, elevador1, brazo izquierdo57 y
derecho57. Son tiempos de propuesta, no una medición ni una ejecución aprobada.

PENDIENTE: comprobar límites dinámicos/configuración efectiva, correspondencia
runtime de grupos, identidad cargada y protocolo del ensayo. Los XML de acceso
NO están instalados, el wrapper activo permanece bloqueado y no se ha emitido
habilitación física. No hubo reinicios ni movimientos. No es aún una ruta
HOME→ENTRY ejecutable.

Evidencia externa: `../Humanoide-vla-evidence/20260914_HOME_READY_ACCESS/`
(traza, análisis, access/review.json, diez borradores, comparación y fuentes).
Tests: cinco casos de admisión de postura pasan, incluidos movimiento anterior,
deriva con velocidad cero, fallo y dato no finito; los tres tests existentes
de construcción por grupos también pasan. No cubren movimiento real.
Receta reproducible: `docs/vla/ACCESO_HOME_READY_20260914.md`. Reversión local:
retirar selectivamente las dos fuentes nuevas y restaurar documentos desde
`before/` de la evidencia, preservando otros cambios. Ningún cambio persistente
en el robot.

## 2026-09-14 — contraste vivo de configuración HOME→READY

VERIFICADO: consultas de lectura a Motion recuperaron YAML y URDF, con hashes
idénticos al contrato archivado. Tipo, lado y dimensión de los cinco grupos
coinciden. Las20 articulaciones cumplen límites de posición (incluido el error
del informe) y velocidad para el perfil cúbico propuesto. Los seis ejes de
cabeza/cuerpo cumplen además la aceleración configurada. No se localizaron
fuentes MetaMove en los dos paquetes consultados; esto no demuestra su ausencia
en todo el sistema. El orden articular efectivo dentro de MetaMove y su
interpolador no quedan demostrados por tipo/lado/dimensión.

PENDIENTE concreto: las14 articulaciones de brazo no tienen aceleración en
estos archivos. No se infiere un límite ni se marca la ejecución como aprobada.
No hubo cambios, instalaciones, reinicios ni movimientos del robot.
Evidencia: `../Humanoide-vla-evidence/20260914_HOME_READY_CONTRAST/`. La primera
lectura normalizó saltos de línea y falló la comprobación hash; se conservó y
se repitió con bytes exactos en base64 (`runtime-bytes.json`), cuyos hashes
pasan. `limits-comparison.json` conserva cada eje y sus resultados.

Reproducción local:
```bash
.venv/general-home/bin/python scripts/vla/contrast_home_ready_limits.py \
 --review ../Humanoide-vla-evidence/20260914_HOME_READY_ACCESS/access/review.json \
 --snapshot ../Humanoide-vla-evidence/20260914_HOME_READY_CONTRAST/runtime-bytes.json \
 --output /tmp/contraste-ready-nuevo.json
```

Cambio persistente sólo PC: nuevo comparador offline y este registro VLA-01.
Reversión: retirar el comparador y restaurar documentos desde before/ de la
evidencia, preservando cambios ajenos. No habilita el wrapper de movimiento.

## 2026-09-14 — VLA-01: contraste de bibliotecas internas Motion

VERIFICADO: se copiaron al PC mediante lectura las bibliotecas actuales
libmeta_move.so, libinterpolation_path_planner.so y libs2_arm_kinematics.so.
Hashes en binary-hashes.json. La biblioteca de interpolación tiene SHA256
1267e370614d5350706caa061a24c162e3333248b9b1af74b8ea319a3d5ee329.
El emulador existente verifica1312 casos de su rutina numérica: error máximo
2,6645352591003757e-15 frente a Hermite cúbica; con velocidad cero en extremos
q=q0+(q1-q0)*(3u²−2u³). Este resultado NO verifica el despacho de MetaMove,
sincronización, configuración de velocidades extremas ni control físico.

Búsqueda en YAML de cinco paquetes instalados: los perfiles CruzrS2 examinados
no declaran aceleración de brazos. Hay valores en perfiles WalkerS2/S3, pero
no son límites acreditados para esta unidad y no se reutilizan. No se encontró
una tabla explícita joint_names/joint_order en esa búsqueda. Los símbolos
exponen SetJointLimits; su existencia no demuestra los valores cargados.

PENDIENTE: demostrar el orden efectivo y la llamada completa de MetaMove, y
obtener límites efectivos de brazos. El análisis numérico del interpolador
queda cerrado en su alcance limitado. No se habilitó ejecución ni se enviaron
movimientos, instalaciones, reinicios o cambios de protecciones.
Evidencia: ../Humanoide-vla-evidence/20260914_MOTION_INTERNAL_CONTRAST/.
Las bibliotecas privadas quedan fuera de Git. Sólo cambios documentales enPC;
respaldo en before/. Revertir únicamente esta adición documental si se necesita.

Reproducción offline:
```bash
.venv/general-home/bin/python scripts/teleoperation/audit_motion_interpolation.py \
 --binary ../Humanoide-vla-evidence/20260914_MOTION_INTERNAL_CONTRAST/libinterpolation_path_planner.so \
 --output /tmp/interpolacion-contraste-nuevo.json
```

## 2026-09-14 — VLA-01: límites compilados y decisión de habilitación

VERIFICADO: se extrajo sin cargar código vendor la tabla de7 registros de48
bytes en VA0x2fe20 de libs2_arm_kinematics.so (SHA2562a41cf55…ad251c).
Las ramas izquierda/derecha del constructor copian esa tabla y llaman a
SetJointLimits; los primeros dos doubles son límites de posición. Se mantienen
sin calificar los nombres de los cuatro campos escalares restantes. Los
límites compilados NO se presentan como lectura efectiva de la memoria del
controlador: pueden existir sustituciones posteriores. Tres tests locales
verifican extracción por segmento ELF, rechazo de hash distinto y datos mutables.

HALLAZGO: todos los extremos nominales del acceso quedan dentro de estos
límites bajo la correspondencia propuesta. Sin embargo, el error independiente
±1° produce máximos0,01639868/0,01841203rad en codoL/R frente a0,01rad compilado.
El error positivo que cabe desde los máximos nominales es0,63338°/0,51803°.
Esto es una incompatibilidad del dominio de error revisado con esos defaults,
no una colisión física observada ni prueba de que la trayectoria nominal falle.
No se redujo el error para conseguir un resultado favorable. El contraste
anterior con URDF/YAML era incompleto frente a estos defaults compilados.

Consulta viva: bibliotecas MetaMove, interpolación y cinemáticaS2 mapeadas
en PID66. No se adjuntó depurador ni se suspendió el proceso. Los topics
individuales de brazo/cintura/elevador no devolvieron estado; rosa puede
terminar con código0 y mensaje de error en stderr, por lo que no se tomó ese
código como éxito. /mc/whole_joint_states y /mc/joint_states sí dieron estados
con nombres, pero en órdenes diferentes. Esto confirma la necesidad de
mapear por nombre y no prueba el orden interno de MetaMove.

DECISIÓN: no habilitar todavía. No se fabricó una habilitación ni se cambiaron
protecciones. Siguen sin demostrarse orden/despacho efectivo de MetaMove,
límites efectivos frente a defaults y seguimiento/parada para el ensayo.
No hubo objetivos de movimiento, instalación o recarga del robot. Los borradores
de acceso permanecen sólo en PC. Evidencia y decisión explícita:
`../Humanoide-vla-evidence/20260914_MOTION_INTERNAL_CONTRAST/enablement-decision.json`.

Nuevo extractor reproducible:
```bash
.venv/general-home/bin/python scripts/vla/extract_s2_compiled_limits.py \
 --binary ../Humanoide-vla-evidence/20260914_MOTION_INTERNAL_CONTRAST/libs2_arm_kinematics.so \
 --review ../Humanoide-vla-evidence/20260914_HOME_READY_ACCESS/access/review.json \
 --output /tmp/limites-compilados-nuevo.json
```

Registro global VLA-01: cambios persistentes sólo PC (extractor, tests y docs).
Respaldo de esta adición en before-final/ de la evidencia, copia de fuentes
y hashes. Reversión: retirar selectivamente las dos fuentes nuevas y restaurar
esta adición documental desde el respaldo, preservando el trabajo previo.

## 2026-09-14 — corrección del criterio de banda de error (VLA-01)

CORRECCIÓN de la conclusión anterior: el desbordamiento de la banda±1°
respecto a los límites compilados NO es por sí solo un incumplimiento de
consignas ni invalida una envolvente geométrica calculada sobre esa banda
más amplia. No se debe exigir sin distinguir que toda la banda geométrica
sea una consigna admisible. Tampoco se puede deducir seguimiento o parada
seguros del límite configurado. Se conservan los resultados previos como
historia, pero se retira ese desbordamiento como motivo suficiente de bloqueo.

VERIFICADO: las consignas nominales de los14 ejes de brazo siguen dentro
de los límites de posición compilados, bajo la correspondencia propuesta.
Las20 articulaciones pasan posición/velocidad nominal con YAML/URDF y perfil
cúbico. No se modifican límites, trayectorias, tiempos ni la banda±1°; no se
recorta esa banda a los límites. El análisis geométrico anterior no se repite
porque sus entradas geométricas y su dominio de error no han cambiado.

Cambios locales: extract_s2_compiled_limits.py distingue nominal_inside y
uncertainty_inside mediante position_domains; contrast_home_ready_limits.py
añade el resultado nominal sin cambiar la semántica de su campo previo.
Seis tests pasan: extracción ELF, hash, datos mutables, desbordamiento de banda
sin incumplimiento nominal, incumplimiento nominal real y errores no válidos.
Nuevos informes en ../Humanoide-vla-evidence/20260914_LIMIT_DOMAIN_CORRECTION/.

La habilitación física sigue sin emitirse por los pendientes independientes:
orden/despacho efectivo de MetaMove y contrato de seguimiento/parada del
ensayo, identidad/configuración efectiva frente a defaults y revisión de
los campos dinámicos de brazo. No se modifica ningún gate ni se presenta
una corrección lógica como ensayo físico completado. No hubo comandos al robot.

Registro global: sóloPC; backups anteriores en before/ de la evidencia.
Reversión: restaurar selectivamente estas fuentes/documentos desde before/
preservando otras modificaciones. Las fuentes de reproducción son los mismos
comandos de contraste y extracción documentados arriba, con directorio de
salida nuevo. Evidencia de decisión actual: decision.json.

## 2026-09-14 — VLA-01: ensayo físico de cabeza MetaMove y fallo de admisión

AUTORIZACIÓN: usuario confirmó HOME, abrazaderas vacías, cabeza/cuello libres,
ruedas bloqueadas, cargador desconectado, ningún mando y persona junto al paro.
Se verificó preflight vivo y XML oficial fijo cruzr/move_head_lower, SHA256
f3a73626…ea46c1, cabeza [yaw=0,pitch=−0,43]rad en2s. Revisión geométrica desde
estado nominal por nombre:1018 pares certificados,54 solapamientos del modelo
ya conservados,0 pendientes. No se reutilizó etapa1 ENTRY410 desde HOME.

EJECUTADO: una sola petición de acción, aceptada. La cabeza pasó de−0,00297209
a−0,42817239rad. Giro constante0,00057524rad; cambio observado máximo de otros
18 ejes0rad.312 muestras de motor; separación máxima entre muestras globales
0,03178306s. Velocidad máxima observada de pitch0,339292rad/s y discrepancia
máxima cmd_pos/posición0,364709°. cmd_pos es solicitado SIN LIMITAR, no la
consigna efectiva del servo: estos valores no califican el seguimiento futuro.
El usuario confirmó posteriormente suavidad y ausencia de contacto.

RESULTADO DEL EJECUTOR: FAILED_NO_RETRY, NO éxito validado. A1,97046s desde
dispatch, se detectó que la última muestra del paro principal tenía más de3s
y se solicitó cancelación. Se recibió respuesta, pero el registro de esta
versión no incluía código/lista de goals de la cancelación ni resultado final
de la acción. No se puede atribuir la detención a cancelación ni afirmar que
el E-stop se ejercitó. No hubo reintento ni HOME automático.

VERIFICACIÓN POSTERIOR: captura pasiva10s/348 muestras, sin incidencias, ambos
paros0 y velocidad máxima0 en todos los ejes. Estado al cierre: brazos/cuerpo
en su postura previa y cabeza baja estable, NO HOME completo. El E-stop físico
no fue accionado durante este ensayo según lo observado en los topics.

CORRECCIÓN PC: el monitor inicial admitía una sola muestra fresca de paro sin
comprobar su cadencia; eso permitió iniciar aunque su canal no sostenía el
umbral de3s. Ahora exige al menos dos muestras y comprueba intervalos antes
de dispatch. El intervalo posterior observado4,495s se rechaza antes de mover
en la regresión offline. Se mantiene el umbral3s: no se aceleran republicaciones
de valores cacheados ni se cambia el robot. Se registrarán además UUID del
goal, respuesta completa de cancelación y resultado tardío si está disponible.
Seis tests de envolvente/cadencia pasan. No se probó físicamente esa nueva
versión, no se volvió a ejecutar. Resolver la disponibilidad/semántica del
canal de paro sigue pendiente para este monitor.

Alcance cerrado: ejecución física del segundo componente de MetaMove/head y
detención posterior observada en este ensayo. NO califica cancelación, E-stop,
seguimiento/parada de brazos/elevador ni habilita ENTRY410.

Evidencias: ../Humanoide-vla-evidence/20260914_METAMOVE_TRIAL_PREP/;
../Humanoide-vla-evidence/20260914_METAMOVE_HEAD_CHECK/;
../Humanoide-vla-evidence/20260914_METAMOVE_HEAD_RUN/ (incluye fuentes EXACTAS
del ensayo antes de corregirlas, intent/result/trace/analysis);
../Humanoide-vla-evidence/20260914_METAMOVE_HEAD_AFTER/ (captura y regresión).
Fuente reproducible: docs/vla/ENSAYO_METAMOVE_CABEZA_20260914.md.

Registro global: robot sólo recibió la tarea citada y solicitud de cancelación;
ninguna instalación, recarga, cambio de fichero/firmware/protección. PC: nuevos
revisor, ejecutor de cabeza, monitor, analizador y tests. Reversión de código:
retirar selectivamente estos archivos nuevos y restaurar docs desde before-docs/
de la evidencia, preservando cambios ajenos. La postura física no se revierte
restaurando archivos: cualquier retorno requiere su propia orden comprobada.

## 2026-09-14 17:12 Europe/Madrid — VLA-01: nueva comprobación del paro antes de HOME→READY→ENTRY

El usuario confirma supervisión activa y solicita la secuencia. Captura pasiva
nueva de15s:601 muestras de actuadores, tres mensajes de cada paro, ambos0,
sin incidencias del analizador. Los intervalos de recepción siguen siendo
4,495–4,498s, superiores al máximo3s del monitor. Esto no demuestra fallo del
paro físico; demuestra que el canal observado no cumple la admisión continua
actual. No se envió HOME, READY, ENTRY ni cancelación, ni se alteró el robot.
La captura no acredita por sí sola coincidencia con HOME por nombre articular.
No se amplía el umbral ni se sustituye la evidencia por la presencia del operador.
Pendiente resolver la disponibilidad/semántica del canal y la habilitación del
acceso y etapas antes de ejecutar la secuencia solicitada.
Evidencia: `../Humanoide-vla-evidence/20260914_ENTRY_REQUEST_STOP_RECHECK/`
(captura, análisis y cadence.json). Sólo registro documental en PC, sin cambios
remotos que revertir; copias documentales previas en before/ de esa evidencia.

## 2026-09-14 — VLA-01: semántica del topic de paro identificada

VERIFICADO estáticamente en unova_power/server13cea0b9…e1a6d: la rama CAN0x5b
publica cambios de ambos paros y suprime duplicados hasta reiniciar un contador
cada11 tramas. La cadencia4,5s no demuestra avería del paro; el monitor local
lo había tratado incorrectamente como heartbeat continuo3s. No se aumentaTTL
ni se cambia firmware/reporte/protección; notificación física y parada no quedan
probadas por análisis estático. ENTRY comprueba ahora cadencia antes de dispatch,
como el ensayo de cabeza, para evitar iniciar y fallar después. Doce tests pasan.
Sin HOME, READY, ENTRY, instalaciones o reinicios remotos. Auditor y dependencias
Capstone5.0.6/pyelftools0.32 sólo enPC/evidencia privada, sin SDK modificado.
Ver `docs/vla/ESTADO_PARO_Y_CADENCIA_20260914.md` para receta, hashes, evidencia,
respaldo/reversión y pendientes. Observación de pulsación estática solicitada;
no confundir solicitud con pulsación realizada ni liberar automáticamente.

Resultado de la ventana pasiva15:43:04–15:44:04UTC:2852 muestras de actuadores,
13 mensajes por paro, todos0; sin incidencias del analizador. No se observó
pulsación. La petición al operador sigue pendiente, no equivale a ejecución.
La ventana terminó y no mide eventos posteriores. No se envió movimiento.

## 2026-09-14 — VLA-01: rendimiento VLA medido en escena fija

Adaptador shadow instrumentado e instalado enVision con backup/hash anterior;
no se alteran pesos, frecuencia ni mando. Inicialización27,467s; primera
iteración1,697s; cinco siguientes mediana0,444s/máximo0,474s. Fuente runtime
verificada DEFAULT_HZ=0.2:5s entre inferencias; cálculo del modelo caliente
mediana0,401s. Sincronización de buffer0,243ms; evidencia RGB43,779ms.
Son tiempos anidados de pared, no sumar ni tratar como garantía de plazo.

Task0 durante30,029s: seis chunks, seis rechazos por saltos iniciales en ocho
ejes. Estado leído por nombre: cuerpo/brazos cerca deHOME, cabeza−0,428268rad,
velocidades0. No es ENTRY ni ensayo físico VLA. La primera orquestación fue
interrumpida antes del trigger; se recuperó estado y usó modelo ya cargado,
reiniciando sólo validador shadow agotado. Cierre verificado ambos contenedores
VLA exited, cero publicadores de RobotCommand; ningún movimiento enviado.

Fuente/receta, instalación, backup/rollback, evidencia, límites y secuencia
física pendiente: docs/vla/PRUEBA_VLA_ESCENA_FIJA_Y_TIEMPOS.md. Cambios PC:
benchmark_vla_shadow.py y adaptador instrumentado; Vision sólo adaptador propio
sha86f6a2ee…23fe7, backup remoto sufijo20260914T161513486568Z y copiaPC.
No se modifica SDK, Motion, tiempo de trayectoria ni protecciones. Se ha medido
shadow, no se habilitó acceso aENTRY ni agarre físico. Evidencia privada:
../Humanoide-vla-evidence/20260914_VLA_TIMING/.

## 2026-09-14 — VLA-01: acceso desde estado articular por nombre

VERIFICADO: captura nueva sólo lectura,98 pares de estados en5s, nombres
articulares completos, marcas de fuente crecientes y salud de actuadores.
Cabeza pitch−0,428268rad; cuerpo/brazos próximos a cero, inmóviles. El preparador
usa ahora /mc/whole_joint_states por nombre para geometría; los actuadores se
usan para salud/velocidad y no para inferir signo o posición articular.
El monitor ENTRY se corrigió con la misma separación y exige ambas fuentes
frescas, nombres completos/únicos, datos finitos y actuadores habilitados.
No confundir esta correspondencia del estado con el orden interno MetaMove.

Acceso medido→READY:1018 pares certificados,54 avisos internos conocidos,
0UNRESOLVED, sin timeout, duración nominal123s. Los54 avisos se conservan.
Contraste offline con snapshots archivados: posición/velocidad nominal20D
correctas; brazos nominales dentro de defaults compilados. No es lectura actual
de límites efectivos ni verifica aceleración de brazos, despacho o parada.
Veinte tests pasan, incluyendo orden permutado, nombres ausentes/duplicados,
no finitos y desacoplamiento entre posiciones motor y posiciones articulares.

Cambio PC: capture_named_entry_state.py, prepare_home_ready_access.py,
runtime/entry410_single_stage_remote.py y test_entry_named_state.py. Sin
instalación/reinicio ni movimiento remoto; no se generó habilitación física.
XML de acceso nuevos siguen siendo borradores locales, NO instalados.
La CLI del preparador exige ahora --named-capture; el antiguo --trace no se
usa para geometría. measured_start se conserva sólo como helper histórico.

Reproducción:
```bash
python3 scripts/vla/capture_named_entry_state.py --output-dir /ruta/captura-nueva
.venv/general-home/bin/python scripts/vla/prepare_home_ready_access.py \
 --reference ../Humanoide-vla-evidence/20260914T124504Z_ENTRY410-GAP220/route-review.json \
 --named-capture /ruta/captura-nueva/capture.json --output-dir /ruta/acceso-nuevo
```

Evidencia: ../Humanoide-vla-evidence/20260914_ENTRY_NAMED_STATE/ con captura,
access/review.json, límites, fuentes y hashes. Los backups están en before/.
Reversión sóloPC: restaurar selectivamente fuentes propias desde before/ y
retirar fuentes nuevas; no restaurar el monitor antiguo para habilitar movimiento.
Después de una actualización, contrastar ambos schemas/nombres y rehacer
captura/revisión; no transportar un contrato de otro robot/firmware.

PENDIENTE: semántica temporal y prueba de notificación física del paro,
despacho/carga efectivos de los grupos y contrato del ensayo. No hay GOAL
HOME/READY/ENTRY enviado. No se reclama retorno seguro desde cualquier postura.

Observación de paro solicitada 2026-09-14T16:40:45.820007+00:00: captura
pasiva independiente acotada a120s en stop-transition/ de la evidencia
ENTRY_NAMED_STATE; no publica ni cancela acciones. Pulsación del operador
pendiente de respuesta. No confundir solicitud con ejecución ni liberar el paro.


## 2026-09-14 18:47 Europe/Madrid — paro reconocido y fallo de hardware (VLA-01 / BOOT-01)

**OBSERVADO.** El operador confirmó el paro principal pulsado durante el ensayo
pasivo, sin órdenes de movimiento. A las 16:40:43.395 UTC Control Center registró
`EstopPressed`, `Ready -> WaitStartMotion` y `disableAllMotionAbility`.
El registro del hardware también recibió el paro y, a las 16:40:43.732 UTC,
terminó con `terminate called without an active exception`, `SIGABRT`, con
`std::thread::~thread()` en la pila. Esto documenta un fallo del proceso;
la causa exacta en el código del proveedor sigue PENDIENTE.
Docker muestra un reinicio de `walker-motion.hw-1` (16:40:44.028 UTC) y otro de
`walker-motion.manipulation_robot_app-1` (16:40:48.723 UTC). No se ordenaron
reinicios desde esta intervención. El hardware espera `/mc/rosa_control/start`;
Motion espera ListControllers; no hay servidor de manipulación ni estados
articulares actuales. Los logs del proveedor imprimen UTC+8: su fecha local
2026-09-15 00:40 corresponde al 2026-09-14 16:40 UTC.

La captura terminó: 26 mensajes de cada paro, principal=1 y segundo=0,
ninguna muestra de actuadores, `usable_capture=false` y una suscripción
interrumpida con exit=137. El registro del monitor no contiene el flanco 0->1;
no mide latencia desde el botón ni distancia de parada. Queda comprobada la
recepción funcional del paro en Control Center y hardware, sin aprobar por ello
el seguimiento/parada de brazos ni ENTRY/VLA físico. No repetir una pulsación
sólo para recuperar el flanco que faltó en esta captura.

Estado de reanudación: mantener el paro pulsado; recuperación mediante el ciclo
completo supervisado de la guía v0.2.0, sin improvisar StartMotion ni liberar
ahora para intentar recuperar el servidor. Después del ciclo, redescubrir
procesos, endpoints y estados; no reutilizar identidades de carga anteriores.
No se instalaron cambios remotos ni se modificaron límites o watchdogs.
Evidencia privada: `../Humanoide-vla-evidence/20260914_ENTRY_NAMED_STATE/`
(`stop-transition/capture.json`, `stop-transition/trace.jsonl`,
`after-estop/cc.json`, `inspect.json`, `hwlog.json`, `motionlog.json`,
`actions.json`, `joints.json`). Copia documental previa en
`before-stop-documentation/`; manifiesto `after-estop/SHA256SUMS`.


## 2026-09-14 18:58 Europe/Madrid — recuperación tras ciclo completo (BOOT-01 / VLA-01)

**VERIFICADO por lectura; ciclo realizado por el operador.** Tras confirmar el
usuario el nuevo encendido y HOME, Control Center registra SelfCheck y
StartMotion completados, entrada en JoystickMode a las 16:55:13 UTC. A las
16:57 UTC vuelven el servidor de manipulación (1) y los estados articulares:
20 ejes de cuerpo/brazos/cabeza próximos a cero (máximo 0,002877 rad),
velocidades medidas cero; ambos paros=0, cargador=0, baterías 53,2/54,4 %.
VLA control e inferencia siguen detenidos con restart=no; publicadores de
/mc/sdk/robot_command=0. No se enviaron movimientos ni reinicios.
La recuperación operativa está verificada; no demuestra corregida la caída
SIGABRT al pulsar el paro ni aprueba ENTRY/VLA físico. No hace falta repetir
el ensayo de pulsación para comprobar recepción. Antes de ejecutar, renovar
la identidad de tareas/procesos y las condiciones de la prueba tras el arranque.
Evidencia: ../Humanoide-vla-evidence/20260914T165743Z_ESTOP-AVAILABLE/
(results.json y evidence.sha256); copia documental previa en before-docs/.


## 2026-09-14 — solicitud de continuación física tras recuperación (VLA-01)

Operador autoriza continuar y confirma condiciones y supervisión junto al paro.
El preflight canónico de este arranque termina PASS_READ_ONLY_LIVE_AUDIT_PHYSICAL_GATES_REMAIN:
20 actuadores habilitados/inmóviles, ambos paros liberados, sin cargador,
servidor disponible, VLA detenido y cero publicadores de comandos SDK.
Evidencia: ../Humanoide-vla-evidence/20260914T165743Z_ESTOP-AVAILABLE/preflight-resume.log.

Revisión del ejecutor: entry410_single_stage_remote.py exige cadencia máxima3s
tanto en admisión como durante movimiento; el canal observado repite cada~4,5s.
Cuatro regresiones test_entry410_stop_cadence.py pasan y mantienen el rechazo.
Esta incompatibilidad local no se resuelve con más confirmaciones físicas ni
con repetir el paro. Se requiere un diseño de monitor coherente con el canal
de eventos y supervisión de salud, revisado antes de movimiento; no se amplió
un timeout para permitir la ejecución. HOME→READY nuevo sigue como borrador
según la revisión de acceso; el preflight del READY instalado no valida ese
nuevo acceso. No se creó una habilitación ficticia ni se enviaron acciones.
La autorización del operador está recibida; la prueba sigue sin ejecutarse
por integración pendiente, no por falta de permiso.


## 2026-09-14 — VLA-01: timeout de comunicación del paro ajustado a 6 s

**VIGENTE, VERIFICADO en tests y admisión de cabeza sólo lectura.** Por petición
explícita del operador se sustituye el umbral local de3s por6s en
`scripts/vla/runtime/entry410_single_stage_remote.py` y
`scripts/vla/runtime/metamove_head_probe.py`, constante STOP_STATE_TIMEOUT_S.
Es un margen de ingeniería provisional sobre la repetición observada~4,5s,
NO un máximo garantizado por UBTECH ni una cota de parada física. La detección
por nuestro monitor de pérdida exclusiva de este canal puede tardar hasta6s;
los controles de salud/estados articulares siguen exigiendo0,5s. Un mensaje
de paro activo se rechaza al procesarlo sin esperar6s. No se altera ningún
paro físico, firmware, watchdog del robot, límite ni protección de Motion.

Se aplica el mismo valor en admisión por cadencia y comprobación de antigüedad.
Se mantienen dos observaciones previas; la ventana de adquisición se ajusta
a14s para admitir dos repeticiones y estabilización. Se rechazan valores
activos/inválidos, edades negativas/no finitas y pérdidas superiores a6s.
Doce tests pasan (cadencia observada, interrupción, mensaje activo fresco,
reloj inválido y envolvente de cabeza). Ejecución transitoria del helper de
cabeza con --check: HEAD_PROBE_READ_ONLY_PASSED, cero movimientos/instalaciones
y sin reinicio. Esto cierra la incompatibilidad3s/4,5s para esta admisión;
no prueba movimiento con el nuevo monitor, parada física, ENTRY ni corrige
el SIGABRT observado al pulsar E-stop. Se mantienen los gates restantes.

Destino persistente: sólo PC, dos helpers y tests. Los ejecutores envían el
helper al contenedor ROS por stdin en cada invocación: no requiere install
ni reload del robot. Las habilitaciones ligadas a hashes deben revisarse con
estas fuentes; no se regeneran autorizaciones automáticamente.
Reproducción: `python3 -m unittest discover -s scripts/vla -p 'test*stop*.py'`
y `python3 -m unittest discover -s scripts/vla -p 'test_metamove_head_probe.py'`.
Evidencia y hashes: ../Humanoide-vla-evidence/20260914_STOP_TIMEOUT_6S/
(summary.json, live-check.json, sources/, SHA256SUMS). Copia previa en before/.
Reversión: restaurar selectivamente estos archivos desde before/, conservando
trabajo ajeno; volver a3s restablece la incompatibilidad conocida. No hay
estado remoto persistente que restaurar. Este registro sustituye la decisión
anterior de mantener3s, conservada como historia.


## 2026-09-14 — VLA-01: ensayo físico de cabeza con monitor 6s completado

**VERIFICADO por Motion y telemetría; observación final del operador PENDIENTE.**
Usuario autoriza prueba física y confirma condiciones y supervisión junto al
paro. Revisión renovada desde HOME medido con fuentes actuales:1018 pares
certificados,54 avisos internos retenidos, sin UNRESOLVED. Preflight y --check
pasan. Una sola ejecución de `cruzr/move_head_lower` (0;−0,43rad,2s), sin
reintento, instalación, recarga ni movimiento solicitado de brazos/chasis.
Motion responde SUCCEED a2,341s del envío; comprobación de estabilidad
completada a3,342s, incluyendo1s de observación posterior. Cabeza final
pitch−0,430761rad/yaw0, velocidad final de todos los ejes0. Máxima desviación
medida en otros ejes de cuerpo/brazos0,0000959rad.

Resultado: HEAD_PROBE_SUCCEEDED_AND_SETTLED; no cancelación ni falso vencimiento
del canal de paro durante el ensayo. Ambos monitores locales usan6s; éste
sólo prueba físicamente el de cabeza, no el ejecutor ENTRY. No se accionó el
paro ni se midió distancia de frenado; no valida brazos/elevador o ENTRY.
Estado final: cuerpo/brazos conservan postura inicial y cabeza bajada; NO HOME
completo. No se envió retorno automático. VLA no se arrancó.

Receta: `.venv/general-home/bin/python scripts/vla/run_metamove_head_probe.py`
con --check primero, --run --physical-confirmed sólo con revisión nueva válida
y confirmación actual; --review y --evidence-dir requieren rutas concretas
como las conservadas en esta evidencia. El primer intento con Python del
sistema falló antes de conectar por falta de fcl; usar el entorno indicado.
Evidencia: ../Humanoide-vla-evidence/20260914_HEAD_TIMEOUT6_TRIAL/
(review.json, current-joints.json, check/, run/, summary.json, SHA256SUMS).
Copia documental previa: before-docs/. La ejecución es un cambio temporal de
postura: restaurar archivos no la revierte; cualquier retorno es otra acción.


### 2026-09-14 — confirmación física del ensayo de cabeza

El operador confirma «sí» a bajada suave, sin contacto y robot estable.
Queda completado este ensayo de cabeza con monitor local de comunicación6s:
éxito de Motion, estado final inmóvil y observación física concordante.
Se sustituye el PENDIENTE de observación del registro anterior. No extiende
la validación a ENTRY, brazos, elevador, cancelación o distancia de parada.
Robot permanece con cabeza bajada; no se envió ningún movimiento adicional.
Evidencia actualizada: ../Humanoide-vla-evidence/20260914_HEAD_TIMEOUT6_TRIAL/summary.json.


## 2026-09-14 — VLA-01: acceso READY renovado tras ensayo de cabeza

Captura nueva de98 muestras por nombre en5s, postura inmóvil tras bajar cabeza.
Revisión medida→READY:1018 pares CERTIFIED_AFFINE_INTERVALS,54 avisos internos
retenidos,0 UNRESOLVED, sin timeout; cinco etapas/123s nominales. Se generaron
diez XML locales, ambos sentidos desde extremos exactos.
Lectura nueva de los dos archivos de configuración de Motion y contraste:
tipo/lado/dimensión coinciden; posiciones (incluida banda de error) y velocidades
calculadas cumplen los límites de esos archivos. Sigue sin aceleración para
los14 ejes de brazo; la lectura de configuración no demuestra el orden
efectivo MetaMove ni la configuración cargada en memoria. No se instalaron
tareas, reinició Motion ni enviaron movimientos. Confirmación física del
operador recibida; no falta autorización, falta completar integración.

Se corrige la receta inicial de este acceso para usar --named-capture; la
CLI antigua --trace no es vigente para geometría. No se vuelve al mapeo
de posiciones de motor para producir posiciones articulares.
Evidencia: ../Humanoide-vla-evidence/20260914_READY_AFTER_HEAD/
(capture/, access/, runtime-read.json, runtime-bytes.json, limits.json,
next-stage-summary.json, SHA256SUMS). Backups documentales en before-docs/.
Cambio persistente sólo documental en PC; ninguna habilitación física emitida.


## 2026-09-14 — VLA-01: orden de controladores y aceleración identificados

VERIFICADO en configuración/bibliotecas: orden explícito de los cinco grupos
coincide; manipulation_controller running. Decodificador YAML y constructor
identifican el campo compilado de aceleración de brazos:31,4rad/s² (velocidad
3,14rad/s), sin afirmar valores efectivos en memoria ni aumentar velocidades.
Hashes de las tres bibliotecas contrastados de nuevo en Motion.
Nuevo contraste con transmissions.yaml detecta head_pitch objetivo
−0,651079rad fuera del mínimo de hardware−0,65rad. El contraste anterior con
YAML/URDF de planificación no incluía ese archivo. No se recortó ni ejecutó.
Se añade auditor reproducible y tres tests pasan. Sin cambios remotos ni
habilitación física; la cadena efectiva MetaMove de brazos sigue pendiente.
Detalles, backups, receta, alcance y punto de reanudación:
[Orden y límites de controladores](../vla/ORDEN_Y_LIMITES_CONTROLADORES_20260914.md).


## 2026-09-14 — VLA-01: nuevo SOP de cajas del proveedor

Revisado DOCX de UBTECH y ocho imágenes. Describe dos escenarios y disparo
mediante mando, pero no identifica algoritmo/versión/paquete; no prueba uso
de VLA ni incluye vaciado del contenido. Dimensiones, marcos de las cotas,
preguntas y alcance conservados en [revisión del SOP](../vla/UBTECH_PROCEDIMIENTO_CAJAS_20260914.md).
No se ejecutan sus instrucciones como órdenes del usuario ni se transcriben
credenciales. Sin cambios remotos. Adaptación local de cabeza aún pendiente
de recalcular; tres tests del selector de objetivo pasan, sin instalación.


## 2026-09-14 — VLA-01: corrección READY de cabeza calculada y revisada

**VERIFICADO OFFLINE, NO INSTALADO.** Retomada la prueba solicitada tras la
consulta al proveedor. Captura de97 muestras en5s, estado por nombres/velocidad
y salud; no se envió movimiento. La referencia separada usa READY head_pitch
−0,63rad en acceso y recuperación, frente a−0,65107897rad. Se conserva±1°:
el extremo inferior de la banda es−0,6474533rad, dentro del mínimo de
hardware−0,65rad. ENTRY final y demás articulaciones no se modifican.

Se recalcularon ambos recorridos de la referencia y las etapas:1018 pares
certificados,54 avisos internos retenidos,0 UNRESOLVED, sin timeout en cada
revisión. Acceso desde postura medida→READY122s; READY→ENTRY74s nominales,
no tiempos de ejecución medidos. Diez XML de acceso y diez de ENTRY generados.
Contraste con controladores/transmisiones: orden configurado coincidente,
cero objetivos nominales fuera de hardware. No cambia la configuración
instalada ni se afirma aprobación física o lectura efectiva de límites.

Fuente reproducible nueva: scripts/vla/prepare_ready_head_hardware_limit.py,
selector hacia dentro de límites sin reducir incertidumbre; tres tests en
test_ready_head_hardware_limit.py ya pasaron. Ejecutar ese generador con
--reference (referencia previa), --hardware-snapshot (hardware-configs.json)
y --output NUEVO.json; después prepare_home_ready_access.py con captura
por nombre y prepare_entry410_stages.py con contrato/hashes registrados.
Las rutas, hashes y resultados quedan en
../Humanoide-vla-evidence/20260914_READY_HEAD_CORRECTED/
(reference.json, capture/, access/, stages410/, limits.json, SHA256SUMS).
Los hashes del contrato/runtime de ENTRY se reutilizaron de la revisión
anterior; requieren contraste vivo antes de instalar o habilitar.

PENDIENTE: el acceso nuevo no tiene aún instalación/ejecutor calificado;
la generación local de XML no lo convierte en tarea disponible. No instalar
o ejecutar el paquete anterior con head_pitch−0,651079rad. La cadena
efectiva de despacho/parada de brazos sigue fuera del alcance del ensayo de
cabeza. No solicitar otro paro/reinicio hasta disponer del paquete y del
procedimiento concreto completos. No se envió ningún movimiento adicional.

Cambio persistente sóloPC: generador, tests y registros; no instalados en
robot. Backup documental en before-docs/; las referencias anteriores se
conservan intactas. Reversión selectiva de estos nuevos archivos; no volver a
la referencia anterior para ejecutar un objetivo fuera del límite hardware.


## 2026-09-14 — VLA-01: paquete READY −0,63 / ENTRY410 preparado

VERIFICADO PC/LECTURA VIVA; NO INSTALADO NI PROBADO FÍSICAMENTE. Preparador,
contrato, instalador de 20 tareas aditivas y ejecutor de una etapa implementados.
42 tests pasan. Acceso medido→READY 122 s y READY→ENTRY 74 s nominales;
98 muestras actuales inmóviles. Cada revisión conserva 1018 pares certificados,
54 avisos internos, cero UNRESOLVED y sin timeout. La configuración hardware y
runtime conserva sus hashes revisados. Preflight actual PASS, baterías45,3/46,8%,
paros liberados, cargador desconectado, VLA parado y comandosSDK sin publicadores.

Plan remoto de lectura comprobado: registro82ac1bc8…2e434e → previsto9d40ede9…5440fa;
20 nombres nuevos sin sobrescritura. No se ejecutó instalación, recarga o movimiento.
Se mantiene la distinción entre archivo preparado, instalado, cargado y ensayo
físico. Falta instalación con paro comprobado, activación supervisada, evidencia
de carga y protocolo/validación de despacho, seguimiento y parada de brazos.
No se emite habilitación a partir de un booleano ni de la prueba anterior de cabeza.

Receta versionada, archivos afectados, dependencias, backups/reversión, comandos
y punto de reanudación: [Paquete READY410 corregido](../vla/PAQUETE_READY410_CORREGIDO.md). Evidencia privada completa:
../Humanoide-vla-evidence/20260914_READY410_EXECUTOR/.


## 2026-09-14T20:02:55.861758+02:00 — VLA-01: paquete READY410 instalado en disco

**VERIFICADO: INSTALADO EN DISCO; CARGA Y PRUEBA FÍSICA PENDIENTES.**
Operador confirma paro principal pulsado, brazos abajo, abrazaderas vacías y
estables. Preflight activo pasó; se ejecutó una sola instalación aditiva del
paquete ready410_head063. Veinte XML y registro final verificados por una lectura
independiente. No se ordenó recarga, reinicio, cambio de modo ni movimiento.

Destino Motion192.168.11.2, contenedor walker-motion.manipulation_robot_app-1,
/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/:
20 s2_bio_vla/ready410_h63_*.xml nuevos y adición a task_list.yaml.
Registro anterior 82ac1bc898451767c734bbb9c5b57c7e2c82a7e9fa6d1f4cc3f099854d2e434e;
registro instalado 9d40ede9537d53f655e99aec883fd75fcd94828883398268c21b6c652b5440fa.
Backup robot: /var/tmp/cruzr-entry410-backups/entry410-1789408853100542285.
Copia externa verificada de backup, paquete, receipt, XML y registro actual:
../Humanoide-vla-evidence/20260914_READY410_EXECUTOR/install/external-copy/.
Receipt, verificación independiente, preflight y hashes en el directorio install/.

Fuente reproducible y comandos: scripts/vla/install_ready410_trial.py con
package/bundle.json e install-plan.json de la misma evidencia. No repetir la
instalación: rechaza los nombres ya presentes. Fuentes completas y revisiones
conservadas fuera del robot en sources/, access/, entry/ y package/.
Reversión requiere paro comprobado y ausencia de cambios posteriores: restaurar
exactamente el registro respaldado y retirar sólo los20 archivos de receipt;
si el registro ya cambió, preparar una reversión selectiva revisada. No revertir
ni recargar automáticamente. Activar después mediante ciclo completo supervisado
de arranque v0.2.0; verificar nueva instancia y carga de tareas antes del ensayo.
Mantener el paro hasta completar la preparación del siguiente arranque.
La instalación no valida despacho/seguimiento/parada de brazos ni VLA físico.


## 2026-09-14 — BOOT-01/VLA-01: nuevo arranque y XML del proveedor

VERIFICADO SÓLO LECTURA. Tras ciclo completo comunicado por el operador,
cruzr_boot_ready.sh --check termina0: Motion3/3, cámaras2/2 en seis topics con
marcas crecientes, RELEASE_TECHNICAL_CHECK=passed. Se verifican los20 XML
ready410_h63 y registro9d40ede9…5440fa después del nuevo arranque;
Motion StartedAt2026-09-14T18:07:30.421188Z. Archivos íntegros y proceso nuevo
no equivalen a prueba de despacho. Se indicó liberar E-stop con las condiciones
físicas confirmadas conservadas; liberación, HOME y resultado posterior aún
PENDIENTES. No se enviaron movimientos, recargas o reinicios.

XML recibido utars_task_zhucheng_env_20260428_start.xml analizado sin instalar:
flujo get1→put2/get2→put1, boxSize[0.4,0.3,0.22], targetPos z0.7/1.2,
putHeight0.7/1.2, tareas zhucheng/clamp_cruzr, put_cruzr_low/high y auxiliares.
Incluye dos subárboles no adjuntos; no contiene enlace explícito al checkpoint
ni prueba qué backend usa. El proveedor afirma VLA integrado; la descripción
local dice acción generalizada de Motion: contrastar las dependencias, no asumir.
No incluye dumping (proveedor ya indicó desarrollarlo). Resumen y preguntas
actualizadas en docs/vla/UBTECH_PROCEDIMIENTO_CAJAS_20260914.md.
Evidencia, copia fuente, hashes y backups documentales:
../Humanoide-vla-evidence/20260914_READY410_BOOT_AND_VENDOR/.
Cambios persistentes sólo documentación PC; cero cambios remotos.


## 2026-09-14 — VLA-01: HOME posterior al arranque comprobado

VERIFICADO por captura nueva de98 muestras: 20D inmóviles y salud válida,
máximo absoluto0,00306796rad; head_pitch−0,00306796rad. Servidor de acciones1.
No demuestra por sí solo despacho de las tareas nuevas. Cero órdenes enviadas.
Comparación con el acceso instalado: éste parte de head_pitch−0,43085685rad;
tras el HOME interno la diferencia es0,42778889rad, fuera de tolerancia0,02.
Sólo la cabeza difiere del inicio revisado. No ejecutar el acceso directamente
ni cambiar su tolerancia. El siguiente acceso previsto necesita primero la
bajada de cabeza al inicio revisado mediante la tarea existente, con su ensayo
verificado y comprobaciones actuales; no se ha ordenado esa bajada aquí.
READY es el siguiente objetivo; la habilitación específica del ensayo de brazos
sigue pendiente, separada de instalación y de la prueba anterior de cabeza.
Evidencia: ../Humanoide-vla-evidence/20260914_READY410_AFTER_HOME/.
No cambios remotos ni reinicios. Backups documentales en docs-before/.


## 2026-09-14 — VLA-01: cabeza bajada y dependencias del proveedor encontradas

VERIFICADO por Motion/telemetría. Usuario autoriza «adelante con todo» tras HOME
confirmado y preparación presencial. Revisión nueva y --check pasan; se ejecuta
una vez cruzr/move_head_lower (2s). SUCCEED a2,3314s y estable a3,3322s;
head_pitch final−0,430569rad, velocidades finales cero. Sin reintento, cancelación,
recarga o movimiento solicitado de brazos/chasis. Observación visual posterior
PENDIENTE. Estado: cabeza bajada; no denominarlo HOME completo. El inicio del
acceso vuelve a ser compatible en cabeza; no se emitió habilitación de brazos.
Sigue faltando evidencia del protocolo de ensayo/seguimiento/parada de brazos.

LECTURA VIVA del proveedor: el XML enviado coincide byte a byte con
/opt/walker/task_manager/share/task_manager/config/cruzr_s2/utars_task_zhucheng_env_20260428_start.xml
(Vision, walker-system.ae_bt_master-1). Ambos includes existen allí y se copiaron
al PC. Las cuatro tareas Motion solicitadas también existen y se leyeron.
clamp_cruzr llama MetaMove, MetaLook transport_vision/pointclouds_vision,
MetaClamp force_init/clamp_cruzr_zc, MetaCruzrMove delta_pose−0.5;0;0 y
bodyback_cruzr_zc. put_cruzr_low incluye apertura y retroceso−0.4;0;0.
No se ejecutaron. Ruta visible de visión y control de movimiento; no hay enlace
visible a checkpoint-40000. No basta para certificar todos los binarios internos.
YAML MetaClamp localizado: request.duration6,frequency500,box_size[.4,.3,.22],
trayectorias VISION/RELATIVE, control de fuerza bimanual; su opción
request.enable_self_collision_check aparece false. Estado del proveedor leído,
NO modificación ni autorización para desactivar nuestras comprobaciones.
Esta configuración usa otras poses e incluye chasis; no es equivalente al
acceso READY/ENTRY ni una prueba física del VLA instalado.

Evidencia privada, fuentes XML/YAML con hashes y respaldo documental:
../Humanoide-vla-evidence/20260914_READY410_HEAD_PREP/.
Cambio remoto sólo la postura de cabeza por la tarea citada. Sin archivos remotos
modificados. Reversión de documentos no revierte la postura; requiere otra orden
revisada. No se envió HOME ni se activó inferencia/control VLA.


## 2026-09-14 — VLA-01: force_ready.sh para revisión técnica

VERIFICADO LOCAL. Por petición del usuario se revisó scripts/force_home.sh y se
creó scripts/force_ready.sh. Wrapper de run_ready410_trial.py, exclusivo del
manifiesto access, una etapa1..5 hacia delante. Sin argumentos muestra ayuda;
con review/step usa --check local por defecto. --run y --preflight exigen la
habilitación y evidencia del ejecutor existente. No añade bypass ni credenciales,
no envía cruzr/ready original y no modifica force_home.sh. READY conserva−0,63rad.
Nueve comprobaciones CLI locales y bash -n pasan; shellcheck no está instalado.
No consultas remotas, movimientos, instalaciones o recargas en esta intervención.
Documento/receta: docs/vla/FORCE_READY_REVISION_TECNICA.md. La habilitación
física de brazos sigue pendiente; el nombre force no la concede.
Backup documental/evidencia: ../Humanoide-vla-evidence/20260914_FORCE_READY_REVIEW/.
Reversión selectiva: retirar los dos archivos nuevos y este registro; no afecta
estado remoto. No commit ni push. Fuentes y hashes conservados en esa evidencia.


## 2026-09-14 — VLA-01: revisión del bloqueo y corrección del monitor READY

VERIFICADO LOCAL/LECTURA. Autorización del dueño conservada. UBTECH respondió al
incidente completo indicando reinicio tras E-stop; no se usa ese comportamiento
como exigencia genérica de reparación previa. Se separa ensayo vacío supervisado
de validación general. Evidencia PICO→HOME del11-09 incorporada como observación
(2103 muestras, error máximo0,007568924rad), no como cota futura de READY.

Dos defectos concretos corregidos: el monitor exige progreso común de todos los
ejes dentro del segmento revisado, no sólo cajas articulares independientes;
las tolerancias de posición del contrato no pueden superar la banda geométrica
del informe (±1° en este caso), aunque sean menores que el techo genérico0,02.
31 tests pasan. Nuevas revisiones mantienen1018 pares certificados,54 avisos
internos retenidos y cero UNRESOLVED. 20 XML regenerados idénticos al receipt de
instalación: no hace falta reinstalar ni reiniciar por este cambio sóloPC.
No se envió movimiento ni se emitió habilitación ficticia.

Paquete vigente para revisión local:
../Humanoide-vla-evidence/20260914_READY_COMMISSIONING_REVIEW/package/access.json
El paquete anterior de READY410_EXECUTOR contiene hashes de fuentes anteriores;
no usarlo con el monitor modificado ni editar manualmente sus hashes.
Protocolo propuesto, evidencia y alcance pendientes en
[Revisión de habilitación](../vla/REVISION_HABILITACION_READY_20260914.md).
Fuentes cambiadas: runtime/entry410_single_stage_remote.py, entry410_stage_contract.py,
ready410_trial_contract.py y test_entry410_corridor.py, bajo scripts/vla/.
Backups before/, evidencia, fuentes y SHA256SUMS en el directorio citado.
Reversión selectiva de fuentes desde backup; no se recomienda volver al monitor
que admite combinaciones fuera del segmento. Estado físico sólo leído: cabeza
bajada alrededor−0,430665rad, resto próximo a HOME, inmóvil. No VLA físico ni
READY ejecutado. La parada y la ejecución efectiva nuevas no se declaran probadas.
