# ---------------------------------------------------------------------------------------------------
# Modified from the Holosoma framework (Amazon FAR): https://github.com/amazon-far/holosoma
# Copyright Amazon.com, Inc. or its affiliates. Licensed under the Apache License, Version 2.0.
# This file was CHANGED for DDC: it carries the deployable support-relative dynamic-CoM observation
# and/or the human-science balance reward library and its config (see training/TRAINING.md).
# The Apache-2.0 license text is in the repository LICENSE; attribution is in training/NOTICE.
# ---------------------------------------------------------------------------------------------------

"""Whole Body Tracking observation presets for the G1 robot."""

from dataclasses import replace

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
        # DEPLOYABLE balance obs: CoM-rel-support-center position + relative velocity, base frame, 4 dims total.
        # pure FK (encoders + IMU gyro), no base linear velocity / absolute position needed; the dynamic world-frame xCoM stays critic-privileged.
        # noise=0.015: domain randomization before real-robot transfer (covers encoder-velocity noise + mass/kinematic model error).
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
    # PRIVILEGED / critic-only: xCoM relative to support-foot center (base frame). Deliberately not in the actor:
    # it depends on world-frame CoM velocity, unreliable on hardware -> adding it to the actor causes a sim2real gap. Critic is training-only, not deployed.
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

robust_actor_terms = actor_obs_shared.terms.copy()
_robust_sensor_curriculum = {
    "stage_steps": [0, 80_000, 200_000],
    "max_delay_ms": [2.0, 5.0, 8.0],
    "dof_vel_noise": [0.02, 0.05, 0.10],
    "jitter_ms": 1.0,
    "stress_probability": 0.05,
    "stress_delay_ms": 15.0,
    "stress_dof_vel_noise": 0.20,
}
robust_actor_terms.update(
    {
        # All deployable sensor-derived terms share one per-episode fractional
        # delay.  Their dimensions and the 463-D ONNX contract stay unchanged.
        "base_ang_vel": replace(
            robust_actor_terms["base_ang_vel"],
            func="holosoma.managers.observation.terms.wbt:RobustDelayedSensorObservation",
            params={**_robust_sensor_curriculum, "source": "base_ang_vel", "resample_on_reset": True},
        ),
        "projected_gravity": replace(
            robust_actor_terms["projected_gravity"],
            func="holosoma.managers.observation.terms.wbt:RobustDelayedSensorObservation",
            params={"source": "projected_gravity"},
        ),
        "dof_pos": replace(
            robust_actor_terms["dof_pos"],
            func="holosoma.managers.observation.terms.wbt:RobustDelayedSensorObservation",
            params={"source": "dof_pos"},
        ),
        "dof_vel": replace(
            robust_actor_terms["dof_vel"],
            func="holosoma.managers.observation.terms.wbt:RobustDelayedSensorObservation",
            params={"source": "dof_vel"},
            noise=0.0,
        ),
        "whole_body_com_rel_support_center": replace(
            robust_actor_terms["whole_body_com_rel_support_center"],
            func="holosoma.managers.observation.terms.wbt:RobustDelayedSensorObservation",
            params={"source": "whole_body_com_rel_support_center"},
        ),
    }
)

g1_29dof_wbt_robust_observation = replace(
    g1_29dof_wbt_observation,
    groups={
        "actor_obs": replace(actor_obs_shared, terms=robust_actor_terms),
        "critic_obs": g1_29dof_wbt_observation.groups["critic_obs"],
    },
)

__all__ = [
    "g1_29dof_wbt_observation",
    "g1_29dof_wbt_observation_w_object",
    "g1_29dof_wbt_robust_observation",
]
