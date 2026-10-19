# app2: CVAT Community privado en servidor

Receta creada y aplicada 19-10-2026 (Europe/Madrid). CVAT está instalado y se
comprobaron UI/API, acceso por túnel, cuenta local, anotación y exportación COCO
sintéticos. El [informe de instalación](../../../../docs/app2/SERVIDOR_LOCAL_INSTALACION.md)
registra inventario previo/posterior, incidencias y evidencia. Para retomar sin
reinstalar, seguir la [guía operativa](../../../../docs/app2/RETOMAR_APP2.md).

Versión estable fijada: **v2.79.0**, publicada 15-10-2026. Commit:
`9176834830e2e931a8d3a6857dcf43c6cc0ee927`.
Archivo: `https://codeload.github.com/cvat-ai/cvat/tar.gz/9176834830e2e931a8d3a6857dcf43c6cc0ee927`.
SHA256 verificado al preparar esta receta:
`dd269cb19c73f841c7bcd029c92fd1876eadd5a212fb4b55a2c7594511dd8c14`.
Los diez digests de imágenes resueltos se conservan en `images.lock.yml`, tanto
en esta carpeta versionada como en servidor/respaldo. Ese lock sólo contiene
referencias públicas de imágenes; no contiene secretos. No basta con los tags
de upstream ni se debe sobrescribir el lock existente para una sesión normal.

## Alcance y aislamiento

- Docker Compose existente, versión >=2.24.4. No instala paquetes del host.
- Proyecto `app2-cvat`; los nombres globales del vendor se retiran con `!reset`.
- Red propia `app2-cvat_cvat`; Traefik sólo descubre contenedores del proyecto.
- Única publicación: `127.0.0.1:18080` → Traefik8080. Dashboard8090 sin publicar.
- Siete volúmenes Docker con prefijo `app2-cvat_`: DB, datos, claves, logs,
  Redis, eventos y caché. Usan DockerRootDir, observado en SSD Samsung990PRO.
- No GPU, inferencia, entrenamiento ni conexión con Motion/Vision.
- CVAT básico completo: proyectos/tareas, polígonos/máscaras manuales, API,
  importación/exportación COCO y workers oficiales. Sin Nuclio/SAM añadido.

Se conserva **la analítica local oficial** (ClickHouse, Vector, Grafana).
Upstream la activa por defecto y varios backends dependen de ClickHouse.
`CVAT_ANALYTICS=0` oculta parte de la función, pero por sí solo no elimina esas
dependencias ni el transporte de logs. No se introduce una variante reducida
sin comprobar su ciclo completo de creación, anotación, importación y exportación.
Las fotos/anotaciones no se suben a CVAT Online ni se configura cloud storage.
Se necesita Internet para las descargas iniciales de imágenes/fuentes y para
que Grafana instale el plugin oficial fijado por upstream. El funcionamiento
posterior sin Internet debe ensayarse; esta receta no aplica un firewall egress.

La DB conserva la autenticación `trust` del Compose oficial en la red privada;
no se publica Postgres/Redis/ClickHouse. No es un límite contra administradores
Docker u otros usuarios con control del host. Traefik usa el socket Docker de
lectura que monta upstream. El proyecto se aisla para evitar conflictos; no es
un sandbox frente a un administrador del daemon.

## Aplicación en el servidor

Ejecutar sólo en el servidor autorizado. Copiar esta carpeta íntegra al servidor
junto con el resto de scripts app2. Antes de cambiar Docker, conservar inventario
de contenedores/imágenes/volúmenes/redes/puertos y comparar después; el script
no detiene cargas ajenas. El directorio pequeño guarda fuentes/configuración;
las fotos y resultados persistentes deben permanecer en volúmenes del SSD.

```bash
bash scripts/app2/server/cvat/cvat.sh --help
bash scripts/app2/server/cvat/cvat.sh --prepare "$HOME/app2/cvat"
bash scripts/app2/server/cvat/cvat.sh --check "$HOME/app2/cvat"
bash scripts/app2/server/cvat/cvat.sh --lock "$HOME/app2/cvat"
bash scripts/app2/server/cvat/cvat.sh --pull "$HOME/app2/cvat"
bash scripts/app2/server/cvat/cvat.sh --up "$HOME/app2/cvat"
bash scripts/app2/server/cvat/cvat.sh --status "$HOME/app2/cvat"
```

`--check` exige DockerRootDir `/var/lib/docker`, muestra su montaje y pide
200GiB libres para el presupuesto conjunto app2. Verificar que sigue siendo el
SSD separado observado; no cambia montajes ni aplica cuotas de disco/RAM/CPU.
`--up` conserva reinicio `always` oficial, persistente tras reiniciar el host.
La primera migración puede tardar: si la API aún no responde, revisar los logs
del proyecto y repetir `--status`, sin recrear ni borrar volúmenes.

La extracción usa `tar --same-permissions` sobre el archivo fijado y comprobado:
conserva los modos públicos de las fuentes vendor que Vector/Grafana leen por
bind mount. El `umask077` sigue protegiendo recibos, locks y demás archivos
generados. La primera aplicación reveló `Permission denied` en Vector
(`/etc/vector/vector.toml`) y Grafana (`/var/lib/grafana/dashboards`) porque una
versión anterior extraía como usuario sin conservar esos modos. Los aliases
DNS estaban presentes: ese incidente no demuestra un defecto de aliases.
Para una carpeta ya preparada, `--prepare` conserva lo existente y no repara
permisos automáticamente. La reparación debe limitarse a los archivos y
directorios vendor montados bajo `upstream/components/analytics/`, restaurando
los modos del archivo fijado; después, reiniciar sólo Vector/Grafana del
proyecto. No aplicar cambios recursivos a `~/app2`, secretos, volúmenes o datos.
El resultado real de esa reparación se registra en la intervención principal.

Crear administrador mediante terminal privada, después de responder API/UI:

```bash
bash scripts/app2/server/cvat/cvat.sh --admin "$HOME/app2/cvat"
```

Introduce nombre/correo y contraseña en los prompts de Django. No pasar la
contraseña como argumento, variable versionada, grabación de terminal o log.
La cuenta es local a esta instalación. No hay contraseña de administrador en
los scripts y no se reutilizan credenciales SSH ni de otros servicios.

Desde el PC, abrir el túnel en una terminal y mantenerla abierta:

```bash
ssh -p 2649 -N -o ExitOnForwardFailure=yes \
  -L 127.0.0.1:18080:127.0.0.1:18080 luisacuna@192.168.1.43
```

Abrir **http://localhost:18080** en Chrome. Usar `localhost`: el router oficial
se fija a ese Host. Si el puerto18080 del PC está ocupado, resolver ese conflicto
antes; cambiar sólo el puerto local produciría enlaces base inconsistentes.

## Verificación funcional y respaldo

`--status` verifica GET `/api/server/about` y GET `/`, además del estado de los
18 servicios. No demuestra que el etiquetado/exportación funcione.
Con la cuenta local, crear una tarea pequeña con una copia de imágenes propias,
anotar un polígono por instancia, guardar, reabrir y exportar **COCO1.0** con
imágenes. Comprobar JSON de instancias/clases/segmentación, reimportar a una
tarea de prueba y revisar que los contornos se conservan. Anotar IDs/resultados
y borrar sólo tareas de prueba si procede. No asumir que estar `Up` valida datos.

Guardar fuera de Git: fuente descargada/recibos SHA, `compose.app2.yml`, script,
`images.lock.yml`, `--config`, IDs/digests reales, estado de contenedores y prueba
UI/API/COCO. Para datasets reales, mantener originales, exportación COCO y
backup de tareas/proyectos en otra ubicación privada. Los siete volúmenes en
un mismo SSD son persistencia, no una copia externa. El backup consistente de
la DB requiere procedimiento propio; no copiar en caliente sus ficheros.

Reversión conservadora:

```bash
bash scripts/app2/server/cvat/cvat.sh --down "$HOME/app2/cvat"
```

Detiene/retira sólo contenedores y red de app2-cvat; preserva volúmenes,
imágenes, fuentes y bloqueo de versiones. No usa `docker system prune`, `down
--volumes` ni cambios de daemon. No reemplazar la fuente/lock sobre una DB ya
migrada: futuras actualizaciones requieren backup y guía oficial.

## Fuentes primarias consultadas

- [Release v2.79.0](https://github.com/cvat-ai/cvat/releases/tag/v2.79.0).
- [Compose exacto](https://github.com/cvat-ai/cvat/blob/9176834830e2e931a8d3a6857dcf43c6cc0ee927/docker-compose.yml).
- [Instalación Community](https://docs.cvat.ai/docs/administration/community/basics/installation/).
- [Analítica oficial](https://docs.cvat.ai/docs/administration/community/advanced/analytics/).
- [COCO](https://docs.cvat.ai/docs/dataset_management/formats/format-coco/).
- [Semántica Compose reset/override](https://docs.docker.com/reference/compose-file/merge/).

Quedan pendientes el ensayo completo de CVAT sin Internet, la reimportación
COCO, datos reales y recuperación de un backup completo. Pull/up, digests,
administrador, túnel y prueba sintética de polígono/exportación ya están
VERIFICADOS según el informe; no repetir la instalación para usar el editor.
No hay publicación de fotografías ni servicios externos autorizada por esta receta.
