# syntax=docker/dockerfile:1
# linux/amd64 manifest checked against registry-1.docker.io on 2026-10-19.
# Official base: compressed layers 4,432,776,135 bytes; do not install a host driver.
FROM pytorch/pytorch:2.10.0-cuda12.8-cudnn9-runtime@sha256:b85566342b86d13a67712e9315d40cdc2dad7f8d86df1aff3831f80835edbcca

LABEL org.opencontainers.image.title="app2 local RF-DETR training" \
      app2.rfdetr.version="1.11.2" \
      app2.rfdetr.source="7433d5919d0f7e72cc6cb78663e0a731afd499e0"

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    XDG_CACHE_HOME=/cache/xdg RF_HOME=/cache/rfdetr \
    HF_HOME=/cache/huggingface TORCH_HOME=/cache/torch \
    TRITON_CACHE_DIR=/cache/triton MPLCONFIGDIR=/cache/matplotlib \
    HF_HUB_DISABLE_TELEMETRY=1 DO_NOT_TRACK=1 \
    WANDB_MODE=disabled WANDB_DISABLED=true \
    OMP_NUM_THREADS=8 MKL_NUM_THREADS=8

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y libgl1 libglib2.0-0 python3-venv \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv --system-site-packages /opt/app2/venv

# Inherit the base's CUDA/PyTorch wheels without modifying Ubuntu's Python.
ENV VIRTUAL_ENV=/opt/app2/venv PATH="/opt/app2/venv/bin:${PATH}"
COPY requirements.txt /opt/app2/requirements.txt
RUN --mount=type=cache,id=app2_training_pip,target=/root/.cache/pip \
    python -m pip install --report /opt/app2/install-report.json -r /opt/app2/requirements.txt \
    && python -m pip check \
    && python -m pip freeze --all > /opt/app2/environment.freeze.txt \
    && groupadd --gid 10001 app2 \
    && useradd --uid 10001 --gid 10001 --create-home app2 \
    && mkdir -p /cache /datasets /checkpoints \
    && chown 10001:10001 /cache /datasets /checkpoints

COPY --chown=10001:10001 . /opt/app2/training/
WORKDIR /opt/app2/training
USER 10001:10001
CMD ["python", "smoke.py", "--help"]
