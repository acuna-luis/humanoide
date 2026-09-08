# Reanudación offline — 08-09-2026

## VERIFICADO: contraste P1/P2/P3 cerrado, montaje no resuelto

Se abrió la foto original izquierda `/home/lacuna/Imágenes/1.jpeg` y se
verificó su SHA-256 contra `config/clamp_photo_landmarks.json`. Las referencias
reconocidas por el operador son los índices 0, 1 y 4 (base cero) de los seis
centros ya anotados. No se midió la ilustración generativa ni se reajustó una
homografía usando sólo tres puntos.

Se reconstruyó la asignación de los dos ajustes destacados del informe
externo `20260907_clamp_outer_correspondence_v2.json`: ordenar CAD y píxeles
por atan2 respecto al centroide, invertir según winding y aplicar cyclic_shift,
como hace `scripts/audit_clamp_photo_correspondence.py`.

| Referencia | Píxel original aproximado | CAD XY mm: winding −1 / shift 4 | CAD XY mm: winding +1 / shift 2 |
|---|---|---|---|
| P1 | 580,491; 837,614 | 16,2572; +4,9703 | 16,2572; −4,9703 |
| P2 | 646,737; 837,614 | 16,2572; −4,9703 | 16,2572; +4,9703 |
| P3 | 543,439; 1020,632 | −12,433; +11,594 | −12,433; −11,594 |

Ambas conservan RMS central 0,851952 px y exterior 10,205335 px. Son ajustes
2D, no dos montajes físicos acreditados ni precisión métrica. Las etiquetas
identifican puntos de imagen, pero no asignan identidad CAD independiente:
por eso no aportan una restricción que descarte uno de los dos ajustes.
No volver a pedir reconocer esos mismos tornillos o repetir fotos/cotas.

## VERIFICADO histórico: orden de cabeza ya observado

El run externo `20260904T130344_E6.1C-READY/actual_result.yaml` registra
`head_meta_move_runtime_order_verified: yaw_then_pitch`. Su muestra
`whole-joint-state-after.json` conserva por nombre:

- `head_pitch_joint = −0,6510789706582119 rad`;
- `head_yaw_joint = +0,00019174759848570515 rad`.

Ante XML `−0.0;−0.65`, respalda yaw;pitch para esa ejecución histórica.
Los barridos del 07-09 que ensayan ambos órdenes son estudios de sensibilidad;
no debe presentarse el orden histórico como un dato nunca medido. No se ha
redescubierto hoy el controlador instalado ni se han regenerado esos barridos.
Esto tampoco elimina la discrepancia geométrica cabeza–torso: ambos casos
auditados la mostraban. READY permanece intacto y su ausencia de contacto real
se conserva como premisa del operador, no como validación del modelo.

## Estado y siguiente trabajo

Git estaba limpio, main sincronizada con origin/main al comenzar. Sólo lectura
local, cálculo de correspondencias y documentación: cero conexiones al robot,
movimientos, cambios de modo o despliegues. Estado físico actual desconocido;
el reporte de ayer no se reutiliza como preflight. No hay monitor activo.

PENDIENTE: registro físico del plano/cara del sensor y montaje con incertidumbre,
correspondencia de mallas del cuello y uniones, barrido completo con herramientas
y escena, ejecución/seguimiento/parada. Los dos ajustes 2D no acotan por sí solos
todo el espacio de montajes 3D. No convertirlos en un peor caso exhaustivo.
HOME→READY→HOME sigue sin aprobación. El próximo análisis debe abordar una de
esas dependencias con evidencia nueva, no repetir el ajuste de tornillos.
