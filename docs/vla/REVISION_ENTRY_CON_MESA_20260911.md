# ENTRY frente a la mesa actual: resultado de la revisión

**2026-09-11, Europe/Madrid. Análisis offline y lectura del robot; cero movimientos.**

ENTRY es un objetivo articular fijo. Acercar el chasis a la mesa no cambia
los ángulos ni la inclinación de ENTRY40 (31,196° según FK). Se estudiaron
entradas completas alternativas: episodio430 (0,022°) y438 (4,362°).
Sus RGB originales se decodificaron y los vectores se cotejaron de nuevo
contra los parquets: frame0, task0 y estado/acción coincidentes con E6.0Z.

## Actualización: mesa recolocada por el operador

**OBSERVADO/INFERENCIA, 11-09:** después de «he movido la mesa para centrar
la caja», el detector devolvió `0.085918 0.380019 0.920165 -3.897038`
en cámara. TF completo nuevo, nube de2.518 puntos y RGB VLA960×576 obtenidos
sólo por lectura; la caja se ve completa. Articulaciones inmóviles,
brazos/cuerpo HOME numérico y cabeza pitch−0,430569rad.

Con TF, el origen detectado queda aproximadamente en
`[0.834951, -0.052574, 0.778017] m` en base_link. La desviación lateral
pasa de12,0cm a5,3cm hacia la derecha del robot. No representa una orden de
avance ni una tolerancia verificada del detector.

**Cálculo condicional:** se trasladaron ambos volúmenes originales por el
cambio detectado `[-0.000894, +0.067610, -0.001928] m`, manteniendo sus
extensiones. Esto presupone traslación conjunta de mesa/caja y orientación
constante; no se ha demostrado el registro completo del tablero, patas o
largueros ni una incertidumbre acotada. Las capturas no son simultáneas.
El detector también cambió su ángulo; esa diferencia no se usa para afirmar
que la orientación es idéntica. Los resultados siguientes dependen de esta
aproximación y no certifican la nueva escena.

- Observación→READY: sin avisos OBB, cota mínima muestreada186,6mm.
- READY→430/438: **desaparece el aviso de abrazadera derecha contra caja**.
  Sólo quedan avisos OBB torso/elevador–tablero; al refinarlos las distancias
  muestreadas son37,1/39,2mm para430 y32,8/40,9mm para438.
- La ruta directa observación→ENTRY mantiene avisos de brazos contra mesa/caja.
  Se conserva la propuesta por READY para la siguiente revisión.

No se ha enviado movimiento ni cambiado el contrato ENTRY40. La siguiente
validación debe fijar la escena registrada y la transición completa con
abrazaderas (incluida recuperación), antes de instalar una ENTRY alternativa.
430 sigue siendo el candidato prioritario por torso vertical. Shadow0/5 y
VLA físico0/4. No se requiere volver a medir las dimensiones declaradas del
mismo tablero.

Evidencia posterior separada en `recentered/`, incluidos `obstacles.json`,
`registration-inference.json`, nube, RGB y ambos resultados. Para reproducirla,
prepare otro directorio con `metric-scene.json` y
`candidate-source-verification.json` de `recentered/`; añada al primer analizador
`--obstacles-json RUTA/recentered/obstacles.json`. El segundo lee esos mismos
límites del resultado; ninguno sobrescribe resultados existentes.

## Resultado geométrico anterior: mesa antes de recolocar

Se obtuvo la transformación cámara estéreo→base_link y una nube actual de
2.529 puntos muestreados. La nube es **no organizada**: sus índices no son
píxeles RGB. No se reutilizan como correspondencias de imagen.
El detector anterior transformado sitúa la caja aproximadamente en
`[0.835, -0.120, 0.780] m` respecto a base_link: unos12cm a la derecha del
robot. La muestra del detector y la transformación no son simultáneas;
el cálculo presupone que se mantuvo la escena inmóvil entre las capturas.

Se modelaron dos volúmenes conservadores parciales, informados por nube,
detector, fotografías y cotas previas, en coordenadas base_link:

| Volumen inferido | Mínimos XYZ, m | Máximos XYZ, m |
|---|---|---|
| tablero | `[0.50, -0.61, 0.60]` | `[1.44, 0.31, 0.72]` |
| exterior de caja | `[0.60, -0.45, 0.64]` | `[1.07, 0.21, 0.93]` |

Estos límites incluyen holgura exploratoria; **no son una reconstrucción
certificada ni una escena completa**. No califican patas, largueros de madera,
resto del taller, registro físico de abrazaderas, errores dinámicos o frenado.
La caja se trata como volumen exterior lleno para esta aproximación previa
al agarre. CameraInfo estéreo no entregó muestra; una primera proyección con
intrínsecos archivados y TF redondeado no se usa como registro métrico final.

Se comprobaron201 muestras por segmento, con curvas articulares sincronizadas
entre extremos; esto no acredita el interpolador real de Motion.

| Recorrido candidato | Resultado frente a los dos volúmenes |
|---|---|
| observación→READY | sin avisos OBB; cota mínima muestreada187mm |
| READY→430/438 | avisos de torso/elevador contra tablero y abrazadera derecha contra caja |
| observación→430/438 directa | avisos adicionales de muñeca, sensor y abrazaderas contra tablero |

El refinamiento de los avisos de READY→ENTRY usa61 muestras por intervalo
marcado y las representaciones sólidas del modelo, incluidas sus envolventes
convexas. No se presenta como contacto exacto del hardware:

- Torso/elevador contra tablero: separaciones mínimas **32,6–41,8mm** en las
  muestras refinadas; desaparecen esos avisos preliminares de OBB.
- **Abrazadera derecha contra caja: distancia0 en ambos candidatos** dentro
  de estas envolventes. Persiste un posible solapamiento; no demuestra contacto
  físico, pero impide aceptar el recorrido con esta representación y escena.

No se rebajó ningún margen ni se excluyó la abrazadera para obtener un PASS.
La revisión parcial no revalida los solapamientos internos pendientes del
modelo completo. No se ha aprobado ni enviado READY, ENTRY o VLA.

## Próximo paso señalado antes de recolocar (histórico)

Corregir/verificar la alineación lateral de **mesa y caja respecto al robot**
y recalcular la aproximación por READY. Acercarlo más no corrige los12cm
laterales. Desplazar sólo la caja podría dejarla cerca del borde del tablero;
no se prescribe una corrección física a partir del detector sin verificar el
apoyo completo y el espacio de la base.

Mantener como último estado observado brazos/cuerpo HOME y cabeza−0,43rad.
La entrada erguida sigue siendo un candidato; el contrato operativo ENTRY40
no se cambió. Shadow0/5 y VLA físico0/4.

## Evidencia y reproducción

Fuentes, RGB de candidatos, nube, TF, resultados, backups documentales y hashes:
`../Humanoide-vla-evidence/20260911T114330Z_VLA-ENTRY-SCENE/`.

Los dos analizadores se ejecutan desde la raíz con `.venv/general-home/bin/python`:

```bash
python3 - <<'PY'
from pathlib import Path
import shutil
src = Path('../Humanoide-vla-evidence/20260911T114330Z_VLA-ENTRY-SCENE')
dst = Path('/tmp/vla-entry-fixture-review-new')
dst.mkdir()
for name in ('metric-scene.json', 'candidate-source-verification.json'):
    shutil.copy2(src/name, dst/name)
PY
.venv/general-home/bin/python scripts/vla/analyze_vla_entry_fixture_sweep.py \
  --evidence-dir /tmp/vla-entry-fixture-review-new
.venv/general-home/bin/python scripts/vla/refine_vla_entry_fixture_sweep.py \
  --evidence-dir /tmp/vla-entry-fixture-review-new
```

Son recetas de diagnóstico para estos candidatos y estos volúmenes parciales;
no son planificadores ni ejecutores generales. Rechazan sobrescribir resultados.
Una reproducción con las fuentes versionables coincidió exactamente con ambos
resultados iniciales.

Para decodificar los vídeos y cotejar parquets se creó sólo en el PC
`.venv/vla-scene` con acceso a paquetes del sistema y se añadieron PyAV18.1.0
y PyArrow25.0.1. Reinstalación:

```bash
python3 -m venv --system-site-packages .venv/vla-scene
.venv/vla-scene/bin/pip install -r scripts/vla/scene_decode_requirements.txt
```

No se modificó el SDK, el dataset ni el checkpoint. Ficha VLA-01. Reversión:
retirar este entorno nuevo y las tres fuentes locales añadidas; deshacer sólo
las ediciones documentales de esta intervención usando `before/`, preservando
trabajo previo. No hay restauración remota: no se alteró ningún servicio o
archivo del robot y no se envió movimiento en esta revisión.
