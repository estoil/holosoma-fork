"""Whole Body Tracking command presets for the G1 robot."""

from dataclasses import replace

from holosoma.config_types.command import CommandManagerCfg, CommandTermCfg, MotionConfig, NoiseToInitialPoseConfig

init_pose_config = NoiseToInitialPoseConfig(
    overall_noise_scale=1.0,
    dof_pos=0.1,
    root_pos=[0.05, 0.05, 0.01],
    root_rot=[0.1, 0.1, 0.2],
    root_lin_vel=[0.5, 0.5, 0.2],
    root_ang_vel=[0.52, 0.52, 0.78],
    object_pos=[0.05, 0.05, 0.0],
)

motion_config = MotionConfig(
    motion_file="holosoma/data/motions/g1_29dof/whole_body_tracking/sub3_largebox_003_mj.npz",
    body_names_to_track=[
        "pelvis",
        "left_hip_roll_link",
        "left_knee_link",
        "left_ankle_roll_link",
        "right_hip_roll_link",
        "right_knee_link",
        "right_ankle_roll_link",
        "torso_link",
        "left_shoulder_roll_link",
        "left_elbow_link",
        "left_wrist_yaw_link",
        "right_shoulder_roll_link",
        "right_elbow_link",
        "right_wrist_yaw_link",
    ],
    body_name_ref=["torso_link"],
    use_adaptive_timesteps_sampler=False,  # 关采样器 → 非frame0的起始帧走均匀随机
    start_at_timestep_zero_prob=1.0,  # 100% 从 frame0，避免中段 RSI 掩盖单脚失败
    noise_to_initial_pose=init_pose_config,
)

motion_config_w_object = replace(
    motion_config,
    motion_file="holosoma/data/motions/g1_29dof/whole_body_tracking/sub3_largebox_003_mj_w_obj.npz",
)

# Single-motion robust training: explicitly learn a quiet double-support pose,
# enter the Taichi clip smoothly, and return to/hold the same stable pose.
robust_motion_config = replace(
    motion_config,
    motion_file="motions_from_web/taichi_g1_danjiao_4_4_holosoma.npz",
    use_adaptive_timesteps_sampler=True,
    # Half of resets exercise the complete stand -> motion -> stand sequence;
    # the remainder focus on failure-heavy phases through adaptive RSI.
    start_at_timestep_zero_prob=0.5,
    freeze_at_timestep_zero_prob=0.0,
    enable_default_pose_prepend=True,
    default_pose_prepend_hold_duration_s=2.0,
    default_pose_prepend_duration_s=2.0,
    enable_default_pose_append=True,
    default_pose_append_duration_s=2.0,
    default_pose_append_hold_duration_s=4.0,
    noise_to_initial_pose=replace(
        init_pose_config,
        dof_pos=0.05,
        root_pos=[0.02, 0.02, 0.01],
        root_rot=[0.05, 0.05, 0.10],
        root_lin_vel=[0.20, 0.20, 0.10],
        root_ang_vel=[0.20, 0.20, 0.30],
    ),
)

g1_29dof_wbt_command = CommandManagerCfg(
    params={},
    setup_terms={
        "motion_command": CommandTermCfg(
            func="holosoma.managers.command.terms.wbt:MotionCommand",
            params={
                "motion_config": motion_config,
            },
        ),
    },
    reset_terms={
        "motion_command": CommandTermCfg(
            func="holosoma.managers.command.terms.wbt:MotionCommand",
        )
    },
    step_terms={
        "motion_command": CommandTermCfg(
            func="holosoma.managers.command.terms.wbt:MotionCommand",
        )
    },
)

g1_29dof_wbt_command_w_object = replace(
    g1_29dof_wbt_command,
    setup_terms={
        "motion_command": CommandTermCfg(
            func="holosoma.managers.command.terms.wbt:MotionCommand",
            params={
                "motion_config": motion_config_w_object,
            },
        )
    },
)

g1_29dof_wbt_robust_command = replace(
    g1_29dof_wbt_command,
    setup_terms={
        "motion_command": CommandTermCfg(
            func="holosoma.managers.command.terms.wbt:MotionCommand",
            params={"motion_config": robust_motion_config},
        )
    },
)

__all__ = [
    "g1_29dof_wbt_command",
    "g1_29dof_wbt_command_w_object",
    "g1_29dof_wbt_robust_command",
]
