# Propuesta offline PICO→HOME para revisión

2026-09-08. Autorizado preparar propuesta antes de ejecutar. Captura sana e
inmóvil clasificada OTHER (ni HOME ni READY); coordenadas ROS20D explícitas.

Generador: scripts/teleoperation/plan_pico_home_offline.py. Sólo lee archivos y
emite JSON no ejecutable; no importa transporte ROS/SSH, no exporta XML ni --run.
Hipótesis: brazos a cero conservando seis ejes del cuerpo, después seis ejes a
cero. NO es búsqueda de camino ni orden demostrado seguro. Curva quintic con
reposo en extremos; v0,15/a0,5 provisionales. Duración total 25.870372 s.

Límites20D URDF pasan en extremos y, por interpolación monótona, entre ellos.
No compara límites instalados actuales ni geometría real de abrazaderas,
colisiones, estabilidad, frenado o equivalencia del interpolador Motion.
No convertir esta propuesta en una orden ni ensayarla como prueba de seguridad.
Tres tests pasan (incluyen reposo/cuerpo conservado, estado inválido y límites).

PENDIENTE: revisión geométrica y presencial cualificada del recorrido y
selección de ejecución verificable. La petición de script que mueva desde PICO
NO está completada; este resultado sólo concreta una hipótesis numérica para
revisión. Sin movimiento ni cambios remotos. No monitor persistente.

Evidencia: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260908T091751.718676Z_PICO-HOME-CHECK/propuesta-home.json` y capturas de origen.
