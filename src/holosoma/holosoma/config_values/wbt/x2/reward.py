"""X2 机器人全身动作跟踪奖励预设，包含 31 个自由度和 OBD 平衡奖励。

平衡奖励根据 ``robot_config.asset.robot_type``，从
``managers/reward/terms/wbt.py`` 中选择 X2 踝关节坐标系下的支撑多边形。
"""

from holosoma.config_types.reward import RewardManagerCfg, RewardTermCfg

x2_31dof_wbt_reward = RewardManagerCfg(
    terms={
        "motion_global_ref_position_error_exp": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:motion_global_ref_position_error_exp",
            params={"sigma": 0.3},
            weight=0.5,
        ),
        "motion_global_ref_orientation_error_exp": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:motion_global_ref_orientation_error_exp",
            params={"sigma": 0.4},
            weight=0.5,
        ),
        "motion_relative_body_position_error_exp": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:motion_relative_body_position_error_exp",
            params={"sigma": 0.3},
            weight=1.0,
        ),
        "motion_relative_body_orientation_error_exp": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:motion_relative_body_orientation_error_exp",
            params={"sigma": 0.4},
            weight=1.0,
        ),
        "motion_global_body_lin_vel": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:motion_global_body_lin_vel",
            params={"sigma": 1.0},
            weight=1.0,
        ),
        "motion_global_body_ang_vel": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:motion_global_body_ang_vel",
            params={"sigma": 3.14},
            weight=1.0,
        ),
        "action_rate_l2": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:penalty_action_rate",
            weight=-0.1,
        ),
        "limits_dof_pos": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:limits_dof_pos",
            params={"soft_dof_pos_limit": 0.9},
            weight=-10.0,
        ),
        # X2 body names: allow foot_contact_point / ankle_roll / wrist contacts.
        "undesired_contacts": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:UndesiredContacts",
            params={
                "threshold": 1.0,
                "undesired_contacts_body_names": (
                    "^(?!left_foot_contact_point$)(?!right_foot_contact_point$)"
                    "(?!left_wrist_yaw_link$)(?!right_wrist_yaw_link$)"
                    "(?!left_wrist_roll_link$)(?!right_wrist_roll_link$)"
                    "(?!left_ankle_roll_link$)(?!right_ankle_roll_link$).+$"
                ),
            },
            weight=-0.1,
        ),
        "reference_support_contact_mismatch_penalty": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:ReferenceSupportContactMismatchPenalty",
            params={
                "force_threshold": 5.0,
                "force_tau": 0.5,
                "stance_miss_weight": 1.0,
                "swing_extra_contact_weight": 1.0,
            },
            weight=-2.0,
        ),
        "support_xcom_polygon_margin": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:SupportXcomPolygonMarginPenalty",
            params={
                "threshold": 1.0,
                "single_support_safety_margin": 0.02,
                "double_support_safety_margin": 0.03,
                "gravity": 9.81,
                "com_height_floor": 0.25,
                "max_penalty": 0.04,
                "penalty_power": 1.0,
            },
            weight=-50.0,
        ),
        "xcom_ttb": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:XcomTtbPenalty",
            params={
                "threshold": 1.0,
                "single_support_ttb_threshold": 0.30,
                "double_support_ttb_threshold": 0.20,
                "v_min": 0.01,
                "gravity": 9.81,
                "com_height_floor": 0.25,
                "max_penalty": 0.09,
            },
            weight=-15.0,
        ),
        "single_support_foot_slip_penalty": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:SingleSupportFootSlipPenalty",
            params={"force_threshold": 1.0},
            weight=-1.0,
        ),
        "stance_ankle_action_rate": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:StanceAnkleActionRatePenalty",
            params={
                "left_joint_names": ["left_ankle_pitch_joint", "left_ankle_roll_joint"],
                "right_joint_names": ["right_ankle_pitch_joint", "right_ankle_roll_joint"],
                "threshold": 1.0,
                "joint_weights": [1.0, 1.0],
            },
            weight=-0.3,
        ),
    }
)

x2_31dof_wbt_fast_sac_reward = RewardManagerCfg(
    terms={
        **x2_31dof_wbt_reward.terms,
        "action_rate_l2": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:penalty_action_rate",
            weight=-0.1,
        ),
        "motion_global_ref_position_error_exp": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:motion_global_ref_position_error_exp",
            params={"sigma": 0.3},
            weight=1.0,
        ),
        "motion_global_ref_orientation_error_exp": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:motion_global_ref_orientation_error_exp",
            params={"sigma": 0.4},
            weight=0.5,
        ),
        "motion_relative_body_position_error_exp": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:motion_relative_body_position_error_exp",
            params={"sigma": 0.3},
            weight=2.0,
        ),
        "motion_relative_body_orientation_error_exp": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:motion_relative_body_orientation_error_exp",
            params={"sigma": 0.4},
            weight=1.0,
        ),
    }
)

__all__ = ["x2_31dof_wbt_fast_sac_reward", "x2_31dof_wbt_reward"]
