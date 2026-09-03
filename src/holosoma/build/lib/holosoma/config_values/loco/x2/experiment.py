from dataclasses import replace

from holosoma.config_types.experiment import ExperimentConfig, NightlyConfig, TrainingConfig
from holosoma.config_values import (
    action,
    algo,
    command,
    curriculum,
    observation,
    randomization,
    reward,
    robot,
    simulator,
    termination,
    terrain,
)

x2_31dof = ExperimentConfig(
    env_class="holosoma.envs.locomotion.locomotion_manager.LeggedRobotLocomotionManager",
    training=TrainingConfig(project="hv-x2-manager", name="x2_31dof_manager"),
    algo=replace(algo.ppo, config=replace(algo.ppo.config, num_learning_iterations=25000, use_symmetry=True)),
    simulator=simulator.isaacgym,
    robot=robot.x2_31dof,
    terrain=terrain.terrain_locomotion_mix,#地形
    observation=observation.x2_31dof_loco_single_wolinvel,
    action=action.x2_31dof_joint_pos,
    termination=termination.x2_31dof_termination,
    randomization=randomization.x2_31dof_randomization,
    command=command.x2_31dof_command,
    curriculum=curriculum.x2_31dof_curriculum,
    reward=reward.x2_31dof_loco,
    nightly=NightlyConfig(
        iterations=5000,
        metrics={"Episode/rew_tracking_ang_vel": [0.7, "inf"], "Episode/rew_tracking_lin_vel": [0.55, "inf"]},
    ),
)

x2_31dof_fast_sac = ExperimentConfig(
    env_class="holosoma.envs.locomotion.locomotion_manager.LeggedRobotLocomotionManager",
    training=TrainingConfig(project="hv-x2-manager", name="x2_31dof_fast_sac_manager"),
    algo=replace(algo.fast_sac, config=replace(algo.fast_sac.config, num_learning_iterations=50000, use_symmetry=True)),
    simulator=simulator.isaacgym,
    robot=robot.x2_31dof,
    terrain=terrain.terrain_locomotion_mix,
    observation=observation.x2_31dof_loco_single_wolinvel,
    action=action.x2_31dof_joint_pos,
    termination=termination.x2_31dof_termination,
    randomization=randomization.x2_31dof_randomization,
    command=command.x2_31dof_command,
    curriculum=curriculum.x2_31dof_curriculum_fast_sac,
    reward=reward.x2_31dof_loco_fast_sac,
    nightly=NightlyConfig(
        iterations=50000,
        metrics={"Episode/rew_tracking_ang_vel": [0.8, "inf"], "Episode/rew_tracking_lin_vel": [0.95, "inf"]},
    ),
)

__all__ = ["x2_31dof", "x2_31dof_fast_sac"]
