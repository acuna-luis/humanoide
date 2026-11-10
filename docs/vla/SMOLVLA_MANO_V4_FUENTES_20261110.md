# Fuentes locales para la mano v4 y el puente SmolVLA — 10-11-2026

**Investigación y simulación sin movimiento.** El usuario pidió buscar en los
documentos disponibles y continuar con la información existente. La búsqueda
encontró especificaciones de posición y un modelo v4 que no figuraba en la
búsqueda anterior; no demuestra todavía su equivalencia con las manos instaladas
ni permite habilitar el puente físico.

## Manuales y modo de mano

El manual SDK suministrado, sección 5.9.2, indica `HW_TYPE=cruzr_s2_v1_sps`,
siete nombres en el orden del ejemplo y que el control de la mano v4 sólo
admite posición; las posiciones no deben estar vacías. También dice que poner
un eje no controlado a cero lo lleva a cero: eso **no** equivale a conservar
su pose actual. Se contrastó con el original chino de
`Cruzr S2 优必选SDK二次开发文档【对外】6.24.pdf` y su traducción local
`Cruzr_S2_Manual_SDK_ES.pdf` (traducción SHA256
`f259295565283268b34bcda6123dd92ae9ed559b54e62161a8a013f347d48842`).
Los documentos pueden contener datos de conexión y no se copian a Git.
El ejemplo del manual enumera siete nombres y modo5, pero el fuente
`pub_hand_command.cpp` del paquete demo Cruzr inspeccionado contiene sólo seis
nombres por mano y omite `thumb_pip`. No trasladar ese demo directamente a la
mano v4 de siete ejes.

Por separado, la inspección estática previa de la biblioteca instalada
identificó ramas internas `5=Position` y `7=Current`, que toma el campo
denominado `torque`. Esto no demuestra que corriente o par estén soportados
oficialmente para este uso, ni da unidades, conversión, fuerza segura o
comportamiento físico. El manual v0.3 también habla de posición, pero no es
prueba de compatibilidad con el v0.2.0 instalado.

Los manuales describen `cc.api.sdk.switch_mc_mode` para ceder y recuperar
autoridad; el ejemplo VLA muestra cambio de controladores con chasis y
manipulación detenidos. No se encontró una especificación que identifique esos
cambios con los Trigger `motion_sdk` de esta unidad, ni que garantice la parada
de una consigna ya aceptada. Respuesta positiva o destrucción del publicador no
demuestran por sí solas una parada física.

## Modelo de mano hallado en Descargas

El ZIP privado `/home/lacuna/Descargas/四代手-URDF.zip`, SHA256
`96f957ee0d346b8ff0654e219891ba23ebe5f2a315ca793a83dde9741019e561`,
contiene modelos izquierdo y derecho `hand_v4_evt3`. Por cada mano se
identificaron 13 enlaces, 12 articulaciones (11 revolutas y una fija), 13
geometrías de colisión declaradas y ninguna articulación `mimic`. Los 11 nombres
del URDF no coinciden literalmente con los siete nombres de estado de la mano
v4 observada. Faltan comprobar versión, montaje, transformación, acoplamiento
de los cuatro ejes adicionales y relación con los estados; no adoptar sus
límites o geometría como validación de la unidad.

Auditor reproducible, sólo lectura, sin extracción y sin copiar binarios a Git:

```bash
python3 -B scripts/vla/audit_vendor_v4_hand_urdf.py '/home/lacuna/Descargas/四代手-URDF.zip'
```

El reporte privado `../Humanoide-vla-evidence/20261110_VENDOR_HAND_V4_AUDIT/report.json`
tiene SHA256 `bce57966ed663cd83bbbe035633c4bfdd8d1d26e1a74a0a9a418f35c00d9d9f4`.

## Secuencia simbólica de mano

`scripts/vla/ball_hand_phase_policy.py` implementa en memoria la secuencia
solicitada: abierta en aproximación; cerrar sólo cuando señales externas
declaran posición y solicitud; mantener cierre mientras se sube y baja; abrir
sólo al declarar suelta y apoyo. Acepta como máximo una transición por
actualización. La salida es una etiqueta simbólica, **no** valores de dedos,
un mensaje ROS ni una orden. Las señales son externas, no comprueban posición,
altura, agarre, apoyo, actualidad o identidad de sensores. Sin esas pruebas no
sirve como habilitación física.

El puente necesita además comprobar controlador y parada real para SPS,
traducir y cualificar siete posiciones, reconocer la pelota y la posición de
agarre, obtener límites/velocidades aplicables y comprobar la escena. La CPU
a bordo tardó62,932s en una muestra; el shadow previo en Ada es más rápido,
sin demostrar lazo de control ni latencia de extremo a extremo.
