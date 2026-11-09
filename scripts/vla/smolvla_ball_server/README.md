# Entorno aislado para experimento SmolVLA de pelota

**09-11-2026: imagen, GPU, dataset y piloto experimental offline comprobados.**
Esta receta no crea una política utilizable ni convierte las observaciones
existentes en acciones válidas. No publica, configura ni contacta el robot.

Servidor `aisrv`, usuario `luisacuna`: primera copia de fuentes en
`/home/luisacuna/cruzr-smolvla-ball-20261109/`, corrección de compilación de
`evdev` en `build2/` y fuente de descarga de modelos en `model-fetch/`. Primer
build falló por falta de cabeceras Linux; build2 finalizó con imagen
`sha256:4d15e9e6c5a1071bfe522a5258a8db07b448bc29f698c4a48c43c252754f36fa`.
`--gpu-check` detectó RTX 6000 Ada con torch 2.7.1+cu128 y CUDA runtime 12.8.
`lerobot-train --help` también terminó correctamente sin red ni GPU.
Hay diferencias entre los README históricos de las copias del servidor y esta
versión actual: consultar hashes en evidencia antes de reproducir.

Volumen propio `cruzr-smolvla-ball-public-models-20261109`, ~2,8 GiB: modelos
públicos fijados y 20 archivos verificados por SHA-256 offline. Un paso y un
benchmark de100 pasos completaron con modelo y procesador cargados offline.
Los datos privados seleccionados se transfirieron al servidor y se verificaron;
el piloto de1.000 pasos completó, sin publicar ni controlar el robot.
Evidencia privada: `../Humanoide-vla-evidence/20261109_VLA_BALL_OFFLINE_PREP/server/`
(construcciones, checks, inventarios, manifiesto, hashes, paquetes y estado).

## Fuente, dependencias y límites

- LeRobot 0.5.1: commit `1396b9fab7aecddd10006c33c47a487ffdcb54b4`.
- Base Python 3.12 Bookworm fijada por digest; PyTorch 2.7.1 y torchvision
  0.22.1 con ruedas CUDA 12.8; torchcodec 0.5.0. La instalación exige Internet
  a Debian, PyPI, PyTorch y GitHub. La construcción ejecuta código de terceros.
- No hay lock completo de dependencias transitivas ni snapshot de Debian. Un
  rebuild puede diferir. Conservar el identificador de imagen y exportar
  `/usr/local/share/cruzr-smolvla/pip-freeze.txt` y `dpkg-list.txt`; registrar
  fuentes y hash antes de afirmar que es reproducible byte a byte.
- El modelo base **no está incluido**. Su descarga, revisión de licencia y
  fijación de revisión/hash se gestionan aparte; no copiar tokens ni enviar
  grabaciones al Hub. Este proyecto necesita un contrato de acción cualificado
  y un dataset separado; `training_ready=false` sigue vigente.
- Durante la comprobación CUDA el contenedor usa `--network none` y ningún
  volumen de robot o de datos. Las variables HF desactivan red/telemetría para
  ejecuciones derivadas; para un entrenamiento offline habrá que mantener el
  aislamiento y aportar modelo/dataset local y salida propia de forma explícita.

## En el servidor, tras revisar esta receta

Comprobar espacio y estado de GPU y clientes sin detener nada. El SSD gestionado
por Docker dispone históricamente de espacio, pero no asumir capacidad o VRAM
libre actuales. El host comparte GPU con Ollama y otros servicios. **No borrar
imágenes, volúmenes o procesos de APP2.** La copia de esta carpeta al servidor
es una acción distinta que debe registrarse junto a su destino y hashes.

```bash
./server.sh --help
./server.sh --check
./server.sh --build
./server.sh --gpu-check
```

`--build` cambia el servidor y usa red; rechaza una etiqueta ya existente.
`--gpu-check` crea un contenedor temporal, usa la GPU y lo elimina al terminar;
no ejecuta entrenamiento. Registrar fecha, tiempo, consumo GPU, resultado y la
ausencia final del contenedor. La imagen construida resolvió dependencias y
pasó CUDA y las pruebas de uno y100 pasos; no extrapolar a otros parámetros.

La receta de entrenamiento experimental está en `OFFLINE_TRAINING.md`; los
objetivos siguen sin cualificar para control. No usar `lerobot-rollout`.

## Preparación de pesos públicos

`fetch_models.sh --fetch` crea un volumen nuevo exclusivo y ejecuta
`fetch_models.py` con dos snapshots públicos de Hugging Face, fijados por SHA
de revisión. Descarga archivos JSON, safetensors, TXT y las tarjetas README;
excluye derivados ONNX, fotografías y grabaciones privadas. Los repositorios son
`lerobot/smolvla_base` y `HuggingFaceTB/SmolVLM2-500M-Video-Instruct`; ambas
tarjetas declaran Apache-2.0, revisar las licencias y los términos efectivos.
Los tamaños mínimos de pesos son ~0,91 GB y ~2,03 GB respectivamente, más
metadatos y caché; reservar margen. Guarda SHA-256 de cada archivo obtenido y
un manifiesto en el volumen, sin registrar tokens. Ante fallo deja el volumen
parcial y rechaza otra ejecución con el mismo nombre para evitar sobrescrituras.

**Red:** esta fase usa `--network bridge` y el programa solicita los snapshots
mediante HTTPS, sin credenciales implícitas. Docker bridge no impone una lista
de destinos o protocolos, por lo que no se debe afirmar que exista aislamiento
de red por host; si se exige permitir exclusivamente destinos HTTPS concretos,
hace falta un proxy o un filtro de salida independiente antes de ejecutar.
Se mantiene `--network none` para el futuro entrenamiento con datos privados.
La carga local del modelo y procesador se verificó en las pruebas de uno y100
pasos; no extrapolar esa verificación a otros modelos o revisiones.

## Reversión selectiva

Para revertir, conservar antes el ID registrado y verificar que ningún
contenedor ajeno use la imagen.
Retirar exclusivamente la etiqueta creada con `docker image rm
cruzr-smolvla-ball:0.5.1-1396b9fa`; no ejecutar `docker system prune`, no eliminar
volúmenes ni servicios preexistentes. Docker BuildKit puede conservar capas o
caché, incluidas las de una construcción fallida: retirar la etiqueta no asegura
liberar esa caché y no debe hacerse una limpieza global. La copia de recetas en el servidor se
retira solo tras respaldar cualquier edición posterior. El volumen
`cruzr-smolvla-ball-public-models-20261109` contiene exclusivamente modelos
públicos según el manifiesto actual; antes de retirarlo verificar que ningún
contenedor lo use y que no se hayan agregado resultados o datos privados.
La orden selectiva sería `docker volume rm
cruzr-smolvla-ball-public-models-20261109`; no elimina otros volúmenes.
