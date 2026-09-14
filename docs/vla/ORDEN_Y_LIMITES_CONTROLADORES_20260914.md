# Orden de controladores y aceleración compilada — 14-09-2026

Estado: verificación estática y consultas de lectura; sin movimiento ni cambios
remotos. Fuentes reproducibles: `scripts/vla/audit_ready_controller_contract.py`
y `scripts/vla/test_ready_controller_contract.py`.

## Hallazgos nuevos

1. `cruzr_s2_v1_mc_config/config/controllers_config.yaml` contiene el orden
   explícito de los cinco grupos. Coincide con las etapas generadas, incluidos
   los siete ejes de cada brazo: shoulder_pitch, shoulder_roll, shoulder_yaw,
   elbow_roll, elbow_yaw, wrist_pitch, wrist_roll; prefijos L/R.
2. `/mc/controller_manager/list_controllers`, tipo
   `rosa_control_msgs/srv/ListControllers`, devuelve `manipulation_controller`
   running; `sdk_controller` y `vla_sdk_controller` initialized. La consulta
   sólo lista estados: no carga, cambia ni inicia controladores. Los recursos
   de esa respuesta aparecen ordenados alfabéticamente: no usarlos como orden
   de los vectores de comandos.
3. En `libcomponent.so` f6d076fb…a25acf, la decodificación YAML lee `vel`
   (cadena VA0xcd363) hacia el vector en stack+0xd0 y `acc` (0xcd367) hacia
   stack+0xf0. En 0x95b9f..0x95bc0 copia sus elementos a xmm0/xmm1 y llama
   a JointLimits. El constructor0x975a0 copia xmm0/xmm1 al registro+0x10/+0x18.
   Se identifica así el cuarto double de los registros como aceleración.
4. En `libs2_arm_kinematics.so` 2a41cf55…ad251c, la tabla ya extraída de
   siete registros contiene velocidad3,14rad/s y aceleración31,4rad/s²
   para los siete ejes; defaults compartidos por ambos brazos. Son límites
   compilados identificados, NO una lectura de los objetos vivos ni una
   recomendación de velocidad. No se acelera la trayectoria.
5. Las tres bibliotecas actuales de Motion (component, s2_arm y MetaMove)
   conservan exactamente los hashes de las copias analizadas.

## Discrepancia que el contraste anterior no incluía

`config_mc_cruzr_s2_v1/config/ecat_hardware/transmissions.yaml` fija para
head_pitch_joint un mínimo−0,65rad. El acceso READY archivado pide
−0,6510789706582119rad: excede ese límite nominal en0,00107897rad (~0,0618°).
El YAML de planificación permitía−0,68rad; por eso el contraste anterior con
YAML/URDF de planificación pasaba. La nueva comprobación añade las
transmisiones de hardware y conserva el rechazo; no recorta silenciosamente
el objetivo ni reduce la banda de incertidumbre.

Cambiar esa orientación exige regenerar y revisar el acceso y la transición
siguiente, además de comprobar compatibilidad con la entrada del VLA. No se
modificó el READY instalado ni se regeneró una habilitación física.

## Alcance y punto de reanudación

La ausencia de una tabla de orden y de significado para el campo de
aceleración queda resuelta en los archivos/bibliotecas examinados. Siguen sin
comprobar la cadena completa MetaMove→transporte→ejes para brazos mediante
ensayo o lectura efectiva, y cualquier sustitución de límites posterior a
la construcción. No convertir `configured_group_order_matches` en
`effective_dispatch_verified`. El auditor mantiene physical_approval=false.
Se necesita corregir/revisar la discrepancia de cabeza antes de instalar
este acceso. La prueba de cabeza anterior sigue válida en su alcance.

## Reproducción y conservación

```bash
.venv/general-home/bin/python scripts/vla/audit_ready_controller_contract.py \
 --review ../Humanoide-vla-evidence/20260914_READY_AFTER_HEAD/access/review.json \
 --hardware-snapshot ../Humanoide-vla-evidence/20260914_ARM_MAPPING_LIMITS/hardware-configs.json \
 --component-binary ../Humanoide-vla-evidence/20260914_MOTION_INTERNAL_CONTRAST/libcomponent.so \
 --arm-binary ../Humanoide-vla-evidence/20260914_MOTION_INTERNAL_CONTRAST/libs2_arm_kinematics.so \
 --output /tmp/ready-controller-audit-nuevo.json
.venv/general-home/bin/python -m unittest discover -s scripts/vla -p 'test_ready_controller_contract.py'
```

Tres tests pasan: discrepancia nominal pequeña, orden invertido, snapshot
alterado y rechazo de binario no auditado. Evidencia privada en
`../Humanoide-vla-evidence/20260914_ARM_MAPPING_LIMITS/`: snapshots, hashes
actuales, estado de controladores, disassemblies, contract-audit.json y
SHA256SUMS. Copia previa documental en before-docs/. Cambios persistentes
sólo PC: auditor, tests y documentación; reversión selectiva de estos nuevos
archivos y restauración documental desde backup. No instalación/reload remoto.
Después de firmware: renovar snapshots/hashes y revisar el flujo de datos;
el auditor rechaza otros binarios en vez de reutilizar offsets.


## 2026-09-14 — VLA-01: corrección READY de cabeza calculada y revisada

**VERIFICADO OFFLINE, NO INSTALADO.** Retomada la prueba solicitada tras la
consulta al proveedor. Captura de97 muestras en5s, estado por nombres/velocidad
y salud; no se envió movimiento. La referencia separada usa READY head_pitch
−0,63rad en acceso y recuperación, frente a−0,65107897rad. Se conserva±1°:
el extremo inferior de la banda es−0,6474533rad, dentro del mínimo de
hardware−0,65rad. ENTRY final y demás articulaciones no se modifican.

Se recalcularon ambos recorridos de la referencia y las etapas:1018 pares
certificados,54 avisos internos retenidos,0 UNRESOLVED, sin timeout en cada
revisión. Acceso desde postura medida→READY122s; READY→ENTRY74s nominales,
no tiempos de ejecución medidos. Diez XML de acceso y diez de ENTRY generados.
Contraste con controladores/transmisiones: orden configurado coincidente,
cero objetivos nominales fuera de hardware. No cambia la configuración
instalada ni se afirma aprobación física o lectura efectiva de límites.

Fuente reproducible nueva: scripts/vla/prepare_ready_head_hardware_limit.py,
selector hacia dentro de límites sin reducir incertidumbre; tres tests en
test_ready_head_hardware_limit.py ya pasaron. Ejecutar ese generador con
--reference (referencia previa), --hardware-snapshot (hardware-configs.json)
y --output NUEVO.json; después prepare_home_ready_access.py con captura
por nombre y prepare_entry410_stages.py con contrato/hashes registrados.
Las rutas, hashes y resultados quedan en
../Humanoide-vla-evidence/20260914_READY_HEAD_CORRECTED/
(reference.json, capture/, access/, stages410/, limits.json, SHA256SUMS).
Los hashes del contrato/runtime de ENTRY se reutilizaron de la revisión
anterior; requieren contraste vivo antes de instalar o habilitar.

PENDIENTE: el acceso nuevo no tiene aún instalación/ejecutor calificado;
la generación local de XML no lo convierte en tarea disponible. No instalar
o ejecutar el paquete anterior con head_pitch−0,651079rad. La cadena
efectiva de despacho/parada de brazos sigue fuera del alcance del ensayo de
cabeza. No solicitar otro paro/reinicio hasta disponer del paquete y del
procedimiento concreto completos. No se envió ningún movimiento adicional.

Cambio persistente sóloPC: generador, tests y registros; no instalados en
robot. Backup documental en before-docs/; las referencias anteriores se
conservan intactas. Reversión selectiva de estos nuevos archivos; no volver a
la referencia anterior para ejecutar un objetivo fuera del límite hardware.
