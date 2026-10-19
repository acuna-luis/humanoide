"""Local-only paths and provenance for RF-DETR 1.11.2 App2 commands."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
from datetime import datetime, timezone
from pathlib import Path

RFDETR_VERSION = "1.11.2"
RFDETR_COMMIT = "7433d5919d0f7e72cc6cb78663e0a731afd499e0"
WEIGHTS_NAME = "rf-detr-seg-nano.pt"
RESOLUTION = 312


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def weights_path() -> Path:
    return Path(os.environ.get("RF_HOME", "/cache/rfdetr")) / WEIGHTS_NAME


def cached_weights() -> Path:
    """Refuse implicit download in offline commands and validate public weights."""
    from rfdetr.assets.model_weights import validate_pretrain_weights

    path = weights_path()
    if not path.is_file():
        raise FileNotFoundError(f"Run the explicit online precache command first: {path}")
    validate_pretrain_weights(str(path), strict=True)
    return path


def new_run(root: Path, label: str) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    path = root / f"{stamp}_{label}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def runtime_inventory() -> dict:
    import torch

    packages = {}
    for name in ("rfdetr", "torch", "torchvision", "transformers", "pytorch-lightning", "torchmetrics", "peft", "supervision"):
        packages[name] = importlib.metadata.version(name)
    if packages["rfdetr"] != RFDETR_VERSION:
        raise RuntimeError(f"Expected RF-DETR {RFDETR_VERSION}; found {packages['rfdetr']}")
    info = {
        "utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": packages,
        "rfdetr_source_commit": RFDETR_COMMIT,
        "torch_cuda": torch.version.cuda,
        "cudnn": torch.backends.cudnn.version(),
        "cuda_available": torch.cuda.is_available(),
        "cuda_devices": [],
    }
    if torch.cuda.is_available():
        for index in range(torch.cuda.device_count()):
            props = torch.cuda.get_device_properties(index)
            info["cuda_devices"].append({
                "index": index, "name": props.name,
                "total_memory_bytes": props.total_memory,
                "compute_capability": [props.major, props.minor],
            })
    return info


def local_train_kwargs(dataset: Path, output: Path, *, epochs: int, batch_size: int | str, workers: int) -> dict:
    """Shared pilot recipe; RF-DETR writes effective batch/configuration locally."""
    return {
        "dataset_dir": str(dataset),
        "dataset_file": "roboflow",  # Local COCO train/valid layout; no API access.
        "output_dir": str(output),
        "epochs": epochs,
        "batch_size": batch_size,
        "resolution": RESOLUTION,
        "multi_scale": "off",
        "amp_dtype": "auto",
        "device": "cuda:0",
        "num_workers": workers,
        "tensorboard": False,
        "wandb": False,
        "mlflow": False,
        "clearml": False,
        "save_dataset_grids": False,
        "progress_bar": "tqdm",
        "run_test": False,
        "seed": 42,
        "checkpoint_interval": 1,
    }
