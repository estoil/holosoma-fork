from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from loguru import logger

from holosoma.config_types.algo import AlgoInitConfig
from holosoma.envs.base_task.base_task import BaseTask
from holosoma.utils.safe_torch_import import torch

if TYPE_CHECKING:
    from holosoma.config_types.experiment import ExperimentConfig


class BaseAlgo:
    def __init__(self, env: BaseTask, config: AlgoInitConfig, device, multi_gpu_cfg=None):
        self.env = env
        self.config = config
        self.device = device

        self.is_multi_gpu = multi_gpu_cfg is not None
        if multi_gpu_cfg is not None:
            self.gpu_global_rank = multi_gpu_cfg["global_rank"]
            self.gpu_local_rank = multi_gpu_cfg["local_rank"]
            self.gpu_world_size = multi_gpu_cfg["world_size"]
        else:
            self.gpu_global_rank = 0
            self.gpu_local_rank = 0
            self.gpu_world_size = 1
        self.is_main_process = self.gpu_global_rank == 0
        self._experiment_config: ExperimentConfig | None = None
        self._wandb_run_path: str | None = None

    def setup(self):
        return NotImplementedError

    def learn(self):
        return NotImplementedError

    def load(self, path):
        return NotImplementedError

    @property
    def inference_model(self):
        return NotImplementedError

    @property
    def actor_onnx_wrapper(self):
        return NotImplementedError

    def env_step(self, actions, extra_info=None):
        obs_dict, rewards, dones, extras = self.env.step(actions, extra_info)
        return obs_dict, rewards, dones, extras

    def attach_checkpoint_metadata(
        self,
        experiment_config: ExperimentConfig,
        wandb_run_path: str | None = None,
    ) -> None:
        """Attach metadata that should be saved with checkpoints."""

        self._experiment_config = experiment_config
        self._wandb_run_path = wandb_run_path

    def _checkpoint_metadata(self, iteration: int | None = None) -> dict[str, Any]:
        if self._experiment_config is None:
            raise RuntimeError("Experiment config metadata missing. Call attach_checkpoint_metadata() before saving.")

        metadata: dict[str, Any] = {"experiment_config": self._experiment_config.to_serializable_dict()}
        if self._wandb_run_path:
            metadata["wandb_run_path"] = self._wandb_run_path
        if iteration is not None:
            metadata["iteration"] = int(iteration)
        return metadata

    def has_curricula_enabled(self) -> bool:
        """Check if any curricula are enabled in the environment.

        This helper method checks for the presence of various curriculum flags
        to determine if any curriculum learning is active. This is commonly used
        for multi-GPU synchronization and logging purposes.

        Returns
        -------
        bool
            True if any curriculum is enabled, False otherwise.
        """
        return getattr(self.env, "use_reward_penalty_curriculum", False) or getattr(
            self.env, "use_domain_rand_scale_curriculum", False
        )

    def _synchronize_curriculum_metrics(self):
        """Synchronize curriculum-related metrics across all GPUs."""
        # Check if any curricula are enabled before synchronizing
        if not self.has_curricula_enabled():
            return

        env = self._unwrap_env()
        env.synchronize_curriculum_state(device=self.device, world_size=self.gpu_world_size)

    def get_inference_policy(self, device: str | None = None) -> Callable[[dict[str, torch.Tensor]], torch.Tensor]:
        """Get a callable policy function for inference.

        This method returns a function that takes observations as input and returns
        actions. The policy function is configured to run on the specified device.

        Parameters
        ----------
        device : str | None, optional
            The device to run the policy on (e.g., 'cuda', 'cpu').
            If None, uses the default device.

        Returns
        -------
        Callable[[torch.Tensor], torch.Tensor]
            A function that takes observations as input and returns actions.
            The function expects input observations as a torch.Tensor and
            returns actions as a torch.Tensor. Both input and output tensors
            should be on the specified device.

        Notes
        -----
        This is an abstract method that should be implemented by subclasses.
        The returned policy function should:
        - Run the policy network on the specified device
        - Return actions in the expected format
        """
        raise NotImplementedError

    @torch.no_grad()
    def evaluate_policy(self, max_eval_steps: int | None = None):
        raise NotImplementedError

    def _get_eval_motion_status(self, env_id: int = 0) -> dict[str, Any] | None:
        """读取当前 play/eval 中的 motion 文件、motion id 和时间步。"""
        env = self._unwrap_env()
        command_manager = getattr(env, "command_manager", None)
        if command_manager is None:
            return None

        motion_command = command_manager.get_state("motion_command")
        if motion_command is None or not hasattr(motion_command, "motion_ids"):
            return None

        motion_id = int(motion_command.motion_ids[env_id].detach().cpu().item())
        global_timestep = int(motion_command.time_steps[env_id].detach().cpu().item())
        motion_start = int(motion_command.motion.motion_start_idx[motion_id].detach().cpu().item())
        motion_end = int(motion_command.motion.motion_end_idx[motion_id].detach().cpu().item())
        local_timestep = max(0, global_timestep - motion_start)
        motion_length = max(1, motion_end - motion_start)

        motion_files = getattr(motion_command.motion, "loaded_motion_files", [])
        motion_file = motion_files[motion_id] if motion_id < len(motion_files) else "<generated_or_unknown_motion>"

        return {
            "motion_id": motion_id,
            "motion_file": motion_file,
            "motion_name": Path(motion_file).name,
            "global_timestep": global_timestep,
            "local_timestep": local_timestep,
            "motion_length": motion_length,
        }

    def _log_eval_motion_status_if_changed(
        self, status: dict[str, Any] | None, step: int, last_motion_key: tuple[int, str] | None
    ) -> tuple[int, str] | None:
        """motion 切换时写日志，避免每个 step 都刷屏。"""
        if status is None:
            return last_motion_key

        motion_key = (status["motion_id"], status["motion_file"])
        if motion_key != last_motion_key:
            logger.info(
                "Play step {}: running motion_id={} motion_file={} timestep={}/{} (global_timestep={})",
                step,
                status["motion_id"],
                status["motion_file"],
                status["local_timestep"],
                status["motion_length"],
                status["global_timestep"],
            )
        return motion_key

    def _start_eval_video_recording(self) -> bool:
        """在 policy 真正开始 rollout 前开启连续录像，并丢弃 reset 阶段的短片缓冲。"""
        env = self._unwrap_env()
        simulator = getattr(env, "simulator", None)
        video_recorder = getattr(simulator, "video_recorder", None)
        if video_recorder is None or not video_recorder.enabled:
            return False

        video_recorder.start_manual_recording(episode_id=0)
        logger.info("Started continuous eval video recording")
        return True

    def _stop_eval_video_recording(self, enabled: bool) -> None:
        """在 eval 结束或异常退出时强制写出连续录像。"""
        if not enabled:
            return

        env = self._unwrap_env()
        simulator = getattr(env, "simulator", None)
        video_recorder = getattr(simulator, "video_recorder", None)
        if video_recorder is None:
            return

        video_recorder.stop_manual_recording()
        logger.info("Stopped continuous eval video recording")

    def save(self, path=None, name="last.ckpt"):
        raise NotImplementedError

    def _unwrap_env(self) -> BaseTask | Any:
        """Return the underlying environment.

        Algorithms that wrap the task (e.g. ``FastSACEnv``) keep a reference to the
        original environment as ``unwrapped_env`` during construction, so we simply
        return that when it is present.
        """
        return getattr(self, "unwrapped_env", self.env)

    def _collect_env_state(self) -> dict[str, torch.Tensor | float]:
        """Collect environment state for checkpointing via the environment interface."""
        env = self._unwrap_env()
        state = env.get_checkpoint_state()
        return state or {}

    def _restore_env_state(self, env_state: dict[str, torch.Tensor | float] | None) -> None:
        """Restore environment state from checkpoint via the environment interface."""
        if not env_state:
            return
        env = self._unwrap_env()
        env.load_checkpoint_state(env_state)
