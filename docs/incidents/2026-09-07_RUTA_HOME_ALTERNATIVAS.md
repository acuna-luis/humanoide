# Ruta HOME: alternativa localizada, ejecución no aprobada

## Petición de resolución con peor caso, sin soporte

Se contrastaron los artefactos orientation_bound y wrist_mesh_witness existentes.
Con centro hipotético en sixforce y todas las orientaciones incluidas, la
envolvente nominal ya tiene radio 119,411 mm; el testigo izquierdo de muñeca
está a 40,639 mm. Diferencia nominal −78,772 mm, antes de añadir incertidumbre.
Es solapamiento del modelo, no penetración física medida. Añadir reservas no
puede convertir este resultado en separación. Los errores de centro previos
10–75 mm eran sensibilidad, no cotas físicas demostradas.

Si la caja descriptiva contiene el origen y se consideran todas sus rotaciones
alrededor de él, su unión es la bola de radio del vértice más lejano: todo radio
hasta ese vértice está dentro de la caja y puede rotarse en cualquier dirección.
Por tanto la esfera no pierde precisión respecto a ESA familia de cajas; la
imprecisión está en admitir giros/formas que el montaje real quizá no permite.
No se ha probado que todos esos giros sean físicamente montables.

Conclusión: peor caso amplio no aprobable con esta evidencia. Para una
validación robusta útil hay que restringir la familia a montajes físicamente
compatibles, o medir su registro por una referencia identificable. No basta
elegir el giro que pasa ni excluir la muñeca. Se puede continuar localmente
sin fabricante, pero no afirmar solución completa/ausencia de colisiones con
las fotografías actuales. El problema independiente de HOME interno tampoco
desaparece por ampliar la geometría. Sin movimientos ni cambios remotos.

## Revisión de las referencias ya aportadas

Revisados de nuevo la foto izquierda local 1.jpeg, cotas A=95/T=130 y el
informe outer_correspondence_v2. No se identifica una cota escalar adicional
que por sí sola cierre el montaje. Se corrige la expectativa de «una única
medida»: falta correspondencia de referencias físicas con el modelo, no el
tamaño general de la abrazadera.

- A identifica distancia al eje, no dónde está el origen URDF a lo largo de él.
- B/C identifican el plano de unión descriptivo, no prueban qué plano del STL
  corresponde a esa unión ni el signo de su normal.
- Patitas interiores identifican orientación respecto al robot en la foto,
  no los ejes locales del sensor para cualquier postura.
- El ajuste de fijaciones exteriores conserva ambigüedad de correspondencia;
  no justifica escoger R/t por menor error de imagen.

No repetir A–F/T ni fotos genéricas ni solicitar acceso/desmontaje inseguro.
La información mínima externa útil es un croquis de referencia del sensor
sixforce_link: origen y ejes sobre una vista física identificable, cara de
salida donde se fija el útil y su distancia al origen. No requiere CAD completo
de la abrazadera. Si esa identificación no está disponible, requiere registro
geométrico cualificado; aquí no se puede reemplazar por una orientación asumida.
No cambia el contrato ni concede aprobación. Inspección documental/local, sin red.

## Candidato v2 — límites articulares de posición

Se añade --urdf obligatorio al generador offline. Comprueba nombres explícitos,
límites revolute finitos/ordenados y extremos de las tres etapas para 14 ejes.
No trata límites ausentes como infinito; rechaza con código 3. Al ser
`s'(u)=30u²(1-u)²>=0`, cada posición queda dentro de sus extremos durante toda
la curva: **comprobación continua de rango articular, no de colisión**.

Resultado con vendor_cruzr_s2_v1.urdf preservado: URDF_POSITION_BOUNDS_PASS_ONLY,
sin infracciones ni límites ausentes. Evidencia externa
20260907_home_offline_candidate_v2.json incluye hash URDF. Seis tests pasan.
No confundir estos límites con los activos de Motion, no leídos en este paso.

La ruta geométrica no ha cambiado. Persiste solapamiento del modelo esférico
con muñeca propia documentado previamente; no se resuelve ralentizando ni
eliminando ese par. No procede declarar un plan libre de colisiones con esa
aproximación. Falta modelo relativo útil–muñeca suficientemente acotado, además
de postura/entorno y protección de arranque. Sin conexiones ni cambios remotos.

## Generación temporal offline implementada

`scripts/build_home_offline_candidate.py` no depende de ROS, SSH, SDK ni
controladores. Lee contrato histórico local y emite exclusivamente JSON nuevo,
sin sobrescribir evidencias. No produce tarea XML ni comandos ejecutables.

Retorno histórico de brazos READY B→A→staging→cero sintético. No usa las
duraciones antiguas. Para cada desplazamiento máximo d y límites provisionales
v=0,15 rad/s, a=0,5 rad/s²:

`q=q0+(q1-q0)*(10u³-15u⁴+6u⁵)`, `u=t/T`.

Máximos analíticos: velocidad `1,875*d/T`; aceleración
`(10/sqrt(3))*d/T²`. Se selecciona T que satisface ambos, con pequeña reserva
numérica (no margen físico). Velocidad/aceleración cero en ambos extremos;
cada waypoint se alcanza en reposo. No garantiza límite de jerk.

| Segmento | Duración calculada |
|---|---:|
| READY B→A | 4,644505 s |
| A→staging | 23,244523 s |
| staging→cero de brazos | 7,500008 s |
| Total | 35,389035 s |

Cinco tests: extremos/derivadas, máximos analíticos, desplazamiento cero,
rechazo de entradas inválidas/overflow y salida no ejecutable. Integrados en
suite offline. Evidencia externa `20260907_home_offline_timing_candidate.json`
incluye hashes del contrato histórico y generador.

**Alcance estricto:** temporización, no búsqueda de camino ni prueba de
colisiones. Otros ejes sin especificar, nunca rellenados a cero. No postura
actual ni escena, no límites de posición verificados. No equivalencia con el
interpolador vendor: copiar tiempos a MetaMove no demuestra cumplimiento.
Las tres etapas conservan el camino geométrico histórico y por tanto sus
pendientes de colisión; ralentizarlo no los resuelve. Continúa physical_authorized=false.

## Continuación — búsqueda de interfaz plan-only

**VERIFICADO, 07-09:** ampliada la búsqueda más allá de la profundidad inicial.
Las definiciones ROSA están en share/<paquete>/idls/<paquete>/action y srv.
Se leyeron archivos, no se invocaron servicios ni acciones.

| Interfaz examinada | Datos expuestos | Resultado |
|---|---|---|
| ArmTask.action | Goal task_name/yaml_args; resultado NodeState; feedback estado y tiempos | No expone trayectoria previa ni campo plan_only tipado. yaml_args libre no demuestra que admita dry-run |
| GetMnpActionList.srv + MnpActionInfo.msg | Filtro y catálogo: id, nombre, duración, archivo, disponibilidad/modelo | No devuelve puntos articulares ni validación geométrica |
| PickPlanner.action | Query/dimensiones → punto, pose de objeto, pick_offset | No es plan articular de retorno HOME |
| WalkPlanner.action | Query → punto 3D | No es plan articular HOME |

La búsqueda de archivos *plan*.srv/action y *trajectory*.srv/action en
/opt/walker de este contenedor encontró únicamente esos dos planners de visión.
La búsqueda de plan_only/dry_run/trajectory/planning en .srv/.action de
mc_task_msgs y mc_internal_msgs no encontró coincidencias. Es alcance de
archivos instalados; no prueba ausencia de APIs ocultas ni de otro contenedor.

SDK local: headers skill.h/work.h del archivo
SDK/c++/ubt_api_tiny_colcon.0624.tar.xz permiten launch, estado/resultado,
pause/resume/stop; no declaran un método de exportación de plan previo.
Leídos mediante tar a stdout, sin extracción ni modificación del SDK.
Tampoco se ejecutaron ejemplos, bibliotecas ni clientes SDK.

Conclusión: **no existe evidencia suficiente para usar la ruta vendor como
plan-only**. La alternativa OMPL instalada no queda aprobada por su nombre.
No enviar goal y cancelarlo luego, ni usar E-stop como sustituto de un modo
sin ejecución. Para independizar planificación se necesita una implementación
local desconectada del controlador o una interfaz vendor documentada. Ninguna
elimina los pendientes de geometría, equivalencia de ejecución e intercepción
de HOME interno. No se afirma haber resuelto la ruta física.

Hashes de definiciones mc_task_msgs leídas:

- ArmTask.action: 64ecf688b57d21ed5415721522f8d85f3a2981e31e43479c3fa7460e64351150
- GetMnpActionList.srv: c9f01714f8aa4b479eb66796b45d762f7f96054fc7983cf5c66834aa64d97fa6
- MnpActionInfo.msg: 78525cc573447d9009966b357364b18e664db568aecc7ff104323e3ebcb3544e

Sin cambios remotos, movimiento ni rearme. Estado físico no verificado.

## Resultado del 07-09 — VERIFICADO por lectura conectada

Redescubiertos Motion y walker-motion.manipulation_robot_app-1. Lectura de
XML/YAML con docker exec y utilidades de lectura. Sin ROS, movimiento,
reinicios, modificaciones remotas ni sustitución de tareas.

| Ruta | Definición instalada | Decisión |
|---|---|---|
| cruzr/home | Cinco MetaMove concurrentes a cero, 6 s | No reutilizar desde postura arbitraria; sin retirada previa explícita |
| cruzr/open_arm_before_home | Brazos, elevador y cintura concurrentes 3 s; después cinco grupos a cero en 2 s | No es una retirada cartesiana validada |
| move_dual_arms_home_ompl | MetaMove cuyo YAML solicita OMPL; 14 objetivos cero, 5 s | Candidato de planificación, NO ejecutar |
| move_waist_arms_home_planning | 16 objetivos; comentario waist(2)+brazos(14) | No reutilizar sin adaptación: descripción Cruzr examinada tiene cintura de un eje |
| move_base_waist_arms_home_planning | 22 objetivos; base(6)+waist(2)+brazos(14) | No reutilizar para esta unidad ni implicar chasis en recuperación |

OMPL de brazos solicita state_space=0, planner_type=0 (comentario RrtConnect),
planning_time=5, simplifying_time=1, self_collision_tolerance=0.02,
env_collision_tolerance=0.02, goal_reached_tolerance=0.03,
n_interpolation=10 y enable_dynamic_planner=false. Parámetros literales, no
garantías de holgura real ni evidencia de barrido continuo. Duración 5 s no
demuestra cumplimiento de 0,15 rad/s y 0,5 rad/s². source_type=1 está comentado
PreviousMulti: no asumir entorno actualizado.

La descripción cruzr_s2_robot_description.yaml declara model=clamp bilateral,
X_ParentBase de manos [0,0.089,+0.094] y [0,0.089,-0.094]. Es configuración
vendor, no montaje físico verificado ni volumen de patitas/soporte. No convertir
directamente a sensor–útil sin contrastar referencias y convenciones. Un archivo
instalado tampoco prueba qué configuración está activa en memoria.

El paquete manipulation_planners contiene bibliotecas/configuraciones. En la
búsqueda acotada no se localizaron .srv/.action de planificación sin ejecución
ni el header ompl_planner_config.h referido por YAML. No prueba inexistencia
de otra API. MetaMove se trata como planificar Y mover; no se invoca como consulta.

## Resolución pendiente, no sustituible por un cambio a ciegas

Separar generación de plan y ejecución. Hace falta obtener un plan inspeccionable
sin movimiento (API demostrada o planificación local), desde estado completo
medido y con geometría registrada e incertidumbre validada. El barrido esférico
previo no aprueba el útil frente a su propia muñeca. Después, verificar límites,
recorrido e integración en arranque: una tarea nueva en PC no intercepta el HOME
anterior de StartMotion. No sustituir por XML vacío, SUCCESS artificial ni tarea
genérica de otra configuración. No se asignan ángulos de retirada a ciegas.

**Candidato identificado; ruta ejecutable e integración de arranque pendientes.**
Sin aprobación física. No liberar E-stop/reiniciar para ensayar. Más fotos
genéricas no resuelven la interfaz de planificación/ejecución.

## Fuentes y hashes de lo leído hoy

Prefijos dentro del contenedor:

- TM: /opt/walker/manipulation_task_manager/share/manipulation_task_manager/config/
- MT: /opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config/
- MP: /opt/walker/manipulation_platforms/share/manipulation_platforms/config/

| Fuente | SHA-256 |
|---|---|
| TM/cruzr/home.xml | 50d819d6d6190280c6efee1dc275877362c3f7c807ec733fbc3c7ed217daed88 |
| TM/cruzr/open_arm_before_home.xml | ec2c187c2217ca2dc1767179fba570677f062527fa7070729e81b05141f8980c |
| TM/move_dual_arms_home_ompl.xml | 7b350487a785e9505cf52c4640e10d1697723c53dde97b01527c7d22086fce77 |
| MT/meta_move/move_dual_arms_home_ompl.yaml | 029aeb479652d4b04121955596b05b7f78040fc4f57bedb72a313be93f3e0623 |
| MP/cruzr_s2_robot_description.yaml | bcc4a0dd3f013e42db2c57c063b00d5517f94cfef0b36aa10fce8d10070f22d7 |

Identifican archivos instalados actuales, no bytes activos durante el incidente.
