"""FastSAC 动作边界回归测试。"""

from types import SimpleNamespace

import pytest
import torch

from holosoma.agents.fast_sac.fast_sac_agent import FastSACEnv


def _make_wrapper(action_scales: torch.Tensor) -> FastSACEnv:
    """构造只包含动作边界计算所需字段的轻量包装器。"""
    robot_config = SimpleNamespace(
        dof_names=["joint_a", "joint_b"],
        dof_pos_lower_limit_list=[-1.0, -2.0],
        dof_pos_upper_limit_list=[2.0, 1.0],
        init_state=SimpleNamespace(default_joint_angles={"joint_a": 0.5, "joint_b": -0.5}),
    )
    wrapper = FastSACEnv.__new__(FastSACEnv)
    wrapper._env = SimpleNamespace(
        robot_config=robot_config,
        device="cpu",
        action_scales=action_scales,
    )
    return wrapper


def test_action_boundaries_use_actual_per_joint_scales() -> None:
    """Actor 边界经过环境逐关节缩放后应恢复原始目标位置范围。"""
    action_scales = torch.tensor([0.25, 0.5])
    wrapper = _make_wrapper(action_scales)

    boundaries = wrapper._compute_action_boundaries()

    expected_max_range = torch.tensor([1.5, 1.5])
    torch.testing.assert_close(boundaries, torch.tensor([6.0, 3.0]))
    torch.testing.assert_close(boundaries * action_scales, expected_max_range)


@pytest.mark.parametrize("invalid_scale", [0.0, -0.1, float("nan"), float("inf")])
def test_action_boundaries_reject_invalid_scales(invalid_scale: float) -> None:
    """无效缩放不能静默产生无限或方向错误的动作边界。"""
    wrapper = _make_wrapper(torch.tensor([0.25, invalid_scale]))

    with pytest.raises(ValueError, match="joint_b"):
        wrapper._compute_action_boundaries()
