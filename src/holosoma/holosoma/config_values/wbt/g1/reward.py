"""Whole Body Tracking reward presets for the G1 robot."""

from holosoma.config_types.reward import RewardManagerCfg, RewardTermCfg

g1_29dof_wbt_reward = RewardManagerCfg(
    terms={
        # Motion tracking rewards - global reference frame
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
        # Motion tracking rewards - relative body frame
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
        # Motion tracking rewards - body velocities
        "motion_global_body_lin_vel": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:motion_global_body_lin_vel",
            params={"sigma": 1.0},
            weight=1.0,
        ),
        "motion_global_body_ang_vel": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:motion_global_body_ang_vel",
            params={"sigma": 3.14},  # 退回 072007:松跟踪、给平衡更多自由(收紧治晃但夺走平衡自由,两难→退回)
            weight=1.0,
        ),
        
        # 保留 holosoma 原有 ZMP 支撑域奖励（与 OBD 五项并存）
        "zmp_support_region_exp": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:ZMPSupportRegionReward",
            params={
                "contact_body_names": ("left_ankle_roll_link", "right_ankle_roll_link"),
                "sigma": 0.05,
                "support_margin": 0.04,
                "vertical_force_threshold": 1.0,
                "debug_log_interval": 200,
            },
            weight=0.5,
        ),

        # Regularization rewards
        "action_rate_l2": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:penalty_action_rate",
            weight=-0.1,
        ),
        "limits_dof_pos": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:limits_dof_pos",
            params={"soft_dof_pos_limit": 0.9},
            weight=-10.0,
        ),
        "undesired_contacts": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:UndesiredContacts",
            params={
                "threshold": 1.0,
                "undesired_contacts_body_names": (
                    "^(?!left_foot_contact_point$)(?!right_foot_contact_point$)"
                    "(?!left_wrist_yaw_link$)(?!right_wrist_yaw_link$)"
                    "(?!left_ankle_roll_link$)(?!right_ankle_roll_link$).+$"
                ),
            },
            weight=-0.1,
        ),
        # Anti foot-hopping. Penalizes mismatch between the reference support phase (precomputed
        # offline into each motion npz) and the robot's actual foot contact. Logic identical to
        # whole_body_tracking; weight rescaled from WBT's -10 to -2 for holosoma's reward magnitude.
        "reference_support_contact_mismatch_penalty": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:ReferenceSupportContactMismatchPenalty",
            params={
                "force_threshold": 5.0,
                "force_tau": 0.5,
                "stance_miss_weight": 1.0,
                "swing_extra_contact_weight": 1.0,
            },
            weight=-2.0,  # 回退 0705 原值(重跑 0705 配置,2026-07-15)
        ),
        # Balance: penalize the extrapolated CoM (xCoM) approaching/leaving the support polygon.
        # LINEAR hinge (penalty_power=1): weight * relu(safety - margin); safety=0.02 ≈ the reference's
        # single-leg xCoM margin, so ~0 for good tracking, rises as xCoM drifts to/over the foot edge.
        # per-step: 脚边 -0.02, 出界>=2cm 封顶 -0.04. Needs whole-body CoM via simulator.get_body_masses().
        "support_xcom_polygon_margin": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:SupportXcomPolygonMarginPenalty",
            params={
                "threshold": 1.0,
                "single_support_safety_margin": 0.02,
                "double_support_safety_margin": 0.03,
                "gravity": 9.81,
                "com_height_floor": 0.25,
                "max_penalty": 0.04,
                "penalty_power": 1.0,  # 线性 hinge(原平方→1):米级 margin 下线性才有可观梯度
            },
            weight=-50.0,  # 回退 0705 原值(重跑 0705 配置,2026-07-15)
        ),
        # Balance: penalize small Time-To-Boundary of the xCoM (time to cross the support polygon).
        "xcom_ttb": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:XcomTtbPenalty",
            params={
                "threshold": 1.0,
                "single_support_ttb_threshold": 0.30,  # 退回 072007 原值(fine-tune 只让 DR 变)
                "double_support_ttb_threshold": 0.20,
                "v_min": 0.01,
                "gravity": 9.81,
                "com_height_floor": 0.25,
                "max_penalty": 0.09,
            },
            weight=-15.0,  # 回退 0705 原值(重跑 0705 配置,2026-07-15)
        ),
        # Anti-slip: during single-leg support, penalize the support foot's horizontal sliding.
        "single_support_foot_slip_penalty": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:SingleSupportFootSlipPenalty",
            params={"force_threshold": 1.0},
            weight=-1.0,
        ),
        # Stance-foot ankle stability: during single-leg support, penalize ankle (pitch+roll)
        # action-rate of the stance foot (gated by ACTUAL single-support contact, like WBT).
        "stance_ankle_action_rate": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:StanceAnkleActionRatePenalty",
            params={
                "left_joint_names": ["left_ankle_pitch_joint", "left_ankle_roll_joint"],
                "right_joint_names": ["right_ankle_pitch_joint", "right_ankle_roll_joint"],
                "threshold": 1.0,
                "joint_weights": [1.0, 1.0],
            },
            weight=-0.3,  # 回退 0705 原值(重跑 0705 配置,2026-07-15)
        ),
    }
)

g1_29dof_wbt_fast_sac_reward = RewardManagerCfg(
    terms={
        **g1_29dof_wbt_reward.terms,
        "action_rate_l2": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:penalty_action_rate",
            weight=-1.0,  # proven from-scratch value (072007); anti-flail is achieved via convergence/stability, not a heavier action-rate
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
        # Motion tracking rewards - relative body frame
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

g1_29dof_wbt_reward_w_object = RewardManagerCfg(
    terms={
        **g1_29dof_wbt_reward.terms,
        # Motion tracking rewards - global reference frame
        "object_global_ref_position_error_exp": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:object_global_ref_position_error_exp",
            params={"sigma": 0.3},
            weight=1.0,
        ),
        "object_global_ref_orientation_error_exp": RewardTermCfg(
            func="holosoma.managers.reward.terms.wbt:object_global_ref_orientation_error_exp",
            params={"sigma": 0.4},
            weight=1.0,
        ),
    }
)

__all__ = ["g1_29dof_wbt_fast_sac_reward", "g1_29dof_wbt_reward", "g1_29dof_wbt_reward_w_object"]
