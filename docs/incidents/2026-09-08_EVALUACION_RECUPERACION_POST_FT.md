# Evaluación de recuperación post-FT desde postura PICO

2026-09-08. Usuario autoriza «haz todo lo necesario» para recuperar HOME.
Se conserva confirmación física de caja retirada, abrazaderas vacías, estabilidad,
no contacto, zona libre y mandos detenidos. No se pide repetir esa confirmación.

VERIFICADO por nuevas lecturas: actuadores 20D sanos, inmóviles, delta consigna
máximo 0,001900 rad, posición máxima 1,660630 rad; NO HOME. Diferencia máxima
brazos respecto READY 0,783134774 rad, hombro pitch izquierdo. La tarea PICO
cancelada previamente no convierte la postura en READY. No hay fallo de servo
que justifique rearme como solución a la geometría de retirada.

Rutas instaladas releídas: cruzr/home envía cinco grupos concurrentes a cero
en 6 s; no contiene retirada previa. move_dual_arms_home_ompl solicita 14 ceros,
5 s, RrtConnect, nube PreviousMulti y planificación dinámica desactivada.
La revisión previa de interfaces no demostró plan-only ni representación real
registrada de las abrazaderas. Invocarlo no es diagnóstico: puede mover.

PENDIENTE/BLOQUEANTE: trayectoria desde postura actual con geometría real y
recorrido comprobable. No se reemplaza por interpolación directa, objetivos
inventados, exclusión de colisiones o reinicio que pueda disparar HOME interno.
Para completar físicamente se necesita recuperación presencial cualificada o
un procedimiento del proveedor aplicable a esta postura/protección y montaje.
Esto es limitación técnica de recuperación, no falta de autorización del dueño.
No se solicitó otra aprobación ni se envió movimiento/rearme/reinicio.
No cambios remotos persistentes. Robot permanece en postura PICO detenida;
sin vigilancia continua. No apagar como método improvisado de descenso.

Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260908T075121Z_POST-FT-RECOVERY-ASSESSMENT/` (estados, rutas y comparación por articulación).
