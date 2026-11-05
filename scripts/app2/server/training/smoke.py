#!/usr/bin/env python3
"""Precache public weights, verify CUDA/inference, or run one synthetic train step.

The synthetic rectangles have no relationship to a private image or App2's
future classes. A passing smoke test validates software execution, not accuracy.
"""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path
import subprocess
import time

from common import RESOLUTION, RFDETR_COMMIT, cached_weights, new_run, runtime_inventory, sha256, weights_path, write_json


def synthetic_image(index: int = 0):
    from PIL import Image, ImageDraw

    image = Image.new("RGB", (RESOLUTION, RESOLUTION), (32, 32, 32))
    draw = ImageDraw.Draw(image)
    x = 35 + index * 10
    y = 50 + index * 8
    draw.rectangle((x, y, x + 99, y + 79), fill=(210, 180, 50))
    return image, [x, y, 100, 80]


def create_synthetic_coco(root: Path) -> Path:
    """Two train and two validation rectangles in RF-DETR's local COCO layout."""
    root.mkdir(parents=True, exist_ok=False)
    for split, offset in (("train", 0), ("valid", 2)):
        target = root / split
        target.mkdir()
        images, annotations = [], []
        for number in range(2):
            image, bbox = synthetic_image(number + offset)
            filename = f"synthetic_{number}.png"
            image.save(target / filename)
            images.append({"id": number + 1, "file_name": filename, "width": RESOLUTION, "height": RESOLUTION})
            x, y, w, h = bbox
            annotations.append({
                "id": number + 1, "image_id": number + 1, "category_id": 1,
                "bbox": bbox, "area": w * h, "iscrowd": 0,
                "segmentation": [[x, y, x + w, y, x + w, y + h, x, y + h]],
            })
        write_json(target / "_annotations.coco.json", {
            "info": {"description": "App2 synthetic software smoke only"},
            "licenses": [], "images": images, "annotations": annotations,
            "categories": [{"id": 1, "name": "synthetic_rectangle", "supercategory": "synthetic"}],
        })
    return root


def precache(output: Path) -> dict:
    from rfdetr import RFDETRSegNano
    from rfdetr.assets.model_weights import ModelWeights, download_pretrain_weights, validate_pretrain_weights

    path = weights_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    download_pretrain_weights(str(path), validate_md5=True)
    validate_pretrain_weights(str(path), strict=True)
    asset = ModelWeights.from_filename(path.name)
    assert asset is not None
    # Construction is CPU-only in this API; Nano's patch12 uses bundled DINO config.
    model = RFDETRSegNano(pretrain_weights=str(path), resolution=RESOLUTION, device="cpu")
    del model
    manifest = {
        "filename": path.name, "source_url": asset.url,
        "upstream_md5": asset.md5_hash, "sha256": sha256(path),
        "bytes": path.stat().st_size, "source_commit": RFDETR_COMMIT,
        "cpu_model_construction_passed": True,
    }
    write_json(path.parent / "public-weights-manifest.json", manifest)
    return manifest


def gpu_inference(output: Path) -> dict:
    import numpy as np
    import torch
    import torchvision
    from rfdetr import RFDETRSegNano

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable; verify NVIDIA Container Toolkit/runtime before continuing")
    torch.cuda.set_device(0)
    torch.cuda.reset_peak_memory_stats()
    # Exercise CUDA kernel launch, cuBLAS/backward, and torchvision's compiled CUDA op.
    matrix = torch.randn((256, 256), device="cuda", requires_grad=True)
    loss = (matrix @ matrix).square().mean()
    loss.backward()
    assert matrix.grad is not None and torch.isfinite(matrix.grad).all()
    boxes = torch.tensor([[0, 0, 10, 10], [1, 1, 9, 9]], dtype=torch.float32, device="cuda")
    selected = torchvision.ops.nms(boxes, torch.tensor([0.9, 0.8], device="cuda"), 0.5)
    assert selected.tolist() == [0]
    del matrix, loss, boxes, selected
    path = cached_weights()
    model = RFDETRSegNano(pretrain_weights=str(path), resolution=RESOLUTION, device="cuda:0")
    image, _ = synthetic_image()
    image.save(output / "synthetic_input.png")
    started = time.perf_counter()
    detections = model.predict(image, threshold=0.0)
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - started
    if detections.mask is None:
        raise RuntimeError("The segmentation model did not return a mask array")
    if not np.isfinite(detections.xyxy).all() or not np.isfinite(detections.confidence).all():
        raise RuntimeError("Inference produced non-finite outputs")
    summary = {
        "synthetic_input_sha256": sha256(output / "synthetic_input.png"),
        "weights_sha256": sha256(path),
        "resolution": RESOLUTION, "detections": len(detections),
        "mask_shape": list(detections.mask.shape),
        "inference_seconds_with_initialization": elapsed,
        "torch_max_memory_allocated_bytes": torch.cuda.max_memory_allocated(),
        "torch_max_memory_reserved_bytes": torch.cuda.max_memory_reserved(),
        "torchvision_cuda_nms_passed": True,
        "synthetic_cuda_backward_passed": True,
        "accuracy_claim": False,
    }
    del model
    gc.collect()
    torch.cuda.empty_cache()
    return summary


def synthetic_train(output: Path) -> dict:
    import torch
    from pytorch_lightning import Callback, seed_everything
    from rfdetr import RFDETRDataModule, RFDETRModelModule, build_trainer
    from rfdetr.config import RFDETRSegNanoConfig, SegmentationTrainConfig

    if not torch.cuda.is_available():
        raise RuntimeError("This training smoke requires a CUDA GPU")
    seed_everything(42, workers=True)
    dataset = create_synthetic_coco(output / "synthetic_dataset")
    model_config = RFDETRSegNanoConfig(
        pretrain_weights=str(cached_weights()), resolution=RESOLUTION,
        device="cuda:0", num_classes=1,
    )
    train_config = SegmentationTrainConfig(
        dataset_dir=str(dataset), dataset_file="roboflow", output_dir=str(output / "fit"),
        batch_size=1, epochs=1, num_workers=0,
        multi_scale="off", scale_jitter=False, amp_dtype="auto",
        accelerator="gpu", devices=1, use_ema=False,
        tensorboard=False, wandb=False, mlflow=False, clearml=False,
        save_dataset_grids=False, progress_bar=None, run_test=False,
        dont_save_weights=True, seed=42,
    )

    class BackwardEvidence(Callback):
        count = 0
        nonzero_parameters = 0

        def on_after_backward(self, trainer, module):
            self.count += 1
            for parameter in module.parameters():
                if parameter.grad is not None:
                    if not torch.isfinite(parameter.grad).all():
                        raise RuntimeError("Non-finite gradient in synthetic RF-DETR backward")
                    self.nonzero_parameters += int(torch.count_nonzero(parameter.grad).item() > 0)

    evidence = BackwardEvidence()
    module = RFDETRModelModule(model_config, train_config)
    datamodule = RFDETRDataModule(model_config, train_config)
    trainer = build_trainer(
        train_config, model_config, fast_dev_run=1,
        include_training_callbacks=False, enable_model_summary=False,
        num_sanity_val_steps=0, logger=False, enable_checkpointing=False,
    )
    trainer.callbacks.append(evidence)
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    trainer.fit(module, datamodule)
    torch.cuda.synchronize()
    if trainer.global_step != 1 or evidence.count != 1 or evidence.nonzero_parameters == 0:
        raise RuntimeError("Expected exactly one optimizer step and finite nonzero gradients")
    summary = {
        "optimizer_steps": trainer.global_step,
        "backward_calls": evidence.count,
        "parameters_with_nonzero_finite_gradient": evidence.nonzero_parameters,
        "trainer_precision": trainer.precision,
        "elapsed_seconds": time.perf_counter() - started,
        "torch_max_memory_allocated_bytes": torch.cuda.max_memory_allocated(),
        "torch_max_memory_reserved_bytes": torch.cuda.max_memory_reserved(),
        "dataset": "synthetic rectangles only", "accuracy_claim": False,
        "train_config": train_config.model_dump(mode="json"),
        "model_config": model_config.model_dump(mode="json"),
    }
    return summary


def export_onnx(output: Path) -> dict:
    """Export the public checkpoint and execute the graph on a synthetic tensor."""
    import numpy as np
    import onnx
    import onnxruntime as ort
    from rfdetr import RFDETRSegNano

    model = RFDETRSegNano(pretrain_weights=str(cached_weights()), resolution=RESOLUTION, device="cuda:0")
    started = time.perf_counter()
    path = model.export(
        output_dir=str(output / "onnx"), format="onnx", opset_version=17,
        shape=(RESOLUTION, RESOLUTION), batch_size=1, dynamic_batch=False,
        verbose=False, output_name="app2_seg_nano_312_public_smoke",
        notes={"purpose": "synthetic software smoke", "rfdetr_source": RFDETR_COMMIT},
    )
    onnx.checker.check_model(str(path))
    graph = onnx.load(str(path))
    options = ort.SessionOptions()
    options.intra_op_num_threads = 8
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(path), sess_options=options, providers=["CPUExecutionProvider"])
    inputs = session.get_inputs()
    if len(inputs) != 1 or inputs[0].shape != [1, 3, RESOLUTION, RESOLUTION]:
        raise RuntimeError(f"Unexpected static ONNX input signature: {[(i.name, i.shape) for i in inputs]}")
    outputs = session.run(None, {inputs[0].name: np.zeros((1, 3, RESOLUTION, RESOLUTION), dtype=np.float32)})
    if not outputs or not all(np.isfinite(value).all() for value in outputs):
        raise RuntimeError("ONNX Runtime did not produce finite outputs")
    return {
        "onnx_file": str(path), "sha256": sha256(path), "bytes": path.stat().st_size,
        "elapsed_seconds": time.perf_counter() - started,
        "ir_version": graph.ir_version,
        "opsets": [{"domain": i.domain, "version": i.version} for i in graph.opset_import],
        "inputs": [{"name": i.name, "shape": i.shape, "type": i.type} for i in inputs],
        "outputs": [{"name": meta.name, "shape": list(value.shape), "dtype": str(value.dtype)}
                    for meta, value in zip(session.get_outputs(), outputs)],
        "onnx_checker_passed": True, "onnxruntime_cpu_passed": True,
        "numerical_parity": "PENDING", "vision_tensorrt86_compatibility": "PENDING",
        "accuracy_claim": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("precache", "gpu", "train", "export"))
    parser.add_argument("--output-root", type=Path, default=Path("/checkpoints/smoke"))
    args = parser.parse_args()
    output = new_run(args.output_root, args.mode)
    write_json(output / "runtime.json", runtime_inventory())
    freeze = subprocess.run(["python", "-m", "pip", "freeze", "--all"], check=True, capture_output=True, text=True)
    (output / "environment.freeze.txt").write_text(freeze.stdout, encoding="utf-8")
    operations = {"precache": precache, "gpu": gpu_inference, "train": synthetic_train, "export": export_onnx}
    started = time.perf_counter()
    try:
        result = operations[args.mode](output)
        result.update({"status": "PASS", "mode": args.mode, "elapsed_total_seconds": time.perf_counter() - started})
        write_json(output / "result.json", result)
        print(json.dumps({"status": "PASS", "mode": args.mode, "output": str(output), "result": result}, sort_keys=True))
    except Exception as error:
        write_json(output / "result.json", {"status": "FAIL", "mode": args.mode, "error": str(error)})
        raise


if __name__ == "__main__":
    main()
