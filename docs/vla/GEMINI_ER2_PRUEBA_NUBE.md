# Prueba temporal de Gemini Robotics ER 2 en nube

**ID:** GR2-CLOUD-PILOT-20261021. **Fecha:** 21-10-2026 Europe/Madrid.
**Estado:** dos inferencias HTTP completadas; sin conexión o comandos al robot.

El usuario autorizó una prueba temporal con API de nube y confirmó explícitamente
el envío de una captura real guardada. La producción local sigue siendo el
requisito; esta excepción no autoriza streaming continuo, nuevas capturas ni
control físico. No se habilitaron servicios ni se instalaron paquetes.

## Resultado observado

| Entrada | Resultado | Duración de una llamada | Alcance |
|---|---|---|---|
| Imagen sintética de tres formas | 3 instancias, JSON y cajas normalizadas válidos; IoU mínimo de cajas 0,9733 | 3,468 s | Prueba geométrica y de protocolo, no precisión industrial |
| Recorte de bandeja real | 8 instancias y 8 cajas 2D, coincide con estimación visual independiente previa | 9,401 s | Un único encuadre guardado, no benchmark ni identificación de referencia |

Modelo informado por la API: `gemini-robotics-er-2-preview`. Dos llamadas REST
`generateContent`, salida estructurada JSON validada localmente; sin herramientas
de control. Uso informado: 1658 y 3324 tokens totales, respectivamente; no se
calculó coste monetario. Los tiempos incluyen petición/respuesta y generación,
no son percentiles, FPS sostenidos ni prestaciones de un modelo local.

La foto original `head_raw.png`, 1920×1536, pertenece al lote
`app2/datasets/pieces_head_20261019T115423Z_v002`. Se envió solamente el recorte
(x0,y0,x1,y1)=(745,1080,1315,1440), 570×360, sin personas ni fondo de fábrica.
La identidad de sus píxeles con esa región original se verificó; el original
permanece sin cambios. PNG enviado: SHA256
`af53c69ed6650ddbbdd961903a39e57921eaffb5c802e9833ccb622046aef544`.

## Limitaciones de la conclusión

- La revisión visual previa contó siete piezas agrupadas y una aislada; no es
  un dataset completo de ground truth aceptado. No se calculó mAP/IoU real.
- Las cajas se superponen en el grupo central; no equivalen a máscaras.
- El modelo describió ejes con articulación en distintos extremos, pero no se
  confirma referencia industrial, identidad ITR/OTR, pose 3D ni agarre.
- Su frase sobre longitudes completas visibles no se acepta como verificación:
  el cartón y los solapamientos ocultan algunos límites.
- La prueba acredita inferencia ER 2 con las credenciales usadas; no concede
  acceso a GR2 VLA/On-Device 2 ni demuestra adaptación o ejecución en S2/Y1.

## Reproducción y estado

Helper versionado: [probe_gemini_er2.py](../../scripts/app2/workflow/probe_gemini_er2.py).
`--help` y `--check` no envían datos. `--run` transmite la imagen elegida a Google,
requiere clave de entorno existente y una carpeta de resultados nueva. Consultar
`--help` antes de una nueva prueba; no apunta a cámaras vivas ni a interfaces ROS.

Ejemplo usando los archivos privados de esta prueba, sin ejecutarlo automáticamente:

```bash
python3 scripts/app2/workflow/probe_gemini_er2.py --check \
  --image ../Humanoide-vla-evidence/20261021T100204Z_GR2_CLOUD_PILOT/inputs/pieces_roi.png \
  --prompt-file ../Humanoide-vla-evidence/20261021T100204Z_GR2_CLOUD_PILOT/inputs/pieces-prompt.txt
```

Evidencia privada: `../Humanoide-vla-evidence/20261021T100204Z_GR2_CLOUD_PILOT/`.
Contiene autorización y procedencia en `input-manifest.json`, revisión previa,
respuestas/validación de las dos llamadas, `pilot-summary.json` y superposición
`pieces-comparison.png`. No contiene claves de API. No se añadieron fotografías
a Git ni anotaciones a CVAT. Una visualización con matplotlib falló por módulo
ausente; se utilizó Pillow ya disponible, sin instalar dependencias.

Las credenciales se enviaron sólo en cabeceras a la API oficial de Google,
sin imprimirse ni persistirse. No se usó Files API para crear archivos remotos;
las imágenes sí se transmitieron como contenido de las peticiones de inferencia.
No se puede revertir ese envío; esta intervención no verificó retención del
proveedor. Reversión local: retirar selectivamente helper y documentos tras
conservar revisiones posteriores; backups documentales y hashes en evidencia.
Sin commit ni push.
