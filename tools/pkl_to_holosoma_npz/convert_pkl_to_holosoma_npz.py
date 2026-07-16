#!/usr/bin/env python3
"""
Convert GMR/video2robot PKL motions to Holosoma-compatible NPZ motions.

Design goals:
1) Produce NPZ files that satisfy Holosoma WBT required keys.
2) Preserve original PKL content without loss by embedding raw pickle bytes.
3) Support single-file and batch directory conversion.
4) Validate shapes and fail fast in strict mode.
"""

from __future__ import annotations

import argparse
import json
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


G1_29_DOF_JOINT_NAMES = [
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


REQUIRED_PKL_KEYS = {
    "fps",
    "root_pos",
    "root_rot",
    "dof_pos",
}

OPTIONAL_PKL_KEYS = {
    "local_body_pos",
    "link_body_list",
}


def _default_g1_xml_path() -> Path:
    # holosoma/tools/pkl_to_holosoma_npz/convert_*.py -> holosoma/
    holosoma_root = Path(__file__).resolve().parents[2]
    candidates = [
        holosoma_root.parent / "third_party/GMR/assets/unitree_g1/g1_mocap_29dof.xml",
        holosoma_root.parent / "video2robot/third_party/GMR/assets/unitree_g1/g1_mocap_29dof.xml",
        holosoma_root / "src/holosoma/holosoma/data/robots/g1/g1_29dof.xml",
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[0]


@dataclass
class ConvertConfig:
    local_body_pos_frame: str
    preserve_raw: bool
    compressed: bool
    strict: bool


def _as_float_array(name: str, value: Any, ndim: int | None = None) -> np.ndarray:
    arr = np.asarray(value, dtype=np.float32)
    if ndim is not None and arr.ndim != ndim:
        raise ValueError(f"{name} must be {ndim}D, got shape={arr.shape}")
    return arr


def _normalize_quat_xyzw(quat_xyzw: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(quat_xyzw, axis=-1, keepdims=True)
    norm = np.clip(norm, 1e-8, None)
    return quat_xyzw / norm


def _xyzw_to_wxyz(quat_xyzw: np.ndarray) -> np.ndarray:
    return quat_xyzw[..., [3, 0, 1, 2]]


def _quat_conjugate_xyzw(q: np.ndarray) -> np.ndarray:
    out = q.copy()
    out[..., :3] *= -1.0
    return out


def _quat_multiply_xyzw(q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
    x1, y1, z1, w1 = [q1[..., i] for i in range(4)]
    x2, y2, z2, w2 = [q2[..., i] for i in range(4)]
    x = w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2
    y = w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2
    z = w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2
    w = w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
    return np.stack([x, y, z, w], axis=-1)


def _quat_rotate_xyzw(q: np.ndarray, v: np.ndarray) -> np.ndarray:
    v_quat = np.zeros(v.shape[:-1] + (4,), dtype=np.float32)
    v_quat[..., :3] = v
    q_inv = _quat_conjugate_xyzw(q)
    return _quat_multiply_xyzw(_quat_multiply_xyzw(q, v_quat), q_inv)[..., :3]


def _gradient_time(x: np.ndarray, dt: float) -> np.ndarray:
    if x.shape[0] < 2:
        return np.zeros_like(x, dtype=np.float32)
    return np.gradient(x, dt, axis=0).astype(np.float32)


def _quat_to_axis_angle_xyzw(q: np.ndarray) -> np.ndarray:
    qn = _normalize_quat_xyzw(q)
    xyz = qn[..., :3]
    w = np.clip(qn[..., 3], -1.0, 1.0)
    angle = 2.0 * np.arccos(w)
    s = np.sqrt(np.clip(1.0 - w * w, 0.0, None))
    axis = np.zeros_like(xyz, dtype=np.float32)
    valid = s > 1e-8
    axis[valid] = xyz[valid] / s[valid][..., None]
    axis[~valid] = np.array([0.0, 0.0, 1.0], dtype=np.float32)
    return axis * angle[..., None]


def _angular_velocity_from_quat_xyzw(quat_xyzw: np.ndarray, dt: float) -> np.ndarray:
    n = quat_xyzw.shape[0]
    if n < 2:
        return np.zeros((n, 3), dtype=np.float32)
    w = np.zeros((n, 3), dtype=np.float32)
    for i in range(n - 1):
        q_rel = _quat_multiply_xyzw(quat_xyzw[i + 1], _quat_conjugate_xyzw(quat_xyzw[i]))
        aa = _quat_to_axis_angle_xyzw(q_rel)
        w[i] = aa / max(dt, 1e-8)
    w[-1] = w[-2]
    return w


def _validate_lengths(root_pos: np.ndarray, root_rot: np.ndarray, dof_pos: np.ndarray, local_body_pos: np.ndarray) -> int:
    t = root_pos.shape[0]
    if root_rot.shape[0] != t or dof_pos.shape[0] != t or local_body_pos.shape[0] != t:
        raise ValueError(
            "Frame count mismatch among root_pos/root_rot/dof_pos/local_body_pos: "
            f"{root_pos.shape[0]}/{root_rot.shape[0]}/{dof_pos.shape[0]}/{local_body_pos.shape[0]}"
        )
    return t


def _load_pickle(path: Path) -> dict[str, Any]:
    with path.open("rb") as f:
        obj = pickle.load(f)
    if not isinstance(obj, dict):
        raise TypeError(f"Expected dict in {path}, got {type(obj)}")
    return obj


def _build_output_path(input_path: Path, input_root: Path, output_root: Path) -> Path:
    rel = input_path.relative_to(input_root).with_suffix(".npz")
    return output_root / rel


def _has_local_body_kinematics(data: dict[str, Any]) -> bool:
    local_body_pos = data.get("local_body_pos")
    link_body_list = data.get("link_body_list")
    if local_body_pos is None or link_body_list is None:
        return False
    local_arr = np.asarray(local_body_pos)
    if local_arr.size == 0 or local_arr.ndim != 3:
        return False
    if len(link_body_list) == 0:
        return False
    return True


def _compute_body_kinematics_mujoco(
    robot_xml: Path,
    root_pos: np.ndarray,
    root_rot_xyzw: np.ndarray,
    dof_pos: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str]]:
    import mujoco as mj

    if not robot_xml.exists():
        raise FileNotFoundError(f"Robot XML not found for FK: {robot_xml}")

    model = mj.MjModel.from_xml_path(str(robot_xml))
    data = mj.MjData(model)
    if model.nq - 7 != dof_pos.shape[1]:
        raise ValueError(
            f"DOF mismatch for FK: model expects {model.nq - 7}, motion has {dof_pos.shape[1]}"
        )

    body_names: list[str] = []
    body_ids: list[int] = []
    for body_id in range(1, model.nbody):
        name = mj.mj_id2name(model, mj.mjtObj.mjOBJ_BODY, body_id)
        if name:
            body_names.append(name)
            body_ids.append(body_id)

    t = root_pos.shape[0]
    n_bodies = len(body_ids)
    body_pos_w = np.zeros((t, n_bodies, 3), dtype=np.float32)
    body_quat_w = np.zeros((t, n_bodies, 4), dtype=np.float32)
    body_lin_vel_w = np.zeros((t, n_bodies, 3), dtype=np.float32)
    body_ang_vel_w = np.zeros((t, n_bodies, 3), dtype=np.float32)
    root_quat_wxyz = _xyzw_to_wxyz(root_rot_xyzw)
    vel_buffer = np.zeros(6, dtype=np.float64)

    for frame in range(t):
        data.qpos[:3] = root_pos[frame]
        data.qpos[3:7] = root_quat_wxyz[frame]
        data.qpos[7:] = dof_pos[frame]
        mj.mj_forward(model, data)
        for j, body_id in enumerate(body_ids):
            body_pos_w[frame, j] = data.xpos[body_id]
            body_quat_w[frame, j] = data.xquat[body_id]
            mj.mj_objectVelocity(model, data, mj.mjtObj.mjOBJ_BODY, body_id, vel_buffer, 0)
            body_lin_vel_w[frame, j] = vel_buffer[0:3]
            body_ang_vel_w[frame, j] = vel_buffer[3:6]

    return body_pos_w, body_quat_w, body_lin_vel_w, body_ang_vel_w, body_names


def convert_one(
    input_path: Path,
    output_path: Path,
    cfg: ConvertConfig,
    robot_xml: Path | None = None,
) -> None:
    data = _load_pickle(input_path)
    missing = sorted(REQUIRED_PKL_KEYS - set(data.keys()))
    if missing:
        msg = f"{input_path} missing required keys: {missing}"
        if cfg.strict:
            raise KeyError(msg)
        print(f"[WARN] {msg}")

    fps = float(data.get("fps", 30.0))
    dt = 1.0 / max(fps, 1e-8)

    root_pos = _as_float_array("root_pos", data["root_pos"], ndim=2)
    root_rot_xyzw = _normalize_quat_xyzw(_as_float_array("root_rot", data["root_rot"], ndim=2))
    dof_pos = _as_float_array("dof_pos", data["dof_pos"], ndim=2)

    if root_pos.shape[1] != 3:
        raise ValueError(f"root_pos must be (T,3), got {root_pos.shape}")
    if root_rot_xyzw.shape[1] != 4:
        raise ValueError(f"root_rot must be (T,4), got {root_rot_xyzw.shape}")
    if root_pos.shape[0] != dof_pos.shape[0] or root_pos.shape[0] != root_rot_xyzw.shape[0]:
        raise ValueError(
            "Frame count mismatch among root_pos/root_rot/dof_pos: "
            f"{root_pos.shape[0]}/{root_rot_xyzw.shape[0]}/{dof_pos.shape[0]}"
        )

    t = root_pos.shape[0]
    root_quat_wxyz = _xyzw_to_wxyz(root_rot_xyzw)

    if _has_local_body_kinematics(data):
        local_body_pos = _as_float_array("local_body_pos", data["local_body_pos"], ndim=3)
        body_names_list = [str(x) for x in data["link_body_list"]]
        if local_body_pos.shape[0] != t:
            raise ValueError(f"local_body_pos frames {local_body_pos.shape[0]} != {t}")
        if local_body_pos.shape[2] != 3:
            raise ValueError(f"local_body_pos must be (T,B,3), got {local_body_pos.shape}")
        if cfg.local_body_pos_frame == "root":
            q_rep = np.repeat(root_rot_xyzw[:, None, :], local_body_pos.shape[1], axis=1)
            body_pos_w = _quat_rotate_xyzw(q_rep, local_body_pos) + root_pos[:, None, :]
        elif cfg.local_body_pos_frame == "world":
            body_pos_w = local_body_pos.copy()
        else:
            raise ValueError(f"Unsupported local_body_pos_frame: {cfg.local_body_pos_frame}")
        body_quat_w = np.repeat(root_quat_wxyz[:, None, :], body_pos_w.shape[1], axis=1).astype(np.float32)
        use_fk_velocities = False
    else:
        xml_path = robot_xml or _default_g1_xml_path()
        print(f"[INFO] {input_path}: local_body_pos missing; computing FK via {xml_path.name}")
        body_pos_w, body_quat_w, body_lin_vel_w, body_ang_vel_w, body_names_list = _compute_body_kinematics_mujoco(
            xml_path, root_pos, root_rot_xyzw, dof_pos
        )
        use_fk_velocities = True

    joint_pos = np.concatenate([root_pos, root_quat_wxyz, dof_pos], axis=1).astype(np.float32)

    root_lin_vel = _gradient_time(root_pos, dt)
    root_ang_vel = _angular_velocity_from_quat_xyzw(root_rot_xyzw, dt)
    dof_vel = _gradient_time(dof_pos, dt)
    joint_vel = np.concatenate([root_lin_vel, root_ang_vel, dof_vel], axis=1).astype(np.float32)

    body_names = np.asarray(body_names_list, dtype=np.str_)
    if not use_fk_velocities:
        body_lin_vel_w = _gradient_time(body_pos_w, dt)
        body_ang_vel_w = np.repeat(root_ang_vel[:, None, :], body_pos_w.shape[1], axis=1).astype(np.float32)

    if dof_pos.shape[1] == len(G1_29_DOF_JOINT_NAMES):
        joint_names = np.asarray(G1_29_DOF_JOINT_NAMES, dtype=np.str_)
    else:
        joint_names = np.asarray([f"joint_{i}" for i in range(dof_pos.shape[1])], dtype=np.str_)
        if cfg.strict:
            raise ValueError(
                f"DOF count {dof_pos.shape[1]} does not match G1-29 expected {len(G1_29_DOF_JOINT_NAMES)} "
                "while strict mode is enabled."
            )
        print(
            f"[WARN] {input_path}: DOF={dof_pos.shape[1]} != 29; using fallback joint names joint_0..joint_{dof_pos.shape[1]-1}."
        )

    if body_names.shape[0] != body_pos_w.shape[1]:
        raise ValueError(
            f"body_names length {body_names.shape[0]} does not match body_pos_w bodies {body_pos_w.shape[1]}"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "fps": np.array([fps], dtype=np.float32),
        "joint_pos": joint_pos,
        "joint_vel": joint_vel,
        "body_pos_w": body_pos_w.astype(np.float32),
        "body_quat_w": body_quat_w,
        "body_lin_vel_w": body_lin_vel_w,
        "body_ang_vel_w": body_ang_vel_w,
        "body_names": body_names,
        "joint_names": joint_names,
        "converter_name": np.array(["convert_pkl_to_holosoma_npz"], dtype=np.str_),
        "converter_note": np.array(
            [
                "body_quat_w/body_ang_vel_w are schema-compatible approximations from root orientation; "
                "raw pickle is embedded for lossless recovery."
            ],
            dtype=np.str_,
        ),
        "source_pkl_path": np.array([str(input_path)], dtype=np.str_),
    }

    if cfg.preserve_raw:
        raw_pickle_bytes = np.frombuffer(pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL), dtype=np.uint8)
        payload["raw_pickle_bytes"] = raw_pickle_bytes
        payload["raw_root_pos"] = root_pos.astype(np.float32)
        payload["raw_root_rot_xyzw"] = root_rot_xyzw.astype(np.float32)
        payload["raw_dof_pos"] = dof_pos.astype(np.float32)
        if data.get("local_body_pos") is not None:
            payload["raw_local_body_pos"] = np.asarray(data["local_body_pos"], dtype=np.float32)
        if data.get("link_body_list") is not None:
            payload["raw_link_body_list"] = np.asarray(data["link_body_list"], dtype=np.str_)
        payload["raw_keys_json"] = np.array([json.dumps(sorted(data.keys()))], dtype=np.str_)

    saver = np.savez_compressed if cfg.compressed else np.savez
    saver(output_path, **payload)
    print(f"[OK] {input_path} -> {output_path} | frames={t}, dof={dof_pos.shape[1]}, bodies={body_pos_w.shape[1]}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert video2robot/GMR PKL motions to Holosoma-compatible NPZ format."
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input-file", type=Path, help="Path to one PKL file.")
    source.add_argument("--input-dir", type=Path, help="Directory containing PKL files.")
    parser.add_argument("--output-file", type=Path, help="Output NPZ path (single-file mode only).")
    parser.add_argument("--output-dir", type=Path, help="Output NPZ directory (batch mode).")
    parser.add_argument("--recursive", action="store_true", help="Recursively search PKL files under --input-dir.")
    parser.add_argument(
        "--local-body-pos-frame",
        choices=["root", "world"],
        default="root",
        help="Interpret frame of local_body_pos from PKL. Use 'root' for video2robot default.",
    )
    parser.add_argument(
        "--no-preserve-raw",
        action="store_true",
        help="Disable embedding raw pickle data. Default preserves raw data for no-loss archival.",
    )
    parser.add_argument("--no-compress", action="store_true", help="Use np.savez (faster) instead of np.savez_compressed.")
    parser.add_argument("--strict", action="store_true", help="Fail on schema ambiguities (recommended for production).")
    parser.add_argument(
        "--robot-xml",
        type=Path,
        default=None,
        help="MuJoCo XML used for FK when local_body_pos is missing (default: holosoma G1 29DOF).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    cfg = ConvertConfig(
        local_body_pos_frame=args.local_body_pos_frame,
        preserve_raw=not args.no_preserve_raw,
        compressed=not args.no_compress,
        strict=args.strict,
    )

    if args.input_file:
        in_file = args.input_file.expanduser().resolve()
        if not in_file.exists():
            raise FileNotFoundError(in_file)
        out_file = args.output_file
        if out_file is None:
            out_file = in_file.with_suffix(".npz")
        out_file = out_file.expanduser().resolve()
        convert_one(in_file, out_file, cfg, robot_xml=args.robot_xml)
        return

    in_dir = args.input_dir.expanduser().resolve()
    if not in_dir.exists():
        raise FileNotFoundError(in_dir)
    out_dir = args.output_dir
    if out_dir is None:
        out_dir = in_dir.parent / f"{in_dir.name}_npz"
    out_dir = out_dir.expanduser().resolve()
    pattern = "**/*.pkl" if args.recursive else "*.pkl"
    pkl_files = sorted(in_dir.glob(pattern))
    if not pkl_files:
        raise FileNotFoundError(f"No PKL files found in {in_dir} (recursive={args.recursive})")
    print(f"[INFO] Found {len(pkl_files)} PKL files.")
    for p in pkl_files:
        out_file = _build_output_path(p, in_dir, out_dir)
        convert_one(p, out_file, cfg, robot_xml=args.robot_xml)
    print(f"[DONE] Converted {len(pkl_files)} files to {out_dir}")


if __name__ == "__main__":
    main()
