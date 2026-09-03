from __future__ import annotations

import numpy as np
import pytest

from holosoma.utils.sim_utils import load_motion_initial_state, world_to_body_vector_xyzw


def _write_motion(path, joint_names):
    num_joints = len(joint_names)
    joint_pos = np.zeros((2, 7 + num_joints), dtype=np.float32)
    joint_vel = np.zeros((2, 6 + num_joints), dtype=np.float32)
    # Deliberately non-unit wxyz quaternion: -90-degree yaw after normalization.
    joint_pos[:, 3] = np.sqrt(2.0)
    joint_pos[:, 6] = -np.sqrt(2.0)
    joint_pos[1, 7:] = np.arange(num_joints, dtype=np.float32)
    joint_vel[1, 6:] = np.arange(num_joints, dtype=np.float32) + 10.0
    np.savez(
        path,
        fps=np.array([50]),
        joint_names=np.asarray(joint_names),
        joint_pos=joint_pos,
        joint_vel=joint_vel,
    )


def test_load_motion_initial_state_reorders_joints_and_normalizes_quaternion(tmp_path):
    path = tmp_path / "motion.npz"
    _write_motion(path, ["joint_b", "joint_a"])

    state = load_motion_initial_state(path, 1, ["joint_a", "joint_b"])

    assert state.timestep == 1
    assert state.fps == 50.0
    np.testing.assert_allclose(
        state.root_state[3:7],
        [0.0, 0.0, -np.sqrt(0.5), np.sqrt(0.5)],
        atol=1e-7,
    )
    np.testing.assert_allclose(state.dof_pos, [1.0, 0.0])
    np.testing.assert_allclose(state.dof_vel, [11.0, 10.0])


def test_load_motion_initial_state_rejects_incomplete_floating_base_state(tmp_path):
    path = tmp_path / "motion.npz"
    np.savez(
        path,
        fps=np.array([50]),
        joint_names=np.asarray(["joint_a"]),
        joint_pos=np.zeros((2, 1), dtype=np.float32),
        joint_vel=np.zeros((2, 1), dtype=np.float32),
    )

    with pytest.raises(ValueError, match="joint_pos must have shape"):
        load_motion_initial_state(path, 0, ["joint_a"])


def test_world_to_body_vector_uses_inverse_orientation():
    quat_yaw_90_xyzw = np.array([0.0, 0.0, np.sqrt(0.5), np.sqrt(0.5)], dtype=np.float32)

    vector_b = world_to_body_vector_xyzw(np.array([0.0, 1.0, 0.0]), quat_yaw_90_xyzw)

    np.testing.assert_allclose(vector_b, [1.0, 0.0, 0.0], atol=1e-6)
