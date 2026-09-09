# Transferencia de caja entre mesas sin AprilTags

**2026-09-09 — Reanudación y HOME cerrados (VERIFICADO):**
La ejecución `SRG3DFN4` terminó con código 0 en 443 s. Depósito Motion
SUCCEED, retirada odométrica 0,492029 m y HOME vendor
`43d16648-273d-4395-854b-d0f94e679652`, SUCCEED/status4. Medición final:
`MEASURED_HOME=1`, 20D máximo absoluto 0,002780 rad, brazos 0,000863 rad,
velocidad máxima 0. No se reiniciaron contenedores ni se alteraron límites.
Punto de reanudación: robot en HOME detrás de mesa 2; caja liberada por la
acción de depósito. Confirmación visual final del operador no recogida aún.
Evidencia persistida en
`../Humanoide-vla-evidence/20260909T112523Z_USLAM-AUX-RESUME/completed-transfer/`.
Las entradas «en curso» de abajo describen fases anteriores ya terminadas.


**2026-09-09 — Depósito reanudado con éxito (VERIFICADO Motion y mapa):**
`--resume-held-approach --yes --fast` avanzó 0,474785 m y luego 0,503024 m,
recalculando tras una llegada intermedia con error 0,029 m. Pose final fresca
−0,323384265933/1,06489210132/1,66272749992: error de posición 0,0043 m y
orientación −1,10° respecto al depósito enseñado. No se ampliaron tolerancias.
`cruzr/blue_workbin_auto_deposit`, goal
`165d4649-88a7-4ab1-b47d-9b61e2c36dbd`, SUCCEED/status4; registro posterior
`deposited_open_near_table`, sin eventos inseguros y articulaciones quietas.
Log `/tmp/cruzr-table-transfer.SRG3DFN4` y copia en evidencia
`20260909T112523Z_USLAM-AUX-RESUME`. Recuperación de HOME aún en curso.
Pendiente una repetición completa desde mesa 1 para verificar físicamente el
tratamiento del resultado auxiliar de navegación; esta reanudación no navegó.


**2026-09-09 — Reanudación medida dentro de la aproximación (VERIFICADO offline; ejecución en curso):**
Los 5,1 cm eran error de localización respecto a la **premesa virtual**, situada
1,0 m antes de la pose de depósito enseñada; no distancia caja–mesa. El intento
`gl8OhUFM` bloqueó antes de avanzar al superar 5 cm. Una corrección local
0,049032 m adelante/−0,047125 m lateral se interrumpió por objetivo fuera del
arco frontal (−75,2°); hubo avance parcial, no se repitió. Nueva pose fresca
−0,241386/0,120383/1,657037: unos 5,3 cm dentro del tramo, 1,9 cm lateral.
Cambio LOCAL: `--resume-held-approach` sólo sin tags calcula el resto desde
pose fresca, dentro del corredor y orientación enseñados, y rechaza una
proyección recta fuera del margen. Cada tramo recalcula la distancia desde la
llegada medida; también el flujo normal deja de acumular distancias nominales.
Se conservan tolerancias de mapa, agarre, paros, LiDAR y límites de primitivas.
97 pruebas workbin pasan (incluyen corredor, distancias, ausencia de repetición
de agarre/retirada y bloqueo antes de movimiento). No se cambia perfil ni XML.
Rollback: con robot detenido, retirar el modo nuevo y revisar sólo las funciones
modificadas, preservando cambios anteriores. Nunca repetir una distancia fija
desde un tramo parcialmente recorrido. Copia del código probado en evidencia/changed.
Ejecución `--resume-held-approach --yes --fast`, log
`/tmp/cruzr_remaining_resume_run.log`; resultado físico pendiente.


**2026-09-09 — Corrección del aviso VSLAM auxiliar y reanudación desde premesa (en curso):**
nuevo intento `/tmp/cruzr-table-transfer.yk6hsjdq`, 328 s, se detuvo por el
rechazo explícito de VSLAM_MAP_DIR_ERROR pese a llegada real a premesa.
Planificador: FINISH, goal interno5e585d95-e06f-44ed-9904-8e80aa273c86;
pose objetivo -0,216672/0,070232/1,681930, lectura fresca posterior
-0,261118/0,049621/1,685730, error<0,05 m. Agarre vigente0,566 m,
Fy28,7 N/Fz-10,1 N, 20D inmóviles y writer de RobotCommand0.
Cambio LOCAL map_route: caso excepcional sólo para navigate-map-pose en uslam,
respuesta status4 + dmsg navigation_start SUCCEEDED + desc exactamente
VSLAM_MAP_DIR_ERROR. Esa combinación exige todavía tres lecturas frescas
estables y llegada dentro de las tolerancias configuradas; si no, bloquea.
Fuera de ese caso conserva rechazo estricto (fusion/auto, otros errores,
lectura fallida, desviación, aborto). El aviso se informa; no se finge resuelto
el guardado visual ni se cambia el árbol vendor. LiDAR y controles intactos.
94 tests workbin/sintaxis/diff correctos. Usuario autorizó corregir y continuar
con la misma disposición; se inició --resume-held --yes --fast, sin repetir
agarre, retirada inicial ni navegación a premesa. Resultado físico pendiente.
Evidencia: `../Humanoide-vla-evidence/20260909T112523Z_USLAM-AUX-RESUME/`.

**09-09-2026: referencia enseñada y reanudación aproximación→depósito→HOME verificadas en esta unidad; repetición del ciclo completo con el tratamiento VSLAM auxiliar pendiente.**

## Incidente de primera prueba, 09-09-2026

**VERIFICADO:** llegó a premesa con la caja, pero se interrumpió antes del avance
final y depósito. La lectura ROS 2 por defecto devolvía una pose retenida de más
de cuatro horas antes. También se había guardado esa pose como referencia de
depósito; esa referencia no representa una enseñanza válida.

El lector corregido usa suscripción VOLATILE y dos muestras con sellos
crecientes, edad máxima 3 s respecto al reloj del robot, marco map y geometría
válida. Se ha probado en vivo sin movimiento. Los perfiles anteriores carecen
de `capture_method=volatile-stamped-v2` y ahora se rechazan; **volver a enseñar
desde la posición física de depósito, no añadir esa marca a mano**.

También se rechaza `VSLAM_MAP_DIR_ERROR` aunque la envoltura de la acción diga
SUCCEEDED/status=4. En este intento fue un fallo de guardado visual auxiliar
después del FINISH del planificador, no la causa de no alcanzar la premesa.
Su resolución sigue pendiente. El robot no ha completado todavía el ciclo.

No repetir `--run` con la caja ya sujeta ni usar `--resume-held` con la referencia
antigua. Primero resolver la situación de carga presencialmente y registrar
la referencia correcta. Evidencia: `../../../Humanoide-vla-evidence/20260909T104241Z_NO-TAG-NAV-FAILURE/`.
Cambios locales en map_route, lector y validación del perfil; sin cambios remotos.
Para rollback hay copias de los scripts anteriores en la evidencia, pero esa
versión conserva el defecto y no debe usarse para mover ni enseñar.

El ejecutor es [cruzr_blue_workbin_table_transfer_no_tag.sh](../../scripts/cruzr_blue_workbin_table_transfer_no_tag.sh).
Utiliza el mismo orquestador y las mismas primitivas de agarre, navegación,
depósito por contacto y HOME. La recogida conserva el detector de la caja azul.
Para mesa 2 utiliza una pose de base enseñada en el mapa y una aproximación
odométrica. No necesita el script, servicio, tópico ni visibilidad de AprilTags.

## Qué se guarda

Un perfil local `config/cruzr_mesa2_drop.json`, generado por el script:

- **Pose de depósito**: posición de la **base del robot**, no de la mesa ni del
  centro de la caja. X/Y en metros del mapa; orientación yaw en radianes.
- **Distancia de aproximación**: separación elegida entre premesa y depósito,
  de 0,10 a 1,20 m. La premesa se calcula detrás del robot según su orientación.
  No se copia el antiguo punto MESA2_PRE ni su desplazamiento de 1,08 m.
- **Tolerancias de llegada**: inicialmente 0,05 m y 0,05 rad (aproximadamente
  2,9°). Sirven para aceptar/rechazar la pose, no para corregirla. Su margen debe
  caber físicamente en la mesa teniendo en cuenta la distancia desde la base
  hasta la caja: un error angular también desplaza sus esquinas.
- Nombre y tipo de mapa, huella de `umap.json`/`user/task.json`, fecha de captura
  y método de adquisición fresca `capture_method=volatile-stamped-v2`.

La huella detecta cambios de esos archivos; no detecta una mesa movida ni prueba
la exactitud del SLAM. Tras modificar mapa, ubicación/altura de mesas, montaje,
caja o postura de transporte, volver a enseñar y comprobar la referencia.

[Ejemplo de formato](../../config/examples/cruzr_mesa2_drop.example.json): está
intencionadamente incompleto, con `null` donde faltan datos reales. No sirve
para ejecutar y no hay coordenadas físicas inventadas.

## 1. Enseñar mesa 2 cuando el robot esté conectado

1. Preparar y localizar el mapa. Detener el modo de grabación y terminar de
   guardar los puntos antes de enseñar. Esta variante no carga ni relocaliza
   mapas durante una transferencia.
2. Con el procedimiento de control presencial habitual, situar la base en la
   posición y orientación desde las que se depositaría la caja en mesa 2.
   La caja debe quedar completamente sobre la superficie de apoyo al descender,
   con holgura; deben corresponder el montaje y postura del agarre workbin.
   **Guardar una pose cualquiera, por ejemplo HOME junto a la mesa, no demuestra
   que desde ella la caja vaya a quedar apoyada.** No es necesario abrir para
   guardar la referencia.
3. Detener el mando/PICO y cualquier otro controlador. Mantener el robot estable
   y la zona despejada. El registro comprueba actuadores y tres poses estables;
   no mueve ni coloca automáticamente el robot en la posición deseada.
4. Elegir una premesa despejada detrás de esa pose, alineada con ella, y comprobar
   todo el trayecto recto. La distancia del ejemplo siguiente es **ilustrativa**;
   usar la que corresponda al espacio real:

   ```bash
   export CRUZR_MAP_NAME=MESAS2
   export CRUZR_MAP_TYPE=uslam
   ./scripts/cruzr_blue_workbin_table_transfer_no_tag.sh \
     --teach-mesa2 --approach-distance 1.0
   ```

   El comando registra X/Y/yaw actuales y calcula una premesa 1 m detrás.
   **No ejecuta ese metro de movimiento.** No mide obstáculos ni valida el apoyo.
   Si la pose fluctúa más de 10 mm o 0,02 rad entre muestras, no guarda el perfil.

Por defecto el archivo se crea sólo si no existe. Para sustituirlo expresamente,
con el robot en la nueva pose de depósito y detenido:

```bash
./scripts/cruzr_blue_workbin_table_transfer_no_tag.sh \
  --teach-mesa2 --approach-distance 1.0 --overwrite-mesa2
```

**09-09-2026 — VERIFICADO offline:** `--overwrite-mesa2` conserva el archivo
anterior si la captura falla. Tras validar la nueva captura, crea una copia
exacta `.bak.*` junto al perfil (ruta `MESA2_PROFILE_BACKUP`) y sustituye el JSON
de forma atómica. No mueve el robot. Sólo se admite con `--teach-mesa2` y rechaza
enlaces simbólicos. Para rollback, con el flujo detenido, restaurar esa copia
en la ruta original; usarla sólo si corresponde a la disposición física vigente.
La enseñanza real de la nueva referencia sigue pendiente.

Para registrar una disposición distinta,
utilizar otro nombre, sin sobrescribir la anterior:

```bash
export CRUZR_MESA2_PROFILE="$PWD/config/mesa2_nueva.json"
./scripts/cruzr_blue_workbin_table_transfer_no_tag.sh \
  --teach-mesa2 --approach-distance 1.0
```

Conservar ese `CRUZR_MESA2_PROFILE` para check, ejecución y reanudación, o pasar
`--mesa2-profile ARCHIVO` en cada comando. Cada ejecución copia y valida el perfil
una vez; editarlo mientras se ejecuta no cambia sus objetivos.

## 2. Primera prueba por etapas

Con el robot preparado frente a la caja en mesa 1, caja vacía, mesas fijas,
recorrido libre, cargador/Ethernet desconectados, otros mandos detenidos y una
persona junto al paro:

```bash
./scripts/cruzr_blue_workbin_table_transfer_no_tag.sh --check
./scripts/cruzr_blue_workbin_table_transfer_no_tag.sh --stage-held --fast
```

`--check` sólo comprueba. `--stage-held` recoge, retrocede 0,50 m de mesa 1,
navega a la premesa enseñada y termina con la caja sujeta. Comprueba la pose de
llegada y el agarre; no se acerca a depositar ni ejecuta HOME.

Después de comprobar caja estable y el recorrido/apoyo libre en mesa 2:

```bash
./scripts/cruzr_blue_workbin_table_transfer_no_tag.sh --resume-held --fast
```

Antes de avanzar exige estar en la premesa. Divide la aproximación en tramos
iguales de hasta 0,60 m, usando la primitiva existente (por ejemplo 1,0 m =
0,50 + 0,50 m). Comprueba la pose de mapa después de cada tramo, incluida la
posición final. Sólo después ordena depósito por contacto y recuperación HOME.
La vuelta a HOME incluye su propio retroceso de 0,50 m.

Las confirmaciones interactivas piden escribir **`TRANSFERIR SIN TAGS`**. `--yes`
sólo omite esa pregunta en un flujo exterior con condiciones ya confirmadas.

## 3. Ciclo completo y reanudaciones

Tras validar la disposición por etapas:

```bash
./scripts/cruzr_blue_workbin_table_transfer_no_tag.sh --run --fast
```

| Modo | Estado inicial requerido |
| --- | --- |
| Sin argumentos / `--check` | Diagnóstico; no mueve. |
| `--run` / `--stage-held` | Caja sobre mesa 1, todavía sin agarrar. |
| `--resume-held-from-mesa1` | Agarre completado en mesa 1; aún no ha retrocedido. |
| `--resume-held-navigation` | Caja sujeta y retirada de mesa 1 ya completada; no repite retirada. |
| `--resume-held` | Caja sujeta, robot en la premesa enseñada. |

El equivalente sin wrapper es:

```bash
./scripts/cruzr_blue_workbin_table_transfer.sh --without-apriltag --run --fast
```

`--fluid` se mantiene reservado a la variante AprilTag. La variante sin tags
usa `--fast` y conserva preflight fresco, límites y resultados de las acciones.
No aumenta velocidades ni tolerancias para conseguir llegar al depósito.

## Si se interrumpe

- **Mapa/huella/tipo incorrecto:** preparar el mapa o enseñar la nueva disposición.
  No cambiar sólo la huella del JSON para forzar la aceptación.
- **Premesa bloqueada por navegación:** se detiene; no cambia de destino, no
  desactiva LiDAR y no añade otro retroceso. Revisar la elección de premesa.
- **Pose fuera de tolerancia antes o después de avanzar:** conserva la caja y
  no deposita. No hay corrección automática. Revisar la posición real.
- **Aproximación interrumpida:** puede haber recorrido parte de la distancia.
  `--resume-held` comprueba la premesa y no sirve para repetir ciegamente el tramo.
- **Depósito o HOME interrumpido:** apoyo/liberación o retroceso pueden haber
  empezado. Consultar estado y registros antes de elegir recuperación.

Durante navegación con carga se mantiene el perfil temporal LiDAR autorizado;
se restaura percepción original antes de aproximar y también ante fallo.
`TRANSFER_LOG_DIR` contiene perfil utilizado y logs de las etapas
`MAP_STAGING_CHECK`, `MAP_APPROACH_*` y `MAP_APPROACH_CHECK_*`.

## Alcance de la comprobación

Este método presupone mesas inmóviles, suelo plano, localización válida y una
postura de agarre repetible. El depósito por contacto no comprueba por sí solo
que toda la base de la caja esté sobre la mesa. Registrar una pose y superar
los checks de software tampoco lo demuestran: sigue siendo necesaria la
comprobación presencial de la disposición y sus márgenes.

No se ha ejecutado esta variante en la unidad física. Su tiempo total y el
ahorro frente a AprilTags se medirán con `TIMING_TOTAL` después de validarla.
