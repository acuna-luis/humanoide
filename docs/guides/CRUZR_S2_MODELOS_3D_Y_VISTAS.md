# Modelos 3D y vistas del Cruzr S2

21-10-2026, Europe/Madrid. ID `MODELS-VIEWS-20261021`.

Los archivos del proveedor permiten entregar vistas y una representación 3D del
robot completo. Incluyen geometría de superficies STL y un ensamblaje URDF;
no contienen un STEP nativo del robot completo ni acreditan cotas de fabricación.

## Entrega local y estado

Fuente conservada sin modificar ni borrar originales:
`/home/lacuna/Descargas/Lark20261021-084746/`.

En su subcarpeta `preparado/`:

| Archivo o carpeta | Utilidad y estado |
| --- | --- |
| `Vistas_y_especificaciones_Cruzr_S2.pdf` | Páginas 7–8 del manual: vistas frontal/trasera y especificaciones del proveedor. Preparado. |
| `Vista_frontal_y_trasera.png` | Lámina de componentes del manual. Preparada. |
| `Vista_perspectiva.png` | Vista en perspectiva del manual. Preparada. |
| `modelo_abrazaderas/cruzr_s2_description/` | Variante `splint`, extraída y verificada; URDF y mallas originales. |
| `modelo_pinzas/cruzr_s2_description/` | Variante alternativa PGC, extraída y verificada por separado. |
| `Cruzr_S2_abrazaderas_referencia_mm.stl` | Ensamblaje visual de abrazaderas en milímetros, con articulaciones URDF a cero. Generado y verificado. |
| `Cruzr_S2_abrazaderas_referencia_mm.json` | Informe de generación y hashes del ensamblaje. Generado y verificado. |
| `LEEME.txt`, `fuentes_y_verificacion.json` | Instrucciones de apertura, alcance y procedencia. |

Archivo para enviar, fuera de `preparado/`:
`Cruzr_S2_vistas_y_modelo_3D_abrazaderas.zip` — **VERIFICADO** el 21-10-2026
a las 09:38:04 Europe/Madrid (07:38:04 UTC). Tamaño: 41 954 103 bytes
(aproximadamente 41,9 MB). Sus 74 archivos pasan verificación CRC y SHA256.
SHA256 del ZIP:
`976bada68c4c518b05b63274c4a202ddf75650914eb71f665c9a2f5b8fbbcbb9`.

Incluye el manual resumido español revisado en DOCX (6 páginas), el LEEME final,
las dos imágenes, el PDF, STL e informe, procedencia y
el paquete URDF/STL completo de `modelo_abrazaderas/` (66 archivos). La variante
`modelo_pinzas/` se conserva extraída localmente y queda fuera del envío.
El manual describe además la colección Lark original completa: los otros ZIP de
manos, pinzas y teleoperación no están incluidos en esta selección. El LEEME lo aclara.
Recibos: `preparado/verificacion_paquete.json` y
`../Humanoide-vla-evidence/20261021T071610Z_MODELOS_3D_LOCAL/delivery-package.json`.

Para el destinatario que solicita vistas o, preferiblemente, un modelo 3D,
la opción práctica es enviar el paquete de abrazaderas con el STL ensamblado,
las vistas y el URDF original con sus mallas. Para diseñar piezas o fabricar
adaptaciones se necesita el CAD oficial apropiado y verificar sus cotas.

## Qué representan las dos variantes

- `cruzr_s2_description_splint.zip`: 48 enlaces y 47 articulaciones URDF.
  Sustituye los efectores PGC por dos piezas fijas, `L_hand_link` y
  `R_hand_link`, unidas a los sensores de fuerza/par. Es la variante de
  abrazaderas seleccionada para esta entrega.
- `cruzr_s2_description.zip`: 52 enlaces y 51 articulaciones URDF. Cada efector
  tiene una base PGC y dos dedos con articulaciones prismáticas. Es una variante
  alternativa de pinzas, no el modelo articulado de las manos v4.

El resto de enlaces y articulaciones coinciden. Las mallas compartidas son
idénticas; `splint` añade dos STL y cambia el URDF. Ambos paquetes tienen el
mismo nombre y rutas internas: **extraerlos siempre en destinos separados**.

Las vistas del manual muestran manos; el STL entregado usa los efectores de la
variante `splint`. Son representaciones diferentes del proveedor. La denominación
abrazaderas no demuestra que su geometría u orientación coincidan exactamente
con los efectores y el montaje de la unidad física actual.

Se comprobaron CRC y hashes de los archivos extraídos, árboles URDF conectados
a `base_link`, referencias de malla presentes y estructura binaria de los STL.
Incluyen chasis, ruedas, elevador, torso, cabeza y ambos brazos. Algunas mallas
incluidas no se usan en el ensamblaje URDF. Esta revisión no valida la precisión
dimensional ni la correspondencia exacta con la unidad física actual.

## Abrir y usar los archivos

El STL ensamblado se abre en un visor 3D o mediante **Importar malla/STL** en un
CAD. Elegir **milímetros**: STL no guarda la unidad y el ensamblador convierte
las coordenadas a mm. Conserva las superficies trianguladas de las piezas; no
las convierte en un sólido paramétrico ni realiza una unión booleana.

El URDF usa metros y conserva los enlaces, articulaciones y referencias
`package://cruzr_s2_description/...`. Para abrirlo en un visor compatible con
URDF, conservar juntas las carpetas `urdf/` y `meshes/` y resolver ese paquete.
No basta con enviar el archivo `.urdf` suelto.

El ensamblaje STL fija todas las articulaciones en **q=0 del URDF**. Es una
postura de referencia del modelo: **no es una lectura del robot ni demuestra
su HOME actual**. No se ha usado el robot para generar estas vistas.

Generación verificada: 45 geometrías visuales de un árbol de 48 enlaces,
846 393 triángulos y 42 319 734 bytes. El informe verifica los hashes de las 47
fuentes usadas. SHA256 del STL:
`4acef165c8540c2859590661aecc1c0513a026aa187b367a9b8c018ade2a0a1d`.
Estas comprobaciones validan la reproducción del ensamblaje, no sus cotas físicas.

## Reproducción local

Ejecutar en PC, con destinos nuevos o sin sobrescribir archivos existentes:

```bash
fuente='/home/lacuna/Descargas/Lark20261021-084746'
salida="$fuente/preparado"
mkdir -p "$salida/modelo_abrazaderas" "$salida/modelo_pinzas"
unzip -n "$fuente/cruzr_s2_description_splint.zip" -d "$salida/modelo_abrazaderas"
unzip -n "$fuente/cruzr_s2_description.zip" -d "$salida/modelo_pinzas"
```

Desde la raíz de este repositorio, con Python y NumPy ya disponibles:

```bash
python3 scripts/docs/assemble_cruzr_urdf_stl.py \
  --package-root "$salida/modelo_abrazaderas/cruzr_s2_description" \
  --output "$salida/Cruzr_S2_abrazaderas_referencia_mm.stl" \
  --report "$salida/Cruzr_S2_abrazaderas_referencia_mm.json"
```

El script exige destinos nuevos, transforma las geometrías `visual` siguiendo
el árbol URDF y genera un STL binario y su informe. No ejecuta código del
proveedor ni se conecta al robot. No se instalaron paquetes para esta entrega.

SHA256 de los ZIP de origen:

| Fuente | SHA256 |
| --- | --- |
| `cruzr_s2_description_splint.zip` | `ceabd4aa5c21233dcb326d94f08cf857a4717f289767d4aff5ac765b2742c469` |
| `cruzr_s2_description.zip` | `7cb7f856223ce99a86d44349be475a2b5925d57ca694ee069a96c808802e297e` |

Los ZIP, modelos, PDF e imágenes permanecen fuera de Git. Se versionan esta guía
y la receta de ensamblaje; los originales no se borran. La reversión local
consiste en retirar únicamente los derivados de `preparado/` y el ZIP de
entrega, después de conservar lo que se haya enviado. No hay cambios del robot
que revertir.

## Extraer las vistas del manual y empaquetar la entrega

Con `fuente` y `salida` definidos como arriba, usar destinos nuevos:

```bash
paginas_modelo=$(mktemp -d)
pdfseparate -f 7 -l 8 "$fuente/2-Cruzr_S2_Product_Manual.pdf" "$paginas_modelo/pagina-%d.pdf"
test ! -e "$salida/Vistas_y_especificaciones_Cruzr_S2.pdf"
pdfunite "$paginas_modelo/pagina-7.pdf" "$paginas_modelo/pagina-8.pdf" "$salida/Vistas_y_especificaciones_Cruzr_S2.pdf"
test ! -e "$salida/Vista_frontal_y_trasera.png"
pdftoppm -f 7 -l 7 -scale-to 1600 -singlefile -png "$fuente/2-Cruzr_S2_Product_Manual.pdf" "$salida/Vista_frontal_y_trasera"
test ! -e "$salida/Vista_perspectiva.png"
pdftoppm -f 1 -l 1 -scale-to 1600 -singlefile -png "$fuente/2-Cruzr_S2_Product_Manual.pdf" "$salida/Vista_perspectiva"
```

El directorio temporal contiene sólo las páginas intermedias. Verificar el PDF
resultante mediante `pdfinfo` y lectura/renderizado; conservar el manual original.
El ZIP final contiene los siete archivos de `preparado/`, el DOCX revisado de
la carpeta principal y únicamente
el paquete original de abrazaderas. La PGC permanece extraída por separado.
El LEEME y la procedencia describen los archivos verificados; conservarlos con
el modelo. Para empaquetar un destino nuevo:

```bash
python3 - "$salida" "$fuente/Cruzr_S2_vistas_y_modelo_3D_abrazaderas.zip" <<'PYCODE'
from pathlib import Path
import hashlib, sys, zipfile
source, target = map(Path, sys.argv[1:])
names = ('LEEME.txt', 'Vistas_y_especificaciones_Cruzr_S2.pdf',
         'Vista_frontal_y_trasera.png', 'Vista_perspectiva.png',
         'Cruzr_S2_abrazaderas_referencia_mm.stl',
         'Cruzr_S2_abrazaderas_referencia_mm.json', 'fuentes_y_verificacion.json')
files = [source/name for name in names]
files += sorted(p for p in (source/'modelo_abrazaderas').rglob('*') if p.is_file())
files.append(source.parent/'Manual_resumen_archivos_Cruzr_S2_ES.docx')
assert all(p.is_file() and not p.is_symlink() for p in files)
prefix = 'Cruzr_S2_vistas_y_modelo_3D_abrazaderas/'
def member(path):
    return prefix + (path.name if path.parent == source.parent else path.relative_to(source).as_posix())
with zipfile.ZipFile(target, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
    for path in files:
        bundle.write(path, member(path))
with zipfile.ZipFile(target) as bundle:
    assert bundle.testzip() is None
    for path in files:
        assert hashlib.sha256(bundle.read(member(path))).digest() == hashlib.sha256(path.read_bytes()).digest()
print(hashlib.sha256(target.read_bytes()).hexdigest(), target)
PYCODE
```

El hash del ZIP depende también de las fechas/metadatos de los archivos; el hash
del STL y los de sus fuentes permiten comprobar la geometría reproducida.

## Manual resumido en español para el disco externo

El 21-10-2026 se creó `Manual_resumen_archivos_Cruzr_S2_ES.docx` en la raíz de
`/home/lacuna/Descargas/Lark20261021-084746/`, con seis páginas A4 tras añadir una primera página de alcance para el solicitante.
Incluye todos los grupos de archivos originales y explica extracción, partes,
formatos, compatibilidad de los instaladores y qué copiar al disco externo.
Distingue los originales de los derivados opcionales: no supone que `preparado/`
o el ZIP 3D ya estén en la copia externa. No reproduce credenciales.

[Fuente HTML editable](MANUAL_RESUMEN_ARCHIVOS_LARK_CRUZR_S2_ES.html) y
[generador](../../scripts/docs/build_lark_summary_docx.py). Para recrear desde
el repositorio con Python/lxml y LibreOffice ya instalados, usar un destino nuevo:

```bash
python3 scripts/docs/build_lark_summary_docx.py \
  --output /RUTA/NUEVA/Manual_resumen_archivos_Cruzr_S2_ES.docx
```

El generador usa un perfil temporal aislado de LibreOffice, fija tablas dentro
de los márgenes y la primera página de alcance y los cinco capítulos, verifica XML/contenido y no sobrescribe
archivos. La copia al disco externo queda a cargo del operador después de revisar.

## Actualización de entrega con el manual revisado

El ZIP se actualizó el 21-10-2026 a las 09:38:04 Europe/Madrid, conservando su
nombre. Se añadió el DOCX de seis páginas y se corrigió el alcance en el LEEME;
los otros 72 archivos conservan el contenido anterior. La versión inicial sin
manual está respaldada fuera de Git en
`../Humanoide-vla-evidence/20261021T073801Z_ZIP_MANUAL_UPDATE/archive-before.zip`,
SHA `1a1f6aafcff60d3d6013a12d7fdf1566d9e845cea75ceaf97ee4352f3ee18d28`.
`delivery-package.json` conserva la comparación y los hashes de los 74 miembros.
Para revertir, cotejar ese hash y restaurar sólo el archivo derivado, conservando
las revisiones posteriores del usuario. No se alteraron los archivos originales
recibidos ni el DOCX independiente. Copiar de nuevo este ZIP al disco externo
si se quiere trasladar la versión que ya incluye el manual.
