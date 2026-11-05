#!/usr/bin/env python3
"""One real optimizer step on converted synthetic COCO; save, reload and infer."""
from __future__ import annotations
import argparse
import gc
import json
from pathlib import Path
import time

from common import RESOLUTION, cached_weights, new_run, runtime_inventory, sha256, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, default=Path("/checkpoints/workflow-training"))
    parser.add_argument("--synthetic-only", action="store_true", required=True,
                        help="Required: this short check does not qualify real material recognition")
    args = parser.parse_args()
    from coco_prepare import validate_coco_dataset
    validation = validate_coco_dataset(args.dataset)
    import torch
    from pytorch_lightning import Callback, seed_everything
    from rfdetr import RFDETRDataModule, RFDETRModelModule, RFDETRSegNano, build_trainer
    from rfdetr.config import RFDETRSegNanoConfig, SegmentationTrainConfig
    from rfdetr.datasets.coco import annotated_category_ids, filter_parent_categories
    from torch.utils.tensorboard import SummaryWriter
    from PIL import Image
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA unavailable; this check will not silently fall back to CPU")
    output = new_run(args.output_root, "checkpoint_roundtrip")
    write_json(output / "runtime.json", runtime_inventory())
    write_json(output / "dataset_validation.json", validation)
    train_coco = json.loads((args.dataset / "train/_annotations.coco.json").read_text())
    categories = train_coco["categories"]
    effective_categories = filter_parent_categories(categories, annotated_category_ids(train_coco))
    if not effective_categories:
        raise ValueError("No trainable categories")
    class_mapping = {str(i): int(c["id"]) for i, c in enumerate(effective_categories)}
    seed_everything(42, workers=True)
    model_config = RFDETRSegNanoConfig(pretrain_weights=str(cached_weights()), resolution=RESOLUTION,
                                      device="cuda:0", num_classes=len(effective_categories))
    train_config = SegmentationTrainConfig(
        dataset_dir=str(args.dataset), dataset_file="roboflow", output_dir=str(output / "fit"),
        batch_size=1, epochs=1, num_workers=0, multi_scale="off", scale_jitter=False,
        amp_dtype="auto", accelerator="gpu", devices=1, use_ema=False, tensorboard=False,
        wandb=False, mlflow=False, clearml=False, save_dataset_grids=False,
        progress_bar=None, run_test=False, dont_save_weights=True, seed=42,
    )

    class ParameterEvidence(Callback):
        backward_calls = 0
        nonzero_gradients = 0
        parameter_name = None
        before = None
        after = None

        def on_after_backward(self, trainer, module):
            self.backward_calls += 1
            for parameter in module.parameters():
                if parameter.grad is not None:
                    if not torch.isfinite(parameter.grad).all():
                        raise RuntimeError("Non-finite gradient")
                    self.nonzero_gradients += int(torch.count_nonzero(parameter.grad).item() > 0)

        def on_before_optimizer_step(self, trainer, module, optimizer):
            for name, parameter in module.named_parameters():
                if parameter.grad is not None and torch.count_nonzero(parameter.grad).item():
                    self.parameter_name = name
                    self.before = parameter.detach().float().cpu().clone()
                    return
            raise RuntimeError("No parameter with nonzero gradient before optimizer step")

        def on_train_batch_end(self, trainer, module, outputs, batch, batch_idx):
            if self.parameter_name:
                self.after = dict(module.named_parameters())[self.parameter_name].detach().float().cpu().clone()

    evidence = ParameterEvidence()
    started = time.perf_counter()
    try:
        module = RFDETRModelModule(model_config, train_config)
        datamodule = RFDETRDataModule(model_config, train_config)
        trainer = build_trainer(train_config, model_config, fast_dev_run=1,
            include_training_callbacks=False, enable_model_summary=False,
            num_sanity_val_steps=0, logger=False, enable_checkpointing=False)
        trainer.callbacks.append(evidence)
        torch.cuda.reset_peak_memory_stats()
        trainer.fit(module, datamodule)
        torch.cuda.synchronize()
        if trainer.global_step != 1 or evidence.backward_calls != 1 or evidence.before is None:
            raise RuntimeError("Expected one optimizer step and measured gradients")
        delta = float((evidence.after - evidence.before).abs().max())
        if not delta > 0:
            raise RuntimeError("No measured parameter update")
        # Explicit safe tensor/dict checkpoint; no pickle Namespace or remote paths.
        state = {k: v.detach().cpu().clone() for k, v in module.model.state_dict().items()}
        checkpoint = output / "synthetic_step1.pth"
        config = model_config.model_dump(mode="json")
        config["class_names"] = [c["name"] for c in effective_categories]
        torch.save({"model": state, "args": config}, checkpoint)
        manifest = {"architecture": "RFDETRSegNano", "resolution": RESOLUTION,
            "rfdetr_version": "1.11.2", "synthetic_only": True, "optimizer_steps": 1,
            "checkpoint_sha256": sha256(checkpoint), "categories": categories,
            "class_index_to_category_id": class_mapping, "num_classes": len(effective_categories),
            "dataset_version": args.dataset.name,
            "dataset_manifest_sha256": sha256(args.dataset / "dataset_manifest.json"),
            "train_annotations_sha256": sha256(args.dataset / "train/_annotations.coco.json"),
            "accuracy_validated": False}
        write_json(checkpoint.with_suffix(".manifest.json"), manifest)
        reloaded = RFDETRSegNano(pretrain_weights=str(checkpoint), resolution=RESOLUTION,
                                num_classes=len(effective_categories), device="cuda:0")
        loaded_state = reloaded.model.model.state_dict()
        if set(loaded_state) != set(state) or any(not torch.equal(state[k], loaded_state[k].detach().cpu()) for k in state):
            raise RuntimeError("Reloaded model parameters differ from saved trained tensors")
        image_data = json.loads((args.dataset / "valid/_annotations.coco.json").read_text())["images"][0]
        with Image.open(args.dataset / "valid" / image_data["file_name"]) as image:
            prediction = reloaded.predict(image.convert("RGB"), threshold=0.0)
        import numpy as np
        if (not np.isfinite(prediction.xyxy).all() or not np.isfinite(prediction.confidence).all()
                or prediction.mask is None or not np.isfinite(prediction.mask).all()
                or len(prediction.xyxy) != len(prediction.class_id)
                or len(prediction.xyxy) != len(prediction.confidence)
                or len(prediction.xyxy) != len(prediction.mask)
                or not set(map(int, prediction.class_id)).issubset(set(range(len(effective_categories) + 1)))):
            raise RuntimeError("Reloaded checkpoint inference failed")
        writer = SummaryWriter(str(output / "tensorboard"))
        writer.add_scalar("infrastructure/optimizer_steps", trainer.global_step, 1)
        writer.add_scalar("infrastructure/measured_parameter_max_delta", delta, 1)
        writer.close()
        result = {"status": "PASS", "optimizer_steps": 1, "backward_calls": evidence.backward_calls,
            "parameters_with_nonzero_finite_gradient": evidence.nonzero_gradients,
            "updated_parameter": evidence.parameter_name, "max_parameter_delta": delta,
            "checkpoint": str(checkpoint), "checkpoint_sha256": sha256(checkpoint),
            "checkpoint_reload_all_tensors_equal": True, "checkpoint_inference_finite": True,
            "raw_prediction_count": len(prediction),
            "background_prediction_count": int((prediction.class_id == len(effective_categories)).sum()),
            "foreground_prediction_count": int((prediction.class_id < len(effective_categories)).sum()),
            "torch_max_memory_allocated_bytes": torch.cuda.max_memory_allocated(),
            "torch_max_memory_reserved_bytes": torch.cuda.max_memory_reserved(),
            "elapsed_seconds": time.perf_counter() - started, "trainer_precision": trainer.precision,
            "synthetic_only": True, "app2_accuracy_claim": False}
        write_json(output / "result.json", result)
        print(json.dumps({"output": str(output), **result}))
    except Exception as error:
        write_json(output / "result.json", {"status": "FAIL", "error_type": type(error).__name__, "error": str(error)})
        raise


if __name__ == "__main__":
    main()
