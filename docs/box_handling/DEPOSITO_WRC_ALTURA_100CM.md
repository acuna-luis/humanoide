# Depósito WRC y estantería a 100 cm

2026-09-16, Europe/Madrid. Diagnóstico de lectura; sin movimientos, instalación,
recarga ni modificación de mapa/XML/YAML del robot por el agente.

## Resultado verificado

La tarea `wrc_cruzr/put_cruzr_wrc_low` llama a `wrc/put_cruzr_wrc_low`
y después a `wrc/open_arm_cruzr`: la apertura está incluida. La ampliación del
ejecutor enlazó esta tarea original; no adaptó sus alturas a la estantería local.

Fuentes archivadas del proveedor:
- [XML](../../vendor/ubtech/cruzr_s2/snapshot_20260916/motion/tasks/wrc_cruzr/put_cruzr_wrc_low.xml).
- [YAML](../../vendor/ubtech/cruzr_s2/snapshot_20260916/motion/meta_clamp/wrc/put_cruzr_wrc_low.yaml).

El YAML leído en Motion conserva estos objetivos. Ruta instalada:
`/opt/walker/manipulation_meta_tasks/share/manipulation_meta_tasks/config/meta_clamp/wrc/put_cruzr_wrc_low.yaml`.

| Instante | X de ambas manos | Z de ambas manos | Z del torso |
|---|---:|---:|---:|
| Inicio del plan observado | ≈0,30 m | ≈1,10 m | ≈1,23 m |
| 6 s | 0,75 m | 0,65 m | 1,20 m |
| 10 s | 0,95 m | 0,65 m | 1,20 m |
| 12 s | 0,95 m | 0,45 m | 1,00 m |

Son coordenadas de referencias del planificador, **no alturas medidas de la base
de la caja ni prueba de que se alcanzara el último punto**. El registro Motion
con hora interna 18:52:19.854 confirma la composición ABSOLUTE/RELATIVE del YAML:
Z izquierda `1.10007 0.65 0.65 0.45`, derecha `1.10028 0.65 0.65 0.45`.
El `1.2` del YAML es el objetivo Z del torso, no la altura de la estantería.
El descenso programado explica el intento demasiado bajo comunicado por el usuario.
Acercar la estantería o modificar put1 no cambia estos objetivos verticales.
El perfil además configura `box_size: [0.6, 0.4, 0.28]`, distinto de la caja
real comunicada `0.603 × 0.397 × 0.217 m`; su efecto concreto debe revisarse al adaptar.

## Referencias del documento

Fuente: `Cruzr S2 搬箱子操作流程.docx`, texto y figuras originales; copia
[saneada/texto chino](../vendor/ubtech/box_handling/texto_zh.md).

- Escenario 1, get1: 59 cm desde el centro de la rueda derecha hasta el frente
  de la caja; lateral de 16 cm entre los lados derechos indicados.
- Escenario 1, put1: 90 cm desde el centro de la rueda derecha hasta la parte
  inferior de la estantería (`架子最下面`); lateral de 20 cm respecto al centro
  del pie derecho. Es distancia horizontal, no altura. El texto no define con
  precisión suficiente su equivalencia con el borde del tablero de otro mueble.
- El texto describe un extremo inferior a 85 cm ajustable ±10 cm, el otro a
  99 cm ajustable; nivel superior a 129 cm e inclinación de 10°.
- La fotografía del conjunto muestra un nivel inferior cercano al suelo:
  discrepancia visual con esas alturas, sin convertir píxeles en medidas.
- Escenario 2: niveles inferiores de 70 y 90 cm, superiores de 125 cm;
  put1 a 33,5 cm desde el centro frontal del parachoques. Es otro escenario y
  otra referencia; no sustituir directamente los 90 cm del escenario 1.
- No se encontró una altura de 120 cm en el texto del documento.

Los 59 y 90 cm no son intercambiables: cambian el objeto de referencia y la
trayectoria de manipulación. Tampoco quedan validados 90 cm para la estantería
local por aparecer en la receta del proveedor.

## Estado y reanudación

OBSERVADO: el usuario comunica agarre exitoso tras acercar las cajas e intento
de depósito demasiado bajo. Luego indica reinicio y que llevará el robot a HOME;
no se atribuye ese movimiento al agente ni se da HOME por medido tras el reinicio.
Se toma como requisito vigente la superficie de depósito indicada ahora: 100 cm.

PENDIENTE: variante de depósito adaptada a esa superficie, dimensiones reales,
transformación referencia de mano→base de caja, inclinación, profundidad de
inserción y holgura antes de bajar. No basta cambiar Z a 1,00 m: mano y base de
caja son puntos distintos. No repetir el depósito original para probar distancia.
No se ha producido ni instalado una trayectoria corregida en esta revisión.

Evidencia externa: `../Humanoide-vla-evidence/20260916T105936Z_DEPOSIT_HEIGHT/`,
`yaml.json` y `log.json`. Consultas de lectura; no requieren reversión del robot.
Respaldos de los documentos previos en `before-docs/` de esa misma evidencia.
