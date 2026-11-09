#!/usr/bin/env python3
"""Inferencia de pelota por stdin/stdout; no contiene ROS ni control físico.

Ejecutar únicamente mediante shadow_live_inference.sh, en contenedor aislado.
La observación se valida, pero relojes y comandos siguen sin cualificar.
"""
import argparse
import base64
import contextlib
import hashlib
import importlib.metadata
import io
import json
import math
import os
from pathlib import Path
import sys
import time

from train_offline import sha256, verify_dataset
from evaluate_train_offline import guard_prediction_batch, validate_checkpoint, validate_stats
from evaluate_failed_offline import TRAIN_MANIFEST_SHA, CHECKPOINT_FILES, VLM_FILES, verify_hashes

MAX_LINE_BYTES = 8 * 1024 * 1024
MAX_PNG_BYTES = 5 * 1024 * 1024


def validate_observation(row, training, previous_image_ns=None):
    if not isinstance(row, dict) or row.get('schema') != 'cruzr_ball_live_observation_v1':
        raise ValueError('esquema de observación inesperado')
    if row.get('task') != training['task'] or row.get('state_names') != training['state_names']:
        raise ValueError('tarea u orden de ejes incompatible con entrenamiento')
    state = row.get('state27')
    if not isinstance(state, list) or len(state) != 27 or any(
        isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in state
    ):
        raise ValueError('estado incompleto o no finito')
    keys = ('image_source_ns', 'joint_source_ns', 'hand_source_ns')
    if any(type(row.get(k)) is not int or row[k] <= 0 for k in keys):
        raise ValueError('sellos de fuente inválidos')
    image_ns = row['image_source_ns']
    if previous_image_ns is not None and image_ns <= previous_image_ns:
        raise ValueError('imagen repetida o fuera de orden')
    if any(not 0 <= image_ns - row[k] <= 80_000_000 for k in keys[1:]):
        raise ValueError('estado no causal o mayor de 80 ms por sello ROS')
    times = row.get('received_monotonic_ns')
    if not isinstance(times, dict) or any(type(times.get(k)) is not int or times[k] <= 0 for k in ('image', 'joint', 'hand')):
        raise ValueError('recepciones monotónicas inválidas')
    if any(not 0 <= times['image'] - times[k] <= 500_000_000 for k in ('joint', 'hand')):
        raise ValueError('estado no causal o mayor de 500 ms en recepción')
    encoded = row.get('png_b64')
    if not isinstance(encoded, str) or len(encoded) > ((MAX_PNG_BYTES + 2) // 3) * 4:
        raise ValueError('imagen ausente o demasiado grande')
    try:
        payload = base64.b64decode(encoded, validate=True)
    except (ValueError, UnicodeEncodeError) as exc:
        raise ValueError('base64 inválido') from exc
    if not payload or len(payload) > MAX_PNG_BYTES or hashlib.sha256(payload).hexdigest() != row.get('image_sha256'):
        raise ValueError('hash o tamaño de imagen inválido')
    return payload


def emit(event):
    print(json.dumps(event, separators=(',', ':'), allow_nan=False), flush=True)


def run(args):
    if any(os.environ.get(k) != '1' for k in ('HF_HUB_OFFLINE', 'TRANSFORMERS_OFFLINE', 'HF_HUB_DISABLE_TELEMETRY')):
        raise ValueError('se requiere entorno offline')
    if importlib.metadata.version('lerobot') != '0.5.1' or not 0 <= args.seed <= 2**31 - 1:
        raise ValueError('versión LeRobot o semilla inesperada')
    if not 1 <= args.max_samples <= 1000:
        raise ValueError('el máximo de muestras debe estar entre 1 y 1000')
    train, checkpoint, vlm = (Path(x).resolve(strict=True) for x in (args.train, args.checkpoint, args.vlm))
    if any(not p.is_dir() for p in (train, checkpoint, vlm)):
        raise ValueError('entradas inexistentes')
    if sha256(train / 'manifest.json') != TRAIN_MANIFEST_SHA:
        raise ValueError('manifest de entrenamiento inesperado')
    verify_hashes(checkpoint, CHECKPOINT_FILES)
    verify_hashes(vlm, VLM_FILES)
    training = verify_dataset(train)
    validate_checkpoint(checkpoint, vlm)
    validate_stats(train, checkpoint)
    # Dependencias y modelo pueden producir logs: stdout está reservado para JSONL.
    with contextlib.redirect_stdout(sys.stderr):
        import numpy as np
        import torch
        from PIL import Image
        from lerobot.configs.policies import PreTrainedConfig
        from lerobot.policies.factory import make_pre_post_processors
        from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
        if args.device == 'cuda':
            if not torch.cuda.is_available() or torch.cuda.mem_get_info(0)[0] < 8 * 1024**3:
                raise ValueError('menos de 8 GiB libres en GPU')
            torch.cuda.set_per_process_memory_fraction(0.35, 0)
        torch.set_num_threads(2)
        config = PreTrainedConfig.from_pretrained(checkpoint, local_files_only=True)
        config.device = args.device
        config.vlm_model_name = str(vlm)
        model = SmolVLAPolicy.from_pretrained(checkpoint, config=config, local_files_only=True)
        model.eval()
        pre, post = make_pre_post_processors(policy_cfg=config, pretrained_path=str(checkpoint),
            preprocessor_overrides={'device_processor': {'device': args.device}, 'tokenizer_processor': {'tokenizer_name': str(vlm)}},
            postprocessor_overrides={'device_processor': {'device': 'cpu'}})
    names = training['action_names'][:7]
    indices = [training['state_names'].index(name) for name in names]
    emit({'event': 'ready', 'schema': 'cruzr_ball_live_shadow_v1', 'physical_control_qualified': False,
          'model_sha256': CHECKPOINT_FILES['model.safetensors'], 'max_samples': args.max_samples})
    previous_image_ns = None
    count = 0
    while count < args.max_samples:
        raw = sys.stdin.buffer.readline(MAX_LINE_BYTES + 1)
        if not raw:
            break
        if len(raw) > MAX_LINE_BYTES or not raw.endswith(b'\n'):
            raise ValueError('línea incompleta o mayor del límite')
        row = json.loads(raw)
        payload = validate_observation(row, training, previous_image_ns)
        previous_image_ns = row['image_source_ns']
        with Image.open(io.BytesIO(payload)) as image:
            if image.format != 'PNG' or image.mode != 'RGB' or image.size != (960, 576):
                raise ValueError('formato, color o dimensiones de imagen inesperados')
            pixels = np.array(image, dtype=np.uint8)
        observation = {'observation.images.camera1': torch.from_numpy(pixels).permute(2, 0, 1).to(torch.float32) / 255.0,
                       'observation.state': torch.tensor(row['state27'], dtype=torch.float32), 'task': training['task']}
        with contextlib.redirect_stdout(sys.stderr):
            batch = guard_prediction_batch(pre(observation))
            model.reset()
            torch.manual_seed(args.seed + count)
            if args.device == 'cuda': torch.cuda.synchronize()
            start = time.perf_counter()
            with torch.inference_mode():
                chunk = model.predict_action_chunk(batch)
                if tuple(chunk.shape) != (1, 8, 8): raise ValueError('forma de predicción inválida')
                decoded = post(chunk[:, 0, :])
            if args.device == 'cuda': torch.cuda.synchronize()
            elapsed = time.perf_counter() - start
            prediction = decoded.detach().cpu().reshape(-1).tolist()
        if len(prediction) != 8 or any(not math.isfinite(v) for v in prediction):
            raise ValueError('predicción no finita')
        delta = [prediction[j] - row['state27'][idx] for j, idx in enumerate(indices)]
        emit({'event': 'prediction', 'index': count, 'image_sha256': row['image_sha256'],
              'image_source_ns': row['image_source_ns'], 'prediction': prediction,
              'proposed_minus_observed_rad': delta, 'inference_seconds': elapsed,
              'physical_control_qualified': False})
        count += 1
    emit({'event': 'done', 'samples': count, 'physical_control_qualified': False})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('train', 'checkpoint', 'vlm'): parser.add_argument('--' + key, required=True)
    parser.add_argument('--device', choices=('cpu', 'cuda'), default='cpu')
    parser.add_argument('--seed', type=int, default=20261109)
    parser.add_argument('--max-samples', type=int, default=10)
    try:
        run(parser.parse_args())
    except (OSError, ValueError, KeyError, TypeError, OverflowError, importlib.metadata.PackageNotFoundError) as exc:
        print('ERROR shadow: ' + str(exc), file=sys.stderr)
        sys.exit(1)
