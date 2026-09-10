# HOME interno con apertura previa de hombros

## Estado del 10-09-2026

**Instalación verificada; ensayo físico pendiente.** El propietario confirma
brazos abajo, abrazaderas vacías y ausencia de contacto, y solicita sustituir
`cruzr/home` tras el incidente de cierre hacia el cuerpo. Principal pulsado,
servo liberado y cargador desconectado comprobados antes y después de escribir
y de reiniciar únicamente manipulación. No se enviaron movimientos, cambios
de modo, StartMotion ni liberación del paro.

Se reemplazó el XML que utiliza la tarea **`cruzr/home`**, conservando su nombre.
Esto incluye las llamadas internas de Control Center. No es sólo otro nombre
para la tarea PICO del script. El tiempo instalado es **20 s nominales**; la
candidata de **6 s permanece como borrador local no instalable con el gestor**.

| Etapa | Comportamiento | Tiempo instalado |
|---|---|---:|
| Abrir | Resta 0,4 rad (22,9°) al roll de cada hombro; conserva los otros ángulos actuales | 2,5 s |
| Bajar abiertos | Brazos a cero salvo hombros roll a −0,6 rad | 10 s |
| Recoger cuerpo | Cabeza, elevador y cintura a cero; brazos permanecen abiertos | 3,75 s |
| Cerrar abajo | Brazos ya bajados a cero | 3,75 s |

La primera etapa utiliza el puerto nativo `delta_joint_angles`, confirmado
en el registro de puertos y en el parser de la biblioteca MetaMove instalada.
No utiliza NaN, constantes PICO para los otros ejes ni nuevos publicadores.
Por ello, desde brazos abajo no los eleva primero a PICO. Desde las referencias
PICO nominales, el roll pasa de aproximadamente −0,199 a −0,599 rad.
La apertura conserva la asimetría inicial; eso **no** valida una recuperación
desde brazos asimétricos, tras contacto ni con una caja sujeta.

## Alcance y tiempos

Las cuatro referencias nominales revisadas son: PICO con cuerpo flexionado,
PICO con cuerpo a cero, brazos abajo con cuerpo a cero y brazos abajo con cuerpo
flexionado. No es una garantía para cualquier postura. El XML no incorpora
un clasificador de postura ni un detector de carga; el estado físico debe
comprobarse antes de activar una ruta que pueda llamar HOME.

Se conservan las primitivas y protecciones Motion. El barrido de envolventes
archivadas usó 501 muestras por etapa y referencia: mínimo muestreado fuera de
uniones locales de muñeca **69,7925 mm** y menor cota condicional entre muestras
**7,9290 mm**, suponiendo interpolación común monótona. Todos los pares locales
siguen registrados; sin nuevas exenciones de colisión. Esto no certifica
seguimiento, frenado, montaje real ni obstáculos externos.

La candidata de seis segundos reparte las etapas en 0,75 / 3 / 1,125 / 1,125 s.
Bajo la hipótesis quintic, los máximos analíticos son 1,0 rad/s y 4,106 rad/s²;
para veinte segundos, 0,3 rad/s y 0,370 rad/s². Son cálculos, no mediciones ni
límites certificados. La candidata de seis exige 3,33× velocidad y 11,11×
aceleración respecto a veinte. Que el HOME directo durase seis segundos no
valida los tiempos de este recorrido de cuatro etapas. Por el acercamiento
real al cuerpo observado, no se ha activado simultáneamente esa aceleración.

## Archivos y verificación

- Modelo: `scripts/teleoperation/cruzr_internal_home_open_path.py`.
- XML instalado: `scripts/teleoperation/tasks/cruzr_internal_home_open_v3_20s.xml`.
- Borrador: `scripts/teleoperation/tasks/cruzr_internal_home_open_v3_6s_DRAFT.xml`.
- Gestor: `scripts/teleoperation/cruzr_install_internal_home.py`.
- Auditoría sin robot: `scripts/teleoperation/audit_internal_home_open_path.py`.

Siete pruebas nuevas pasan: conservación de ángulos, reproducción de las
cuatro etapas desde cada referencia, ausencia de elevación PICO desde abajo,
rechazo de datos/XML incorrectos, preflight frente a cambios de seguridad/build,
instalación atómica y respaldo, rechazo de sobrescritura concurrente y rechazo
de instalar seis segundos. Las veinte pruebas del ejecutor PICO también pasan.
Compilación Python y `git diff --check` correctos. ShellCheck no disponible.

Ruta remota:
`/opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/cruzr/home.xml`.

| Archivo | SHA256 |
|---|---|
| HOME anterior | `50d819d6d6190280c6efee1dc275877362c3f7c807ec733fbc3c7ed217daed88` |
| HOME nuevo 20 s | `05174d2b4cf003b9b1c5274cd445b0d4faefe4276c5fbe8e59e68e6b64ee8cbe` |
| Biblioteca MetaMove requerida | `bfeab1c7a295b58cd96fddd20916fc3f7fe16bd8c8ad1e77720f48aad34ccc69` |

El gestor conserva tarea, task_list y bibliotecas. Rechaza hashes inesperados,
recomprueba el principal inmediatamente antes de escribir y usa reemplazo
atómico. Guarda el original y un manifiesto en el volumen persistente
`/etc/walker/trajectory-overlays/20260910T100528.529307Z_home_open_v3/`.

Recarga verificada: proceso de manipulación pasó de
`2026-09-10T09:43:22.269215253Z` a `2026-09-10T10:06:09.485280596Z`.
El XML conserva el hash nuevo después. Sigue esperando ListControllers bajo
E-stop; **no se afirma que haya ejecutado o comprobado en vivo el árbol**.
CC conserva ID `4a7eab87…b2522`, StartedAt `09:41:44.52140852Z`, RestartCount0.
No se reinició CC ni hw. La recarga no es una recuperación del arranque.

## Uso del gestor y reanudación

Comprobación local sin robot:

```bash
python3 scripts/teleoperation/cruzr_install_internal_home.py --check
```

Para comprobar en el robot, con principal pulsado y cargador desconectado:

```bash
python3 scripts/teleoperation/cruzr_install_internal_home.py --preflight
```

**La instalación y recarga ya se realizaron; no repetir para intentar arrancar.**
Para otra instalación, sólo con brazos abajo/vacíos, robot estable y principal
mantenido: `--install`, después `--reload`. Ninguno envía HOME ni autoriza
liberar el E-stop. No aplicar desde brazos elevados para forzar recuperación.

Punto pendiente: primera prueba física supervisada de veinte segundos y
verificación de HOME, antes de ensayar o activar seis segundos. El aviso de voz
de arranque sólo indica preparación técnica; no valida esta trayectoria.
La programación de arranque y el ensayo físico se revisan por separado.

El XML modificado reside en la capa escribible del contenedor y permanece tras
reinicio del mismo contenedor/robot; una recreación o actualización puede
restaurar el original. **Antes de usar HOME tras una actualización, ejecutar la
comprobación y revisar esta adaptación.** No se ha instalado un verificador
automático del hash en cada arranque.

Reversión: con robot detenido y E-stop mantenido, revisar el manifiesto y
restaurar selectivamente `home.before.xml` sólo si se quiere retirar esta
adaptación. Ese respaldo recupera el HOME directo que causó el acercamiento;
no hay rollback automático ante un fallo del movimiento ni debe usarse para
probar desde PICO. No restaura otros archivos ni revierte cambios ajenos.

## Compatibilidad del preflight canónico

**VERIFICADO 10-09-2026:** al instalar este overlay quedó sin actualizar el
contrato del comprobador local `scripts/cruzr_blue_workbin_cycle.sh`, que también
utiliza el ejecutor PICO a través del auditor E6.0G. Por eso rechazó precisamente
el SHA del HOME nuevo, incluso con servidor de acciones disponible.

Corregido en el PC: acepta el HOME original conocido o este XML exacto y, para
este último, exige también `libmeta_move.so` con el SHA de la tabla anterior.
Publica `INTERNAL_HOME_VARIANT=open-v3-20s` y su SHA; los hashes desconocidos
siguen rechazados. Reconocer la variante original conserva compatibilidad de
diagnóstico: no recomienda restaurarla ni valida su uso desde PICO.
E6.0G distingue errores de hash y conserva su detalle; un error del comprobador
ya no se presenta automáticamente como WaitStartMotion.

Seis pruebas en `scripts/test_workbin_home_contract.py`: ambas variantes,
HOME/biblioteca desconocidos o ausentes, los otros hashes obligatorios,
coherencia con el instalador/XML local y propagación del error del auditor.
Cinco pruebas previas de preflight pasan. Consulta real posterior con
`cruzr_pico_to_home_owner.sh --preflight`: perfil4× exacto, referencia PICO
body_zero inmóvil, `PICO_HOME_PREFLIGHT_OK` y `MOVEMENT_COMMANDS=0`.

No requiere reinstalar ni recargar el robot. Para recrear esta corrección tras
actualizar el PC, conservar ambos scripts y la prueba; para un firmware nuevo,
revisar de nuevo contratos y hashes, sin añadir automáticamente los nuevos.
Backup previo y log real en
`../Humanoide-vla-evidence/20260910T114627Z_HOME-PREFLIGHT-CONTRACT/`.
Reversión selectiva de estos dos scripts del PC devuelve el rechazo del overlay;
no revierte el HOME del robot. El ensayo físico sigue siendo independiente.

Evidencia local:

- `../Humanoide-vla-evidence/20260910T095255Z_HOME-ROUTE-REVIEW/`: contratos,
  binario leído, modelo, barrido y comparación temporal.
- `../Humanoide-vla-evidence/20260910T100548.301769Z_INTERNAL-HOME-CHANGE/`:
  instalación y comprobaciones antes/después.
- `../Humanoide-vla-evidence/20260910T100621.887349Z_INTERNAL-HOME-CHANGE/`:
  recarga y comprobaciones antes/después.
