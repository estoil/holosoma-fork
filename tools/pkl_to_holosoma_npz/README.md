# PKL to Holosoma NPZ Converter

This tool converts `video2robot` / GMR PKL motion files into Holosoma-compatible WBT motion NPZ files.

## What this converter guarantees

- Generates required Holosoma keys:
  - `fps`, `joint_pos`, `joint_vel`
  - `body_pos_w`, `body_quat_w`, `body_lin_vel_w`, `body_ang_vel_w`
  - `body_names`, `joint_names`
- Preserves original PKL content without loss by default:
  - embeds `raw_pickle_bytes` (exact serialized PKL dictionary)
  - stores key raw arrays (`raw_root_pos`, `raw_root_rot_xyzw`, etc.)

## Important note about orientation fields

Typical `video2robot` PKL does not contain per-link orientations (`body_quat_w`) and per-link angular velocities directly.
To satisfy Holosoma schema:

- `body_quat_w` is approximated from root orientation (replicated over links)
- `body_ang_vel_w` is approximated from root angular velocity (replicated over links)

No source information is discarded, because the original PKL bytes are embedded in the NPZ.

## Usage

### Single file

```bash
cd /home/wxy/taichi_deploy/holosoma
python tools/pkl_to_holosoma_npz/convert_pkl_to_holosoma_npz.py \
  --input-file /home/wxy/taichi_deploy/video2robot/data/single_leg_balance_mjzu/robot_motion_track_1.pkl \
  --output-file /home/wxy/taichi_deploy/video2robot/data/single_leg_balance_mjzu/robot_motion_track_1_holosoma.npz
```

### Batch directory

```bash
cd /home/wxy/taichi_deploy/holosoma
python tools/pkl_to_holosoma_npz/convert_pkl_to_holosoma_npz.py \
  --input-dir /home/wxy/taichi_deploy/video2robot/data \
  --output-dir /home/wxy/taichi_deploy/video2robot/data_holosoma_npz \
  --recursive
```

## Common options

- `--strict`: fail on ambiguous schema conditions (recommended in CI/production)
- `--local-body-pos-frame root|world`: how to interpret `local_body_pos` (default `root`)
- `--no-preserve-raw`: disable raw PKL embedding (not recommended)
- `--no-compress`: save with `np.savez` instead of `np.savez_compressed`

