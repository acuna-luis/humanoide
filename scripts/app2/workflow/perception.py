"""File-only RF-DETR inference. No camera, ROS, robot or PLC control clients."""
from __future__ import annotations
import json
import math
from pathlib import Path
import time

from common import RESOLUTION, cached_weights, sha256


def checkpoint_category(class_id: int, mapping: dict[int, int]) -> int | None:
    """RF-DETR custom heads expose N as background; COCO public heads differ."""
    if class_id == len(mapping):
        return None
    if class_id not in mapping:
        raise ValueError("Class index is outside the checkpoint's mapping")
    return mapping[class_id]


class LocalPerception:
    def __init__(self, weights: Path | None = None, device: str = "cuda:0", threshold: float = .5):
        from rfdetr import RFDETRSegNano
        if not math.isfinite(threshold) or not 0 <= threshold <= 1:
            raise ValueError("threshold must be finite and in [0,1]")
        self.threshold = threshold
        self.categories = {}
        self.class_mapping = {}
        self.manifest = None
        if weights is None:
            weights = cached_weights()
            purpose = "public_COCO_infrastructure_only"
        else:
            weights = Path(weights).resolve(strict=True)
            self.manifest = json.loads(weights.with_suffix(".manifest.json").read_text())
            if self.manifest["checkpoint_sha256"] != sha256(weights):
                raise ValueError("Checkpoint hash differs from its manifest")
            self.categories = {int(c["id"]): c["name"] for c in self.manifest["categories"]}
            self.class_mapping = {int(k): int(v) for k, v in self.manifest["class_index_to_category_id"].items()}
            if set(self.class_mapping) != set(range(len(self.class_mapping))) or not set(self.class_mapping.values()).issubset(self.categories):
                raise ValueError("Invalid class-index to COCO category mapping")
            purpose = "synthetic_training_only" if self.manifest.get("synthetic_only") else "custom_checkpoint_unqualified"
        kwargs = dict(pretrain_weights=str(weights), resolution=RESOLUTION, device=device)
        if self.categories:
            kwargs["num_classes"] = len(self.class_mapping)
        self.model = RFDETRSegNano(**kwargs)
        self.metadata = {
            "architecture": "RFDETRSegNano", "rfdetr_version": "1.11.2", "resolution": RESOLUTION,
            "checkpoint_sha256": sha256(weights), "checkpoint_path": str(weights),
            "device": device, "purpose": purpose, "app2_material_accuracy_validated": False,
            "dataset_version": None if self.manifest is None else self.manifest.get("dataset_version"),
            "dataset_manifest_sha256": None if self.manifest is None else self.manifest.get("dataset_manifest_sha256"),
            "synthetic_training": bool(self.manifest and self.manifest.get("synthetic_only")),
            "pose_3d_status": "CALIBRATION_REQUIRED", "empty_container_status": "UNKNOWN",
        }

    def predict(self, image):
        import numpy as np
        import torch
        started = time.perf_counter()
        result = self.model.predict(image.convert("RGB"), threshold=self.threshold)
        if self.metadata["device"].startswith("cuda"):
            torch.cuda.synchronize()
        if (not np.isfinite(result.xyxy).all() or not np.isfinite(result.confidence).all()
                or len(result.xyxy) != len(result.confidence) or len(result.xyxy) != len(result.class_id)
                or (result.mask is not None and (len(result.xyxy) != len(result.mask) or not np.isfinite(result.mask).all()))):
            raise ValueError("Non-finite prediction")
        detections = []
        background_count = 0
        for i, (box, score, category) in enumerate(zip(result.xyxy, result.confidence, result.class_id)):
            coco_id = None
            if self.class_mapping:
                coco_id = checkpoint_category(int(category), self.class_mapping)
                if coco_id is None:
                    background_count += 1
                    continue
            item = {"bbox_xyxy": box.tolist(), "confidence": float(score), "class_id": int(category),
                    "class_name": self.categories.get(coco_id, f"COCO_or_unmapped_{int(category)}"),
                    "coco_category_id": coco_id}
            if result.mask is not None:
                import cv2
                mask = result.mask[i].astype(np.uint8)
                if mask.shape != (image.height, image.width):
                    raise ValueError("Mask dimensions differ from source image")
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                item["mask_polygons"] = [c.reshape(-1, 2).tolist() for c in contours if len(c) >= 3]
                item["mask_area_pixels"] = int(mask.sum())
            detections.append(item)
        return {"detections": detections, "metadata": dict(self.metadata),
                "raw_prediction_count": len(result), "background_predictions_excluded": background_count,
                "inference_seconds": time.perf_counter() - started,
                "material_identity_from_shape": "UNCONFIRMED"}
