# Cambio entre abrazaderas y manos v4

**Entrada única:** `scripts/hands/cambiar_efector.sh`. Fecha: 15-10-2026.

Automatiza la configuración y recarga de Motion y Control Center para esta unidad
Cruzr S2 v0.2.0. Conserva las imágenes Docker, HOME, tareas, grabaciones y archivos
personalizados. El montaje físico del efector se realiza con el robot apagado,
según el procedimiento del proveedor; el script no sustituye esa operación.

## Comandos habituales

Desde la raíz del repositorio, en una terminal interactiva del PC:

```bash
# Consultar el cambio a manos v4 sin modificar el robot.
bash scripts/hands/cambiar_efector.sh --to v4 --check

# Aplicar, después de montar físicamente ambas manos v4 con alimentación apagada.
bash scripts/hands/cambiar_efector.sh --to v4 --apply
```

Para volver al perfil de abrazaderas, después de desmontar las manos con
alimentación apagada y montar las abrazaderas o dejar las muñecas vacías:

```bash
bash scripts/hands/cambiar_efector.sh --to clamp --check
bash scripts/hands/cambiar_efector.sh --to clamp --apply
```

Sin `--apply` ni `--verify`, se ejecuta únicamente la comprobación. `--check`
consulta configuración y contenedores; no certifica HOME ni el montaje físico.

## Secuencia del operador

1. Terminar las tareas y llevar el robot a HOME mediante un procedimiento ya
   validado. Apagar y cambiar físicamente los efectores según el SOP.
2. Encender el robot. Si el perfil anterior impide terminar el arranque, usar
   el caso de recuperación indicado más abajo; no repetir HOME para probar.
3. Ejecutar `--check`. Revisar que detecta los dos ordenadores y el destino deseado.
4. Ejecutar `--apply`. Confirmar hardware correcto, objeto retirado, recorrido
   despejado, cargador desconectado, otros mandos detenidos y persona junto al paro.
5. El script comprueba HOME medido y baterías. Cuando lo solicite, pulsar el paro
   principal y mantenerlo pulsado; el paro de servos debe estar liberado.
6. Esperar las fases automáticas. No cambiar modos, controles ni alimentación.
7. Cuando indique `WaitEStopRelease`, retirar soportes del recorrido solo si los
   brazos se sostienen estables. Liberar el principal con la zona libre y persona
   junto al paro. La secuencia nativa puede iniciar HOME, incluidos los dedos.
8. Esperar el resultado `PERFIL_Y_HOME_VERIFICADOS=clamp` o `=v4`.

La aplicación pide confirmaciones en esa misma terminal. No admite `--yes` ni
entrada no interactiva. No hace falta otro comando para cada fase ni un reinicio
físico si la recarga termina correctamente.

Si perfil, fuentes persistentes y estado ya coinciden, solo verifica el resultado:
no vuelve a parar ni recrear contenedores innecesariamente.

## Recuperación tras un arranque fallido

Si el efector ya se cambió con el robot apagado y el perfil anterior impide
publicar HOME, no se puede cumplir la comprobación normal de postura. Con los
brazos asegurados contra caída o golpe por personal capacitado, puede usarse:

```bash
# Ejemplo: manos retiradas y muñecas vacías; arranque aún configurado como SPS.
bash scripts/hands/cambiar_efector.sh --to clamp --apply --secured-recovery
```

Para manos ya instaladas, sustituir `clamp` por `v4`. Este modo exige confirmar
`BRAZOS ASEGURADOS`; mantiene las lecturas reales de paros, cargador, baterías,
configuración y verificaciones finales. No valida una recuperación desde contacto,
fallo de servo, articulación fuera de límites o soporte dentro del recorrido.
En esos casos se aplica la [guía de recuperación](CRUZR_S2_RECUPERACION_TRAS_CONTACTO_TELEOP.md).
No usarlo para continuar desde una postura arbitraria sin asegurar los brazos.

## Qué automatiza y qué conserva

- Descubre los contenedores por etiquetas de Compose; no depende de sus IDs anteriores.
- Coordina `HW_TYPE=cruzr_s2_v1` para abrazaderas y `cruzr_s2_v1_sps` para manos v4.
- Cambia solo el campo HW_TYPE compartido de Compose y DB global en Motion,
  y el selector exclusivo de CC en Compose/metafile Vision. El resto de servicios
  Vision y su HW_TYPE global se conservan.
- Guarda archivos anteriores, inventario de imágenes/montajes y cambios de las
  capas de escritura, incluidos binarios modificados y grabaciones `.motion`.
- Copia los respaldos al PC y verifica los hashes antes de parar servicios.
- Rechaza cambios de configuración o identidad de contenedor posteriores al inventario.
- Detiene CC y los nueve servicios Motion revisados; no arranca `debug` ni VLA.
- Recrea con `--no-build --pull never`; compara imágenes, ejecución, privilegios,
  montajes y entorno. Solo admite el cambio previsto de HW_TYPE.
- Restaura archivos y verifica hashes con los contenedores aún detenidos.
- Para v4 conserva o aplica la corrección ENI ya revisada de esta unidad, únicamente
  desde el original conocido. No modifica `dynamic_config.yaml` para forzar un perfil.
- Arranca Motion y CC, conserva el guard de arranque/voz y espera el paro.
- Tras liberación manual, verifica dos muestras frescas de HOME20D, reposo,
  actuadores sin fallos y controladores activos. Para v4 exige además estados
  avanzantes de siete articulaciones por mano.

No arranca teleoperación, no envía un HOME extra y no desplaza el chasis. La batería
mínima de esta herramienta es 20% en ambos packs. Rechaza hardware, ENI o guard
no revisados; una actualización del proveedor necesita revisión de compatibilidad.
No hay una duración fija: se ahorra investigación y trabajo manual, pero permanecen
las esperas reales de arranque, comprobación y HOME.

## Verificar después sin cambiar nada

```bash
bash scripts/hands/cambiar_efector.sh --to clamp --verify
# Con manos v4 y perfil SPS ya cargado:
bash scripts/hands/cambiar_efector.sh --to v4 --verify
```

`--verify` nunca corrige posturas ni perfiles. Puede esperar de forma acotada a
que termine el arranque. Si la postura permanece fuera de HOME o hay movimiento,
no declara éxito. HOME medido no autoriza por sí solo navegación ni transporte.

Después de un cambio exitoso, usar el lanzador correspondiente:
`probar_pico.sh` para abrazaderas y `probar_pico_v4.sh` para manos. Las condiciones
físicas y el preflight de teleoperación siguen siendo independientes.

## Si algo falla o se interrumpe

**16-10-2026 — corrección de restauración de montajes.** Una sesión v4 llegó a
recrear Motion y Vision, pero falló al copiar `.bash_history` sobre un bind mount
de CC (`device or resource busy`). Los dos historiales eran los únicos miembros
del respaldo de capa de CC. El backend ahora excluye destinos de montajes en
captura, restauración y verificación, también para respaldos antiguos. Conserva
los tar/manifest originales y registra exclusiones; no ejecuta `docker cp` si la
vista efectiva está vacía. Se comprueban hashes, miembros y metadatos del tar.
La comparación es de rutas POSIX; no certifica aliases arbitrarios mediante
cadenas de symlinks preexistentes.

Sólo para una sesión revisada que intentó recrear ambos hosts, sin haber intentado
arrancarlos, con todos los contenedores del destino ya recreados y detenidos:

```bash
bash scripts/hands/cambiar_efector.sh --to v4 --apply --secured-recovery \
  --resume-from /ruta/absoluta/a/EFFECTOR-FECHA-ID
```

La reanudación exige respaldos externos íntegros, marcadores de la sesión original,
fuentes exactamente iguales al plan e imágenes/entorno/montajes compatibles.
Verifica Motion existente sin reescribirlo, termina la restauración de Vision y
continúa el arranque bajo paro. No repite backup, instalación ni recreación.
Se conservan las confirmaciones físicas y la liberación manual del paro. Otros
puntos de interrupción necesitan revisión; no se borra el marcador para forzar
el comando. La evidencia nueva enlaza la carpeta original con `resume-plan.json`.

El script conserva evidencia y no reintenta fases de control, no revierte
controles automáticamente y no manda HOME. Mantener el estado físico seguro y
revisar `interrupted.json`, `phase-*.json`, `plan.json` y los recibos privados.
No liberar el paro para probar ni lanzar otra aplicación encima de una sesión
incompleta. Una marca de sesión activa bloquea otro `--apply`.

Las copias locales se guardan por defecto fuera de Git en:

```text
../Humanoide-vla-evidence/EFFECTOR-FECHA-ID/
```

Las copias de cada host y el marcador activo están en:

```text
/home/walker/.local/share/cruzr-effector-switch/FECHA-ID/
/home/walker/.local/share/cruzr-effector-switch/active.json
```

No compartir estos respaldos sin sanear: contienen configuración privada. No
extraerlos completos sobre el robot. Una reversión debe recuperar selectivamente
las fuentes y archivos anteriores, recrear las mismas imágenes bajo paro y
volver a verificar; requiere revisar hasta qué fase llegó la sesión.

Si un responsable ya ha recuperado el sistema y confirmado el destino, puede
cerrar la sesión interrumpida mediante verificación de HOME y archivos:

```bash
# Sustituir ID por el valor exacto de session en plan.json; mantener el destino correcto.
bash scripts/hands/cambiar_efector.sh --to clamp --verify --finish-session 20261015T120000Z-1234abcd
```

Este comando no instala, reinicia ni recupera posturas. Solo retira el marcador
si coincide la sesión/destino y pasan las verificaciones de los archivos y del
estado actual. Si falló antes de completar los respaldos, necesita revisión
manual; no se elimina el marcador para saltarse un error.

## Validación de esta entrega

Pruebas offline de ambos sentidos, formatos/aliases YAML, integridad del respaldo,
cambios inesperados, orden de fases e interrupción antes de START. `--check`
consultado en ambos destinos en esta unidad sin cambios remotos. El cambio físico
a **v4 con este script** se completó el 16-10, tras corregir el fallo descrito y
reanudar la misma sesión sin repetir recreación: WaitEStopRelease, liberación
manual confirmada, HOME20D medido/reposo/sin fallos, controlador de manos activo
y estados avanzantes de siete ejes por mano. Respaldos y archivos verificados,
sesión cerrada en ambos hosts. 42 pruebas offline pasan. No se ha ensayado aún
el sentido v4→clamp con el script bidireccional. La migración
manual previa a abrazaderas sí completó HOME, según el
[incidente de retirada de manos](../incidents/2026-10-15_ARRANQUE_SIN_MANOS.md).

Fuentes: [orquestador](../../scripts/hands/switch_effector.py),
[plan de configuración](../../scripts/hands/effector_profile_config.py),
[operaciones remotas](../../scripts/hands/effector_profile_remote.py).
