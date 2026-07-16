"""Whole Body Tracking observation presets for the G1 robot."""

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
            func="holosoma.managers.observation.terms.wbt:base_ang_vel",  # 回退 0705(去掉 IMU OU 变体),2026-07-15
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
            func="holosoma.managers.observation.terms.wbt:projected_gravity",  # 回退 0705(去掉 IMU OU 变体),2026-07-15
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
        # DEPLOYABLE balance obs: CoM-rel-support-center 位置 + 相对速度,base 系,共 4 维。
        # 纯 FK(编码器 + IMU 陀螺),不需 base 线速度/绝对位置;动态世界系 xCoM 留 critic 特权。
        # noise=0.015:上真机前的域随机(覆盖编码器速度噪声 + 质量/运动学模型误差)。
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
    # PRIVILEGED / critic-only: xCoM relative to support-foot center (base frame). 故意不加进 actor:
    # 它依赖世界系 CoM 速度,真机不可靠 → 加 actor 会有 sim2real gap。critic 仅训练用,不部署。
    "whole_body_xcom_rel_support_center": ObsTermCfg(
        func="holosoma.managers.observation.terms.wbt:whole_body_xcom_rel_support_center",
        scale=1.0,
        noise=0.0,
    ),
}

critic_obs_w_object_terms = critic_obs_shared_terms.copy()
critic_obs_w_object_terms.update(
    {
        "obj_pos_b": ObsTermCfg(
            func="holosoma.managers.observation.terms.wbt:obj_pos_b",
            scale=1.0,
            noise=0.0,
        ),
        "obj_ori_b": ObsTermCfg(
            func="holosoma.managers.observation.terms.wbt:obj_ori_b",
            scale=1.0,
            noise=0.0,
        ),
        "obj_lin_vel_b": ObsTermCfg(
            func="holosoma.managers.observation.terms.wbt:obj_lin_vel_b",
            scale=1.0,
            noise=0.0,
        ),
    }
)

g1_29dof_wbt_observation = ObservationManagerCfg(
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

g1_29dof_wbt_observation_w_object = ObservationManagerCfg(
    groups={
        "actor_obs": actor_obs_shared,
        "critic_obs": ObsGroupCfg(
            concatenate=True,
            enable_noise=False,
            history_length=1,
            terms=critic_obs_w_object_terms,
        ),
    },
)

__all__ = ["g1_29dof_wbt_observation", "g1_29dof_wbt_observation_w_object"]
