# Prioridad: HOME→READY y READY→HOME, VLA fuera de alcance

## 07-09: READY final inalterable — condición necesaria del destino

Por petición explícita del propietario, la variante de cabeza fija anterior
queda DESCARTADA para esta solicitud: cambia el estado final de READY. No se
borra su evidencia histórica. No se modificaron tareas operativas ni READY.

audit_ready_endpoint.py lee objetivos de cabeza/cintura del XML local y brazos
del último punto del YAML forward histórico. Añade require_same_endpoint para
rechazar cualquier cambio numérico del destino, incluida cabeza fija. Es una
comprobación offline, no un nuevo gate instalado en Motion. Los ejes restantes
se declaran cero sintético; la equivalencia con configuración instalada sigue
sin demostrarse.

VERIFICADO en modelo: se evaluó cabeza–torso en READY completo, con sus brazos
finales y las dos hipótesis de orden de cabeza. Ambas distancias STL son cero.
Para los dos triángulos testigo de cada hipótesis, un cálculo independiente
por sistema lineal 3×3 encuentra dos cruces arista–cara. Se guardan coordenadas,
parámetros baricéntricos y residuos; no es sólo una alerta AABB ni depender del
mismo kernel de distancias. Evidencia 20260907_ready_endpoint_locked.json.

Consecuencia lógica condicionada al modelo: todo camino con ese destino lo
contiene, por lo que cambiar únicamente tramos intermedios no puede convertirlo
en un recorrido sin intersecciones del modelo. No demuestra contacto físico
ni imposibilidad del robot real. Para resolverlo hay que contrastar superficies
del cuello, sus referencias y el estado real; no desplazar/recortar mallas ni
excluir pares para forzar aprobación. Permanecen pendientes los útiles reales,
escena, seguimiento y frenado. El permiso de modificación no aporta esa evidencia.

Cuatro tests pasan: identidad del destino, rechazo de cambios por grupo,
rechazo de cabeza fija y cruce/separación con cálculo independiente. Cero red,
comandos o despliegue. Siguiente trabajo útil: validar correspondencia del modelo
del cuello y referencias de montaje, no buscar rodeos para un extremo inconcluso.

## 07-09: refinamiento y variante de cabeza fija — INFERENCIA condicionada

refine_home_ready_witnesses.py verifica hashes del barrido anterior antes de
reconstruir cada testigo. Refinados los 48 pares AABB contra superficies STL:
36 distancias positivas en SU testigo y 12 intersecciones numéricas. No son
mínimos de toda la ruta. Seis ceros pertenecen a la pinza PGC histórica, no a
las abrazaderas instaladas; los otros seis corresponden a uniones adyacentes
bilaterales shoulder_pitch–shoulder_roll, elbow_yaw–wrist_pitch y
wrist_pitch–wrist_roll, ya presentes en cero sintético. No se excluye ninguno
como contacto permitido ni se atribuyen esos ceros a colisiones físicas.

Barrido adicional cabeza–torso: 27 ángulos por cada hipótesis (pitch/yaw),
0→−0,65 rad. En cero, separación superficial 0,199710 mm; las otras 26 muestras
por eje intersectan numéricamente, incluida −0,025 rad. Hallazgo del modelo,
no diagnóstico del robot: pueden intervenir superficies de montaje/modelado.
No es margen físico aceptado, ni justifica ignorar el cuello como adyacencia.

Se genera dentro del informe una variante explícita
SYNTHETIC_ARMS_READY_HEAD_HOLD_NOT_FULL_READY: siete waypoints con cabeza
pitch/yaw cero constante y los puntos de brazos originales en ida/vuelta.
No equivale a READY completo (cambia orientación de cámara), no tiene tiempos,
no es ejecutable ni ha sido desplegada. Evita recorrer el giro de cabeza que
mostró intersecciones, pero conserva la separación inicial insuficientemente
caracterizada y TODOS los pendientes de brazos/útiles/escena. No se afirma
que esta variante esté validada globalmente ni se ordena llevar cabeza a cero.

Evidencia externa: 20260907_full_home_ready_mesh_witnesses_v2.json; incluye
estados completos de testigos, triángulos, pruebas del kernel y candidato.
Tres tests nuevos pasan (reconstrucción, rechazo de calendario desconocido,
reversibilidad/cabeza fija/no autorización del candidato). Sin cambios de XML,
YAML operativo, límites, exclusiones de colisión, robot o PC de control.

Punto de reanudación: no resolver solapamientos iniciales de montaje mediante
rodeos ficticios. Antes de aprobar una ruta se necesita correspondencia de
mallas/útil físico y cobertura del barrido/seguimiento/parada. La autorización
para modificar ruta permite variantes offline, no convertir incertidumbres
en garantías. No se necesitan más fotos genéricas de abrazaderas.

## 07-09: revisión geométrica independiente de la velocidad — OBSERVADO offline

Se amplió el diagnóstico al recorrido sintético HOME→staging→A→READY→A→staging→HOME.
El YAML forward conservado del 03-09 y el recovery local coinciden en A y staging;
esto verifica reversión de puntos, no la trayectoria/control reales ni instalación actual.
audit_home_ready_full_screen.py ensaya 1.836 estados: seis segmentos, 51 muestras,
tres calendarios de brazos (simultáneos/izquierdo primero/derecho primero) y dos
hipótesis del orden de cabeza (-0,65 en pitch o yaw). Los demás ejes se fijan
explícitamente a cero sintético, incluida cintura: no es captura del robot.

828 pares de geometrías, sin eliminar adyacencias: 780 tienen separación AABB
positiva en las muestras; 48 presentan solapamiento y quedan INCONCLUSOS, incluido
head_pitch_link–torso_link. Ni separación entre muestras ni colisión física se
deducen de estos resultados. Se conservaron geometrías PGC/dedos del URDF histórico:
no representan las abrazaderas actuales. shoulder_pitch usa visual provisional.
Faltan geometrías collision en head_base, head_yaw y ambas arm_base; falta determinar
si están cubiertas físicamente por otras mallas, sin inventar volúmenes.

Evidencia externa válida: 20260907_full_home_ready_screen_v2.json, hashes incluidos.
La primera salida sin sufijo v2 quedó incompleta por serialización de entero NumPy;
no usarla. Corregido convirtiendo a int y serializando antes de abrir la salida.
Tres tests pasan (reversión de puntos, índices staging y rechazo de dimensiones).
Los XML de cabeza/cintura se contrastaron por lectura; las hipótesis de este auditor
no se sincronizan automáticamente con cambios futuros de esos XML.

PENDIENTE: refinar los solapamientos sobre mallas, barrido continuo con incertidumbre,
geometría real de útiles/escena y correspondencia de estado/control. Este diagnóstico
no sustituye esos controles ni los de velocidad, seguimiento y frenado. Cero conexiones,
publicaciones, movimientos o cambios de tareas. No aprobación física.

## Hallazgo determinista local

Los XML locales s2_vla_e6_0_ready_s2.xml y s2_vla_e6_0_exact_recovery.xml
contienen etapas de brazos a 1,5 s. En HOME numérico→staging y staging→HOME
hay desplazamiento máximo 0,6 rad por brazo. Por integral de velocidad,
max|v| >= |delta q|/T = 0,40 rad/s. No satisfacen el límite provisional
0,15 rad/s si duration es tiempo real de terminación. No se ha demostrado
reescalado interno del proveedor ni equivalencia con configuración instalada.

El candidato quíntico offline de brazos sí usa 7,500008 s en ese tramo, pero
no sustituye al XML ni demuestra que MetaMove reproduzca la ley. No se cambió
ninguna duración operativa ni se desplegó una tarea.

## Dos recorridos, dos validaciones

| Elemento | HOME→READY | READY→HOME |
|---|---|---|
| Apertura/cierre local 1,5 s | Incompatible con 0,15 rad/s bajo semántica temporal indicada | Igual |
| Trayectoria completa | Incluye cabeza/cintura y MetaMove nombrado clamp_s2_joints_trajectory | Incluye YAML de retorno y cabeza/cintura/brazos |
| Candidato lento brazos | Sólo cálculo offline | Sólo cálculo offline |
| Geometría completa con útil | Pendiente | Pendiente |
| Ley/control/parada reales | Pendiente | Pendiente |
| Autorización física derivada | Ninguna | Ninguna |

READY no es únicamente abrir hombros: el análisis de SALIDA_MUNECA_FIJA no
cubre todos los movimientos de la tarea. Tampoco valida cabeza, cintura ni
el escalonamiento del Parallel vendor. La parte del YAML de recovery tiene
durations [1,0;1,5] y precisa interpretación/contraste adicional, no reutilizar
como trayectoria lenta. Se conservan sin alterar originales y límites.

## Evidencia y continuación

audit_ready_home_timing.py reproduce las cuatro comprobaciones (L/R, ida/vuelta)
sin conexión. Resultado externo 20260907_ready_home_timing_audit.json con hashes.
Sintaxis shell y git diff --check correctos. Se corrigió ayuda obsoleta de
cruzr_vla_ready_pose.sh: la aprobación histórica no habilita nuevas corridas
tras el incidente. Modos activos siguen bloqueados.

Siguiente trabajo: definir contrato lento completo de ida y retorno, incluido
resto de ejes, y contrastar ley del ejecutor sin confundir publicar menos rápido
con frenar una orden aceptada. Después, geometría/escena/control y preflight.
No conexión, ROS, publicación ni movimiento durante esta auditoría.
