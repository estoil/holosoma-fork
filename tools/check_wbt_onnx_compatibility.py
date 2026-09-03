#!/usr/bin/env python3
"""Check that WBT ONNX checkpoints share one deployment-compatible interface."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort


EXPECTED_INPUTS = {"obs": [1, 463], "time_step": [1, 1]}
EXPECTED_OUTPUTS = {
    "actions": [1, 29],
    "joint_pos": [1, 29],
    "joint_vel": [1, 29],
    "ref_pos_xyz": [1, 3],
    "ref_quat_xyzw": [1, 4],
    "reference_support_phase": [1, 2],
    "future_support_phase": [1, 10],
    "future_cmd": [1, 290],
}
REQUIRED_METADATA = {
    "dof_names", "kp", "kd", "action_scale", "robot_urdf", "experiment_config", "iteration"
}
REFERENCE_SHAPES = {(992, 29): 2, (992, 2): 1, (992, 3): 1, (992, 4): 1}


def digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()[:12]


def tensor_constants(model: onnx.ModelProto) -> list[onnx.TensorProto]:
    return [
        attr.t
        for node in model.graph.node if node.op_type == "Constant"
        for attr in node.attribute if attr.type == onnx.AttributeProto.TENSOR
    ]


def reference_digest(constants: list[onnx.TensorProto]) -> str:
    selected = sorted(
        (tuple(t.dims), hashlib.sha256(t.raw_data).hexdigest())
        for t in constants if tuple(t.dims) in REFERENCE_SHAPES
    )
    return digest(selected)


def inspect(path: Path) -> dict:
    model = onnx.load(path, load_external_data=False)
    onnx.checker.check_model(model)
    raw_metadata = {entry.key: entry.value for entry in model.metadata_props}
    metadata = {}
    for key, value in raw_metadata.items():
        try:
            metadata[key] = json.loads(value)
        except json.JSONDecodeError:
            metadata[key] = value

    options = ort.SessionOptions()
    options.intra_op_num_threads = 1
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(path), sess_options=options, providers=["CPUExecutionProvider"])
    inputs = {item.name: list(item.shape) for item in session.get_inputs()}
    outputs = {item.name: list(item.shape) for item in session.get_outputs()}

    smoke = {}
    for timestep in (0, 991, 2000):
        values = session.run(None, {
            "obs": np.zeros((1, 463), dtype=np.float32),
            "time_step": np.array([[timestep]], dtype=np.float32),
        })
        smoke[timestep] = {item.name: value for item, value in zip(session.get_outputs(), values)}

    constants = tensor_constants(model)
    shape_counts = {shape: sum(tuple(t.dims) == shape for t in constants) for shape in REFERENCE_SHAPES}
    match = re.search(r"model_(\d+)\.onnx$", path.name)
    filename_step = int(match.group(1)) if match else None
    iteration = int(metadata.get("iteration", -1))
    joint_limits_present = {"dof_pos_lower", "dof_pos_upper"}.issubset(metadata)

    checks = {
        "onnx_checker": True,
        "required_metadata": REQUIRED_METADATA.issubset(metadata),
        "inputs": inputs == EXPECTED_INPUTS,
        "outputs": outputs == EXPECTED_OUTPUTS,
        "dof_count": len(metadata.get("dof_names", [])) == 29,
        "kp_count": len(metadata.get("kp", [])) == 29,
        "kd_count": len(metadata.get("kd", [])) == 29,
        "action_scale_count": len(metadata.get("action_scale", [])) == 29,
        "motion_constants": shape_counts == REFERENCE_SHAPES,
        "finite_smoke": all(np.isfinite(value).all() for row in smoke.values() for value in row.values()),
        "clip_end_clamps": all(
            np.array_equal(smoke[991][name], smoke[2000][name])
            for name in EXPECTED_OUTPUTS if name != "actions"
        ),
        "iteration_matches_filename": filename_step == iteration,
    }
    return {
        "path": str(path.resolve()),
        "step": filename_step,
        "iteration": iteration,
        "inputs": inputs,
        "outputs": outputs,
        "metadata_keys": sorted(metadata),
        "dof_names": metadata.get("dof_names"),
        "kp": metadata.get("kp"),
        "kd": metadata.get("kd"),
        "action_scale": metadata.get("action_scale"),
        "robot_urdf_digest": digest(metadata.get("robot_urdf")),
        "experiment_config_digest": digest(metadata.get("experiment_config")),
        "reference_digest": reference_digest(constants),
        "reference_constant_shapes": {str(shape): count for shape, count in shape_counts.items()},
        "joint_limits_in_metadata": joint_limits_present,
        "checks": checks,
        "passed": all(checks.values()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("models", nargs="+", type=Path)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    args = parser.parse_args()

    rows = [inspect(path) for path in args.models]
    baseline = rows[0]
    compare_fields = (
        "inputs", "outputs", "dof_names", "kp", "kd", "action_scale",
        "robot_urdf_digest", "experiment_config_digest", "reference_digest",
    )
    common_checks = {field: all(row[field] == baseline[field] for row in rows) for field in compare_fields}
    overall = all(row["passed"] for row in rows) and all(common_checks.values())

    result = {"overall_passed": overall, "cross_model_checks": common_checks, "models": rows}
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    lines = [
        "# Top-5 WBT ONNX 部署一致性检查", "",
        f"- 总结：**{'通过' if overall else '未通过'}**", "",
        "| step | ONNX | IO | 29 DoF | motion 992 | 末帧钳制 | iteration | 结果 |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        c = row["checks"]
        mark = lambda ok: "✅" if ok else "❌"
        lines.append(
            f"| {row['step']} | {mark(c['onnx_checker'])} | {mark(c['inputs'] and c['outputs'])} | "
            f"{mark(c['dof_count'] and c['kp_count'] and c['kd_count'] and c['action_scale_count'])} | "
            f"{mark(c['motion_constants'])} | {mark(c['clip_end_clamps'])} | "
            f"{mark(c['iteration_matches_filename'])} | **{mark(row['passed'])}** |"
        )
    lines += ["", "## 跨模型一致性", ""]
    for field, ok in common_checks.items():
        lines.append(f"- {'✅' if ok else '❌'} `{field}`")
    lines += [
        "", "## 已确认接口", "",
        "- 输入：`obs [1,463]`、`time_step [1,1]`。",
        "- 输出：`actions [1,29]`、当前关节参考、参考位姿、左右脚支撑相位、5 帧 future support/cmd。",
        "- 内嵌动作：992 帧；超过 991 的 timestep 会钳制到末帧。",
        "- 五个模型的关节顺序、KP/KD、action scale、URDF、实验配置和内嵌动作逐项一致。",
        "", "## 注意项", "",
        "- ONNX 元数据没有 `dof_pos_lower/dof_pos_upper`；sim2sim 必须由 G1 robot config/XML 提供并核对关节限位。",
        "- 此检查验证结构与静态数据一致性，不替代闭环 MuJoCo 稳定性测试。",
        "", f"机器可读结果：`{args.json.name}`。", "",
    ]
    args.markdown.write_text("\n".join(lines), encoding="utf-8")
    print(f"overall_passed={overall}")
    for row in rows:
        failed = [key for key, ok in row["checks"].items() if not ok]
        print(f"step={row['step']} passed={row['passed']} failed={failed}")
    print(args.markdown)
    print(args.json)


if __name__ == "__main__":
    main()
