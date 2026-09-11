# Reanudación VLA: alternativas a ENTRY inclinada

**Actualización posterior 11-09:** RGB y parquets430/438 ya revisados; véase
[la revisión de mesa y acceso](REVISION_ENTRY_CON_MESA_20260911.md).
Los pendientes enumerados abajo describen el cierre del ranking inicial.

**2026-09-11, Europe/Madrid — VERIFICADO offline; sin ejecución física.**

Se retoma E6.1 del [plan](../plan_de_trabajo.md). El problema pendiente era
la inclinación observada por el propietario en `episode_000040/frame 0`.
La ida/vuelta histórica no demuestra idoneidad del fixture ni valida el VLA.

## Resultado

Se revisaron las **150 entradas task 0**, de 500 episodios del reporte E6.0Z,
comprobando su SHA-256 contra el contrato congelado E6.1A. Cada alternativa
conserva los 20 ángulos de un único frame; no se mezclan ni ajustan poses.

El URDF splint da **31,196°** para la ENTRY anterior. Hay **113 entradas con
inclinación ≤5° y dentro de los límites articulares de posición**. Los 5° son
un filtro exploratorio, no un límite de seguridad ni el error articular usado
en otros análisis.

| Entrada, frame 0 | Inclinación torso | Cambio máximo frente a ENTRY anterior | Altura origen sensor L/R sobre base_link | Máximo etiqueta action−state |
|---|---:|---:|---:|---:|
| 000040, anterior | 31,196° | 0 rad | 642 / 655 mm | 0,000326 rad |
| 000438, menor cambio entre filtradas | 4,362° | 0,363458 rad | 788 / 787 mm | 0,000750 rad |
| 000432 | 1,110° | 0,456551 rad | 795 / 795 mm | 0,000415 rad |
| 000430, casi vertical | 0,022° | 0,456647 rad | 800 / 800 mm | 0,000305 rad |

En 430 los tres ángulos del elevador son
`[-1.093248963, 0.455688208, 0.637177289] rad`: sus rotaciones se compensan,
dejando el torso casi vertical. Cambian también su posición. No basta poner
el primer ángulo a cero.

Las muñecas quedan aproximadamente 14–16 cm más altas; el origen izquierdo
pasa de x=749 mm a x=686 mm en 430. **No son centros de almohadilla, altura
de mesa ni distancia de aproximación.** No se hereda el fixture de ENTRY40.

## Alcance y próximos pasos

**VERIFICADO:** cinemática directa del URDF; vertical definida como +Z de
base_link en la postura de cuerpo cero, sin asumir +Z local del torso ni
confundir yaw con inclinación. No es una medición del suelo real.
Ocho pruebas pasan: compensación de ejes, yaw, orden 20D, rechazo de datos
incompletos/no finitos/duplicados, límites, conservación del frame y task.

**PENDIENTE**, en este orden:

1. Revisar RGB de 438 y 430 y reconstruir soporte/visibilidad/colocación de
   caja. Priorizar 430 para torso vertical y comparar 438 como menor cambio.
   No se decodificaron esos vídeos ni se reauditó cada parquet en este turno;
   la fuente numérica es el reporte archivado con hash verificado.
2. Revisar acceso y recuperación con las abrazaderas actuales, geometría
   completa, estabilidad y ejecución. Menor cambio articular no demuestra un
   recorrido mejor. HOME/PICO H01/H02 no cubren estas ENTRY ni resuelven H03.
3. Versionar un contrato nuevo ENTRY/fixture y sus gates para el mismo frame.
   Se conserva intacto ENTRY40; este ranking no genera XML ni comandos.
4. Completar cinco shadow frescos P14 con RGB+20D exactos, desde postura y
   escena medidas; después continuar E6.2. La diferencia action−state de la
   tabla pertenece al dataset, **no es una predicción nueva del checkpoint**.

Shadow permanece **0/5**; tareas físicas VLA **0/4**. No se consultó el robot,
arrancó inferencia, modificó checkpoint, servicio, perfil, contenedor o XML.
No se infiere su postura actual del plan histórico.

## Reproducción y reversión

Desde la raíz, con Python 3, NumPy y PyYAML ya disponibles:

```bash
python3 scripts/vla/rank_vla_entry_postures.py \
  --dataset-report ../Humanoide-vla-evidence/20260904T094803_E6.0Z/dataset-entry-states.json \
  --entry-contract scripts/vla/runtime/cruzr_s2_vla_task0_entry_e6_1a.json \
  --urdf cruzr_s2_description_splint/cruzr_s2_description/urdf/cruzr_s2_v1/cruzr_s2_v1.urdf \
  --output-dir /tmp/vla-entry-review-new

python3 -m unittest discover -s scripts/vla -p test_rank_vla_entry_postures.py -v
```

La salida debe ser un directorio nuevo. No requiere instalación en el robot.
Evidencia, backups previos, fuentes finales y hashes:
`../Humanoide-vla-evidence/20260911T103734Z_VLA-ENTRY-UPRIGHT/`.
Resultado: `analysis/entry-postures.json`. Ficha **VLA-01**.
Reversión local: retirar comparador/test nuevos y deshacer sólo las ediciones
documentales de este turno con `before/`, preservando trabajo ajeno.
