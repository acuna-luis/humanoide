# VLA frente a mesa de 80 cm: diagnóstico del 11-09-2026

Fecha/zona: 2026-09-11, Europe/Madrid. Ficha VLA-01.
El operador pidió estudiar la respuesta y después ejecutar el flujo VLA.
Esta intervención comienza con inferencia diagnóstica sin RobotCommand;
no presume que el resultado habilite ejecución física.

## Estado y primera prueba

Inventario fresco: contenedores VLA detenidos, restart=no, entrypoint=null,
comando `bash -lc 'exec sleep infinity'`; no arranque del controlador vendor.
Articulaciones inmóviles, brazos/cuerpo HOME numérico y cabeza−0,430857rad,
paros0/0, cargador0, baterías50,8/49,8%. Dos suscriptores de RobotCommand y
**cero publicadores**. No se atribuye modo automático a esa lectura.

La prueba usa task0 y perfil P14 existente. La escena y postura son las
actuales, **no ENTRY40 ni430/438**. No cuenta entre las cinco pruebas E6.1B
calificadas. No se sustituye el estado real por el de un episodio del dataset.

El primer intento terminó con0 chunks: `TypeError: Object of type String
is not JSON serializable`. El servidor marcó SUCCEEDED pero había fallado
cada intento antes de inferir; por tanto **no es un éxito del modelo**.
El adaptador guardaba directamente `shm_msgs/String` en `frame_id` y
`source_encoding`. El esquema real Image2m declara ambos como buffers con
longitud `size`; no son strings Python. Se corrigió sólo su serialización,
conservando los bytes significativos y rechazando tamaños/UTF-8 inválidos.
La lógica del checkpoint, procesamiento de imagen y límites no se modificó.

El primer exportador también falló porque no existía `shadow.jsonl` al no
haber chunks. Se conservaron por lectura los logs completos y la fuente
remota antes de repetir. Los logs anteriores al ensayo están en
`previous-remote-evidence/`; no tenían capturas de entrada antiguas.

## Cambio reproducible

- Fuente: `scripts/vla/runtime/cruzr_s2_inference_shadow.py`.
- Destino: Vision192.168.11.3,
  `/home/walker/cruzr-vla/additional/safe-runtime/cruzr_s2_inference_shadow.py`.
- Montaje: `/home/ubt/additional/safe-runtime/cruzr_s2_inference_shadow.py`
  en `cruzr-vla-inference`.
- SHA anterior: `840c93e24bd8e24e42d79734bca5c8045b5207f2711f15323a7e83801b7cac22`.
- SHA instalado: `173b55da886ac99b6562ac228f4cab06df30b88dbc867119648fb797cce67b81`.
- Backup remoto: mismo directorio, archivo
  `cruzr_s2_inference_shadow.py.backup-20260911T122841849725Z`.
- Nuevo instalador selectivo `scripts/vla/install_shadow_inference_adapter.py`:
  comprueba hash anterior y contenedor detenido, guarda backup y sustituye
  atómicamente un único archivo. No arranca ni recarga servicios.
- Nuevo test `scripts/vla/runtime/test_cruzr_s2_inference_evidence.py`.
  Nueve tests pasan en total: evidencia real del adaptador con buffers SHM,
  strings normales, bytes residuales, rechazo de datos inválidos y conservación
  de los controles del validador. No requiere ROS/CUDA para ejecutarlos.
- Sin paquetes nuevos, cambios de SDK, checkpoint, perfiles, Motion o trayectorias.

Reaplicar sólo tras comprobar compatibilidad y con inferencia detenida:

```bash
python3 scripts/vla/install_shadow_inference_adapter.py --check
# En --install usar el SHA que realmente se haya revisado, no aceptar uno desconocido.
python3 scripts/vla/install_shadow_inference_adapter.py --install \
  --expected-sha256 840c93e24bd8e24e42d79734bca5c8045b5207f2711f15323a7e83801b7cac22
python3 -m unittest discover -s scripts/vla/runtime -p 'test_cruzr_s2_*' -v
```

Activación: siguiente sesión shadow con el launcher existente; no requiere
reiniciar Motion ni el robot. Reversión: con `cruzr-vla-inference` detenido,
restaurar el backup indicado al destino y verificar SHA anterior; restaurar
la fuente local correspondiente para que el preflight vuelva a coincidir.
No restaurar logs/estados transitorios como configuración de control.

Receta del ensayo diagnóstico (no orden de movimiento):

```bash
./scripts/vla/run_vla_shadow_smoke.sh --task-id 0 \
  --experiment-id E6.1-DIAGNOSTIC-TABLE80-FIXED \
  --shadow-profile cruzr_s2_vla_task0_p14_shadow_e6_1b.json
```

## Resultado posterior

**VERIFICADO:** la corrección permitió generar2 chunks en10,009s, sin errores
de serialización. Inferencias de1,803s y0,435s. Capturas RGB960×576 y los20
ángulos conservados por chunk; PNG y SHA coinciden, `frame_id`/`encoding` son
strings correctos. Desfase imagen–estado registrado76,2 y88,2ms, sin inferir de
ello aptitud para movimiento.

**Resultado del validador:0 aceptados,2 rechazados**, ambos por
`first_point_delta_violations:12`. El primer objetivo del hombro derecho
`R_shoulder_yaw_joint` difiere1,414390rad (81,039°) de la postura real, frente
a0,1rad (5,73°) permitidos. Segundo chunk1,412901rad. La sesión terminó con
ambos contenedores exited/restart=no, cero publicadores RobotCommand y
articulaciones iguales entre lecturas inicial/final, velocidad final0.
No se ordenó movimiento de brazos, cabeza, elevador o chasis.

El PASS del wrapper acredita funcionamiento de shadow y cierre seguro;
**no significa aprobación de sus propuestas ni éxito al recoger la caja**.
La prueba se hizo desde brazos/cuerpo HOME y cabeza observando, fuera de ENTRY.
Por tanto no prueba que80cm sea una altura válida o inválida para el agarre,
ni que430/438 produzcan estos mismos saltos.

No se ejecutó el flujo físico pedido porque las propuestas fallan el control
de continuidad. No se aumentó el límite, recortaron propuestas, sustituyó el
estado real ni habilitó el ejecutor retirado NO_BOX. No se repiten cinco veces
las mismas condiciones rechazadas como supuesto avance del gate.

**Reanudación:** resolver una entrada y escena coherentes (ENTRY40 conserva
su contrato;430/438 siguen candidatas), validar acceso/recuperación con la
mesa presente y comprobar respuesta fresca desde esa entrada. Las cinco
sesiones calificadas siguen0/5 y tareas físicas VLA0/4. La autorización del
usuario para continuar se conserva; falta validación técnica, no otra
aceptación genérica de responsabilidad.

Evidencia privada, fuentes completas, backups, comandos y hashes:
`../Humanoide-vla-evidence/20260911T122137Z_VLA-TABLE80-SHADOW/`.
