# app2 — fotografías originales y fuentes

**Archivo conservado:** 19-10-2026. Zona: Europe/Madrid.
Los originales se mantienen fuera de Git conforme a la política del proyecto;
no publicar imágenes de fábrica ni del entorno sin revisión. El manifiesto
versionado identifica cada fichero con SHA256 y procedencia.

Carpeta estable desde la raíz del repositorio:

```text
../Humanoide-vla-evidence/app2/reference/2026-10-19/
```

## 1. Lámina del cliente: fábrica real

[Abrir lámina original](../../../Humanoide-vla-evidence/app2/reference/2026-10-19/lamina_fabrica_real_ITR_OTR.png).

- Archivo: `lamina_fabrica_real_ITR_OTR.png`, **2189×630**, 827330 bytes.
- SHA256: `e5b22e092e9daedbb3e1591b97e8f1f660ff3a164fa73bd159f908247fdd764e`.
- Procedencia: PNG leído del portapapeles actual tras volver a adjuntar el
  usuario esta misma imagen y solicitar expresamente guardarla.
- Se comprobó visualmente que coincide con la lámina adjunta. PNG guardado
  **sin modificar ni reencodificar**, conservando textos, fotos y flechas rojas.
- Contenido: ITR Material Feed and Empty Container Handling, bloque de
  identificación visual, cinco fotos de fábrica y título posterior OTR.
- [Resumen fiel de requisitos y descripción de las fotos](REQUISITOS_CLIENTE.md).

La anotación previa de «imagen original no disponible como fichero» queda
superada: el original se recuperó y archivó en esta intervención. No confundir
esta lámina con una imagen tomada por las cámaras de nuestro robot.

## 2. Cámaras del robot: escena de pruebas

| Archivo | Resolución | Uso |
|---|---|---|
| [piezas_cabeza_rectificada.png](../../../Humanoide-vla-evidence/app2/reference/2026-10-19/piezas_cabeza_rectificada.png) | 960×576 | Bandeja completa de piezas; vista inicial de trabajo |
| [piezas_cabeza_raw.png](../../../Humanoide-vla-evidence/app2/reference/2026-10-19/piezas_cabeza_raw.png) | 1920×1536 | Más detalle; PNG de imagen sin rectificar, no fichero YUV bruto |
| [vista_cintura.png](../../../Humanoide-vla-evidence/app2/reference/2026-10-19/vista_cintura.png) | 640×360 | Muestra por qué la bandeja queda cortada |
| [vista_chasis.png](../../../Humanoide-vla-evidence/app2/reference/2026-10-19/vista_chasis.png) | 640×360 | Referencia de cámara baja, no vista elegida para las piezas |
| [encuadre_previo_cabeza.png](../../../Humanoide-vla-evidence/app2/reference/2026-10-19/encuadre_previo_cabeza.png) | 960×576 | Historia del encuadre inicial insuficiente |

Son copias exactas de los PNG de las capturas pasivas originales; no se han
anotado ni sustituido sus píxeles. Metadatos de canales/timestamps y capturadores
exactos se conservan en la carpeta privada junto a las fotos. Una resolución
de imagen no certifica precisión métrica ni identidad de referencia.

Fuentes originales adicionales, conservadas:

- `../Humanoide-vla-evidence/20261019T080612Z_CAR_PART_VISION_READONLY/`.
- `../Humanoide-vla-evidence/20261019T084059Z_CAR_PART_VISIBLE_READONLY/`.
- `../Humanoide-vla-evidence/20261019T085657Z_ITR_REQUIREMENTS_SCREENSHOT/`
  conserva la primera transcripción; el original gráfico se recuperó después.

## 3. Comprobación y traslado del archivo

Desde la raíz del repositorio, verificar las copias sin modificar imágenes:

```bash
(cd ../Humanoide-vla-evidence/app2/reference/2026-10-19 && sha256sum -c SHA256SUMS)
```

Se conserva además un paquete privado de traslado:

```text
../Humanoide-vla-evidence/app2/reference/app2_referencias_2026-10-19.tar.gz
```

Para ver su contenido sin extraerlo:

```bash
tar -tzf ../Humanoide-vla-evidence/app2/reference/app2_referencias_2026-10-19.tar.gz
```

El paquete y la carpeta están en el mismo PC: no equivalen a un backup en
otro equipo. Al migrar o respaldar app2, copiar también este archivo privado;
un clon Git no contiene los PNG. Los enlaces de este documento se resuelven
localmente si la carpeta hermana conserva la misma estructura.

El [manifiesto](manifest_fotos.json) permite verificar una copia aunque cambie
su ubicación. Las siguientes sesiones deben añadir nuevas capturas con fecha
distinta, sin sobrescribir estas referencias.
