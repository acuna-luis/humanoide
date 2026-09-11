# Decisión de entrada VLA — 11-09-2026

**Resultado: agarre físico NO ejecutado.** Dentro de la intervención limitada
por el operador a15min se completó una comparación offline de las tres
entradas y se concretaron los impedimentos de acceso/escena. No se sustituyó
el VLA por el detector tradicional ni se reutilizaron sus propuestas rechazadas.
Fecha/zona:2026-09-11, Europe/Madrid; inicio12:35:46UTC. FichaVLA-01.

## Qué se comprobó

Checkpoint40000 sin modificar, escenas/estados originales frame0 de episodios
40,430,438, task0 y cinco semillas0–4 por episodio. Se comprobaron hashes de
vídeo/parquet y correspondencia de episodio/task/frame/20D mediante el lector
existente. Son15 inferencias nuevas con RGB y estados del dataset, **no cinco
shadow actuales ni quince agarres**. El contenedor temporal sólo tuvo red
`none`, checkpoint/overlay montados read-only y copias del dataset en un directorio
propio de trabajo, y ninguna importación ROS o transporte de comandos.

| Entrada | Continuidad inicial de brazos | Peor salto inicial, rad | Grados aproximados |
|---|---:|---:|---:|
|40, antigua inclinada|5/5|0,033086|1,90°|
|430, erguida|5/5|0,031726|1,82°|
|438, casi erguida|5/5|0,032916|1,89°|

La comprobación de esta tabla es delta inicial de los14 brazos contra0,1rad
por eje. Los JSON conservan además predicción10×20, errores frente al dataset
y avisos de rango/otros ejes. No es aprobación de trayectoria completa,
seguimiento, contacto, agarre o recuperación. No demuestra generalización a
la imagen azul actual. Las5 pruebas shadow calificadas continúan0/5.

## Geometría y altura

Se compararon los tres extremos con el modelo splint completo, conservando
982 pares,45 formas y el criterio del planificador2mm+1nm. **54 avisos** en
HOME y en cada entrada, sin pares adicionales respecto a HOME. Son problemas
de representación/interfaz, no54contactos reales. No se excluyó ninguno ni se
declaró un extremo validado. La primera salida diagnóstica con `<2mm` daba50;
queda sustituida por `candidate-self-geometry-canonical-margin.json`, que usa
el mismo límite que el planificador y conserva los4 casos del umbral.

El ejecutor E6.1C antiguo sigue retirado expresamente:
`BLOCKED_RETIRED_UNREGISTERED_CLAMP_GEOMETRY`, salida78 antes de movimiento.
Por tanto no existe una ruta lista que se pueda ejecutar cambiando sólo el
nombre de ENTRY. La comparación anterior frente a dos cuboides parciales no
resuelve este control ni el recorrido real y su recuperación.

Nueva estimación fotográfica exploratoria para430/438:

| Episodio | Altura de soporte estimada | Variación debida sólo a±4píxeles |
|---|---:|---:|
|430|89,6cm|88,4–90,8cm|
|438|90,4cm|89,3–91,4cm|

**INFERENCIA, no calibración:** presupone caja de603mm de ancho/217mm de alto,
suelo150mm bajo base_link, intrínsecos archivados y montaje de cámara derivado
de TF actual+URDF. La incertidumbre total de esas premisas no está acotada;
los intervalos de la tabla no son tolerancias físicas aceptadas. No prescribe
subir la mesa ni invalida definitivamente80cm. Sí impide afirmar que elegir
una entrada erguida haya demostrado compatibilidad con la mesa actual.
ENTRY40 conserva su referencia histórica cercana a77cm; no se modificó.

## Cambio y reproducción

Tres herramientas nuevas sólo en PC, sin nuevas dependencias:

- `scripts/vla/evaluate_vla_entry_candidates.py`: prepara los tres episodios
  y evalúa cinco semillas con el checkpoint en contenedor aislado.
- `scripts/vla/audit_vla_entry_candidate_geometry.py`: revisa extremos completos
  sin excluir pares ni generar aprobación física.
- `scripts/vla/estimate_vla_entry_support_height.py`: reproduce la estimación
  fotográfica con todas las premisas y hashes de sus entradas.

El evaluador reutiliza `evaluate_checkpoint_offline.py` y el perfil P14 sin
cambios. Cinco tests existentes del lector/evaluador pasan. La ejecución real
completó las15 inferencias, guardó estados/acciones finitos y mantuvo
`physical_approval=false`. Las herramientas geométricas usan las dependencias
existentes de `.venv/general-home`; la comparación no alteró el URDF/SDK.

Desde la raíz del repositorio, preparación en un directorio nuevo:

```bash
python3 scripts/vla/evaluate_vla_entry_candidates.py prepare \
  --dataset cruzrss2_vla_pack-002/data/utars_clamp_and_place_large_box_full_data_bio_lerobot_0319 \
  --output-dir /tmp/vla-entry-review-new/inputs
```

Copiar esa carpeta, ambos evaluadores y el perfil P14 a un directorio temporal
nuevo en Vision. La invocación reproducible dentro de la imagen NVIDIA
`vla_inference_node_sdk:latest`, **con `--network none`**, es:

```bash
python3 /offline/evaluate_vla_entry_candidates.py infer \
  --input-dir /offline/inputs --output-dir /offline/results \
  --checkpoint /home/ubt/additional/checkpoint-40000 \
  --profile /offline/profile.json \
  --override-parent /home/ubt/additional/safe-runtime/vendor-overrides
```

Montar `/home/walker/cruzr-vla/additional` como `/home/ubt/additional:ro` y
sólo el directorio temporal propio como `/offline:rw`. No montar `/dev/shm`
del host ni arrancar los contenedores persistentes VLA. La orden Docker exacta
usada, fuentes, inputs,15resultados, receta geométrica y hashes están en:
`../Humanoide-vla-evidence/20260911T123920Z_VLA-ENTRY-CANDIDATE-DECISION/`.

Temporal utilizado:
`/tmp/cruzr-vla-entry-offline.6HO18F4m`, contenedor
`cruzr-vla-entry-offline-1239`, network=none, exit0. Tras archivar resultados,
se retiraron contenedor y su directorio completo. Persistentes VLA no arrancados.
Rollback local: retirar sólo estas tres fuentes nuevas y sus referencias
documentales, usando `before/` para preservar todos los cambios anteriores.
No hay configuración remota persistente nueva que restaurar en esta intervención.

## Punto de reanudación

Resolver una transición con representación de abrazaderas aceptada y una
escena compatible con la entrada seleccionada. Después medir esa entrada,
realizar shadow actual y validar progresivamente el mando físico. No se pide
otra autorización genérica: la petición del propietario permanece vigente.
El plazo y la buena continuidad sobre el dataset no permiten convertir una
validación parcial en aprobación del agarre real.
