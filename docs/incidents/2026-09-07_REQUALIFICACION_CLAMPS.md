# Recalificación de clamps y contención local — 07-09-2026

**Fotos recibidas y revisadas:** véase el [contraste del montaje corregido](2026-09-07_CONTRASTE_FOTOS_CLAMPS.md).
Se identificaron sensor, soporte y placas; no se ha obtenido todavía su
transformación métrica. Ya no hace falta solicitar de nuevo las mismas vistas.

## Estado y evidencia recibida

**OBSERVADO por el operador:** perforación el 04-09 a las 13:58 (España),
rayados bilaterales durante el segundo arranque/HOME, aproximadamente 14:20;
inspección física indica daño sólo en carcasa, sin daño interior observado.
Ambas abrazaderas se han restituido a orientación de fábrica. Se incorpora
esta información sin exigir repetir la cronología o la inspección. No equivale
a un certificado independiente ni determina la transformación geométrica.

La [auditoría histórica](2026-09-07_AUDITORIA_CONTACTOS_HOME.md) conserva los
logs originales y sus límites. Esta actualización sustituye sus pendientes
de cronología e inspección ya contestados por el operador.

## Cambios locales VERIFICADOS

### Cierre adicional: no regenerar PASS E6.1C con el proxy antiguo

**VERIFICADO 07-09:** el analizador E6.1C aún conservaba una salida
`PASS_OFFLINE_REDUCED_READY_ENTRY_OWNER_ACCEPTANCE_PENDING` basada en E6.0J.
El lanzador físico ya estaba bloqueado; se detectó una vía de aprobación
documental obsoleta, no se observó un nuevo movimiento ni se le atribuye el
incidente. Se retira ahora también esa salida en las entradas públicas:

- `audit_vla_ready_entry_transition_e6_1c.sh --check/--run`: salida 78 antes
  de leer evidencias, ejecutar análisis o crear una ejecución.
- `analyze_vla_ready_entry_transition_e6_1c.py`: con argumentos válidos,
  informe `BLOCKED_RETIRED_UNREGISTERED_CLAMP_GEOMETRY`, salida 78, gate de
  geometría falso y autorización física falsa. No carga fuentes ni helpers.
  `--output` sólo crea un archivo nuevo; nunca sobrescribe evidencia existente.

Se conserva el algoritmo anterior como función histórica sin llamada desde
la entrada pública, y los informes anteriores no se editan ni eliminan.
Los tests ejecutan ambos modos de shell y la llamada Python directa con
fuentes deliberadamente inexistentes; prueban además que no se sobrescribe
un informe ya creado. Siete tests de recalificación correctos, además de
tres tests del ajuste fotográfico. No se cambió robot, PC como controlador,
servicios, configuración remota ni FT/paros/watchdogs.

Esto no intercepta HOME interno de arranque, UI, SDK ni la copia del guard
instalada en Vision. La retirada no demuestra seguridad de otras rutas.
Reversión futura: implementar y revisar un validador basado en geometría
registrada, no reactivar el algoritmo histórico para obtener un PASS.

| Ruta | Contención actual | Límite |
|---|---|---|
| `cruzr_recover_to_home.sh --run` | Rechazo 78 antes de conexión | También con `--yes --fast` |
| `cruzr_blue_workbin_cycle.sh` | Rechazo de run, grasp, deposit-held, home, home-workbin-internal, prepare-vision, grasp-after-approach | No cubre movimientos anteriores de otros wrappers |
| E6.1C ENTRY / recovery READY | Rechazo antes de conexión | No valida todavía cancelación ni trayectoria |
| E6.0Y recovery | Rechazo antes de conexión | STOP no se bloquea; READY/one-point ya retirados |
| Boot guard del repositorio `--run` | Rechazo local | **Copia instalada en Vision sin modificar** |
| HOME interno Control Center, UI, PICO, SDK y otros clientes | **No interceptados** | Mantener E-stop; no ensayar reinicios ni liberar para comprobar |

El helper `scripts/lib/cruzr_contact_motion_lock.sh` no tiene desbloqueo por
variable de entorno. Son restricciones temporales, no un sistema de seguridad
certificado. No se desactivó FT, paros ni watchdogs. No se desplegaron cambios
en el robot, reiniciaron servicios o publicaron movimientos.

**VERIFICADO:** tres tests locales, con doce variantes de lanzamiento y seis
casos de geometría inválida. Dobles de SSH/ROS/Docker/systemctl detectan una
conexión accidental; los doce lanzamientos fueron rechazados antes de llamarlos.

## Validación offline implementada y resultado

`config/clamp_mount_requalification.json` separa el informe del operador de
las medidas de montaje izquierda/derecha. `scripts/audit_clamp_mount_requalification.py`
comprueba marcos, rotación propia, traslación, dimensiones, incertidumbre,
inclusión de patillas/soportes/tornillos y hashes de evidencia. Transforma las
ocho esquinas del volumen; no vuelve a suponer que su centro es el del proxy.

Resultado guardado fuera de Git:
`/home/lacuna/proyectos/Robots/Humanoide-vla-evidence/20260907_clamp_requalification_inputs.json`.
Estado **BLOCKED_MOUNT_INPUTS**, salida 3 esperada: faltan transformaciones
medidas bilaterales. **No se ha ejecutado ni aprobado un barrido de colisiones.**
El comprobador nunca autoriza movimiento, incluso con entradas completas.

El generador E6.0K queda retirado para nuevos PASS porque heredaba una posición
no medida. Evidencias históricas conservadas. Faltan después: geometría real,
equivalencia de interpolación con Motion, barrido completo (incluido retorno
asimétrico), frenado, y protección del HOME interno de arranque.

## Consulta remota de sólo lectura

Se inspeccionaron argumentos y configuraciones del Control Center activo:
`base.conf` SHA-256 `ddbb0e7a8767d1466272fbcef66b4fa03dccd1a9f4ff3035ba7651dcb2dd5c2f`,
`cc.conf` SHA-256 `be8c98118ddc7ab40d235ac03e82f8614b77623453d197d31863d58f6d34b63f`.
No se encontró un selector de inhibición HOME en esos archivos ni en los
archivos enumerados de `/etc/walker/control_center` a profundidad dos.
Esto **no demuestra que no exista otro mecanismo**. No se modificaron binarios,
configuraciones ni el guard instalado. El estado físico/paros no se verificó.

## Reanudación y reversión

Mantener E-stop accionado. Próximo dato: ubicación y orientación del volumen
real respecto a la muñeca de **cada** clamp corregida. Se conservan dimensiones
ya aportadas; fotos frontal/lateral incluyendo brida y soporte permitirán
identificar referencias y limitar las cotas pendientes, no sustituir metrología.

Después: barridos offline, pruebas del ejecutor con fallos simulados y una
solución demostrada para arranque antes de autorizar un ensayo físico nuevo.
La aceptación de orientación de fábrica no basta para cerrar esas tareas.

Reversión: no retirar el bloqueo para probar. Sustituirlo sólo mediante cambio
revisado y nueva evidencia de recalificación; no restaurar el archivo completo
desde Git porque contiene otros cambios del usuario. Sin commit ni push.
