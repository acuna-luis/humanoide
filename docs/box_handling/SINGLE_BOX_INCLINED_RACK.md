# Variante de una caja: pila a estantería inclinada

**Estado vigente 2026-09-16: get1 del proveedor probado por el operador.**
Con base780mm y lateral160mm hacia fuera, separate_right terminó SUCCEED y
el operador confirmó éxito físico. La variante de depósito inclinado de este
documento sigue siendo diseño offline; no se ejecutó ese ciclo completo.
[Ensayo, disposición y tareas siguientes](GET1_PROVEEDOR_ENSAYO_20260916.md).
Se conserva el [incidente anterior](../incidents/2026-09-16_SEPARATE_RIGHT_POSTURA_PELIGROSA.md).

2026-09-16, Europe/Madrid. DISEÑO OFFLINE; no instalado ni probado físicamente.

## Montaje comunicado

Caja603×397×217mm; base actual780mm desde el suelo. La primera disposición
tenía570mm sobre palé130mm y dos cajas; número de apoyos nuevo no confirmado.
Longitudinal rueda/frente590mm, lateral exterior160mm. Encajada: el operador indica «2 cm por lo
menos» para liberarla. Propuesta inicial 30 mm de elevación vertical; ese dato
no demuestra que 30 mm basten. Confirmar separación antes de retirar.

Destino sin rodillos, superficie de entrada a 1000 mm y salida a 830 mm,
profundidad horizontal600 mm, ancho libre1250 mm y altura libre comunicada500 mm.
Existe tope inferior según el operador; dimensiones/capacidad no comprobadas.
Precisión de medidas no aportada. Estado físico actual no inferido de fotografías.

## Cálculo reproducible

Perfil: [single_box_inclined_rack.json](../../config/box_handling/single_box_inclined_rack.json).
Resultado: [single_box_inclined_rack_review.json](../../config/box_handling/single_box_inclined_rack_review.json).

```bash
python3 scripts/box_handling/prepare_single_box.py
```

Pendiente atan(170/600), aproximadamente15,82°. Orientación propuesta:603 mm
a lo ancho y397 mm en profundidad. La envolvente de la caja inclinada se calcula
como profundidad=d cos(a)+h sin(a), altura=h cos(a)+d sin(a). El informe incluye
el máximo durante el giro0→a. Es aritmética de caja rectangular, no validación
de alcance, IK, colisión, trayectoria ni orientación real de las abrazaderas.
No confundir el sobrante del hueco con margen admisible de navegación.
Los500 mm deben representar el mínimo a lo largo de la entrada; aún sin verificar.

Sin rodillos no se presupone deslizamiento. En el modelo ideal, el umbral de
fricción estática es tan(a)=0,2833; la fricción real no se midió. Tampoco un tope
presente demuestra estabilidad ni capacidad para recibir una caja deslizante.
Planificar apoyo estable antes de abrir, sin caída ni desplazamiento esperado.

## Cambios frente al proveedor

El escenario1 original llama Singapore/separate_right_cruzr para get1: su YAML
incluye giros y desplazamientos laterales; no se reutiliza tal cual para encaje.
El candidato de agarre directo Singapore/clamp_cruzr eleva200 mm y cambia el
torso; tampoco equivale a una elevación pura de30 mm de la caja.
put_cruzr_wrc_low baja200 mm y después el XML abre las abrazaderas, sin una
etapa explícita que alinee la caja a esta pendiente. No adaptar sólo box_size.
Dimensiones originales discrepantes: separate_right603×397×220 mm frente a
depósito600×400×280 mm. Palé: texto26 cm y figura13 cm; usamos medida real13 cm.

## Secuencia prevista y trabajo restante

Un ciclo, cero reintentos automáticos y sin HOME ante fallo:
agarre directo → desencaje vertical → retirada → navegación → alineación y apoyo
inclinado → apertura → retirada de útiles → HOME independiente.

Ya preparado: perfil de medidas, fases separadas y cálculo de envolvente de caja.
Pendiente: registrar poses origen/destino en mapa y geometría de montantes,
nivel superior y tope; transformar contacto caja–útiles, resolver IK y comprobar
barrido de brazos/caja; traducir la secuencia a primitivas con semántica contrastada;
ensayo supervisado de desencaje y apoyo antes de unir el ciclo.
La inclinación cambia la trayectoria de ambos útiles alrededor del centro de caja:
no basta con girar cada muñeca sobre sí misma. No se generan XML ejecutables
con coordenadas o marcos inventados. No se usa VLA en esta propuesta.

## Registro y reversión (BOX-01)

Cambio sólo PC: config/box_handling/, scripts/box_handling/prepare_single_box.py
y este documento. Fuentes del proveedor intactas, sin conexión al robot ni
activación o instalación. Verificación: cálculo ejecutado offline, comprobación
independiente de pendiente, compilación Python y diff check. Backup de documentos
anteriores y hashes de fuentes/resultados:
../Humanoide-vla-evidence/20260916_SINGLE_BOX_VARIANT/.
Reproducible desde archivos versionables, Python3 estándar, sin dependencias externas.
Reversión: retirar estos archivos y notas BOX-01 de forma selectiva. Sin commit/push.

## Ejecutor del agarre derecho del proveedor

El 2026-09-16 se corrigió localmente
`scripts/force_separate_right_cruzr.sh`, que llama sin reintentos a
`Singapore/separate_right_cruzr`. El borrador activaba `set -u` antes de cargar
`/opt/walker/setup.bash`; el setup consulta `COLCON_TRACE` aunque pueda no estar
definida. También contenía un `done` sin bucle. El ejecutor carga ahora el setup
con `nounset` suspendido, aplica un timeout de 45 s y sólo declara éxito cuando
la respuesta contiene `desc: SUCCEED` y `status=4`. No reintenta ni envía HOME.
La corrección pasó `bash -n`; no se ejecutó la tarea durante la corrección.
Backup previo privado: `../Humanoide-vla-evidence/20260916_FORCE_SEPARATE_FIX/`.

Primer ensayo directo: la preparación de cabeza/brazos terminó, pero MetaClamp
falló en 0,36 s con `7101003/VisionDetectionFailure`. El log demuestra la causa:
`Transport vision is not running`; no llegó a evaluar la caja ni a agarrarla.
El árbol completo del proveedor llama `vision/enable_transport_vision_switch`
después de navegar, paso omitido por el ejecutor directo. El script reproduce
ahora ese prerrequisito, espera un segundo y sólo entonces llama al agarre. Ambos
resultados se validan por separado; cualquier fallo termina sin reintento.
Existe el action server `/cv/task/transport_action` y el XML de habilitación
instalado coincide con una acción `MetaLook start_vision_mode=transport_vision`.
Esta corrección pasó `bash -n` y `git diff --check`. Después hubo un incidente
con el primer montaje y un ensayo exitoso con el corregido, registrados arriba.
