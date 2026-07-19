"""动作缓存初始化回归测试。"""

from types import SimpleNamespace

import torch

from holosoma.managers.action.manager import ActionManager
from holosoma.managers.action.terms.joint_control import JointPositionActionTerm


class _FakeActionTerm:
    """记录动作管理器分发结果的轻量动作项。"""

    action_dim = 2

    def initialize_actions(self, env_ids: torch.Tensor, actions: torch.Tensor) -> None:
        self.env_ids = env_ids.clone()
        self.actions = actions.clone()


def test_action_manager_initializes_current_and_previous_actions() -> None:
    """重置动作必须同时写入当前动作、上一动作和动作项。"""
    term = _FakeActionTerm()
    manager = ActionManager.__new__(ActionManager)
    manager.device = "cpu"
    manager._total_action_dim = 2
    manager._action = torch.zeros(3, 2)
    manager._prev_action = torch.zeros(3, 2)
    manager._term_names = ["joint_pos"]
    manager._term_instances = {"joint_pos": term}

    env_ids = torch.tensor([0, 2])
    reset_actions = torch.tensor([[1.0, 2.0], [3.0, 4.0]])
    manager.initialize_actions(env_ids, reset_actions)

    torch.testing.assert_close(manager.action[env_ids], reset_actions)
    torch.testing.assert_close(manager.prev_action[env_ids], reset_actions)
    torch.testing.assert_close(term.actions, reset_actions)


def test_joint_position_initialization_fills_delay_queue() -> None:
    """控制延迟队列的所有槽位都应保持重置姿态。"""
    term = JointPositionActionTerm.__new__(JointPositionActionTerm)
    term.env = SimpleNamespace(
        robot_config=SimpleNamespace(
            control=SimpleNamespace(clip_actions=True, action_clip_value=2.0),
        )
    )
    term._raw_actions = torch.zeros(3, 2)
    term._processed_actions = torch.zeros(3, 2)
    term._actions_after_delay = torch.zeros(3, 2)
    term.action_queue = torch.zeros(3, 4, 2)

    env_ids = torch.tensor([1])
    term.initialize_actions(env_ids, torch.tensor([[3.0, -1.0]]))

    expected = torch.tensor([[2.0, -1.0]])
    torch.testing.assert_close(term._raw_actions[env_ids], torch.tensor([[3.0, -1.0]]))
    torch.testing.assert_close(term._processed_actions[env_ids], expected)
    torch.testing.assert_close(term._actions_after_delay[env_ids], expected)
    torch.testing.assert_close(term.action_queue[env_ids], expected.unsqueeze(1).expand(-1, 4, -1))
