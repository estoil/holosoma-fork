from types import SimpleNamespace

import torch

from holosoma.managers.observation.terms.wbt import _SharedRobustSensorState
from holosoma.config_values.wbt.g1.experiment import g1_29dof_wbt_fast_sac_robust


def _env(num_envs: int = 4096):
    return SimpleNamespace(
        num_envs=num_envs,
        device="cpu",
        dt=0.02,
        common_step_counter=0,
        is_evaluating=False,
    )


def test_robust_sensor_curriculum_stages_and_stress_tail():
    torch.manual_seed(7)
    env = _env()
    state = _SharedRobustSensorState(
        env,
        {
            "stage_steps": [0, 80_000, 200_000],
            "max_delay_ms": [2.0, 5.0, 8.0],
            "dof_vel_noise": [0.02, 0.05, 0.10],
            "stress_probability": 0.05,
            "stress_delay_ms": 15.0,
            "stress_dof_vel_noise": 0.20,
            "jitter_ms": 1.0,
        },
    )
    ids = torch.arange(env.num_envs)

    state.reset(ids)
    nominal = state.noise_scale == 0.02
    assert torch.all(state.delay_ms[nominal] <= 2.0)
    assert torch.all(state.delay_ms[~nominal] >= 2.0)
    assert torch.all(state.delay_ms <= 15.0)

    env.common_step_counter = 200_000
    state.reset(ids)
    nominal = state.noise_scale == 0.10
    assert torch.all(state.delay_ms[nominal] <= 8.0)
    assert torch.all(state.delay_ms[~nominal] >= 8.0)
    assert torch.all(state.delay_ms <= 15.0)


def test_delay_fraction_is_shared_within_step_and_disabled_for_eval():
    torch.manual_seed(3)
    env = _env(32)
    state = _SharedRobustSensorState(env, {"jitter_ms": 1.0})
    state.reset(torch.arange(env.num_envs))

    first = state.delay_fraction()
    second = state.delay_fraction()
    assert torch.equal(first, second)
    assert torch.all((first >= 0.0) & (first <= 1.0))

    env.is_evaluating = True
    assert torch.count_nonzero(state.delay_fraction()) == 0


def test_robust_actor_onnx_contract_is_unchanged():
    terms = g1_29dof_wbt_fast_sac_robust.observation.groups["actor_obs"].terms
    expected_dims = {
        "actions": 29,
        "base_ang_vel": 3,
        "dof_pos": 29,
        "dof_vel": 29,
        "future_cmd": 5 * 58,
        "future_support_phase": 5 * 2,
        "motion_command": 58,
        "motion_ref_ori_b": 6,
        "projected_gravity": 3,
        "reference_support_phase": 2,
        "whole_body_com_rel_support_center": 4,
    }
    assert set(terms) == set(expected_dims)
    assert sum(expected_dims.values()) == 463
