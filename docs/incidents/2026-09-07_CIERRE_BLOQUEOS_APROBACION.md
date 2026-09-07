# Revisión de bloqueos de aprobación — 07-09-2026

**Resultado: NO APROBADO.** No se ha movido ni modificado el robot. La petición
de resolver bloqueos no se interpreta como permiso para omitirlos o seleccionar
tolerancias a fin de producir PASS.

## Refinamiento de muñeca completado

Se sustituyó la distancia a AABB por distancia a triángulos STL en dos testigos
(uno L y uno R) del informe de 201 muestras/segmento. Ambos corresponden al
tramo staging→A, fracción 0,685 del segmento síncrono, postura sintética histórica.

| Testigo | Distancia centro supuesto–superficie STL | Radio mínimo ensayado | Resultado |
|---|---:|---:|---|
| L → L_wrist_pitch_link | 40,639 mm | 139,411 mm | La esfera alcanza la malla |
| R → R_wrist_pitch_link | 40,652 mm | 139,411 mm | La esfera alcanza la malla |

No son distancias de la **abrazadera real** a la muñeca ni profundidades de
penetración del hardware. Demuestran que reemplazar sólo la caja del brazo por
su malla no elimina estos testigos de solapamiento de la **esfera envolvente**.
No se puede rehabilitar el recorrido con esa aproximación ni aumentando radios.
El resto del recorrido no se volvió a evaluar contra STL en este ensayo.

Se reutilizó el kernel versionado `point_triangle_distances_batch`, con cuatro
casos deterministas y 300 comparaciones aleatorias contra referencia escalar,
todos correctos. Se verificó coincidencia de hashes URDF/ZIP/FK con el informe
origen. Se guardan estado, triángulo testigo y centro en coordenadas locales.
No se realiza prueba de interior de malla para inferir separación a partir de
una distancia positiva: aquí existe testigo de superficie dentro de la esfera.

Analizador: `scripts/audit_clamp_wrist_mesh_witness.py`.
Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260907_clamp_wrist_mesh_witness.json`.

## Qué falta para aprobar, sin confundirlo con tareas de software

| Bloqueo | Estado actual | Evidencia necesaria para cerrarlo |
|---|---|---|
| Dimensiones nominales del conjunto | Recibidas, modelo 82×100×130 mm | No repetir A–F/T |
| Prevención de PASS obsoleto y entradas locales enumeradas | Implementada y probada | Conservar; no equivale a protección instalada |
| Útil frente al cuerpo y brazo contrario | Separación condicional en muestras sintéticas | Geometría/errores fundamentados y barrido continuo del ejecutor real |
| Útil frente a su propio brazo | Inconcluso incluso con STL del brazo | Modelo orientado o conjunto de montajes acotado localmente, suficientemente preciso para resolver esta zona |
| Referencias, tolerancias y mallas faltantes | No verificadas completamente | Verificación física trazable de referencias y límites de error; revisar cobertura de hombros |
| Arranque, rearme, HOME interno | No interceptado por bloqueos del repositorio | Procedimiento o mecanismo soportado y comprobado que impida movimiento automático no validado |
| Interpolación, seguimiento y parada | No caracterizados para la prueba | Ejecutor identificado, ley/temporización y límites respaldados; barrido y parada incluidos |
| Estado/escenario actual y retorno seguro | No comprobados en esta intervención offline | Verificación vigente antes de cualquier prueba física; retorno no puede presumirse seguro |

No es obligatorio conseguir CAD del fabricante: puede sustituirse por evidencia
local competente del montaje y comportamiento. **Sí es obligatorio que los
límites usados estén fundamentados.** Elegir 75 mm porque parece pesimista no
demuestra que toda discrepancia esté dentro de ese valor. La aceptación del
propietario de un supuesto no lo convierte en una medición ni en una garantía.

## Punto de parada

El modelo esférico ya alcanzó su límite para aprobar útil–propio brazo. Repetir
muestreos o subir márgenes no resuelve el problema. El siguiente paso relevante
requiere evidencia del montaje y de un procedimiento de arranque/recuperación
seguro; no otra autorización genérica ni una repetición de las mismas fotos.
No iniciar movimientos de identificación, HOME ni rearme para obtenerla.
La inspección presencial reportada de carcasa se conserva; esta conclusión no
la invalida ni exige repetir la cronología.
