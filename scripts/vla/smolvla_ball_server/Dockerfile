FROM python:3.12-slim-bookworm@sha256:935c3c5b12357a7e10caa9c1e6ca5692344d97cf229832ef584be2cec9fc03df

# LeRobot 0.5.1 (fixed release commit); 2.7/0.22/0.5 are a compatible
# torch/torchvision/torchcodec family. Remaining dependencies are resolved at
# build time and recorded below; this is not a fully locked supply chain.
ARG LEROBOT_COMMIT=1396b9fab7aecddd10006c33c47a487ffdcb54b4
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates ffmpeg git libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir 'pip==25.2' \
    && python -m pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cu128 \
       'torch==2.7.1' 'torchvision==0.22.1'
# LeRobot pulls evdev through its input support; its wheel requires Linux UAPI
# headers and a compiler even though this image never operates a device.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential linux-libc-dev \
    && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir 'torchcodec==0.5.0' \
       "lerobot[smolvla] @ git+https://github.com/huggingface/lerobot.git@${LEROBOT_COMMIT}" \
    && python -m pip check \
    && mkdir -p /usr/local/share/cruzr-smolvla \
    && python -m pip freeze > /usr/local/share/cruzr-smolvla/pip-freeze.txt \
    && dpkg-query -W > /usr/local/share/cruzr-smolvla/dpkg-list.txt

# Runtime defaults are offline; do not configure any robot endpoints or Hub
# upload. Weights and datasets must be provisioned separately and deliberately.
ENV HF_HUB_OFFLINE=1 \
    HF_HUB_DISABLE_TELEMETRY=1 \
    HF_HUB_DISABLE_IMPLICIT_TOKEN=1 \
    WANDB_DISABLED=true \
    PYTHONDONTWRITEBYTECODE=1
CMD ["python", "-c", "print('Entorno SmolVLA preparado. No se ha iniciado entrenamiento.')"]
