# Relevo portable: SmolVLA de la pelota — 10-11-2026

Este documento permite a otro agente o persona retomar el piloto sin depender
del historial del chat. Es un resumen del estado **registrado**, no una lectura
del robot en este momento. No concede control físico ni sustituye las fuentes
del proyecto. Léase junto a `AGENTS.md`, `docs/PROJECT_SOURCE_OF_TRUTH.md`,
`docs/vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md` y las fichas enlazadas abajo.
Los documentos globales incluyen hechos históricos de otros efectores y tareas;
no confundirlos con el estado reciente de este piloto. Si la salida de lectura
se trunca, leer el archivo completo por segmentos.

**Para el traslado:** en este PC se prepara la carpeta privada
`/home/lacuna/proyectos/Robots/RELEVO_TRASLADO_20261110/` con copias de los
dos paquetes siguientes, en los subdirectorios `RELEVO_SMOLVLA_20261110/` y
`RELEVO_CRUZR_SDK_20261110/`, y con una copia externa actualizada de esta guía
junto a `LEEME.md`. Para reanudar desde otro PC se traslada la carpeta completa
por un canal privado y se verifican ambos paquetes por separado con sus hashes
obtenidos independientemente. La guía y el LEEME son complementos externos,
no modifican los manifiestos de los paquetes. La preparación en este PC no
acredita que se haya trasladado ni restaurado en otro equipo.

**Resultado del export, 10-11-2026:** la copia para traslado del paquete privado
está en este PC en
`/home/lacuna/proyectos/Robots/RELEVO_TRASLADO_20261110/RELEVO_SMOLVLA_20261110`;
su `manifest.json` tiene
SHA256 `a1029fc48c7be5a250b19511ff9cde735f1917bea23596ad7285738dc1472b1f`.
Conserva el commit `943bc7b07655ac8b1e754ac6bdaf2e718489c799`, 476 archivos
no seguidos elegidos y evidencia seleccionada sin faltantes; su manifiesto
registra 18 exclusiones. La verificación y una restauración en directorio
temporal pasaron **en este PC**; no se ha transferido ni probado en otro. Esta
actualización documental es posterior al paquete y no se encuentra en su bundle.
El archivo privado de hash independiente es
`../Humanoide-vla-evidence/PORTABLE_HANDOFF_20261110/portable-manifest.SHA256`,
cuyo SHA256 es `8410a85a3fb73b982138e9d7dd0a5fc8f42c7aa390fba6ffeeacc154c921065a`.
El paquete no está cifrado y la historia Git contiene una credencial preexistente:
no subirlo a la nube ni publicarlo sin saneamiento y protección.

**SDK complementario, también privado:**
`/home/lacuna/proyectos/Robots/RELEVO_TRASLADO_20261110/RELEVO_CRUZR_SDK_20261110/`
es la copia para traslado de un segundo paquete separado, no incluido en el
manifiesto principal. Conserva la ruta
original del SDK y 12 archivos (298149970 bytes), cotejados con el origen por
SHA256 y tamaño. Su `manifest.json` SHA256 es
`432791258fe0254bf9c418c3a281e2838f93332b6612a0db37593ff7050f7e2e`; registra
el `source_mode` de cada archivo. El índice `SHA256SUMS` tiene SHA256
`85aac5bc4bf44720c78c6a4bbe58af184381fe63c757cab0aa718772478e8e92` y permite
verificar los 12 archivos. La raíz es 0700 y los archivos 0600; algunos
subdirectorios heredados son 0775 pero están protegidos por la raíz privada.
Hay que transferir **ambos paquetes** y verificar cada uno antes de restaurar.
Los modos de origen están registrados; no se promete una restauración automática
de esos modos. La copia SDK no incluye ni certifica imágenes/volúmenes Docker
de Ada y tampoco ha sido trasladada a otro PC.

## Objetivo solicitado

Con la mano derecha, coger la pelota de tenis situada sobre un aro fijo en la
mesa, subirla aproximadamente 20 cm, bajarla y soltarla. El usuario prioriza
comprobar el ciclo de entrenamiento y ejecución antes que la precisión del
resultado. Ha autorizado ensayos físicos, con una persona junto al paro, pero
eso **no acredita las condiciones físicas actuales** ni elimina los requisitos
de supervisión y admisión. Inicialmente pidió comenzar desde HOME; después
solicitó trabajar desde la postura física PICO sin teleoperación activa. Antes
de un ensayo acordar y comprobar su postura concreta, sin inferirla del chat.

Los dedos deben permanecer extendidos durante la aproximación, cerrar en la
posición de agarre, mantener cierre durante elevación y bajada, y abrir para
soltar. La teleoperación usó el gatillo derecho del mando PICO para cerrar y
su liberación para abrir; no se ha demostrado que la señal candidata del modelo
sea una orden v4 equivalente o que sus unidades y fuerza estén cualificadas.

## Qué está probado y qué no

- **Datos y entrenamiento, 09-11-2026:** el piloto utiliza 60 muestras a 2 Hz
  de dos tramos de la **misma segunda grabación**, no dos demostraciones
  independientes. Ninguno empieza en HOME; la elevación de 20 cm no está
  calibrada. La conversión de `cmd_pos` usa una configuración histórica y los
  objetivos articulares son hipótesis offline. La etiqueta de mano es candidata,
  no gatillo PICO ni orden de fuerza validada. El modelo hizo 1.000 pasos de
  entrenamiento en Ada en 390,12 s; 58/60 etiquetas de mano coincidieron en
  las **mismas muestras de entrenamiento**, no en una evaluación independiente.
  Detalles, recetas y hashes: [piloto](PELOTA_SMOLVLA_PILOTO_20261109.md).
- **Inferencia real, 10-11-2026:** Ada produjo predicciones con imágenes y estado
  reales. Con la guardia real de Motion activa, el PC validó una propuesta y
  Motion recibió un permiso por el canal de latido; no hubo goal, UUID entregado
  a guardia, staging, cancelación ni movimiento. Esa comprobación no ejecutó el
  coordinador/worker físico, ni midió la edad completa de imagen desde Vision.
  El modelo propuso cambios grandes también en otros ejes: no enviarlos sin una
  vía y validación específicas. [Resultado](SMOLVLA_NATIVE_ARM_STEP_20261110.md#modelo-y-guardia-reales-sin-meta--10-11-2026).
- **Paso candidato:** el código preparado acepta el objetivo fijo de +0,01 rad
  de muñeca derecha en 4 s solo si la propuesta respalda su dirección y al menos
  el desplazamiento restante hasta ese objetivo desde el estado observado.
  Los otros seis objetivos del brazo se mantienen en la referencia; la mano no
  se acciona. No es ejecución de la política completa ni de la tarea de pelota.
  El modelo, su permiso y el coordinador/worker se probaron conjuntamente solo
  con componentes simulados. El cargador y el ejecutor mantienen
  `model_wrist_dispatch_not_enabled` **antes de conexión**. No afirmar que el
  robot rechazó una orden de SmolVLA: no se ha enviado ninguna.
- **Cabeza y mano:** se registró una bajada de cabeza desde PICO con éxito
  observado y confirmación del usuario; no acredita la postura actual. La
  teleoperación de la mano v4 funcionó para el usuario, pero su conexión a la
  señal del modelo, fuerza y parada no están validadas. Son cuestiones distintas
  del entrenamiento y del paso de muñeca.
- **Incidente 731084:** una tarea *fija*, no generada por el VLA, fue aceptada;
  el supervisor perdió la guardia y después el UUID figuró cancelado. La muñeca
  se observó +0,009875 rad respecto a su referencia y una muestra del codo
  +0,002205 rad. No se observó anomalía por el operador. Se descartó stderr de
  guardia y la causa exacta es desconocida: no atribuirla al codo o al disco.
  Su marker y XML se conservaron; no borrarlos, archivarlos ni enviar HOME
  automáticamente. La admisión específica de sucesor está solo simulada y es
  una excepción al bloqueo anterior, no una recuperación completada.
  [Incidente y límites](SMOLVLA_NATIVE_ARM_STEP_20261110.md#intento-supervisado-interrumpido-731084--10-11-2026).
- **Supervisión, 10-11-2026:** la lectura de respuestas de guardia se separó de
  una escritura de renovación que puede bloquearse; se probó localmente, no en
  Motion. Una escritura positiva ya iniciada aún puede publicar su plazo previo
  hasta un máximo de 0,5 s y una revocación puede quedar pendiente. También se
  reprodujo localmente contención del lock: un ACK fresco puede caducar antes de
  llegar al worker y se rechaza. El intento de corrección de esa contención se
  descartó por regresión; no se sabe si causó 731084. ACK, cancelación y
  velocidad publicada cero no demuestran frenado físico.
- **Último check sintético, 10-11-2026:** se preparó una copia de guardia y
  servidor ROS ficticio aislado para observar cancelación sin mover el robot.
  Los intentos quedaron antes de UUID/goal por lectura de cargador y, tras la
  desconexión comunicada, por `battery_invalid_or_below_30_percent`. La lectura
  posterior registró dos baterías aproximadamente al 26,2 % y 28,4 %; el
  monitor PICO de esta prueba exige al menos 30 % en **cada** batería. El usuario
  dijo que avisaría tras cargar y desconectar; no consta cuándo empezó la carga
  ni el estado actual. No se probó aún la cancelación sintética o física.

## Reanudación mínima

1. Comprobar la carpeta y preservar todo cambio previo: `git status --short
   --branch`. El HEAD del relevo era `a45c150` en la rama local `74-jacob`, pero
   un paquete puede incorporar cambios posteriores y archivos aún sin commit.
   No limpiar, sobrescribir, reiniciar o restaurar estados transitorios.
2. Confirmar qué pide el usuario en la nueva sesión y su autorización vigente;
   no reutilizar una confirmación física antigua. Ante peligro inmediato,
   accionar el E-stop disponible **sin esperar a enviar HOME**. La recuperación
   o un apagado planificado se tratan después cuando la trayectoria sea segura.
3. Cuando el usuario indique que terminó la carga, comprobar de nuevo las dos
   baterías y cargador por lectura actual; el umbral del supervisor de esta
   prueba es 30 % por batería, con cargador desconectado. No cambiar ni falsear
   la protección. No inferir la postura o los contactos por una captura histórica.
4. Revisar el código y `--help` actuales, redescubrir contenedores/endpoints y
   generar una nueva referencia y binding revisados; los anteriores no acreditan
   la postura actual ni coinciden necesariamente con las fuentes actuales. El
   check [sintético](../../scripts/vla/check_pico_wrist_synthetic_cancel.py)
   crea procesos ROS temporales y un goal **ficticio** en un namespace aislado;
   no es una simple lectura. Revisar sus límites, ejecutar solo la prueba
   pertinente y verificar la limpieza por separado en Motion/Vision/Ada.
5. Resolver el bloqueo de acceso compartido y el comportamiento de cancelación,
   conservando evidencia del incidente. El gate sigue cerrado y no debe eludirse
   mediante un binding legacy o cliente alternativo. Una solicitud de cancelación
   no acredita el frenado. Antes de cualquier movimiento volver a comprobar mano
   instalada/objeto sujeto, postura, baterías, cargador, ambos paros, ruedas,
   modo, zona despejada, persona al paro y ausencia de control simultáneo. El
   chequeo de clientes locales no descubre necesariamente todos los otros PC:
   coordinar explícitamente **todos** los ordenadores y controladores, incluido
   el visor PICO y la interfaz web, antes de asumir exclusividad.

Para reproducir o revisar, empezar por
[estado detallado del ejecutor](SMOLVLA_NATIVE_ARM_STEP_20261110.md),
[registro de adaptaciones](../SYSTEM_CUSTOMIZATIONS.md) y
[guía de adquisición/entrenamiento](CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md).
El VLA suministrado y sus recetas ENTRY410 tienen otra historia; no aplicarlas
como si fueran la habilitación del SmolVLA de pelota.

## Cambio de ordenador o de agente

- El repositorio, sus commits **y los cambios existentes sin confirmar** son
  partes distintas del estado. En este PC había modificaciones previas en
  `docs/PROJECT_SOURCE_OF_TRUTH.md` y `docs/vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md`,
  además de archivos no seguidos ajenos; preservarlos y no suponer que otro
  checkout los contiene. No asumir que la rama local está publicada.
- Las dos capturas originales y las evidencias privadas están fuera de Git,
  bajo `../Humanoide-vla-evidence/` **respecto a la raíz del repositorio**. Tomar ambas carpetas
  `20261109T183246Z_EPISODE_7abf3106/` y
  `20261109T183726Z_EPISODE_879a137d/`, más referencias y backups enlazados por
  las fichas. El destino del export se trata como información privada: puede
  contener imágenes, datos del robot y registros. Conservar permisos y SHA256.
- El checkpoint, dataset y entorno de inferencia están también en el servidor
  Ada. Las rutas históricas y receta están en [shadow](../../scripts/vla/SMOLVLA_BALL_LIVE_SHADOW.md)
  y [piloto](PELOTA_SMOLVLA_PILOTO_20261109.md); comprobar disponibilidad y
  hashes, no sobreescribir rutas previas. No basta copiar solo el archivo de
  pesos: hacen falta normalización, esquema, dependencias y configuración
  compatibles. El dataset completo `dataset-v2/lerobot-experiment` (~45 MiB) se
  copió de Ada a `../Humanoide-vla-evidence/PORTABLE_HANDOFF_20261110/ada-dataset-v2/`
  y se verificaron nueve archivos; el índice hermano `ada-dataset-v2.SHA256`
  tiene SHA256 `2492012858bbb868f2d2bb9a65e4e356cde2e816d0d3cd953189fe3d759e296a`.
  Comprobar que el export incluya esa copia o transferirla y verificarla aparte.
  Acceso a Ada, Motion y Vision, host keys y credenciales se preparan por canal
  privado; no añadirlos al repositorio ni a un paquete público.
- **La copia existente no puede darse por libre de secretos:** se detectó al
  menos una credencial literal en un archivo versionado y puede haber otras en
  la historia de Git o en bindings y derivados privados. No publicar ni subir
  el repositorio o el paquete a una nube como si estuviera saneado. Revisar y
  remediar por separado, incluyendo la revocación o rotación que corresponda,
  sin mostrar ni incluir su valor en el relevo. Una exportación privada también
  debe tratarse como sensible hasta revisar su contenido completo.
- El export portable se prepara desde `scripts/vla/export_smolvla_handoff.py`:
  `--output /ruta/privada/nueva` crea un directorio nuevo fuera del repositorio
  y de la evidencia; `--light` excluye las capturas, candidatos, checkpoint y
  dataset grandes. El paquete incluye un bundle Git con la rama y su historia,
  parches binarios separados de cambios staged/unstaged, inventario de no
  seguidos y evidencia seleccionada. `--include-untracked RUTA_RELATIVA` puede
  repetirse para conservar archivos no seguidos no ignorados; por defecto solo
  se inventarían. `--include-evidence RUTA_RELATIVA` selecciona evidencia
  adicional. Bindings antiguos y nombres sensibles se excluyen; revisar en el
  manifiesto las omisiones y lo que queda por copiar. Consultar `--help`.
- Conservar por canal independiente el SHA256 del manifiesto devuelto al crear
  el paquete. En el otro PC, comparar primero el manifiesto con ese SHA, clonar
  el bundle en un checkout **nuevo, privado y fuera del paquete**, y ejecutar
  desde una copia de confianza del script `--verify DIRECTORIO --manifest-sha256
  HASH`. Esa verificación comprueba el conjunto y sus hashes; no prueba
  autenticidad ni cifra nada. Revisar los parches staged/unstaged en ese orden
  antes de aplicarlos; `--verify DIRECTORIO --manifest-sha256 HASH
  --restore-untracked CHECKOUT` restaura solo lo seleccionado sin sobrescribir
  ni aplicar parches. Comprobar que la carpeta `Humanoide-vla-evidence` quede
  al lado de la raíz del checkout y que estén sus archivos requeridos. No aplicar
  parches o copias sobre un trabajo existente sin revisarlos.
- **Crear un paquete local no equivale a haberlo copiado a otro PC**, ni a
  verificar acceso a robot o servidor. El export no incluye automáticamente
  todos los ignorados, todos los datos o el entorno Docker de Ada. Cotejar los
  faltantes con el manifiesto, transferirlos por separado y verificar hashes;
  no añadir credenciales ni alterar las fuentes originales.
- Para Claude u otro agente, indicar explícitamente que lea `AGENTS.md` y las
  fuentes citadas; no asumir que todos los clientes cargan el mismo archivo de
  instrucciones. Acordar en la nueva sesión el alcance de cambios permitido.

## Restauración en un PC nuevo

Usar un paquete recibido por canal privado y el SHA256 de `manifest.json`
recibido por un canal independiente y fiable. **El paquete contiene una
credencial preexistente en la historia Git y no está cifrado:** no lo subas a
una nube ni lo compartas sin saneamiento y protección. Ejecutar lo siguiente
solo en un ordenador de confianza, sustituyendo las rutas y el hash. El destino
completo debe **no existir**; un fallo deja cualquier resultado parcial para
inspección, no se borra ni se sobrescribe automáticamente.

Este primer bloque verifica el manifiesto y el hash del bundle antes de usarlo,
comprueba el bundle en un repositorio temporal vacío, clona un checkout nuevo
fuera del paquete y ejecuta la verificación completa del export. Se detiene si
hay evidencia seleccionada ausente o el checkout no coincide con el commit.

```bash
RELEVO_PAQUETE='/ruta/privada/paquete'
RELEVO_DESTINO='/ruta/privada/destino-que-no-existe'
RELEVO_MANIFEST_SHA256='HASH_RECIBIDO_POR_CANAL_SEPARADO'
export RELEVO_PAQUETE RELEVO_DESTINO RELEVO_MANIFEST_SHA256
(
  set -eu
  umask 077
  mkdir -m 700 -- "$RELEVO_DESTINO"
  python3 - "$RELEVO_PAQUETE" "$RELEVO_MANIFEST_SHA256" <<'PY'
import hashlib, json, re, subprocess, sys, tempfile
from pathlib import Path
package = Path(sys.argv[1]).resolve(strict=True)
expected = sys.argv[2]
if not re.fullmatch(r'[0-9a-f]{64}', expected):
    raise SystemExit('Hash independiente inválido')
raw = (package / 'manifest.json').read_bytes()
if hashlib.sha256(raw).hexdigest() != expected:
    raise SystemExit('Manifiesto distinto del hash independiente')
manifest = json.loads(raw)
matches = [row for row in manifest['files'] if row.get('path') == 'git/branch.bundle']
if len(matches) != 1:
    raise SystemExit('Bundle ausente o duplicado en manifiesto')
bundle = package / 'git' / 'branch.bundle'
if bundle.is_symlink() or not bundle.is_file():
    raise SystemExit('Bundle no es un archivo regular')
h = hashlib.sha256()
with bundle.open('rb') as stream:
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        h.update(block)
if h.hexdigest() != matches[0]['sha256'] or bundle.stat().st_size != matches[0]['size']:
    raise SystemExit('Bundle distinto del manifiesto')
with tempfile.TemporaryDirectory(prefix='cruzr-verify-bundle-') as tmp:
    subprocess.run(['git', 'init', '--bare', '--quiet', tmp], check=True)
    subprocess.run(['git', '-C', tmp, 'bundle', 'verify', str(bundle)], check=True)
print('Manifiesto y bundle comprobados')
PY
  git clone -- "$RELEVO_PAQUETE/git/branch.bundle" "$RELEVO_DESTINO/Humanoide"
  python3 -B "$RELEVO_DESTINO/Humanoide/scripts/vla/export_smolvla_handoff.py" \
    --verify "$RELEVO_PAQUETE" --manifest-sha256 "$RELEVO_MANIFEST_SHA256" \
    > "$RELEVO_DESTINO/verificacion.json"
  python3 - "$RELEVO_DESTINO/verificacion.json" "$RELEVO_DESTINO/Humanoide" <<'PY'
import json, subprocess, sys
result = json.load(open(sys.argv[1], encoding='utf-8'))
if result.get('status') != 'VERIFIED_INTEGRITY':
    raise SystemExit('Hay evidencia seleccionada ausente: revisar el manifiesto')
head = subprocess.check_output(['git', '-C', sys.argv[2], 'rev-parse', 'HEAD'], text=True).strip()
if head != result['commit']:
    raise SystemExit('El checkout no corresponde al commit del paquete')
print('Paquete y checkout verificados:', head)
PY
)
```

El verificador compara con el manifiesto, pero no certifica su procedencia si
el SHA no llegó por canal independiente. La verificación tampoco sanea datos o
credenciales. Revisa ahora `git/status.txt`, `git/untracked.json`, los parches
y los archivos seleccionados. No continúes si no reconoces algún contenido.

Tras revisarlos, el segundo bloque aplica primero el parche staged y después el
unstaged, solo si no están vacíos y tras `git apply --check`; restaura únicamente
los no seguidos elegidos y copia la evidencia a una carpeta hermana nueva.

```bash
(
  set -eu
  umask 077
  if [ -s "$RELEVO_PAQUETE/git/staged.patch" ]; then
    git -C "$RELEVO_DESTINO/Humanoide" apply --check --index "$RELEVO_PAQUETE/git/staged.patch"
    git -C "$RELEVO_DESTINO/Humanoide" apply --index "$RELEVO_PAQUETE/git/staged.patch"
  fi
  if [ -s "$RELEVO_PAQUETE/git/unstaged.patch" ]; then
    git -C "$RELEVO_DESTINO/Humanoide" apply --check "$RELEVO_PAQUETE/git/unstaged.patch"
    git -C "$RELEVO_DESTINO/Humanoide" apply "$RELEVO_PAQUETE/git/unstaged.patch"
  fi
  python3 -B "$RELEVO_DESTINO/Humanoide/scripts/vla/export_smolvla_handoff.py" \
    --verify "$RELEVO_PAQUETE" --manifest-sha256 "$RELEVO_MANIFEST_SHA256" \
    --restore-untracked "$RELEVO_DESTINO/Humanoide"
  if [ -e "$RELEVO_DESTINO/Humanoide-vla-evidence" ] || \
     [ -L "$RELEVO_DESTINO/Humanoide-vla-evidence" ]; then
    printf '%s\n' 'La carpeta de evidencia ya existe; no se sobrescribe.' >&2
    exit 1
  fi
  cp -a -- "$RELEVO_PAQUETE/Humanoide-vla-evidence" "$RELEVO_DESTINO/Humanoide-vla-evidence"
  python3 - "$RELEVO_PAQUETE/manifest.json" "$RELEVO_DESTINO" "$RELEVO_MANIFEST_SHA256" <<'PY'
import hashlib, json, sys
from pathlib import Path, PurePosixPath
manifest_raw = Path(sys.argv[1]).read_bytes()
if hashlib.sha256(manifest_raw).hexdigest() != sys.argv[3]:
    raise SystemExit('El manifiesto cambió durante la restauración')
destination = Path(sys.argv[2])
manifest = json.loads(manifest_raw)
rows = [r for r in manifest['files'] if r['path'].startswith('Humanoide-vla-evidence/')]
expected = set()
for row in rows:
    relative = PurePosixPath(row['path'])
    if relative.is_absolute() or any(p in ('', '.', '..') for p in relative.parts):
        raise SystemExit('Ruta de evidencia inválida')
    path = destination.joinpath(*relative.parts)
    if any(destination.joinpath(*relative.parts[:i]).is_symlink()
           for i in range(1, len(relative.parts) + 1)) or not path.is_file():
        raise SystemExit('Archivo de evidencia ausente o enlace simbólico')
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    if path.stat().st_size != row['size'] or h.hexdigest() != row['sha256']:
        raise SystemExit('Copia de evidencia distinta del manifiesto')
    expected.add(str(relative))
base = destination / 'Humanoide-vla-evidence'
actual = set()
for path in base.rglob('*'):
    if path.is_symlink():
        raise SystemExit('Enlace simbólico no previsto en la copia')
    if path.is_file():
        actual.add(path.relative_to(destination).as_posix())
if actual != expected:
    raise SystemExit('Conjunto de archivos de evidencia inesperado')
print('Copia de evidencia comprobada:', len(expected), 'archivos')
PY
  git -C "$RELEVO_DESTINO/Humanoide" status --short --branch
)
```

Las cerraduras transitorias `.lock` no se incluyen ni se restauran como prueba
de procesos activos. El estado físico, los marcadores de Motion, el entorno
Docker y los clientes conectados se comprueban de nuevo en el destino. Si una
operación falla a mitad, inspecciona el destino parcial y los mensajes antes de
decidir cómo continuar; no borres ni repitas sobre archivos existentes. No se
envía ninguna orden al robot por restaurar el paquete.

El paquete SDK se traslada **aparte**. Tras recibir sus dos hashes por un canal
independiente, se puede verificar en el otro PC antes de copiar nada al checkout:

```bash
RELEVO_SDK='/ruta/privada/RELEVO_CRUZR_SDK_20261110'
RELEVO_SDK_MANIFEST_SHA='HASH_MANIFEST_RECIBIDO_POR_CANAL_SEPARADO'
RELEVO_SDK_INDICE_SHA='HASH_INDICE_RECIBIDO_POR_CANAL_SEPARADO'
(
  set -eu
  test "$(sha256sum -- "$RELEVO_SDK/manifest.json" | cut -d ' ' -f 1)" = "$RELEVO_SDK_MANIFEST_SHA"
  test "$(sha256sum -- "$RELEVO_SDK/SHA256SUMS" | cut -d ' ' -f 1)" = "$RELEVO_SDK_INDICE_SHA"
  cd -- "$RELEVO_SDK"
  sha256sum -c --quiet SHA256SUMS
  printf '%s\n' 'Índice y archivos SDK verificados.'
)
```

El índice y el manifiesto deben contrastarse con los hashes independientes,
no con valores enviados solo junto al paquete. Después, revisar las rutas y
`source_mode` del manifiesto y restaurar de manera selectiva sin sobrescribir
un SDK existente. Los modos originales no se restauran automáticamente y
pueden necesitar revisión manual. Verificar los archivos copiados; esto no
instala el SDK ni verifica que sea compatible con el robot o con Ada.
