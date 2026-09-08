# HOME → READY → HOME: contraste de configuración instalada

Fecha: 2026-09-08. Estado: VERIFICADO para archivos y puntos; PENDIENTE para
validación física del barrido. No se enviaron acciones, publicaciones, recargas
ni cambios remotos. READY final permanece intacto.

## Evidencia viva

Lectura SSH de Motion realizada entre 06:11:10 y 06:11:45 UTC. Primero Docker
activo y descubrimiento de contenedores; después `sha256sum`, lectura de cuatro
archivos y extracto de task_list en `walker-motion.manipulation_robot_app-1`.
Todas las consultas terminaron con rc=0 y stderr vacío. Evidencia textual en
la salida de herramientas de esta sesión; no captura continua de movimiento.

Los hashes remotos coinciden con las referencias locales/históricas:

| Archivo | SHA-256 |
|---|---|
| READY XML | c767f7396a325d375752fbce2351837e7f5e0c750902e4815ddd7acb24e2a9b2 |
| Recovery XML | 9e47b6ee37f83f75036c203b809e9a93284d459316764615496a872ca3b4fbcc |
| Forward MetaMove YAML | 7722b73457a89d6448954944af98ff50b24f586113f6ec7014dd31b1efdef7f6 |
| Recovery MetaMove YAML | bd5f588a4e69c3f5fc38796cccc1adffded293bc5355b67ee18d54f321b6e3b0 |

Referencias: `scripts/vla/runtime/tasks/s2_vla_e6_0_ready_s2.xml`,
`s2_vla_e6_0_exact_recovery.xml` en el mismo directorio,
`scripts/vla/runtime/meta_move/clamp_s2_vla_e6_0_exact_recovery.yaml` y
`Humanoide-vla-evidence/20260903T103858_E4.0/artifacts/remote_clamp_s2_joints_trajectory.yaml`
(directorio de evidencia hermano del repositorio).

La lectura de disco no demuestra qué versión mantiene en memoria el controlador.

## Resultado por sentido

- HOME → READY: HOME → staging → A → B/READY. El XML mueve cabeza/cintura
  en paralelo con la primera etapa de brazos. Registro de tarea:
  `Reverse=false, TimeRatio=0.5`.
- READY → HOME: B → A → staging → HOME. Los puntos de brazos son los de
  ida en orden inverso; cabeza/cintura vuelven en paralelo con la última etapa.
  Registro: `Reverse=false, TimeRatio=1.0`.
- Los YAML contienen duraciones [1.5,1.0] y [1.0,1.5], respectivamente;
  las etapas XML paralelas contienen 1.5. No se traduce TimeRatio a velocidad
  física sin verificar su semántica y los argumentos efectivos del llamador.
- Invertir puntos no demuestra invertir exactamente la curva interpolada,
  sincronización, velocidades o comportamiento ante interrupción.

## Éxitos físicos y alcance

La documentación previa registra READY exitoso en
`20260904T085921_E6.0Y-READY` y recuperación exitosa en
`20260904T092716_E6.0Y-RECOVERY`, además de READY en
`20260904T130344_E6.1C-READY`. Se conservan como evidencia histórica positiva;
no se afirma haber reanalizado aquí todas sus muestras. No está establecida
la equivalencia del montaje de abrazaderas entre cada ensayo y el actual.
El HOME interno exitoso de hoy es otro ensayo, no una ida y vuelta a READY.

## Lo que esta comprobación no cierra

1. La transformación sensor/abrazadera de cada lado continúa nula en
   `config/clamp_mount_requalification.json`. Las cotas delimitan la pieza,
   pero aún no sitúan ese volumen en el modelo cinemático. Por ello el
   cribado robot sin abrazaderas situadas no valida su barrido.
2. Las distancias estáticas diagonales de 174/178 mm no son una distancia
   mínima demostrada a lo largo de ambas rutas.
3. Persiste la discrepancia geométrica cabeza/torso descrita en MODELO_CUELLO.
   La premisa del operador de READY real sin contacto se conserva, pero no
   corrige automáticamente las mallas ni demuestra estados intermedios.
4. Interpolación efectiva, márgenes de incertidumbre y respuesta de parada
   no están demostrados para aprobar el barrido continuo.

Pruebas locales: `test_home_ready_full_screen.py` 3/3,
`test_clamp_work_model.py` 3/3 y `test_ready_endpoint.py` 4/4, todas OK.
Son pruebas de software/contrato, no ensayos físicos.

Punto de reanudación: archivos contrastados y endpoints preservados. No
repetir peticiones genéricas de fotos ni sustituir transformaciones desconocidas
por cero. Antes de habilitar movimiento falta fijar/verificar el registro
geométrico y demostrar el comportamiento efectivo de ambas rutas. No se
ha retirado ningún bloqueo ni se ha cambiado `physical_authorized`.
