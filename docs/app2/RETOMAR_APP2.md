# app2 — trabajar y retomar desde cero

**20-10-2026 — acceso a CVAT todavía bloqueado:** tras el ciclo de apagado
completo y encendido del servidor, el SSD de Docker ha reaparecido `live`, con
capacidad de 2 TB, serie `S7DRNJ0X107187F` y UUID
`b819b286-2006-4474-b2d5-13982b0f1536`. Boot verificado:
`cebc2464-2073-4f1e-82fc-17ee30941a22`; sistema `running`, cero unidades fallidas
y GPU accesible. El disco sigue **sin montar**, Docker está detenido y las cinco
unidades de protección siguen enmascaradas. La lectura SMART privilegiada aportada
por el operador indica `critical_warning=0`, 33,85 °C, cero errores de medio y
cero entradas de error; el extracto nuevo del kernel no muestra EIO ni resets
fallidos. No valida la integridad de EXT4/CVAT ni la estabilidad del disco.
La copia y verificación de los datos siguen **PENDIENTES**: al no disponer de
otro almacenamiento, se prevé copiar los esenciales al disco sano del sistema
(82,68 GB libres observados), previa estimación del tamaño. No se ha montado
el SSD ni iniciado Docker para hacerlo.
[Incidente, copias conservadas y recuperación pendiente](../incidents/2026-10-20_APP2_SSD_DOCKER_NO_RESPONDE.md).
Las comprobaciones de instalación/anotación descritas abajo son del día anterior;
no reinstalar ni repetir la importación para resolver este fallo de almacenamiento.


**ID:** APP2-HANDOFF-20261019. **Fecha/zona:** 19-10-2026, Europe/Madrid.
**Estado:** documentación operativa contrastada con la instalación comprobada.
El código y la documentación se publican en la rama `vision-reconoce` tras la
petición de commit/push del usuario. El paquete privado de relevo conserva una
instantánea anterior, con los cambios sin commit de aquel momento y las fotos
iniciales; su restauración se verifica por separado del servidor.

**Actualización del mismo día:** [especificación rev001](ESPECIFICACION_REV001.md)
y [recorrido local completo](VALIDACION_FLUJO_LOCAL.md). Ya hay conversor COCO,
checkpoint sintético guardado/recargado, lectura de códigos y demo PNG/JSONL.
No equivalen a entrenamiento de ITR real. La etiqueta identificativa estará en
la caja; contenido/formato y asociación pendientes.

**Trabajo real iniciado:** [primer lote de piezas](PILOTO_PIEZAS_REALES.md),
tarea 5/job 5 actual con capturas tras el encuadre; tarea 4/job 4 inicial conservada.
Cuatro vistas relacionadas, grupo compartido conservador y anotación pendiente. Empezar por ese
lote antes de repetir las pruebas sintéticas o intentar entrenar con una escena.

## 1. Qué estamos haciendo y hasta dónde hemos llegado

app2 pretende identificar piezas de dirección, distinguirlas de referencias
parecidas y, posteriormente, alimentar una estación y gestionar cajas vacías.
La fase actual es **percepción offline**. Se realizó únicamente el encuadre de
cabeza autorizado descrito en [el piloto](PILOTO_PIEZAS_REALES.md), con nuevas
fotografías conservadas; el detector no está conectado a controles físicos.
La lámina del cliente y los [requisitos transcritos](REQUISITOS_CLIENTE.md) son la referencia
del alcance; la identificación concreta de las piezas sigue pendiente del cliente.
ITR/OTR orientan la interpretación, pero no son una referencia de material confirmada.

| Elemento | Estado al entregar |
|---|---|
| Fotografías originales | Seis PNG iniciales intactos y cuatro capturas posteriores al encuadre de cabeza, con manifiestos y SHA256; ver [fuentes](FOTOS_Y_FUENTES.md) |
| Editor CVAT | 2.79.0 instalado; UI/API, login, polígono y exportación COCO sintéticos comprobados |
| Entrenador GPU | RF-DETR 1.11.2 Seg Nano, Torch 2.10.0/CUDA 12.8; inferencia y un paso sintético sin red comprobados |
| Exportación | ONNX del modelo público comprobado con ONNX Runtime CPU; no es un modelo app2 |
| Dataset y detector de piezas | Pendientes: escenas diversas, clases confirmadas, máscaras, splits y entrenamiento real |
| Robot | Runtime/cámaras inspeccionados antes; ningún detector app2 instalado ni agarre app2 validado |

El [informe de instalación](SERVIDOR_LOCAL_INSTALACION.md) conserva versiones,
hashes, incidencias resueltas y evidencias. El [plan de recursos](PLAN_LOCAL_RECURSOS_Y_TIEMPOS.md)
contiene presupuestos; los tiempos de entrenamiento aún necesitan medirse.
No reinstalar para retomar ni repetir smokes para sustituir trabajo con datos reales.

## 2. Qué se ejecuta en cada equipo

| Equipo | Función y ubicación |
|---|---|
| PC del operador | Repositorio, navegador, túnel SSH y archivo privado de fotos/evidencias; no necesita GPU para etiquetar |
| Servidor | `luisacuna@192.168.1.43`, puerto SSH 2649; CVAT y entrenamiento local; recetas en `/home/luisacuna/app2/setup` |
| Docker del servidor | Datos grandes en SSD separado bajo volúmenes gestionados por Docker; no guardar datasets crecientes en `/home` |
| Vision del robot | Destino futuro de inferencia; AGX Orin/CUDA 12.2/TRT 8.6.2.3 observados; compatibilidad final pendiente |
| Motion del robot | Fuera de esta fase; no necesita conectarse para etiquetar, preparar o entrenar |

El servidor tiene RTX 6000 Ada de 48 GB, unos 503 GiB de RAM y Docker/NVIDIA ya
operativos. Comparte GPU con Ollama; conservar esas cargas. El entrenamiento
limita CPU/RAM, pero no reserva ni limita VRAM. La instalación usa recursos
propios `app2-cvat` y `app2-training`, sin modificar drivers del host.

## 3. Retomar hoy con el servidor existente

En una terminal del PC, comprobar acceso y consultar estado sin cambiar servicios:

```bash
ssh -p 2649 -o ConnectTimeout=10 luisacuna@192.168.1.43 \
  'bash "$HOME/app2/setup/install_server.sh" --status'
```

Para abrir CVAT, mantener otra terminal abierta:

```bash
ssh -p 2649 -N -o ExitOnForwardFailure=yes \
  -L 127.0.0.1:18080:127.0.0.1:18080 luisacuna@192.168.1.43
```

Abrir **http://localhost:18080**, usuario **app2_admin**. Consultar la contraseña
sólo en una terminal privada; no pegarla en un chat, log, captura o repositorio:

```bash
ssh -p 2649 luisacuna@192.168.1.43 \
  'cat "$HOME/app2/secrets/cvat-admin.json"'
```

El servicio escucha únicamente en loopback. El túnel no inicia entrenamiento
ni manda órdenes al robot; cerrarlo con Ctrl+C no detiene CVAT. Usar `localhost`
en el navegador, que es el Host configurado del editor. Si 18080 está ocupado
en el PC, identificar su proceso antes de abrir otro túnel:

```bash
ss -ltnp 'sport = :18080'
```

No ejecutar `--install` para una sesión normal. Si CVAT está detenido y se quiere
arrancarlo, la acción explícita en el servidor es:

```bash
bash "$HOME/app2/setup/cvat/cvat.sh" --up
bash "$HOME/app2/setup/cvat/cvat.sh" --status
```

Si ya hay una instalación con errores, revisar primero el estado y sus logs;
no borrar datos ni recrear todo como diagnóstico.

## 4. Llegar desde otro PC

Se necesita Linux con Git, OpenSSH, tar, herramientas SHA256 y un navegador.
No instalar CUDA, CVAT o RF-DETR en el PC para usar el servidor existente.

1. Tener acceso a la red privada de `192.168.1.43` y al puerto 2649, directamente
   o mediante una VPN ya autorizada. No hay acceso público/VPN configurado por
   esta intervención. Estar conectado a la red del robot no garantiza esa ruta.
2. Usar una identidad SSH autorizada para ese servidor. Un PC nuevo puede
   requerir que su administrador autorice su clave pública. **No copiar claves
   privadas del PC anterior ni cambiar la autenticación del servidor a ciegas.**
3. Clonar la rama publicada para recuperar el código y la documentación actuales.
   Recuperar aparte las fotos, evidencias y demás archivos privados necesarios:
   Git no contiene imágenes, modelos, la base de datos CVAT ni credenciales.
4. Seguir la sección anterior; cerrar un PC no elimina los datos del servidor.

Comprobaciones locales de herramientas y ruta:

```bash
git --version
ssh -V
tar --version
command -v sha256sum
ip route get 192.168.1.43
```

Estas huellas públicas se obtuvieron el 19-10-2026 por una conexión SSH ya
confiable. Comparar la que muestre el primer acceso del nuevo PC; si difiere,
comprobar el servidor por otro canal antes de aceptar o borrar `known_hosts`:

| Clave de host | Huella observada |
|---|---|
| ED25519, 256 bits | `SHA256:BQU7bkrwnPtnKV039U+aF1o8Pz25bmr7eKHVTWs8Pd4` |
| ECDSA, 256 bits | `SHA256:aXrEA9wNMojf5QVMCVbv4hTFI0f6TtpuQXHA0nK6bK8` |
| RSA, 3072 bits | `SHA256:lSnlDzQdHNJ4hw9c3+1a2Apcdu/6IzPeufLdW7SZPUc` |

No se ha cambiado ninguna cuenta, clave, firewall o ruta para crear este relevo.

### Recuperar el código y las fotografías

Repositorio: `git@github.com:acuna-luis/humanoide.git`, rama `vision-reconoce`.
Para un PC nuevo, clonar en una carpeta que todavía no exista:

```bash
git clone --branch vision-reconoce git@github.com:acuna-luis/humanoide.git Humanoide
cd Humanoide
git status --short --branch
git rev-parse HEAD
```

Conservar el commit mostrado como versión recuperada y contrastarlo con la
publicación que se vaya a usar. No aplicar parches antiguos encima de ese clon
por rutina. En un checkout existente, revisar primero su estado y conservar
cualquier trabajo local antes de actualizarlo.

El paquete descrito en [backup y migración](BACKUP_Y_MIGRACION.md) conserva la
base histórica `06250fb93f47e5a48c93c129819e2b7327b70ca7`, su parche local y
los archivos nuevos de aquel momento. Es una alternativa de recuperación de
esa instantánea, no la fuente actual después de esta publicación. El overlay
posterior también es fechado: ninguno de esos dos paquetes contiene el helper
de importación real ni las capturas y recibos posteriores del trabajo 5.
Consultar el [piloto real](PILOTO_PIEZAS_REALES.md) para sus ubicaciones privadas.

Mantener los dos directorios hermanos en el nuevo PC:

```text
directorio_de_trabajo/
  Humanoide/                         # Código y documentación
  Humanoide-vla-evidence/             # Material privado fuera de Git
    app2/reference/2026-10-19/        # Lámina y cinco imágenes de cámaras
    20261019T101640Z_APP2_SERVER_INSTALL/
    20261019T094304Z_APP2_VISION_RUNTIME_READONLY/
```

El paquete incluye un `README_RESTAURAR.md` con los comandos exactos. Restaurar
en una carpeta nueva; no aplicar el parche encima de trabajo propio existente.
Verificar todos los hashes antes de usar imágenes o recetas restauradas.
El paquete contiene material privado de fábrica: traslado sólo a almacenamiento
propio autorizado. Su presencia en el PC actual no constituye copia externa.

## 5. Inventario que no debe confundirse con el repositorio

| Ubicación | Contenido / tratamiento |
|---|---|
| `scripts/app2/server/` en el repo | Recetas reproducibles; no son los datos guardados por CVAT |
| `~/app2/setup/` en servidor | Copia instalada de recetas; comparar antes de actualizar, no sobrescribir por rutina |
| `~/app2/cvat/upstream/` | Fuente CVAT pública fijada por commit/SHA; conserva modos de lectura de bind mounts |
| `~/app2/cvat/images.lock.yml` | Diez imágenes por digest; copia versionada en recetas |
| `~/app2/secrets/cvat-admin.json` | Credencial local, 0600; no está en el paquete ni en Git |
| `~/app2/receipts/` | Recibos de instalación y pruebas; no sustituye el backup de datos |
| Siete volúmenes `app2-cvat_*` | Base de datos, imágenes, claves, eventos, caché y logs de CVAT |
| `app2_datasets` | Versiones COCO preparadas; montaje sólo lectura al entrenar |
| `app2_training_cache` | Pesos públicos y caché de librerías; UID 10001 |
| `app2_checkpoints` | Smokes y futuros entrenamientos; modelos/resultados no están en Git |
| Archivo privado del PC | Originales, manifiestos y evidencias; consultar [índice de fotos](FOTOS_Y_FUENTES.md) |

Los tres volúmenes de entrenamiento usan UID/GID 10001. No resolver permisos
con `chmod 777`, `chown` sobre todo app2 o escritura directa en `/var/lib/docker`.
Las recetas de transferencia usan contenedores temporales y volúmenes propios.

## 6. Trabajo siguiente, en orden

La [guía de datos y entrenamiento](DATOS_Y_ENTRENAMIENTO.md) desarrolla cada paso:

1. Confirmar referencias objetivo y confundibles, criterio de identificación,
   marcajes disponibles y catálogo de clases. La forma visual puede no bastar
   para separar dos referencias prácticamente iguales; medirlo con ejemplos reales.
2. Reunir un piloto de 30–50 escenas diversas y etiquetar máscaras por instancia
   en CVAT. Conservar origen, sesión, clase y SHA256. Las fotos iniciales son
   referencias, no un dataset suficiente ni un conjunto de prueba independiente.
3. Revisar etiquetas y exportar COCO. Preparar splits por sesión/unidad con el conversor
   CVAT → COCO local ya versionado y probado; revisar los datos reales.
4. Importar la versión revisada, ejecutar `--check` y entrenar un piloto de unas
   tres épocas. Medir memoria/tiempo; revisar errores, no sólo pérdida.
5. Añadir evaluación/inferencia de checkpoint propio y exportación ONNX de esos
   pesos. Los comandos smoke actuales usan el modelo público, no el fine-tuning.
6. Sólo tras superar lo anterior: compatibilidad/paridad TRT 8.6 en Vision,
   adaptador de imágenes SHM y latencia bajo carga. Pose 3D y manipulación se
   abordarán después, con su propio plan y comprobaciones físicas.

El conversor y la inferencia de un checkpoint con manifiesto ya están
verificados en el flujo sintético. Faltan evaluación de referencias reales y
exportación de pesos ajustados para Orin. La guía señala los límites actuales.

## 7. Problemas frecuentes y cómo continuar

| Síntoma | Primera comprobación / respuesta |
|---|---|
| SSH timeout | Ruta privada, puerto 2649, servidor encendido; no reinstalar Docker |
| `Permission denied` en SSH | Clave/cuenta autorizada en ese PC; resolver con administrador, sin copiar claves privadas |
| Huella SSH distinta | Verificar identidad del servidor; no desactivar comprobación de host |
| Navegador no abre CVAT | Túnel activo, puerto local libre y `--status` en servidor; usar localhost |
| API 406 | Esta versión usa `Accept: application/vnd.cvat+json`; el verificador actual ya lo contempla |
| API autenticada 500 / OPA | Revisar aliases/ALLOWED_HOSTS internos y logs; no desactivar autorización |
| Vector/Grafana reinician por permisos | Revisar modos de fuentes públicas según [receta CVAT](../../scripts/app2/server/cvat/README.md); no cambiar datos/secretos |
| Faltan pesos o falla caché | Revisar manifiesto/cache de UID 10001 y [receta de entrenamiento](../../scripts/app2/server/training/README.md); no dar red al entrenamiento |
| Falta `/checkpoints/runs` | Normal antes del primer entrenamiento real: las pruebas existentes están bajo `smoke/` |
| COCO/check de dataset falla | Corregir exportación/mapping/splits, generar una versión nueva; no saltar el check |
| CUDA sin memoria | Consultar ocupación compartida y bajar batch/configuración del trabajo propio; no detener Ollama ajeno |
| Diferencias después de actualizar | Comparar imagen, lock y freeze con informe; respaldar antes de migrar datos |

Para logs del proyecto CVAT, consulta de lectura en el servidor:

```bash
docker ps -a --filter label=com.docker.compose.project=app2-cvat
bash "$HOME/app2/setup/cvat/cvat.sh" --status
docker ps -a --filter label=com.docker.compose.project=app2-training
```

Después de identificar un contenedor propio, usar `docker logs --tail 100 NOMBRE`.
No usar limpiezas globales, `down -v` o borrar volúmenes como reparación.

## 8. Texto para entregar a otro agente

```text
Continúa app2 en este repositorio. Lee AGENTS.md, completo
docs/PROJECT_SOURCE_OF_TRUTH.md y docs/SYSTEM_CUSTOMIZATIONS.md; después
docs/app2/README.md, RETOMAR_APP2.md, SERVIDOR_LOCAL_INSTALACION.md,
DATOS_Y_ENTRENAMIENTO.md y el plan local. Para datasets/entrenamiento lee
también docs/vla/CRUZR_S2_VLA_TELEOP_DATA_GUIDE.md.
Ejecuta git status y conserva el trabajo local. No hay autorización implícita
para commit/push ni para modificar o mover el robot.
Servidor existente: ssh -p 2649 luisacuna@192.168.1.43. No reinstales para
retomar: empieza por --status. CVAT 2.79.0 + RF-DETR 1.11.2 están comprobados
con datos sintéticos. Las fotos privadas están fuera de Git; revisa hashes.
Siguiente hito: catálogo confirmado, piloto de escenas variadas, máscaras y
splits revisados. Existe conversor COCO y demo de checkpoint con manifiesto; faltan evaluación
de piezas reales, exportación propia para TRT8.6 y adaptador SHM. No presentes smokes públicos como
modelo de piezas entrenado. Antes de modificar, respalda y registra cada cambio
en fuentes de verdad y SYSTEM_CUSTOMIZATIONS. Mantén datos/entrenamiento local.
```

Al cerrar cada intervención, anotar dataset/hash, tareas CVAT, estado del proceso,
ruta de ejecución/checkpoint, métricas, cambios aplicados, respaldo y siguiente
paso. Así el siguiente operador retoma desde hechos comprobados.
