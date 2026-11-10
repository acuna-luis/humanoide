# Candidato experimental SmolVLA ARM64 en CPU

**Pendiente:** no se ha construido ni ejecutado esta imagen; no conecta ni
habilita movimiento. La ruta de GPU Ada probada continúa siendo la del shadow.
Vision usa L4T R36.3/ARM64 y su Python 3.10 host carece de LeRobot. El
checkpoint fue entrenado con LeRobot 0.5.1; su
[commit fijado](https://github.com/huggingface/lerobot/blob/1396b9fab7aecddd10006c33c47a487ffdcb54b4/pyproject.toml)
exige Python ≥3.12, PyTorch ≥2.7 y torchvision ≥0.22. La imagen Ada es AMD64.
La imagen histórica de GR00T en Vision es ARM64, pero su historial indica
PyTorch 2.6/torchvision 0.21 y no acredita el entorno SmolVLA.

El digest `df540bfd30bd380e89a349611ce42aa67bcb542d58c047706616eb6ba2f86a1b`
identifica el manifiesto ARM64 de Python 3.12 slim del índice multi-arquitectura
`935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df`.
Las ruedas PyPI de torch 2.7.1 y torchvision 0.22.1 para CPython 3.12/aarch64
existen; la de torch inspeccionada no contiene bibliotecas CUDA. Eso no prueba
que todo LeRobot ni el checkpoint funcionen en el robot. No actualizar JetPack
para esta prueba. Según la [tabla NVIDIA](https://docs.nvidia.com/deeplearning/frameworks/install-pytorch-jetson-platform-release-notes/pytorch-jetson-rel.html),
sus builds PyTorch 2.7 indicadas corresponden a JetPack 6.2, no al 6.0 observado.

## Preparación de entradas offline

```bash
python3 -B scripts/vla/prepare_arm64_cpu_wheelhouse.py --download \
  --output /ruta_privada_nueva/arm64-cpu-prep
python3 -B scripts/vla/prepare_arm64_cpu_wheelhouse.py --check \
  --output /ruta_privada_nueva/arm64-cpu-prep
```

Se descargan cinco wheels verificadas y tres fuentes de `docopt` y `evdev`.
**Esto no es un wheelhouse completo**. Ambas fuentes carecen de wheel PyPI.
La wheel universal `docopt-0.6.2-py2.py3-none-any.whl` se construyó desde la
fuente verificada, sin red, en `built-wheels/`; SHA256
`924cfbf4d2654b5494650ee50ffb3d15b522cdff45eef3f1a2a948108e0c9ffd`.
`evdev` necesita compilación y cabeceras Linux para ARM64/CPython 3.12. Se
deben resolver, descargar y fijar por hash *todas*
las dependencias transitivas en un entorno ARM64 compatible con internet y
probar la instalación sin red. Una resolución cruzada de pip desde x86 puede
evaluar marcadores para x86 y solicitar equivocadamente `torchcodec`; no usar
su éxito como prueba ARM64. No se ha encontrado un constructor ARM64 externo
en el inventario actual de PC/Ada. Un ensayo exploratorio de resolución
cruzada con marcadores ARM y wheel `docopt` alcanza el requisito de `evdev`,
que carece de wheel aarch64 en PyPI. Posteriormente, con la wheel propia de
evdev y restricciones derivadas del freeze Ada, se resolvió en el PC un
candidato de 100 wheels/492 MiB: `...CPU_ARM64_PREP/wheelhouse-candidate/`,
`SHA256SUMS` SHA256
`a92db7e630c79b22f5b36f5eabf6f136a36b51db40bf314b456bc39258daed4f`.
La resolución cruzada no acredita instalación, ABI o inferencia en ARM64. El
staging parcial inicial está en
`../Humanoide-vla-evidence/20261110_SMOLVLA_CPU_ARM64_PREP_V2/`; la versión
previa y el build de `docopt` se conservan en `...CPU_ARM64_PREP/`.

Para reconstruir ese candidato en el PC, con Internet y una salida nueva:

```bash
bash scripts/vla/smolvla_arm64_cpu/resolve_cpu_wheelhouse.sh --check \
  ../Humanoide-vla-evidence/20261109_VLA_BALL_OFFLINE_PREP/server/pip-freeze.txt \
  ../Humanoide-vla-evidence/20261110_SMOLVLA_CPU_ARM64_PREP/built-wheels
bash scripts/vla/smolvla_arm64_cpu/resolve_cpu_wheelhouse.sh --download \
  ../Humanoide-vla-evidence/20261109_VLA_BALL_OFFLINE_PREP/server/pip-freeze.txt \
  ../Humanoide-vla-evidence/20261110_SMOLVLA_CPU_ARM64_PREP/built-wheels \
  /ruta_privada_nueva/arm64-candidate
```

La receta exige las versiones y hashes del freeze y de las dos wheels
compiladas, Python 3.12 y pip 24.0 en x86_64. Genera las constraints excluyendo
las dependencias CUDA/x86 y ajusta explícitamente el marcador de arquitectura
del resolvedor; después exige que tanto constraints como el manifiesto completo
coincidan con los hashes de esta intervención. El resultado y la instalación
nativa siguen requiriendo comprobación. Si una descarga falla o alguna fuente
cambia, conservar la salida parcial y utilizar otra ruta nueva.

`build_evdev_host_gcc.sh --help` describe un constructor experimental con el
GCC nativo 11.4 observado en Vision: monta por separado toolchain y cabeceras
del host en rutas `/host` de sólo lectura, no oculta `/usr`, no incluye ROS ni
sockets, desactiva red y no expone dispositivos adicionales. Recibe fuentes y
herramientas fijadas por hash y sólo escribe en un directorio nuevo. El 10-11
se compiló evdev 2.0.0 y se importaron sus tres extensiones en otro contenedor
limpio ARM64 sin red. La wheel SHA256
`608caec9870027cc36b7c1b552b849b096e5fa001fb3264da49e2efb698f98bb` se conserva
en `...CPU_ARM64_PREP/built-wheels/`; la verificación sólo acredita esa
importación, no LeRobot, SmolVLA ni movimiento. El `--check` sólo revisa
prerequisitos. Fallos anteriores y prueba limpia se conservan en la evidencia.

El contexto de build debe tener un `wheelhouse/` completo, únicamente wheels
y un fichero `wheelhouse/SHA256SUMS` que cubra **todos** los archivos de las
wheels. `check_wheelhouse_manifest.py` exige cobertura exacta y tres hashes
fijados, y rechaza symlinks; la cobertura no demuestra procedencia de las otras
wheels ni que las dependencias sean completas. La imagen base ARM64 identificada por digest debe existir localmente:
importarla desde una copia comprobada, sin modificar la red del robot. La copia
privada `python312-arm64-base.tar` preparada en el PC tiene SHA256
`47a52dc83e013b728d74aafdedf0f365881632e64f88c4aa1a1bd913471309e6` y
contiene la configuración de imagen
`sha256:4703adf8fdd93b1441114e4f87ce2c62f7373fc5f88bda6a546c551625bcc71c`.
La copia carece de etiqueta: tras importarla habrá que comprobar el ID y usar
una etiqueta local nueva como argumento `BASE_IMAGE`, sin sobrescribir otras.
Por ejemplo, comprobar primero que `cruzr-local-python312-arm64:base-20261110`
no existe, cargar el tar en el constructor, contrastar la arquitectura y el ID
indicados y asignar esa nueva etiqueta sólo al ID comprobado. El almacenamiento
de imágenes y la carga deben registrarse y vigilar recursos; no hacerlo sobre
Vision durante su operación sin una evaluación previa de impacto.
El Dockerfile instala únicamente desde wheelhouse y comprueba versión, ausencia
de CUDA e importación de SmolVLA; ningún resultado ha sido probado aún.

`build_cpu_venv.sh` ofrece un ensayo acotado en contenedor con CPU2 y 4 GiB,
sin red ni ROS. Verifica manifiesto y constraints, instala en una carpeta nueva
y comprueba importaciones. El 10-11, la copia interrumpida se reanudó sin
sobrescribir y la instalación en Vision terminó con `pip check` e importación
de SmolVLA correctos. El venv está ligado al montaje `/env` y a la imagen base
por ID; no debe ejecutarse directamente en el host.

Se ha ejecutado el checkpoint de pelota en CPU ARM64 de Vision con una
observación grabada, en contenedor aislado y sin órdenes físicas. Produjo una
predicción en 62,932 s. No es una prueba con datos en vivo ni demuestra agarre
o control; esta latencia tampoco acredita capacidad para un lazo de control.
La copia de Vision está en `/home/walker/cruzr-smolvla-arm64-20261110-inference/`
y el venv en `/home/walker/cruzr-smolvla-arm64-20261110-venv/`. La receta
versionada `run_offline_one.sh --help` recibe esas rutas, el hash de la
observación y las rutas de dataset, checkpoint y VLM; su `--check` precede a
`--run`. El exportador `scripts/vla/prepare_ball_historical_shadow_input.py`
reconstruyó la observación con su imagen y sellos originales; hash del JSONL
`97f220bd7f0145e7341629c9c16b1d514452f4a1b18190f9f70871cdf773534b`.

La ejecución exacta del 10-11, dentro de Vision, fue:

```bash
cd /home/walker/cruzr-smolvla-arm64-20261110-inference
bash scripts/smolvla_arm64_cpu/run_offline_one_v2.sh --check \
  /home/walker/cruzr-smolvla-arm64-20261110-venv train checkpoint vlm \
  historical-observation.jsonl 97f220bd7f0145e7341629c9c16b1d514452f4a1b18190f9f70871cdf773534b
bash scripts/smolvla_arm64_cpu/run_offline_one_v2.sh --run \
  /home/walker/cruzr-smolvla-arm64-20261110-venv train checkpoint vlm \
  historical-observation.jsonl 97f220bd7f0145e7341629c9c16b1d514452f4a1b18190f9f70871cdf773534b
```

El wrapper remoto `run_offline_one_v2.sh` coincide con la fuente versionada
`run_offline_one.sh`, SHA256
`5466052a5a193666ea4370d3bf970b703fe393bdcda5eff9ece662ee31966449`.
El índice de todos los archivos de entrada contrastados entre PC y Vision está
en `...CPU_ARM64_PREP/vision-inference-inputs.sha256` con SHA256
`4dc06e3bc8a6949a01973f547fa064f2791011d89b08bd761d75f74741005f83`.
La salida `vision-inference-run-v2.jsonl` tiene SHA256
`d08bf262b984c8388bb87a6a7d1c30060bc2f939e76ef065f882cab37c9a80d2`.
Tras terminar no quedaba el contenedor temporal y había ~13 GiB disponibles
en Vision. El primer intento está conservado: falló antes de cargar modelo
porque el montaje VLM no coincidía con la ruta fijada del checkpoint.

### Reanudación de la copia interrumpida

La copia propia está en Vision
`/home/walker/cruzr-smolvla-arm64-20261110-wheelhouse/`; no se conoce su
estado posterior a la pérdida de conectividad. La copia del 10-11 se completó
tras reconexión y pasó verificación. Ante una futura interrupción, tras
restablecer la conexión y redescubrir estado, puede reanudarse con `rsync --ignore-existing` desde
`...CPU_ARM64_PREP/wheelhouse-candidate/`, sin sustituir archivos existentes;
copiar las constraints, wrapper y checker sólo si faltan. A continuación
comparar los hashes del wrapper/checker y ejecutar `build_cpu_venv.sh --check`
contra la carpeta y constraints recibidas. El checker rechaza ruedas ausentes,
extras o dañadas, incluidos temporales que pudieran persistir. Si falla, no
instalar ni sobrescribir: conservar esta copia y usar otra carpeta nueva tras
identificar la causa. El destino del venv también debe ser una carpeta nueva
separada. El fallo de red no informa sobre el estado físico del robot.

Cuando las entradas estén listas, en un **constructor ARM64 aislado** y sin
servicios críticos, incluir `constraints-arm64-from-ada.txt` verificado con el
hash que figura en el Dockerfile. El Dockerfile no incluye directiva `syntax`
externa; el backend deberá soportar `RUN --mount` sin descargar un frontend.
La construcción por Dockerfile aún no se ha ensayado ni acredita los límites
de recursos del wrapper `build_cpu_venv.sh`. Como candidato, ejecutar:

```bash
docker build --network=none --platform=linux/arm64 \
  --build-arg BASE_IMAGE=cruzr-local-python312-arm64:base-20261110 \
  -f Dockerfile -t cruzr-smolvla-ball-arm64-cpu:experimental .
```

Registrar el ID exacto, entorno, procedencia y hashes antes de transferirlo.
Una prueba futura debe correr sin red, sin ROS, sin GPU, sin dispositivos y
con entradas de modelo y dataset sólo lectura; medir recursos y latencia antes
de proponer su uso a bordo. Nunca usar este candidato como publicador físico.
