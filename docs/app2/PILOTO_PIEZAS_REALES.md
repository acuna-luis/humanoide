# app2 — primer lote real de piezas

**ID:** APP2-REAL-PIECES-PILOT-20261019.\
**Fecha/zona:** 19-10-2026, Europe/Madrid.\
**Estado:** importación real **VERIFICADA**; anotaciones y revisión humana
**PENDIENTES**. Cabeza bajada con autorización y nuevas capturas verificadas.
No hay entrenamiento de piezas reales ni conexión del detector a controles físicos.

El siguiente paso es dibujar los contornos de las piezas en CVAT. La tarea ya
está preparada: [abrir trabajo actual 5](http://localhost:18080/tasks/5/jobs/5).
Contiene las capturas nuevas tras bajar la cabeza. El [trabajo inicial 4](http://localhost:18080/tasks/4/jobs/4)
se conserva intacto; si ya se empezó a anotar allí, guardar y conservar ese trabajo.
El enlace funciona desde el PC que tenga abierto el túnel descrito debajo.

## 1. Qué se ha preparado

**Actualización tras el encuadre (11:54:23 UTC / 13:54:23 Europe/Madrid):**
tarea **5**, `REAL app2 pieces head 20261019 115423 v002 - REVIEW REQUIRED`,
job **5**. Frame 0: `head_raw.png`, 1920×1536; frame 1: `head_rgb.png`, 960×576.
Dos PNG nuevos, 5.836.158 bytes, dimensiones y hashes contrastados; cero
anotaciones al importar. Se ha revisado visualmente que la bandeja queda entera.
El material continúa sin identificar y las máscaras necesitan revisión humana.
Por prudencia se mantiene el grupo `robot_scene_20261019_084059` del lote previo:
estas vistas relacionadas no representan nuevas escenas independientes para splits.

El primer lote se conserva con los siguientes datos históricos:

| Elemento | Resultado observado al importar |
|---|---|
| CVAT | 2.79.0; proyecto existente 1, `app2-itr-v0`, propietario/esquema comprobados |
| Tarea | 4, `REAL app2 pieces seed 20261019 v001 - REVIEW REQUIRED` |
| Trabajo de anotación | Job 4; estado inicial `new` |
| Frame 0 | `piezas_cabeza_raw.png`, 1920×1536 |
| Frame 1 | `piezas_cabeza_rectificada.png`, 960×576 |
| Anotaciones iniciales | 0; no se han dibujado contornos automáticos |
| Procedencia | Dos PNG originales conservados de las cámaras del robot; 5.784.197 bytes en total |
| Escenas físicas | **Una**: ambas vistas comparten `robot_scene_20261019_084059` |
| Identidad | `itr_candidate`, provisional; `material_id=null` |
| Particiones | Sin asignar; no hay `train`/`valid`/`test` independientes |

Los hashes y dimensiones de ambos originales coinciden con el
[manifiesto de fotografías](manifest_fotos.json). CVAT confirmó nombres,
dimensiones, dos frames y ausencia de anotaciones. Esto comprueba la importación,
no la identidad del material ni la calidad de unas máscaras que aún no existen.
El ID vendrá en la caja; su contenido y la relación con las piezas siguen pendientes.

La vista rectificada es más cómoda para empezar. La imagen raw conserva más
detalle y sirve para revisar los extremos. Sus proyecciones son distintas:
**no copiar polígonos ni coordenadas de una vista a la otra**. Si se anotan ambas,
dibujar y revisar cada contorno sobre su propia imagen.

## 2. Abrir CVAT desde el PC

En el PC utilizado durante esta intervención ya se abrió un túnel local en
`127.0.0.1:18080`. Primero probar el enlace al trabajo. Si funciona, conservar
ese túnel y no iniciar otro en el mismo puerto.

Desde otro PC, o si el túnel ya terminó, abrir una terminal y ejecutar:

```bash
ssh -p 2649 -N -o ExitOnForwardFailure=yes \
  -L 127.0.0.1:18080:127.0.0.1:18080 luisacuna@192.168.1.43
```

Mantenerla abierta y entrar en **http://localhost:18080**, usuario `app2_admin`.
Las credenciales se consultan en privado según [RETOMAR_APP2.md](RETOMAR_APP2.md#3-retomar-hoy-con-el-servidor-existente).
No publicar la contraseña en el chat, capturas o repositorio. Este túnel permite
acceder al editor del servidor; no inicia teleoperación ni entrenamiento.

Si el puerto está ocupado, identificar primero el proceso del PC:

```bash
ss -ltnp 'sport = :18080'
```

El túnel de **esta intervención y este PC** usa el socket de control privado
`../Humanoide-vla-evidence/app2/cvat-pilot.sock`, relativo a la raíz del repositorio.
Para cerrar exclusivamente ese túnel, desde la raíz del repositorio del PC:

```bash
ssh -p 2649 -S ../Humanoide-vla-evidence/app2/cvat-pilot.sock \
  -O exit luisacuna@192.168.1.43
```

Cerrar el túnel no apaga CVAT ni borra trabajo. Ese socket es estado local
transitorio: no asumir que existe en otro PC o después de reiniciar. El túnel
en primer plano del ejemplo se cierra con Ctrl+C en su propia terminal.

## 3. Etiquetar la primera imagen, paso a paso

1. Abrir [el trabajo 5](http://localhost:18080/tasks/5/jobs/5). Comprobar el
   nombre de la tarea y las dos imágenes, para trabajar en el lote real.
2. Ir al **frame 1**, `head_rgb.png`. El frame 0 es la vista raw;
   los números de frame empiezan en cero.
3. Acercar la bandeja con el zoom del editor. Elegir la herramienta **Polygon**
   y la etiqueta **`itr_candidate`**.
4. Empezar por una pieza cuyo borde se distinga bien. Dibujar un contorno
   ajustado alrededor de **una pieza**, incluyendo su barra y sus extremos
   visibles. Cerrar el polígono antes de empezar la pieza siguiente.
5. Seguir sólo los píxeles visibles de esa pieza. Excluir el cartón, separadores,
   huecos y piezas vecinas. No completar por intuición una parte tapada ni unir
   dos piezas por estar en contacto. Si no se distingue a qué pieza pertenece
   un fragmento, dejar esa decisión pendiente para revisión.
6. En sus atributos, conservar **`identity_status=provisional`**. Usar
   **`visibility=visible`** cuando la pieza esté completamente visible y
   **`visibility=partial`** si está recortada u ocluida. Si no puede determinarse,
   usar `indeterminate` y revisar el caso; no marcar `confirmed` sin evidencia
   de referencia documentada.
7. Repetir para las demás piezas distinguibles. Guardar con **Save** y esperar
   la confirmación del editor. Reabrir el trabajo y comprobar que los contornos
   permanecen guardados y sobre la imagen correcta.
8. Revisar la imagen raw del frame 0 para resolver detalles. Si se decide
   anotarla, dibujar sus polígonos desde esa propia vista. Guardar y revisar
   también ese frame.

**Primera revisión parcial — 19-10-2026:** tras indicar el operador que guardó
la primera pieza, la consulta de tarea5/job5 confirma un polígono manual ID10,
frame1, etiqueta `itr_candidate`, 26 vértices dentro de la imagen. La revisión
visual del gráfico comparativo muestra que sigue la pieza aislada derecha e
incluye barra y extremo metálico, sin invadir claramente otra pieza o el cartón.
No se exige rehacer esta primera pasada. `identity_status=provisional` está
conservado; `visibility=indeterminate` sigue sin clasificar. Se recomienda al
operador **`partial`**, porque el extremo inferior queda parcialmente oculto por
el borde delantero de cartón. Después, continuar las demás piezas del frame1 y
guardar. Esta consulta no cambia atributos ni máscaras y no acepta el conjunto
completo. Snapshot y gráfico diagnóstico privado en
`../Humanoide-vla-evidence/20261019T122333Z_APP2_FIRST_CONTOUR_REVIEW/`;
original PNG intacto, sin entrenamiento ni conexión al robot.

La anotación necesita una revisión humana antes de declararse aceptada. No
marcar el lote completo como revisado únicamente por haber pulsado Save. Dejar
registro del revisor, fecha, frames revisados, dudas y cambios de criterio.
Si quedan piezas objetivo visibles sin anotar, esa imagen no debe pasar a
entrenamiento: podrían convertirse en ejemplos incorrectos de fondo.

Un polígono describe la silueta visible. No demuestra referencia industrial,
pose 3D, profundidad, orientación de agarre o fuerza necesaria. Las indicaciones
anteriores preparan un detector de candidatos; distinguir referencias similares
requiere ejemplos y ground truth adicionales.

## 4. Ubicaciones y evidencia para retomar

| Equipo / recurso | Ubicación |
|---|---|
| PC: lote actual de capturas nuevas | `../Humanoide-vla-evidence/app2/datasets/pieces_head_20261019T115423Z_v002/` |
| PC: originales nuevos y metadatos | `../Humanoide-vla-evidence/app2/reference/head_pieces_20261019T115423Z/` |
| Servidor: lote y recibos actuales | `~/app2/receipts/real-pieces-head-20261019T115423Z-v002/` (`input`, `check`, `import`) |
| PC: lote privado original | `../Humanoide-vla-evidence/app2/datasets/pieces_seed_20261019_v001/` |
| PC: manifiesto del lote | `manifest.json` dentro de esa carpeta; imágenes y `SHA256SUMS` junto a él |
| Servidor: copias de entrada | `~/app2/receipts/real-pieces-seed-20261019-v001/input/` |
| Servidor: recibo de check local | `~/app2/receipts/real-pieces-seed-20261019-v001/check/real-images-import-result.json` |
| Servidor: recibo de importación | `~/app2/receipts/real-pieces-seed-20261019-v001/import/real-images-import-result.json` |
| Servidor: helper operativo | `~/app2/workflow/import_real_images.py` |
| Código versionable | [`scripts/app2/workflow/import_real_images.py`](../../scripts/app2/workflow/import_real_images.py) |
| PC: evidencia de intervención | `../Humanoide-vla-evidence/20261019T114329Z_APP2_REAL_PIECES_PILOT/` |

El helper se ejecuta con Python del **host del servidor**, usando biblioteca
estándar y los helpers CVAT existentes. No se reconstruyó la imagen del
entrenador para importar estas fotografías. Las imágenes se enviaron sólo al
CVAT local autorizado, sin servicios de nube. No se alteraron etiquetas o
anotaciones de otras tareas. Las imágenes y evidencias privadas siguen fuera de Git.

El recibo `success=true` indica importación correcta con revisión **PENDING**.
El dato `annotations=0` corresponde al instante inicial; cambiará cuando el
operador guarde trabajo. Para retomar la anotación se abre la tarea existente (actual 5; inicial 4 conservada),
sin repetir el importador ni crear una copia de la tarea.

## 5. Validar o importar otro lote de forma controlada

Esta sección es una receta para un **lote nuevo**, no un paso para continuar el
trabajo 5 ni el trabajo 4 conservado. Primero preparar su manifiesto privado con originales y hashes según
[datos y entrenamiento](DATOS_Y_ENTRENAMIENTO.md). Debe declarar
`schema_version: 1`, `synthetic: false`, `material_id: null`, nombre de tarea
único, `session_group` y una lista de imágenes con `file_name`, `local_path`,
`sha256`, `width`, `height` y `source_kind`. `split` puede omitirse o ser `null`.
Las rutas relativas de imágenes se interpretan respecto al manifiesto.

Conectar al servidor y ejecutar allí, sustituyendo las rutas por las del lote
nuevo y dos directorios de recibos todavía inexistentes:

```bash
ssh -p 2649 luisacuna@192.168.1.43
```

```bash
APP2_BATCH_MANIFEST="$HOME/app2/receipts/REEMPLAZAR_LOTE/input/manifest.json"
APP2_BATCH_CHECK="$HOME/app2/receipts/REEMPLAZAR_LOTE/check"
APP2_BATCH_IMPORT="$HOME/app2/receipts/REEMPLAZAR_LOTE/import"

PYTHONPATH="$HOME/app2/setup/cvat:$HOME/app2/workflow" \
  python3 "$HOME/app2/workflow/import_real_images.py" \
  --manifest "$APP2_BATCH_MANIFEST" --output-dir "$APP2_BATCH_CHECK" --check
```

El check no llama a la API. Exige hashes y dimensiones PNG coincidentes,
archivos regulares sin symlinks, nombres seguros, imágenes diferentes, máximo
16 MiB por imagen y 64 MiB en total. No decodifica ni evalúa visualmente la imagen:
esa revisión corresponde al operador. No asigna splits ni confirma materiales.

Revisar el recibo antes de ejecutar la importación explícita:

```bash
PYTHONPATH="$HOME/app2/setup/cvat:$HOME/app2/workflow" \
  python3 "$HOME/app2/workflow/import_real_images.py" \
  --manifest "$APP2_BATCH_MANIFEST" --output-dir "$APP2_BATCH_IMPORT" --import
```

`--import` usa las credenciales privadas existentes, exige CVAT 2.79.0 y el
proyecto `app2-itr-v0` con propietario/esquema esperados. Crea únicamente una
tarea nueva sin anotaciones; no crea proyectos ni cambia el catálogo. Rechaza
una tarea del mismo nombre en ese proyecto, para preservar las anotaciones ya
realizadas. No sobrescribe recibos existentes. Si falla después de crear la
tarea, conserva su ID y la tarea para diagnóstico: no elimina ni reintenta a
ciegas. No modificar permisos o usar otra cuenta para evitar un rechazo de propietario.

## 6. Cuándo ampliar y cuándo entrenar

Este lote sirve para acordar contornos y practicar el flujo con fotografías
reales. **Dos vistas de una escena no forman un dataset de entrenamiento y
validación independiente**. No repartir sus vistas, recortes o variantes entre
splits ni presentar métricas de generalización a partir de ellas.

El siguiente lote debe incorporar escenas realmente diferentes: piezas
aisladas, bandeja con distintas cantidades y posiciones, huecos, oclusiones,
cambios de luz, vacíos y piezas parecidas. Registrar cada sesión/grupo y reservar
sesiones completas para validar y probar. Las 30–50 escenas del
[plan](PLAN_Y_PREGUNTAS.md#4-lista-principal-de-trabajo) son un presupuesto inicial,
no una garantía de precisión. La referencia de cada confundible debe confirmarse
antes de evaluar identificación por material.

Tras revisión y suficientes grupos independientes: exportar COCO con imágenes,
conservar el ZIP original, preparar el manifiesto de splits y usar el conversor
documentado en [DATOS_Y_ENTRENAMIENTO.md](DATOS_Y_ENTRENAMIENTO.md). El piloto
actual permanece en anotación; no se ha iniciado entrenamiento GPU con estas piezas.

## 7. Encuadre físico: comprobaciones separadas

Se ha solicitado un encuadre nuevo bajando la cabeza. La primera comprobación
`--check-head` detectó un goal activo
`3f72daca-71d0-4706-a66f-fb251af1eec0`; no envió movimiento. Después de que el
operador comunicara el cierre de la teleoperación, otra comprobación ya no
mostró ese bloqueo, pero informó **`CHARGER_CONNECTED=1`**. No se puenteó ese
resultado. Después, el operador confirmó que había desconectado físicamente el
cargador; el check nuevo y el preflight de ejecución confirmaron `CHARGER=disconnected`,
paros 0/0, actuadores habilitados y velocidad medida cero. Baterías antes del
movimiento: 94,6 % / 95,0 %. Se conservan los logs de los bloqueos previos.

Con condiciones físicas actuales confirmadas (manos v4 vacías, ruedas bloqueadas,
robot estable, recorrido libre, mandos detenidos y persona junto al paro), se ejecutó
una sola vez la receta existente, sin instalar ni modificar tareas:

```bash
./scripts/cruzr_blue_workbin_cycle.sh --check-head
./scripts/cruzr_blue_workbin_cycle.sh --prepare-vision --yes
```

La segunda orden es **movimiento físico**; aquí `--yes` utiliza la confirmación
recibida del operador, sin omitir el preflight. Objetivo nativo yaw 0 / pitch −0,43 rad,
2 s. Goal `b34d2b9e-7a03-435d-9118-93ed2f0c3546`: `SUCCEED`, estado de acción 4,
resultado 1101001. Sólo se envió la tarea de cabeza. El postflight volvió a dar
`HEAD_CHECK_OK`, velocidad corporal máxima 0 y delta máximo de consigna 0,003230 rad.
No se midió aquí una comparación de postura de cada brazo antes/después.
No se enviaron HOME, cambios de modo ni órdenes al chasis o desde el detector.

Se capturaron por suscripción las cuatro vistas RGB actuales y se guardaron
originales PNG, metadatos, fuentes y hashes en
`../Humanoide-vla-evidence/app2/reference/head_pieces_20261019T115423Z/`.
Se comprobaron visualmente las dos vistas de cabeza: bandeja completa y piezas
visibles. Sólo esas dos se importaron como tarea 5; cintura/chasis quedan como
referencia de encuadre. [Índice de imágenes y hashes](FOTOS_Y_FUENTES.md#4-capturas-posteriores-al-encuadre-de-cabeza).
Logs: `head-lower.log`, `head-postflight.log`, `fresh-capture-summary.json`
y `fresh-import-result.json` en la evidencia de esta intervención. La consulta
multicanal no decodifica yuv422; la vista raw se capturó después con el lector UYVY
específico conservado. Un intento inicial de SSH rechazó el helper askpass sin
permiso de ejecución: se reutilizó la entrada askpass del script existente, sin
cambiar permisos ni contraseñas.

La cabeza se deja en la postura de observación. No se vuelve automáticamente
a HOME ni se programa otro movimiento. Para deshacer el encuadre se necesita
una nueva acción autorizada con condiciones físicas actuales; no restaurar una
postura supuesta desde una foto.

Son observaciones fechadas, no el estado físico garantizado para una sesión
posterior. Antes de otra acción física deben volver a comprobarse las condiciones
actuales y aplicarse [AGENTS.md](../../AGENTS.md). La tarea de etiquetado descrita
aquí puede continuar con estas imágenes sin cambiar modos o controles del robot.

**Punto de reanudación:** abrir job 5 (o conservar job 4 si ya tiene trabajo),
empezar por frame 1, dibujar y revisar
contornos provisionales; reunir después escenas independientes para el piloto.
