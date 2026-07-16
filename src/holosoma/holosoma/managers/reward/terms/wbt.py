"""Reward terms for Whole Body Tracking tasks."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, List

import torch
from loguru import logger

from holosoma.config_types.reward import RewardTermCfg
from holosoma.managers.command.terms.wbt import MotionCommand
from holosoma.managers.reward.base import RewardTermBase
from holosoma.utils.rotations import quat_error_magnitude

if TYPE_CHECKING:
    from holosoma.envs.wbt.wbt_manager import WholeBodyTrackingManager


def _get_motion_command_and_assert_type(env: WholeBodyTrackingManager) -> MotionCommand:
    motion_command = env.command_manager.get_state("motion_command")
    assert motion_command is not None, "motion_command not found in command manager"
    assert isinstance(motion_command, MotionCommand), f"Expected MotionCommand, got {type(motion_command)}"
    return motion_command


#########################################################################################################
## terms same to managers/reward/terms/locomotion.py
#########################################################################################################


def penalty_action_rate(env: WholeBodyTrackingManager) -> torch.Tensor:
    """Penalize changes in actions between steps.

    Args:
        env: The environment instance

    Returns:
        Reward tensor [num_envs]
    """
    actions = env.action_manager.action
    prev_actions = env.action_manager.prev_action
    return torch.sum(torch.square(prev_actions - actions), dim=1)


def limits_dof_pos(env: WholeBodyTrackingManager, soft_dof_pos_limit: float = 0.95) -> torch.Tensor:
    """Penalize joint positions too close to limits.

    Args:
        env: The environment instance
        soft_dof_pos_limit: Soft limit as fraction of hard limit

    Returns:
        Reward tensor [num_envs]
    """
    # Use soft limits as fraction of hard limits
    m = (env.simulator.hard_dof_pos_limits[:, 0] + env.simulator.hard_dof_pos_limits[:, 1]) / 2  # type: ignore[attr-defined]
    r = env.simulator.hard_dof_pos_limits[:, 1] - env.simulator.hard_dof_pos_limits[:, 0]  # type: ignore[attr-defined]
    lower_soft_limit = m - 0.5 * r * soft_dof_pos_limit
    upper_soft_limit = m + 0.5 * r * soft_dof_pos_limit

    out_of_limits = -(env.simulator.dof_pos - lower_soft_limit).clip(max=0.0)  # lower limit
    out_of_limits += (env.simulator.dof_pos - upper_soft_limit).clip(min=0.0)
    return torch.sum(out_of_limits, dim=1)


#########################################################################################################
## terms specific to Whole Body Tracking
#########################################################################################################

# ================================================================================================
# Robot Tracking Rewards
# ================================================================================================


def motion_global_ref_position_error_exp(env: WholeBodyTrackingManager, sigma: float) -> torch.Tensor:
    motion_command = _get_motion_command_and_assert_type(env)
    error = torch.sum(torch.square(motion_command.ref_pos_w - motion_command.robot_ref_pos_w), dim=-1)
    return torch.exp(-error / sigma**2)


def motion_global_ref_orientation_error_exp(env: WholeBodyTrackingManager, sigma: float) -> torch.Tensor:
    motion_command = _get_motion_command_and_assert_type(env)
    error = quat_error_magnitude(motion_command.ref_quat_w, motion_command.robot_ref_quat_w) ** 2
    return torch.exp(-error / sigma**2)


def motion_relative_body_position_error_exp(env: WholeBodyTrackingManager, sigma: float) -> torch.Tensor:
    motion_command = _get_motion_command_and_assert_type(env)
    error = torch.sum(torch.square(motion_command.body_pos_relative_w - motion_command.robot_body_pos_w), dim=-1)
    return torch.exp(-error.mean(-1) / sigma**2)


def motion_relative_body_orientation_error_exp(env: WholeBodyTrackingManager, sigma: float) -> torch.Tensor:
    motion_command = _get_motion_command_and_assert_type(env)
    error = quat_error_magnitude(motion_command.body_quat_relative_w, motion_command.robot_body_quat_w) ** 2
    return torch.exp(-error.mean(-1) / sigma**2)


def motion_global_body_lin_vel(env: WholeBodyTrackingManager, sigma: float) -> torch.Tensor:
    motion_command = _get_motion_command_and_assert_type(env)
    error = torch.sum(torch.square(motion_command.body_lin_vel_w - motion_command.robot_body_lin_vel_w), dim=-1)
    return torch.exp(-error.mean(-1) / sigma**2)


def motion_global_body_ang_vel(env: WholeBodyTrackingManager, sigma: float) -> torch.Tensor:
    motion_command = _get_motion_command_and_assert_type(env)
    error = torch.sum(torch.square(motion_command.body_ang_vel_w - motion_command.robot_body_ang_vel_w), dim=-1)
    return torch.exp(-error.mean(-1) / sigma**2)

#新增ZMP设计
class ZMPSupportRegionReward(RewardTermBase):
    """基于 ZMP 是否落在脚底支撑区域附近的稳定性奖励。"""

    _CONTACT_BODY_ALIASES = {
        "left_foot_contact_point": "left_ankle_roll_link",
        "right_foot_contact_point": "right_ankle_roll_link",
    }

    def __init__(self, cfg: RewardTermCfg, env: WholeBodyTrackingManager):
        super().__init__(cfg, env)
        self.env = env
        self.sigma = cfg.params.get("sigma", 0.05)
        self.support_margin = cfg.params.get("support_margin", 0.04)
        self.vertical_force_threshold = cfg.params.get("vertical_force_threshold", 1.0)
        self.debug_log_interval = int(cfg.params.get("debug_log_interval", 0))
        self._call_count = 0

        contact_body_names = cfg.params.get(
            "contact_body_names", ("left_ankle_roll_link", "right_ankle_roll_link")
        )
        resolved_contact_body_names = self._resolve_contact_body_names(list(contact_body_names))
        self.contact_body_indexes = self._get_index_of_a_in_b(
            resolved_contact_body_names,
            self.env.simulator.body_names,  # type: ignore[attr-defined]
            self.env.device,
        )
        logger.info(
            "ZMPSupportRegionReward: using contact bodies {} (indexes={})",
            resolved_contact_body_names,
            self.contact_body_indexes.detach().cpu().tolist(),
        )

    def __call__(self, env: WholeBodyTrackingManager, **kwargs) -> torch.Tensor:
        contact_pos_w = self.env.simulator._rigid_body_pos[:, self.contact_body_indexes, :]  # type: ignore[attr-defined]
        contact_forces_w = self.env.simulator.contact_forces[:, self.contact_body_indexes, :]  # type: ignore[attr-defined]

        fz = torch.clamp(contact_forces_w[..., 2], min=0.0)
        total_fz = torch.sum(fz, dim=1)
        has_support = total_fz > self.vertical_force_threshold
        safe_total_fz = torch.clamp(total_fz, min=self.vertical_force_threshold)
        self._maybe_log_debug_stats(total_fz, has_support)

        # 地面 ZMP 常用形式：p_z^xy = sum_i(p_i^xy * f_i^z) / sum_i(f_i^z)
        zmp_xy = torch.sum(contact_pos_w[..., :2] * fz.unsqueeze(-1), dim=1) / safe_total_fz.unsqueeze(-1)

        # 用接触点 xy 的包围盒近似支撑区域，margin 表示允许的脚底/接触面扩展。
        support_min_xy = torch.min(contact_pos_w[..., :2], dim=1).values - self.support_margin
        support_max_xy = torch.max(contact_pos_w[..., :2], dim=1).values + self.support_margin
        clipped_zmp_xy = torch.minimum(torch.maximum(zmp_xy, support_min_xy), support_max_xy)
        outside_error = torch.sum(torch.square(zmp_xy - clipped_zmp_xy), dim=1)

        reward = torch.exp(-outside_error / self.sigma**2)
        return torch.where(has_support, reward, torch.zeros_like(reward))

    def reset(self, env_ids: torch.Tensor | None = None) -> None:
        pass

    def _resolve_contact_body_names(self, body_names: list[str]) -> list[str]:
        """把辅助接触点名称映射到真实承力 body，避免读取到全 0 的 contact force。"""
        simulator_body_names = self.env.simulator.body_names  # type: ignore[attr-defined]
        resolved = []
        for name in body_names:
            alias = self._CONTACT_BODY_ALIASES.get(name, name)
            if alias != name and alias in simulator_body_names:
                logger.warning("ZMPSupportRegionReward: remap contact body '{}' -> '{}'", name, alias)
                resolved.append(alias)
            else:
                resolved.append(name)
        return resolved

    def _maybe_log_debug_stats(self, total_fz: torch.Tensor, has_support: torch.Tensor) -> None:
        """定期打印 ZMP 接触力诊断，确认 reward 是否读到了真实支撑力。"""
        self._call_count += 1
        if self.debug_log_interval <= 0 or self._call_count % self.debug_log_interval != 0:
            return

        logger.info(
            "ZMPSupportRegionReward: mean_total_fz={:.3f}, max_total_fz={:.3f}, support_ratio={:.3f}",
            float(total_fz.mean().detach().cpu()),
            float(total_fz.max().detach().cpu()),
            float(has_support.float().mean().detach().cpu()),
        )

    def _get_index_of_a_in_b(self, a_names: List[str], b_names: List[str], device: str = "cpu") -> torch.Tensor:
        indexes = []
        for name in a_names:
            assert name in b_names, f"The specified name ({name}) doesn't exist: {b_names}"
            indexes.append(b_names.index(name))
        return torch.tensor(indexes, dtype=torch.long, device=device)


# ================================================================================================
# Object Tracking Rewards
# ================================================================================================


def object_global_ref_position_error_exp(env: WholeBodyTrackingManager, sigma: float) -> torch.Tensor:
    motion_command = _get_motion_command_and_assert_type(env)
    error = torch.sum(torch.square(motion_command.object_pos_w - motion_command.simulator_object_pos_w), dim=-1)
    return torch.exp(-error / sigma**2)


def object_global_ref_orientation_error_exp(env: WholeBodyTrackingManager, sigma: float) -> torch.Tensor:
    motion_command = _get_motion_command_and_assert_type(env)
    error = quat_error_magnitude(motion_command.object_quat_w, motion_command.simulator_object_quat_w) ** 2
    return torch.exp(-error / sigma**2)


# ================================================================================================
# Undesired Contacts Rewards
# ================================================================================================


class UndesiredContacts(RewardTermBase):
    def __init__(self, cfg: RewardTermCfg, env: WholeBodyTrackingManager):
        super().__init__(cfg, env)
        self.env = env
        undesired_contacts_body_names = [
            body_name
            for body_name in self.env.simulator.body_names  # type: ignore[attr-defined]
            if re.match(cfg.params.get("undesired_contacts_body_names", ""), body_name)
        ]
        self.undesired_contacts_body_indexes = self._get_index_of_a_in_b(
            undesired_contacts_body_names,
            self.env.simulator.body_names,  # type: ignore[attr-defined]
            self.env.device,
        )
        self.threshold = cfg.params.get("threshold", 1.0)

    def __call__(self, env: WholeBodyTrackingManager, **kwargs) -> torch.Tensor:
        # (num_envs, history_length, num_bodies, 3)
        net_contact_forces = self.env.simulator.contact_forces_history
        is_contact = (
            torch.max(torch.norm(net_contact_forces[:, :, self.undesired_contacts_body_indexes], dim=-1), dim=1)[0]
            > self.threshold
        )
        return torch.sum(is_contact, dim=1)

    def reset(self, env_ids: torch.Tensor | None = None) -> None:
        pass

    #########################################################################################################
    ## Internal Helper functions
    #########################################################################################################
    def _get_index_of_a_in_b(self, a_names: List[str], b_names: List[str], device: str = "cpu") -> torch.Tensor:
        indexes = []
        for name in a_names:
            assert name in b_names, f"The specified name ({name}) doesn't exist: {b_names}"
            indexes.append(b_names.index(name))
        return torch.tensor(indexes, dtype=torch.long, device=device)
