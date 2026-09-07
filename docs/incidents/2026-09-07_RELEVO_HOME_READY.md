# Relevo para continuar el 08-09: HOME → READY → HOME

## Objetivo y restricciones vigentes

Validar ambos recorridos con las abrazaderas reales. El operador autoriza trabajo
offline y modificaciones necesarias, pero el estado final READY debe permanecer
intacto. Solicita asumir READY sin choques reales: es una PREMISA DEL OPERADOR,
no medición independiente ni aprobación de los trayectos. VLA fuera del objetivo
inmediato y sin habilitación física. No usar cabeza fija como sustituto de READY.

## Último estado físico REPORTADO, no comprobación actual

Operador: «energizado, ambos stop liberados, estable sin contacto con el cuerpo».
Después confirmó reconocer referencias en una foto. No confirmó haber accionado
paros, apagado, aislado energía o asegurado mecánicamente los brazos. No consta
estado seguro de fin de jornada. No inferirlo de esta nota. No se enviaron órdenes
de movimiento, parada, reinicio, apagado ni cambios de modo durante este cierre.

Antes de nueva interacción física, comprobar de nuevo estado completo según
AGENTS.md. No acercar manos/instrumentos a zonas de atrapamiento por tener sólo
una postura estable; E-stop no demuestra aislamiento ni retención contra gravedad.
No improvisar apagado: constan cambios de postura históricos al quitar energía.

## Punto exacto de reanudación

El operador reconoció P1/P2/P3 en la figura del brazo IZQUIERDO:

- P1: tornillo superior izquierdo del grupo de seis sobre la pieza plateada.
- P2: tornillo superior derecho de ese grupo.
- P3: tornillo inferior izquierdo de ese grupo.
- S: soporte negro; T: patita visible. Son etiquetas visuales, no puntos métricos.

Figura orientativa: [referencias anotadas](assets/2026-09-07-referencias-clamp/brazo-izquierdo-p1-p2-p3.png).
Generada con herramienta de imágenes sobre la foto existente; una primera versión
tenía línea P2 ambigua y se corrigió. Se conserva sólo la versión final aquí.
No extraer medidas/píxeles de la imagen generada ni usarla para calibración.
Reconocer tornillos no demuestra coordenadas CAD, normal del plano ni ejes ROS.

Foto ORIGINAL para cálculos: `/home/lacuna/Imágenes/1.jpeg`.
SHA256 original: `30052b8cbab874a4aabb133b2e5ae888fe4840c7eec58a5c5359f59a17a9e377`.
SHA256 figura: `0062458fec8a211e06c9df78151d6279ba320b72a5e0f26bd97e6dfe4db29430`.

Siguiente tarea prometida, AÚN NO EJECUTADA: contrastar offline el triángulo
P1/P2/P3 de la foto original con el CAD del sensor disponible. Reutilizar
`2026-09-07_CONTRASTE_FOTOS_CLAMPS.md` y evidencias anteriores: ya existe
ambigüedad de simetría/cara/normal del patrón central y exterior. Las etiquetas
nuevas no la resuelven automáticamente. No repetir ajustes previos sin justificar
qué nueva restricción aportan. Conservar todas las hipótesis compatibles; no
elegir por conveniencia la que evita colisión. No solicitar otra ronda genérica
de fotos ni repetir A–F/T. Si falta una referencia, definirla de forma visible
y verificable antes de pedir medición; no pedir al operador un eje ROS invisible.

## Modelo y evidencias disponibles

- `config/clamp_mount_requalification.json`: cotas completas reportadas; L/R
  translation, rotation y uncertainty siguen null. Evaluador devuelve exit 3,
  BLOCKED_MOUNT_INPUTS, translation ausente en ambos lados.
- `scripts/clamp_work_model.py`: perfil offline sin las seis mallas históricas
  PGC/finger1/finger2; sensores y muñecas conservados. Envolvente nominal
  82×100×130 mm; placa 70×100×36; patitas +12 mm. No colocación mundial inventada.
- `scripts/audit_home_ready_full_screen.py`: perfil installed-clamps por defecto,
  1.836 estados/561 pares de ROBOT/34 avisos AABB inconclusos. Abrazaderas aún NO
  incluidas en distancias mundiales. No llamar a la reducción de pares una mejora
  de seguridad. Perfil histórico disponible sólo para contraste.
- Renderer `scripts/render_home_audit_model.py`: robot sin PGC y envolvente de
  abrazadera separada. Último render externo `20260907_home_clamps_unregistered_visual`.
- `scripts/audit_ready_endpoint.py`: destino leído XML/YAML histórico, inalterable.
  Intersección modelada cabeza–torso confirmada con cruces independientes. Bajo
  premisa del operador se trata como discrepancia del modelo, no choque real.
- Candidato temporal de brazos: 35,389 s por sentido, límites provisionales
  0,15 rad/s y 0,5 rad/s² para curva quíntica ideal; no ejecutable/equivalencia
  vendor. XML local 0,6 rad/1,5 s requiere al menos 0,40 rad/s bajo duración literal.

Raíz de evidencias: `/home/lacuna/proyectos/Robots/Humanoide-vla-evidence`.
URDF: `20260903T093408_E4.1C/artifacts/vendor_cruzr_s2_v1.urdf`.
Resultados: `20260907_home_ready_clamps_profile.json`,
`20260907_ready_endpoint_locked.json` y anteriores enlazados en
[validación](2026-09-07_VALIDACION_HOME_READY_HOME.md).
Última regresión en chat: 3 tests perfil + 7 candidato temporal + 4 destino = 14 OK.

## Pendientes reales y límites de autonomía

Montaje con incertidumbre acotada; correspondencia de mallas/cuello; entorno y
estado inicial actuales; barrido continuo; equivalencia de interpolación,
seguimiento y parada; prueba física posterior con preflight fresco. Los tests
de código no cierran estos pendientes. No sustituirlos por flags true, márgenes
arbitrarios o exclusiones. No hay ruta aprobada ni autorización derivada para
mover/rearmar. Inspección pasiva no implica vigilancia en tiempo real del robot.

Commit de implementación previo al relevo: c453020 (incluye trabajo previo
46b65fe). Usuario autorizó anteriormente commit/push; preservar cambios ajenos.
La anotación se copia al repositorio sin sobrescribir la foto original. No se
guardan credenciales, checkpoints ni paquetes vendor. No hay monitor activo que
quede vigilando el robot durante la noche.
