"""Whole Body Tracking observation presets for the X2 robot (31 DoF).

Actor dim checklist (alphabetical concat, K=5 future frames):
  actions 31 + base_ang_vel 3 + dof_pos 31 + dof_vel 31
  + future_cmd 310 (=31*2*5) + future_support_phase 10
  + motion_command 62 + motion_ref_ori_b 6 + projected_gravity 3
  + reference_support_phase 2 + whole_body_com_rel_support_center 4
  = 493
"""

from holosoma.config_types.observation import ObservationManagerCfg, ObsGroupCfg, ObsTermCfg

actor_obs_shared = ObsGroupCfg(
    concatenate=True,
    enable_noise=True,
    history_length=1,
    terms={
        "motion_command": ObsTermCfg(
            func="holosoma.managers.observation.terms.wbt:motion_command",
            scale=1.0,
            noise=0.0,
        ),
        "motion_ref_ori_b": ObsTermCfg(
            func="holosoma.managers.observation.terms.wbt:motion_ref_ori_b",
            scale=1.0,
            noise=0.05,
        ),
        "base_ang_vel": ObsTermCfg(
            func="holosoma.managers.observation.terms.wbt:base_ang_vel",
            scale=1.0,
            noise=0.2,
        ),
        "dof_pos": ObsTermCfg(
            func="holosoma.managers.observation.terms.wbt:dof_pos",
            scale=1.0,
            noise=0.01,
        ),
        "dof_vel": ObsTermCfg(
            func="holosoma.managers.observation.terms.wbt:dof_vel",
            scale=1.0,
            noise=0.5,
        ),
        "actions": ObsTermCfg(
            func="holosoma.managers.observation.terms.wbt:actions",
            scale=1.0,
            noise=0.0,
        ),
        "projected_gravity": ObsTermCfg(
            func="holosoma.managers.observation.terms.wbt:projected_gravity",
            scale=1.0,
            noise=0.03,
        ),
        "reference_support_phase": ObsTermCfg(
            func="holosoma.managers.observation.terms.wbt:reference_support_phase",
            scale=1.0,
            noise=0.0,
        ),
        "future_support_phase": ObsTermCfg(
            func="holosoma.managers.observation.terms.wbt:future_support_phase",
            params={"num_future_frames": 5},
            scale=1.0,
            noise=0.0,
        ),
        "future_cmd": ObsTermCfg(
            func="holosoma.managers.observation.terms.wbt:future_cmd",
            params={"num_future_frames": 5},
            scale=1.0,
            noise=0.0,
        ),
        # DEPLOYABLE balance obs: CoM-rel-support-center 位置 + 相对速度, base 系, 共 4 维。
        "whole_body_com_rel_support_center": ObsTermCfg(
            func="holosoma.managers.observation.terms.wbt:whole_body_com_rel_support_center",
            scale=1.0,
            noise=0.015,
        ),
    },
)

critic_obs_shared_terms = {
    "motion_command": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:motion_command",
        scale=1.0,
        noise=0.0,
    ),
    "motion_ref_pos_b": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:motion_ref_pos_b",
        scale=1.0,
        noise=0.25,
    ),
    "motion_ref_ori_b": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:motion_ref_ori_b",
        scale=1.0,
        noise=0.05,
    ),
    "robot_body_pos_b": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:robot_body_pos_b",
        scale=1.0,
        noise=0.0,
    ),
    "robot_body_ori_b": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:robot_body_ori_b",
        scale=1.0,
        noise=0.0,
    ),
    "base_lin_vel": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:base_lin_vel",
        scale=1.0,
        noise=0.0,
    ),
    "base_ang_vel": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:base_ang_vel",
        scale=1.0,
        noise=0.2,
    ),
    "dof_pos": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:dof_pos",
        scale=1.0,
        noise=0.01,
    ),
    "dof_vel": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:dof_vel",
        scale=1.0,
        noise=0.5,
    ),
    "actions": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:actions",
        scale=1.0,
        noise=0.0,
    ),
    "projected_gravity": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:projected_gravity",
        scale=1.0,
        noise=0.0,
    ),
    "reference_support_phase": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:reference_support_phase",
        scale=1.0,
        noise=0.0,
    ),
    "future_support_phase": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:future_support_phase",
        params={"num_future_frames": 5},
        scale=1.0,
        noise=0.0,
    ),
    "future_cmd": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:future_cmd",
        params={"num_future_frames": 5},
        scale=1.0,
        noise=0.0,
    ),
    "whole_body_xcom_rel_support_center": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:whole_body_xcom_rel_support_center",
        scale=1.0,
        noise=0.0,
    ),
}

x2_31dof_wbt_observation = ObservationManagerCfg(
    groups={
        "actor_obs": actor_obs_shared,
        "critic_obs": ObsGroupCfg(
            concatenate=True,
            enable_noise=False,
            history_length=1,
            terms=critic_obs_shared_terms,
        ),
    },
)

__all__ = ["x2_31dof_wbt_observation"]
