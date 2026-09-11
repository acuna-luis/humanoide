# Preparación de recuperación sin teleoperación

**11-09-2026 — Preparador implementado y probado; ejecución general pendiente.**
El operador indicó que la teleoperación ya no está disponible. Volver manualmente
a PICO deja de ser el punto de reanudación. La recuperación debe partir de los
veinte ángulos actuales y conservar la asimetría hasta encontrar un camino válido.

Disponible: [`cruzr_prepare_recovery.py`](../../scripts/teleoperation/cruzr_prepare_recovery.py).
No depende de PICO ni pide colocar primero el robot en una referencia. **Es un
preparador, no un ejecutor:** no admite `--run` ni publica objetivos, instala
tareas, reinicia o modifica modos/protecciones. Todavía no resuelve físicamente
el retorno desde H03. No se presenta una negativa a ejecutar como recuperación
completada.

## Un comando para leer y preparar

Con abrazaderas vacías comprobadas por el operador, desde la raíz del repo:

```bash
.venv/general-home/bin/python scripts/teleoperation/cruzr_prepare_recovery.py \
  --check --empty-clamps \
  --output-dir ../Humanoide-vla-evidence/recuperacion-actual-01
```

Usar un directorio nuevo en cada intento. El parámetro `--empty-clamps` registra
una comprobación física; no la deduce de una imagen. Añadir `--scene /ruta/escena.json`
para proporcionar el entorno en el formato del [planificador](../../scripts/teleoperation/general_home/README.md).
Sin escena, el análisis usa una escena vacía explícitamente sintética **sólo
para autocolisiones**; no acredita espacio libre alrededor del robot.

1. Descubre contenedores y registra cinco segundos de actuadores y ambos paros.
2. Comprueba calidad del flujo, marcas progresivas, salud, inmovilidad durante
   la captura, consignas pendientes y ausencia de paros/transiciones.
3. Consulta publicadores de órdenes, estado de acciones y bloqueo del módulo.
4. Lee dos muestras nuevas de `/mc/whole_joint_states`, exige marcas progresivas
   e inmovilidad y conserva los veinte ángulos en sus coordenadas articulares.
5. Entrega ese estado al planificador completo. Éste evalúa límites/geometría
   antes de caminos directos, corredores abiertos, pasos por brazo y búsqueda.
6. Archiva estado, escena, captura, lecturas, plan, resultados, fuentes y hashes.

Código2: captura/control/formato no demostrados. Código3: preparación terminada
con rechazo del modelo o candidato todavía no ejecutable. Incluso un candidato
geométrico conserva `physical_approval=false`, `installable=false`; el informe
no autoriza enviar posiciones al robot. Ningún resultado llama a HOME de forma
automática ni cambia el estado para conseguir que pase una comprobación.

## Resultado real en H03

Evidencia:
`../Humanoide-vla-evidence/20260911T092355Z_RECOVERY-FROM-CURRENT/`.
La versión corregida, carpeta `live-canonical`, recibió101muestras válidas,
paros0/0, articulaciones inmóviles y sin fallos, ningún publicador de órdenes,
ninguna acción activa y módulo libre. Conserva el codo derecho en−1,25959rad,
entre los veinte valores reales. El plan termina `START_GEOMETRY_REJECTED`
con54avisos de interfaces/geometría; **no son54contactos físicos demostrados**.
No se envió ningún movimiento, no hubo mutaciones remotas y no se amplió la
tolerancia del ejecutor PICO para aceptar esta postura.

El primer prototipo, archivado en `live`, utilizaba por error posiciones de
actuadores como posiciones del URDF. El motor del codo derecho entrega signo
positivo donde JointState entrega signo negativo; otros ejes también difieren.
Eso produjo un falso `START_OUTSIDE_LIMITS`. **DESCARTADO como diagnóstico del
robot.** Se corrigió antes de cualquier movimiento: no se infiere una tabla
de signos, se exige el JointState canónico. La captura de motores sigue siendo
útil para salud, velocidad absoluta y error absoluto frente a su propia consigna;
no debe usarse para FK sin una transformación de coordenadas verificada.

Diez pruebas sintéticas pasan, incluyendo inversión de signos motores respecto
a JointState, conservación de asimetría, datos duplicados/antiguos/incompletos,
deriva con velocidad reportada cero, fallos, consignas pendientes, mando activo,
paro y rechazo de una opción `--run` inexistente:

```bash
.venv/general-home/bin/python -m unittest discover \
  -s scripts/teleoperation -p test_prepare_recovery.py -v
```

## Lo que sigue faltando para ejecutar

El cuello de botella sigue siendo un modelo de colisión apto para comprobar
las interfaces del robot, con el registro de abrazaderas y margen aplicable,
y el adaptador de ejecución con seguimiento/parada acotados para trayectorias
nuevas. No basta abrir los hombros, aceptar sólo los pares que salen bien o
declarar una postura intermedia segura por su nombre. Los ensayos H01/H02
acreditan sus recorridos concretos, no la salida de esta postura asimétrica.

El comportamiento previsto para el futuro ejecutor será: medir; seleccionar
un paso intermedio cuya trayectoria y zona de parada estén comprobadas;
ejecutarlo una sola vez; medir de nuevo; continuar hasta HOME o detenerse si
no encuentra una salida demostrada. No se conecta todavía esa ejecución.
No se propone teleoperación, apagado/reinicio o HOME interno como alternativa
automática para saltar el mismo recorrido no resuelto.

Dependencias: venv general-home existente; sin instalaciones nuevas. Cambios
del PC registrados en ANL-01. Backups documentales `before/`, fuentes finales
`after/` y SHA256 en la evidencia anterior. Reversión: retirar selectivamente el
preparador/pruebas nuevos y restaurar las notas correspondientes, preservando
trabajo anterior y posterior. Ningún rollback remoto ni movimiento requerido.
