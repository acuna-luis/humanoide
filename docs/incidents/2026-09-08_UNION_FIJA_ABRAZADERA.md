# Alcance de unión fija y solapamiento de muñeca

2026-09-08. Solicitud: corregir envolvente cerca de la fijación, manteniendo
comprobaciones frente a partes móviles. Revisión offline, sin robot.

VERIFICADO URDF: sixforce está unido por fixed a wrist_roll. wrist_roll se une
a wrist_pitch mediante revolute. Por tanto sólo sensor/wrist_roll pertenecen
al conjunto rígido del montaje. El registro geométrico y las superficies de
contacto siguen ausentes en config/clamp_mount_requalification.json.

Se añadió attachment_topology a scripts/clamp_work_model.py, derivado de
conectividad fixed, sin nombres heurísticos. No atraviesa revolute/prismatic.
Declara explícitamente que conectividad rígida NO permite contacto; regiones
permitidas vacías y envelope_cut_applied=false. No cambia geometría ni filtros
existentes; evita interpretar muñeca completa como fijación estática.

Los dos testigos históricos más desfavorables del informe
20260907_clamp_pessimistic_path_201.json son L/R_wrist_pitch_link, NO wrist_roll.
El recorte de una unión fija no resuelve esos testigos. La esfera no prueba
colisión física, pero no se puede borrar su intersección con una parte móvil
alegando que es la superficie de montaje. Propuesta PICO→HOME continúa sin
validación geométrica; no se recalcula como PASS ni se genera XML ejecutable.

Dos tests de topología y tres tests existentes del modelo pasan. Pendiente
registro de forma/orientación real para reemplazar esfera por envolvente
orientada y acotar superficie fija. No exige CAD completo ni repetir medidas
escalares ya disponibles. Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260908T092429Z_ATTACHMENT-SCOPE/scope.json`.
