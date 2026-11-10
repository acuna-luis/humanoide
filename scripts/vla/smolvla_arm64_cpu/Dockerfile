# EXPERIMENTAL: not built or tested on Vision. Offline CPU-only candidate.
# wheelhouse/ must be complete and validated separately before a build.
ARG BASE_IMAGE=python@sha256:df540bfd30bd380e89a349611ce42aa67bcb542d58c047706616eb6ba2f86a1b
FROM ${BASE_IMAGE}

ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 \
    HF_HUB_DISABLE_IMPLICIT_TOKEN=1 WANDB_DISABLED=true PYTHONDONTWRITEBYTECODE=1 \
    CUDA_VISIBLE_DEVICES=""

COPY check_wheelhouse_manifest.py /tmp/check_wheelhouse_manifest.py
COPY constraints-arm64-from-ada.txt /tmp/constraints.txt
# Exact manifest coverage is mandatory but does not prove dependency provenance
# or runtime compatibility. No robot actuator is mounted or controlled.
RUN --mount=type=bind,source=wheelhouse,target=/wheelhouse,readonly \
    echo 'a92db7e630c79b22f5b36f5eabf6f136a36b51db40bf314b456bc39258daed4f  /wheelhouse/SHA256SUMS' | sha256sum -c \
    && echo '43f61aa31b210761b8b77847e6cac3334a1419dfe59e612d34d5ab9bec04a7b5  /tmp/constraints.txt' | sha256sum -c \
    && python /tmp/check_wheelhouse_manifest.py /wheelhouse \
    && python -m pip install --no-cache-dir --no-index --only-binary=:all: \
       --find-links=/wheelhouse -c /tmp/constraints.txt 'lerobot[smolvla]==0.5.1' 'torch==2.7.1' 'torchvision==0.22.1' \
    && python -m pip check \
    && python -c 'import platform,sys,torch,torchvision,lerobot; assert platform.machine() == "aarch64" and sys.version_info >= (3,12); assert torch.__version__.split("+")[0] == "2.7.1"; assert torchvision.__version__.split("+")[0] == "0.22.1"; assert torch.version.cuda is None; from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy'

CMD ["python", "-c", "print('Entorno ARM64 CPU: construcción experimental; no controla el robot.')"]
