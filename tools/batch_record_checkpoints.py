#!/usr/bin/env python3
"""Record one comparable IsaacSim video for every checkpoint in a run.

The simulator and policy object are created once.  Checkpoints are then loaded
sequentially, which avoids paying IsaacSim startup cost for every video.
Existing, valid-looking output files are skipped so the command is resumable.
"""

from __future__ import annotations

import argparse
import dataclasses
import re
from pathlib import Path

from loguru import logger

from holosoma.agents.base_algo.base_algo import BaseAlgo
from holosoma.utils.eval_utils import CheckpointConfig, load_saved_experiment_config
from holosoma.utils.helpers import get_class
from holosoma.utils.sim_utils import close_simulation_app, setup_simulation_environment


def _step(path: Path) -> int:
    match = re.fullmatch(r"model_(\d+)\.pt", path.name)
    if match is None:
        raise ValueError(f"Unexpected checkpoint name: {path.name}")
    return int(match.group(1))


def _new_video(work_dir: Path, before: set[Path]) -> Path:
    created = set(work_dir.glob("*.mp4")) - before
    if len(created) != 1:
        raise RuntimeError(f"Expected one new video under {work_dir}, found: {sorted(created)}")
    return created.pop()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--height", type=int, default=360)
    parser.add_argument("--frame-stride", type=int, default=1,
                        help="Capture every Nth control frame while retaining full motion duration")
    parser.add_argument("--step-min", type=int, default=None)
    parser.add_argument("--step-max", type=int, default=None)
    parser.add_argument("--reverse", action="store_true")
    parser.add_argument("--worker-id", default="main")
    args = parser.parse_args()

    checkpoints = sorted(args.run_dir.glob("model_*.pt"), key=_step)
    if args.step_min is not None:
        checkpoints = [p for p in checkpoints if _step(p) >= args.step_min]
    if args.step_max is not None:
        checkpoints = [p for p in checkpoints if _step(p) <= args.step_max]
    if args.reverse:
        checkpoints.reverse()
    if not checkpoints:
        raise SystemExit(f"No model_*.pt checkpoints under {args.run_dir}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    work_dir = args.output_dir / f"_encoding_{args.worker_id}"
    work_dir.mkdir(exist_ok=True)

    saved_cfg, saved_wandb_path = load_saved_experiment_config(CheckpointConfig(checkpoint=str(checkpoints[0])))
    config = saved_cfg.get_eval_config()
    camera = dataclasses.replace(
        config.logger.video.camera,
        offset=[3.0, 3.0, 1.8],
        target_offset=[0.0, 0.0, 0.8],
    )
    video = dataclasses.replace(
        config.logger.video,
        enabled=True,
        interval=1,
        width=args.width,
        height=args.height,
        playback_rate=1.0,
        output_format="h264",
        save_dir=str(work_dir),
        upload_to_wandb=False,
        show_command_overlay=True,
        camera=camera,
    )
    config = dataclasses.replace(
        config,
        training=dataclasses.replace(
            config.training,
            headless=True,
            num_envs=1,
            max_eval_steps=args.steps,
            export_onnx=False,
        ),
        logger=dataclasses.replace(config.logger, headless_recording=True, video=video),
    )

    env = simulation_app = algo = None
    try:
        env, device, simulation_app = setup_simulation_environment(config)
        if env.simulator.video_recorder is not None:
            env.simulator.video_recorder.capture_stride = max(args.frame_stride, 1)
        algo_class = get_class(config.algo._target_)
        algo = algo_class(device=device, env=env, config=config.algo.config, log_dir=str(args.output_dir), multi_gpu_cfg=None)
        assert isinstance(algo, BaseAlgo)
        algo.setup()
        algo.attach_checkpoint_metadata(saved_cfg, saved_wandb_path)

        total = len(checkpoints)
        for index, checkpoint in enumerate(checkpoints, 1):
            step = _step(checkpoint)
            output = args.output_dir / f"taichi_g1_danjiao_4_4_step_{step}.mp4"
            if output.exists() and output.stat().st_size > 100_000:
                logger.info("[{}/{}] Skip existing {}", index, total, output.name)
                continue

            logger.info("[{}/{}] Loading {}", index, total, checkpoint.name)
            algo.load(str(checkpoint))
            before = set(work_dir.glob("*.mp4"))
            algo.evaluate_policy(max_eval_steps=args.steps)
            generated = _new_video(work_dir, before)
            generated.replace(output)
            logger.info("[{}/{}] Saved {}", index, total, output)
    finally:
        if env is not None and getattr(env.simulator, "video_recorder", None) is not None:
            env.simulator.video_recorder.cleanup()
        if simulation_app is not None:
            close_simulation_app(simulation_app)


if __name__ == "__main__":
    main()
