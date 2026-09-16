# Flujos y tareas de Cruzr S2 archivados desde el robot

Copia de referencia del 16-09-2026. No es un instalador ni selecciona tareas.
Los archivos conservan exactamente los bytes leídos del robot; manifest.json
registra host, contenedor, ruta original, imagen Docker y SHA-256. Es una copia
de la instalación real, que puede incluir adaptaciones locales: en particular,
`motion/tasks/cruzr/home.xml` no debe considerarse el HOME original de fábrica.

## Los dos escenarios del procedimiento

| Escenario | XML del flujo | Secuencia |
| --- | --- | --- |
| 1: estantería dinámica, desapilado y mesa | [utars_task_canada_wrc_20250930_start.xml](snapshot_20260916/vision/cruzr_s2/utars_task_canada_wrc_20250930_start.xml) | get1→put1, get2→put2, get3→put3 |
| 2: dos estanterías | [utars_task_zhucheng_env_20260428_start.xml](snapshot_20260916/vision/cruzr_s2/utars_task_zhucheng_env_20260428_start.xml) | get1→put2, get2→put1 |

La correspondencia se determinó por la secuencia; las cotas internas no se han
validado contra el montaje físico. Ninguno fue activado al hacer esta copia.
La última consulta del selector seguía en default_task_config.xml.

## Contenido

- `snapshot_20260916/vision/cruzr_s2/`: 54 XML principales, incluidos ambos
  escenarios y el placeholder default_task_config.xml; tres XML de subárboles
  compartidos y un YAML de configuración. Se conserva la estructura relativa
  que usan los includes.
- `snapshot_20260916/motion/tasks/`: 13 XML referenciados por los dos escenarios.
- `snapshot_20260916/motion/meta_clamp/`: 14 YAML referenciados por esas tareas.
- [Catálogo completo](CATALOGO.md): nombres y referencias de navegación de los
  54 XML principales. Los otros flujos están ARCHIVADOS, no cualificados.
- [Dependencias de los dos escenarios](DEPENDENCIAS.md).
- [Manifest e identidades](snapshot_20260916/manifest.json).
- [Documentación china y española, sin credenciales](../../../docs/vendor/ubtech/box_handling/README.md).

Las dependencias copiadas no incluyen binarios de nodos, modelos, mapas, cámaras,
calibraciones, todo el SDK ni cualquier recurso que un nodo cargue internamente.
No se afirma que copiar esta carpeta a otro firmware permita ejecutarla. Las
52 entradas restantes incluyen ejemplos de otros montajes y un placeholder;
no deben interpretarse como 52 escenarios de prueba aprobados.

## Actualizar la copia

Desde la raíz del repo, usar directorios NUEVOS y revisar el diff antes de
conservar otra versión. Requiere Python 3, lxml, conexión SSH configurada y el
helper de lectura ya existente en scripts/collect_estop_available_readonly.py.
El script sólo ejecuta lecturas dentro de los contenedores; no activa tareas.

```bash
python3 scripts/vendor/import_ubtech_box_workflows.py \
  --snapshot-dir vendor/ubtech/cruzr_s2/snapshot_AAAAMMDD \
  --docs-dir docs/vendor/ubtech/box_handling_AAAAMMDD \
  --private-dir ../Humanoide-vla-evidence/VENDOR_ARCHIVE_AAAAMMDD \
  --docx '/home/lacuna/Descargas/Cruzr_S2_Procedimiento_traslado_cajas_ES.docx' \
  --docx '/home/lacuna/Descargas/Cruzr S2 搬箱子操作流程.docx'
```

Los nombres de los contenedores están fijados al baseline contrastado. Tras una
actualización, redescubrirlos y adaptar el importador antes de usarlo. El script
rechaza directorios ya existentes y archivos de configuración con posibles
credenciales; los originales privados nunca se guardan dentro del repositorio.
Las imágenes y el formato DOCX se conservan; se retiran los párrafos de acceso.

Origen privado y respaldo: ../Humanoide-vla-evidence/20260916_VENDOR_ARCHIVE/.
Para revertir esta incorporación, retirar selectivamente las carpetas nuevas y
sus enlaces; no requiere ninguna intervención en el robot. No hay receta de
despliegue automático: decidir compatibilidad/escena es un trabajo distinto.
