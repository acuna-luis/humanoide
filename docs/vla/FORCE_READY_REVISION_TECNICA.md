# force_ready.sh: revisión por el técnico

**Actualización vigente — 2026-09-14: HOME→READY nuevo probado físicamente,
5/5 etapas con éxito.** El propietario aporta los cinco resultados Motion
`SUCCEED` (state 1101001, status 4) y confirma el ensayo exitoso desde HOME.
Se cierra el pendiente de primera ejecución del acceso
`ready410_h63_access_01..05_forward` para este ensayo. Se registra lentitud:
122 s nominales; duración real no cronometrada. La ejecución fue mediante ROSA
directo con un `force_ready.sh` modificado por el operador; el agente conserva
ese archivo. ENTRY/VLA y el monitor Python no quedan probados por este ensayo.
Esta actualización prevalece sobre los estados históricos de READY pendiente.
[Resultados, cinco Goal ID, alcance y evidencia](ENSAYO_HOME_READY_NUEVO_20260914.md).


2026-09-14. VLA-01. Wrapper local, **sin prueba física de brazos ni habilitación
nueva**. No se modificó force_home.sh ni ningún archivo del robot.

`scripts/force_home.sh` envía directamente `cruzr/home` mediante SSH/ROSA.
El nuevo `scripts/force_ready.sh` utiliza las tareas corregidas
`s2_bio_vla/ready410_h63_access_XX_forward` y el ejecutor existente
`scripts/vla/run_ready410_trial.py`. Conserva sus comprobaciones y no copia
credenciales al archivo nuevo. El nombre solicitado no implica un bypass.

La ruta es acceso desde la postura revisada con cabeza bajada a READY, por
cinco etapas: cabeza, cintura, elevador, brazo izquierdo y derecho. READY
objetivo usa head_pitch−0,63rad. No es una trayectoria desde cualquier postura.
Tras un HOME completo, el inicio de este paquete no coincide en cabeza.

Para revisar sin red ni movimiento, desde la raíz del repositorio:

```bash
./scripts/force_ready.sh --help
./scripts/force_ready.sh \
  --review ../Humanoide-vla-evidence/20260914_READY_COMMISSIONING_REVIEW/package/access.json \
  --step 1 --check
```

El técnico puede examinar los veinte ejes de inicio/fin, tarea exacta, duración
y hashes devueltos. Los XML originales del paquete y la copia de lo instalado
están en la evidencia citada en [Paquete READY410](PAQUETE_READY410_CORREGIDO.md).
El entorno Python requerido ya es `.venv/general-home`; no instala paquetes.

Después de disponer de una habilitación revisada y vigente, el formato es:

```bash
./scripts/force_ready.sh --review /ruta/access.json --step 1 --preflight \
  --qualification /ruta/habilitacion.json --evidence-dir /ruta/comprobacion-nueva
./scripts/force_ready.sh --review /ruta/access.json --step 1 --run \
  --qualification /ruta/habilitacion.json --evidence-dir /ruta/ensayo-nuevo
```

**No hay una habilitación de brazos emitida actualmente.** La receta de --run
no es permiso para ejecutarla ahora. No crear un JSON con authorized:true para
simular revisión: el contrato requiere evidencia vinculada, identidad del
proceso/registro y archivos del ejecutor. El comando ejecuta una sola etapa,
requiere terminal y conserva la confirmación física del ejecutor. No incluye
bucles, reintentos, recuperación, instalación ni recarga.

Revisar antes de cualificar: orden efectivo de grupos, identidad cargada,
escena/interfaces, protocolo de ensayo y seguimiento/parada de brazos.
La observación humana y el E-stop no se registran como una medición de distancia
de parada. El monitor de comunicación de 6s conserva su alcance limitado.

Reversión: retirar selectivamente scripts/force_ready.sh y este documento;
no altera tareas remotas ni la postura. Backup/documentación y resultados de
comprobación en ../Humanoide-vla-evidence/20260914_FORCE_READY_REVIEW/.
Recrear copiando este script versionado y conservando el entorno y el paquete
revisado; tras firmware se deben contrastar nuevamente las dependencias y tareas.
