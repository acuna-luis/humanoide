# Prioridad: HOME→READY y READY→HOME, VLA fuera de alcance

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
