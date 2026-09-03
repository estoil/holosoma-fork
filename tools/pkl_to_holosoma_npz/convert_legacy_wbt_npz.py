#!/usr/bin/env python3
"""Convert legacy IsaacLab WBT NPZ files to the current Holosoma motion format."""

from __future__ import annotations

import argparse
from pathlib import Path

import mujoco
import numpy as np


LEGACY_JOINT_NAMES = [
    "left_hip_pitch_joint",
    "right_hip_pitch_joint",
    "waist_yaw_joint",
    "left_hip_roll_joint",
    "right_hip_roll_joint",
    "waist_roll_joint",
    "left_hip_yaw_joint",
    "right_hip_yaw_joint",
    "waist_pitch_joint",
    "left_knee_joint",
    "right_knee_joint",
    "left_shoulder_pitch_joint",
    "right_shoulder_pitch_joint",
    "left_ankle_pitch_joint",
    "right_ankle_pitch_joint",
    "left_shoulder_roll_joint",
    "right_shoulder_roll_joint",
    "left_ankle_roll_joint",
    "right_ankle_roll_joint",
    "left_shoulder_yaw_joint",
    "right_shoulder_yaw_joint",
    "left_elbow_joint",
    "right_elbow_joint",
    "left_wrist_roll_joint",
    "right_wrist_roll_joint",
    "left_wrist_pitch_joint",
    "right_wrist_pitch_joint",
    "left_wrist_yaw_joint",
    "right_wrist_yaw_joint",
]

LEGACY_BODY_NAMES = [
    "pelvis",
    "left_hip_pitch_link",
    "right_hip_pitch_link",
    "waist_yaw_link",
    "left_hip_roll_link",
    "right_hip_roll_link",
    "waist_roll_link",
    "left_hip_yaw_link",
    "right_hip_yaw_link",
    "torso_link",
    "left_knee_link",
    "right_knee_link",
    "left_shoulder_pitch_link",
    "right_shoulder_pitch_link",
    "left_ankle_pitch_link",
    "right_ankle_pitch_link",
    "left_shoulder_roll_link",
    "right_shoulder_roll_link",
    "left_ankle_roll_link",
    "right_ankle_roll_link",
    "left_shoulder_yaw_link",
    "right_shoulder_yaw_link",
    "left_elbow_link",
    "right_elbow_link",
    "left_wrist_roll_link",
    "right_wrist_roll_link",
    "left_wrist_pitch_link",
    "right_wrist_pitch_link",
    "left_wrist_yaw_link",
    "right_wrist_yaw_link",
]

HOLOSOMA_JOINT_NAMES = [
    "left_hip_pitch_joint",
    "left_hip_roll_joint",
    "left_hip_yaw_joint",
    "left_knee_joint",
    "left_ankle_pitch_joint",
    "left_ankle_roll_joint",
    "right_hip_pitch_joint",
    "right_hip_roll_joint",
    "right_hip_yaw_joint",
    "right_knee_joint",
    "right_ankle_pitch_joint",
    "right_ankle_roll_joint",
    "waist_yaw_joint",
    "waist_roll_joint",
    "waist_pitch_joint",
    "left_shoulder_pitch_joint",
    "left_shoulder_roll_joint",
    "left_shoulder_yaw_joint",
    "left_elbow_joint",
    "left_wrist_roll_joint",
    "left_wrist_pitch_joint",
    "left_wrist_yaw_joint",
    "right_shoulder_pitch_joint",
    "right_shoulder_roll_joint",
    "right_shoulder_yaw_joint",
    "right_elbow_joint",
    "right_wrist_roll_joint",
    "right_wrist_pitch_joint",
    "right_wrist_yaw_joint",
]


def _default_scene_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    return root / "src/holosoma/holosoma/data/robots/g1/scenes/scene_g1_29dof_wbt_plane.xml"


def _gradient(values: np.ndarray, dt: float) -> np.ndarray:
    return np.gradient(values, dt, axis=0).astype(np.float32)


def _quat_conjugate_wxyz(q: np.ndarray) -> np.ndarray:
    result = q.copy()
    result[..., 1:] *= -1.0
    return result


def _quat_multiply_wxyz(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    aw, ax, ay, az = [a[..., i] for i in range(4)]
    bw, bx, by, bz = [b[..., i] for i in range(4)]
    return np.stack(
        [
            aw * bw - ax * bx - ay * by - az * bz,
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
        ],
        axis=-1,
    )


def _angular_velocity(quat_wxyz: np.ndarray, dt: float) -> np.ndarray:
    result = np.zeros(quat_wxyz.shape[:-1] + (3,), dtype=np.float32)
    if quat_wxyz.shape[0] < 2:
        return result
    rel = _quat_multiply_wxyz(quat_wxyz[1:], _quat_conjugate_wxyz(quat_wxyz[:-1]))
    rel[rel[..., 0] < 0.0] *= -1.0
    xyz_norm = np.linalg.norm(rel[..., 1:], axis=-1)
    angle = 2.0 * np.arctan2(xyz_norm, np.clip(rel[..., 0], 0.0, None))
    valid = xyz_norm > 1e-8
    result[:-1][valid] = rel[..., 1:][valid] * (angle[valid] / (xyz_norm[valid] * dt))[..., None]
    result[-1] = result[-2]
    return result


def _remove_short_segments(values: np.ndarray, minimum: int) -> np.ndarray:
    values = values.astype(np.int64).copy()
    while values.size > 1:
        starts = np.r_[0, np.flatnonzero(values[1:] != values[:-1]) + 1]
        ends = np.r_[starts[1:], values.size]
        short = np.flatnonzero(ends - starts < minimum)
        if short.size == 0 or starts.size <= 1:
            break
        index = int(short[0])
        if index == 0:
            fill = values[starts[1]]
        elif index == starts.size - 1:
            fill = values[starts[index - 1]]
        else:
            left_len = ends[index - 1] - starts[index - 1]
            right_len = ends[index + 1] - starts[index + 1]
            fill = values[starts[index - 1]] if left_len >= right_len else values[starts[index + 1]]
        values[starts[index] : ends[index]] = fill
    return values.astype(np.float32)


def _contact_phase(clearance: np.ndarray, velocity: np.ndarray) -> np.ndarray:
    planar_speed = np.linalg.norm(velocity[:, :2], axis=-1)
    enter = (clearance < 0.045) & (np.abs(velocity[:, 2]) < 0.35) & (planar_speed < 0.25)
    leave = (clearance > 0.075) | ((clearance > 0.055) & (velocity[:, 2] > 0.45)) | (planar_speed > 0.45)
    phase = np.zeros(clearance.shape[0], dtype=np.float32)
    current = np.count_nonzero(enter[:3]) >= 2
    enter_count = leave_count = 0
    for index in range(clearance.shape[0]):
        if current:
            leave_count = leave_count + 1 if leave[index] else 0
            enter_count = 0
            if leave_count >= 3:
                current = False
                leave_count = 0
        else:
            enter_count = enter_count + 1 if enter[index] else 0
            leave_count = 0
            if enter_count >= 3:
                current = True
                enter_count = 0
        phase[index] = float(current)
    return _remove_short_segments(phase, 5)


def _support_labels(body_pos: np.ndarray, body_vel: np.ndarray, body_names: list[str]) -> tuple[np.ndarray, np.ndarray]:
    indexes = [body_names.index("left_foot_contact_point"), body_names.index("right_foot_contact_point")]
    feet = body_pos[:, indexes]
    feet_vel = body_vel[:, indexes]
    ground = np.quantile(feet[..., 2], 0.01)
    hard = np.stack([_contact_phase(feet[:, i, 2] - ground, feet_vel[:, i]) for i in range(2)], axis=1)
    padded = np.pad(hard, ((2, 2), (0, 0)), mode="edge")
    soft = np.stack([np.convolve(padded[:, i], np.ones(5) / 5.0, mode="valid") for i in range(2)], axis=1)
    state = np.zeros(hard.shape[0], dtype=np.int64)
    left, right = hard[:, 0] > 0.5, hard[:, 1] > 0.5
    state[left & ~right] = 1
    state[right & ~left] = 2
    state[~left & ~right] = 3
    return soft.astype(np.float32), state


def convert(input_path: Path, output_path: Path, scene_path: Path) -> None:
    with np.load(input_path) as source:
        required = {"fps", "joint_pos", "joint_vel", "body_pos_w", "body_quat_w", "body_lin_vel_w", "body_ang_vel_w"}
        missing = required - set(source.files)
        if missing:
            raise ValueError(f"legacy NPZ is missing keys: {sorted(missing)}")
        arrays = {key: source[key].copy() for key in source.files}

    frames = arrays["joint_pos"].shape[0]
    if arrays["joint_pos"].shape != (frames, 29) or arrays["body_pos_w"].shape != (frames, 30, 3):
        raise ValueError("expected legacy G1 shapes joint_pos=(T,29), body_pos_w=(T,30,3)")
    fps = float(np.asarray(arrays["fps"]).reshape(-1)[0])
    dt = 1.0 / fps

    reorder = [LEGACY_JOINT_NAMES.index(name) for name in HOLOSOMA_JOINT_NAMES]
    dof_pos = arrays["joint_pos"][:, reorder].astype(np.float32)
    dof_vel = arrays["joint_vel"][:, reorder].astype(np.float32)
    root_pos = arrays["body_pos_w"][:, 0].astype(np.float32)
    root_quat = arrays["body_quat_w"][:, 0].astype(np.float32)
    root_quat /= np.clip(np.linalg.norm(root_quat, axis=-1, keepdims=True), 1e-8, None)

    model = mujoco.MjModel.from_xml_path(str(scene_path))
    data = mujoco.MjData(model)
    model_joint_names = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, i) for i in range(1, model.njnt)]
    if model_joint_names != HOLOSOMA_JOINT_NAMES:
        raise ValueError(f"unexpected Holosoma model joint order: {model_joint_names}")
    body_names = [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, i) for i in range(1, model.nbody)]

    body_pos = np.empty((frames, len(body_names), 3), dtype=np.float32)
    body_quat = np.empty((frames, len(body_names), 4), dtype=np.float32)
    for frame in range(frames):
        data.qpos[:3] = root_pos[frame]
        data.qpos[3:7] = root_quat[frame]
        data.qpos[7:] = dof_pos[frame]
        mujoco.mj_forward(model, data)
        body_pos[frame] = data.xpos[1:]
        body_quat[frame] = data.xquat[1:]

    body_lin_vel = _gradient(body_pos, dt)
    body_ang_vel = _angular_velocity(body_quat, dt)
    root_lin_vel = _gradient(root_pos, dt)
    root_ang_vel = _angular_velocity(root_quat, dt)
    support_phase, support_state = _support_labels(body_pos, body_lin_vel, body_names)

    common = [name for name in LEGACY_BODY_NAMES if name in body_names]
    legacy_idx = [LEGACY_BODY_NAMES.index(name) for name in common]
    target_idx = [body_names.index(name) for name in common]
    position_rmse = float(np.sqrt(np.mean((arrays["body_pos_w"][:, legacy_idx] - body_pos[:, target_idx]) ** 2)))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_path,
        fps=np.asarray([int(round(fps))], dtype=np.int64),
        joint_pos=np.concatenate([root_pos, root_quat, dof_pos], axis=1),
        joint_vel=np.concatenate([root_lin_vel, root_ang_vel, dof_vel], axis=1),
        body_pos_w=body_pos,
        body_quat_w=body_quat,
        body_lin_vel_w=body_lin_vel,
        body_ang_vel_w=body_ang_vel,
        joint_names=np.asarray(HOLOSOMA_JOINT_NAMES),
        body_names=np.asarray(body_names),
        reference_support_phase=support_phase,
        reference_support_state=support_state,
        legacy_joint_names=np.asarray(LEGACY_JOINT_NAMES),
        legacy_body_names=np.asarray(LEGACY_BODY_NAMES),
        legacy_joint_pos=arrays["joint_pos"],
        legacy_joint_vel=arrays["joint_vel"],
    )
    counts = np.bincount(support_state, minlength=4)
    print(f"wrote {output_path}")
    print(f"frames={frames}, fps={fps:g}, position_rmse_common_bodies={position_rmse:.6g} m")
    print(f"support_state_counts double/left/right/flight={counts.tolist()}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--scene", type=Path, default=_default_scene_path())
    args = parser.parse_args()
    convert(args.input.resolve(), args.output.resolve(), args.scene.resolve())


if __name__ == "__main__":
    main()
