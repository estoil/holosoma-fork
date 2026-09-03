"""Shared simulation utilities for holosoma.

This module provides common functionality for setting up and running simulations,
shared between eval_agent.py and run_sim.py.
"""

from __future__ import annotations

import argparse
import os
import sys
import threading
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger
from typing_extensions import Self

from holosoma.config_types.env import get_tyro_env_config
from holosoma.config_types.experiment import ExperimentConfig
from holosoma.config_types.full_sim import FullSimConfig
from holosoma.config_types.run_sim import RunSimConfig
from holosoma.managers.terrain.manager import TerrainManager
from holosoma.utils.common import seeding
from holosoma.utils.helpers import get_class
from holosoma.utils.rate import RateLimiter
from holosoma.utils.safe_torch_import import torch
from holosoma.utils.simulator_config import SimulatorType, get_simulator_type, set_simulator_type
from holosoma.utils.torch_utils import to_torch

MOTION_STATE_HANDSHAKE_DQ = 12345.0


@dataclass(frozen=True)
class MotionInitialState:
    """Complete floating-base and joint state loaded from a Holosoma motion."""

    timestep: int
    fps: float
    root_state: np.ndarray
    dof_pos: np.ndarray
    dof_vel: np.ndarray


def world_to_body_vector_xyzw(vector_w: np.ndarray, quat_xyzw: np.ndarray) -> np.ndarray:
    """Rotate a world-frame vector into the body frame defined by ``quat_xyzw``."""
    vector = np.asarray(vector_w, dtype=np.float32)
    quat = np.asarray(quat_xyzw, dtype=np.float32)
    norm = float(np.linalg.norm(quat))
    if not np.isfinite(norm) or norm < 1e-6:
        raise ValueError(f"Invalid xyzw quaternion: {quat}")
    quat = quat / norm

    # Rotate with the conjugate quaternion because q maps body vectors to world.
    u = -quat[:3]
    scalar = quat[3]
    return (
        2.0 * np.dot(u, vector) * u
        + (scalar * scalar - np.dot(u, u)) * vector
        + 2.0 * scalar * np.cross(u, vector)
    ).astype(np.float32, copy=False)


def load_motion_initial_state(
    path: str | Path,
    timestep: int,
    expected_joint_names: list[str] | tuple[str, ...],
) -> MotionInitialState:
    """Load and validate a complete robot state from a Holosoma motion NPZ."""
    motion_path = Path(path).expanduser().resolve()
    if not motion_path.is_file():
        raise FileNotFoundError(f"Motion state file does not exist: {motion_path}")

    with np.load(motion_path, allow_pickle=False) as motion:
        required = {"fps", "joint_names", "joint_pos", "joint_vel"}
        missing = sorted(required.difference(motion.files))
        if missing:
            raise ValueError(f"Motion state file is missing required arrays: {missing}")

        joint_names = [str(name) for name in motion["joint_names"].tolist()]
        expected = list(expected_joint_names)
        if len(joint_names) != len(expected) or set(joint_names) != set(expected):
            missing_joints = sorted(set(expected).difference(joint_names))
            extra_joints = sorted(set(joint_names).difference(expected))
            raise ValueError(
                "Motion/simulator joint names do not match: "
                f"missing={missing_joints}, extra={extra_joints}"
            )

        joint_pos = np.asarray(motion["joint_pos"], dtype=np.float32)
        joint_vel = np.asarray(motion["joint_vel"], dtype=np.float32)
        if joint_pos.ndim != 2:
            raise ValueError(f"joint_pos must be 2D, got {joint_pos.shape}")
        num_frames = joint_pos.shape[0]
        if joint_pos.shape[1] != len(joint_names) + 7:
            raise ValueError(
                f"joint_pos must have shape [T, 7 + {len(joint_names)}], got {joint_pos.shape}"
            )
        if joint_vel.ndim != 2 or joint_vel.shape != (num_frames, len(joint_names) + 6):
            raise ValueError(
                f"joint_vel must have shape [{num_frames}, 6 + {len(joint_names)}], got {joint_vel.shape}"
            )
        if not 0 <= timestep < num_frames:
            raise ValueError(f"motion_state_timestep must be in [0, {num_frames - 1}], got {timestep}")

        pos_frame = joint_pos[timestep]
        vel_frame = joint_vel[timestep]
        # Holosoma motion NPZ stores the root quaternion as wxyz, while every
        # simulator-facing root-state tensor uses xyzw.
        root_quat_wxyz = pos_frame[3:7]
        quat_norm = float(np.linalg.norm(root_quat_wxyz))
        if not np.isfinite(quat_norm) or quat_norm < 1e-6:
            raise ValueError(f"Invalid root quaternion at timestep {timestep}: {root_quat_wxyz}")
        root_quat_wxyz = root_quat_wxyz / quat_norm
        root_quat_xyzw = root_quat_wxyz[[1, 2, 3, 0]]

        source_index = {name: index for index, name in enumerate(joint_names)}
        reorder = [source_index[name] for name in expected]
        root_state = np.concatenate(
            [pos_frame[:3], root_quat_xyzw, vel_frame[:6]]
        ).astype(np.float32)
        dof_pos = pos_frame[7:][reorder].astype(np.float32, copy=True)
        dof_vel = vel_frame[6:][reorder].astype(np.float32, copy=True)
        fps_values = np.asarray(motion["fps"]).reshape(-1)
        if fps_values.size != 1 or float(fps_values[0]) <= 0:
            raise ValueError(f"fps must contain one positive value, got {fps_values}")

    if not all(np.isfinite(value).all() for value in (root_state, dof_pos, dof_vel)):
        raise ValueError(f"Motion state at timestep {timestep} contains non-finite values")

    return MotionInitialState(
        timestep=timestep,
        fps=float(fps_values[0]),
        root_state=root_state,
        dof_pos=dof_pos,
        dof_vel=dof_vel,
    )


def setup_simulator_imports(config: ExperimentConfig | RunSimConfig) -> None:
    """Setup simulator-specific imports without side effects.

    Parameters
    ----------
    config : ExperimentConfig | RunSimConfig
        Configuration containing simulator settings.
    """
    set_simulator_type(config.simulator)
    simulator_type = get_simulator_type()

    if simulator_type == SimulatorType.MUJOCO:
        import mujoco

        assert mujoco is not None
    elif simulator_type == SimulatorType.ISAACGYM:
        import isaacgym

        assert isaacgym is not None

    # IsaacSim imports handled in setup_isaaclab_launcher


def setup_isaaclab_launcher(config: ExperimentConfig | RunSimConfig, device: str | None = None) -> Any | None:
    """Handle IsaacSim-specific launcher setup.

    Parameters
    ----------
    config : ExperimentConfig | RunSimConfig
        Configuration containing simulator and training settings.
    device : str
        Resolved device string (e.g., 'cuda:0', 'cpu').

    Returns
    -------
    Any | None
        IsaacSim simulation app instance, or None for other simulators.
    """
    from isaaclab.app import AppLauncher

    parser = argparse.ArgumentParser(description="Run simulation with IsaacSim.")
    parser.add_argument("--num_envs", type=int, default=1, help="Number of environments to simulate.")
    parser.add_argument("--seed", type=int, default=None, help="Seed used for the environment")
    parser.add_argument("--env_spacing", type=int, default=20, help="Distance between environments in simulator.")
    parser.add_argument("--output_dir", type=str, default="logs", help="Directory to store the output.")
    AppLauncher.add_app_launcher_args(parser)

    # Parse known arguments to get argparse params
    args_cli, unknown_args = parser.parse_known_args()

    # Set values from config — divide by world_size for multi-GPU so each rank's
    # AppLauncher only allocates resources for its share of environments.
    # (The full num_envs is divided again in train_agent.train(), but AppLauncher
    # needs the per-rank count at init time to avoid over-allocating GPU memory.)
    world_size = int(os.environ.get("WORLD_SIZE", "1"))
    args_cli.num_envs = config.training.num_envs // world_size if world_size > 1 else config.training.num_envs
    args_cli.seed = config.training.seed
    args_cli.env_spacing = config.simulator.config.scene.env_spacing
    args_cli.output_dir = config.logger.base_dir
    args_cli.headless = config.training.headless
    if int(os.environ.get("WORLD_SIZE", "1")) > 1:
        # Distribute simulator across GPUs when using multi-gpu training
        args_cli.device = f"cuda:{int(os.environ.get('LOCAL_RANK', '0'))}"
        args_cli.distributed = True
    elif device is not None:
        # Use the resolved device
        args_cli.device = device
    else:  # AppLauncher auto-detects
        pass

    # Check if video recording is enabled and add --enable_cameras flag
    video_enabled = config.logger.video.enabled or config.logger.headless_recording
    if video_enabled:
        args_cli.enable_cameras = True

    app_launcher = AppLauncher(args_cli)
    simulation_app = app_launcher.app

    logger.info(f"IsaacSim args_cli: {args_cli}")
    logger.info(f"IsaacSim unknown_args: {unknown_args}")
    sys.argv = [sys.argv[0]] + unknown_args

    return simulation_app


def setup_keyboard_listener(env) -> threading.Thread:
    """Setup keyboard listener thread for simulation control.

    Parameters
    ----------
    env
        Environment instance to control.

    Returns
    -------
    threading.Thread
        Keyboard listener thread (already started).
    """

    def on_press(key, env):
        """Handle keyboard input for simulation control."""
        try:
            if hasattr(key, "char") and key.char:
                if key.char == "n":
                    if hasattr(env, "next_task"):
                        env.next_task()
                        logger.info("Moved to the next task.")
                # Force Control
                elif key.char == "1":
                    if hasattr(env, "apply_force_scale"):
                        env.apply_force_scale /= 2.0
                        logger.info(f"apply_force_scale: {env.apply_force_scale}")
                elif key.char == "2":
                    if hasattr(env, "apply_force_scale"):
                        env.apply_force_scale *= 2.0
                        logger.info(f"apply_force_scale: {env.apply_force_scale}")
        except AttributeError:
            pass

    def listen_for_keypress(env):
        """Listen for keyboard input in a separate thread."""
        try:
            # Delay import so that one can run the rest of this script in headless mode.
            # Trying to import pynput in headless mode gives the following error:
            # ImportError: this platform is not supported:
            # ('failed to acquire X connection: Bad display name ""', DisplayNameError(''))
            from pynput import keyboard as pynput_keyboard

            logger.info("Keyboard controls:")
            logger.info("  n - Next task (if supported)")
            logger.info("  1/2 - Decrease/Increase force scale (if supported)")

            with pynput_keyboard.Listener(on_press=lambda key: on_press(key, env)) as listener:
                listener.join()
        except ImportError:
            logger.warning("pynput not available - keyboard controls disabled")
        except Exception as e:
            logger.warning(f"Keyboard listener failed: {e}")

    key_listener_thread = threading.Thread(target=listen_for_keypress, args=(env,))
    key_listener_thread.daemon = True
    key_listener_thread.start()
    return key_listener_thread


def setup_simulation_environment(
    config: ExperimentConfig | RunSimConfig, device: str | None = None
) -> tuple[Any, str, Any]:
    """Setup simulation environment with shared infrastructure.

    This function handles common setup for training, evaluation and direct simulation:
    - Simulator imports and initialization
    - Device selection and seeding
    - Environment creation
    - Keyboard listener setup (if not headless)

    Parameters
    ----------
    config : ExperimentConfig | RunSimConfig
        Configuration containing all simulation settings.
    device : str | None, optional
        Device to use for simulation. If None, auto-detects CUDA availability.

    Returns
    -------
    tuple[Any, str, Any]
        Tuple of (environment, device_string, simulation_app).
        simulation_app is None for simulators that don't need it (MuJoCo, IsaacGym).
    """
    logger.info("🚀 Setting up simulation environment...")

    # Setup simulator imports
    setup_simulator_imports(config)

    # Device selection - must happen before IsaacSim launcher setup
    if device is None:
        device = "cuda:0" if torch.cuda.is_available() else "cpu"
    logger.info(f"Device: {device}")

    # Handle IsaacSim launcher if needed (for both ExperimentConfig and RunSimConfig)
    simulation_app = None
    if get_simulator_type() == SimulatorType.ISAACSIM:
        simulation_app = setup_isaaclab_launcher(config, device)

    # Set random seed if specified (only for ExperimentConfig)
    if isinstance(config, ExperimentConfig) and config.training.seed is not None:
        seeding(config.training.seed, torch_deterministic=config.training.torch_deterministic)
        logger.info(f"Seed: {config.training.seed}")

    # For RunSimConfig, we need a different approach since it doesn't have env_class or training configs
    if isinstance(config, RunSimConfig):
        # For run_sim.py, we'll create the simulator directly instead of using environment wrapper
        logger.info("Direct simulation mode - creating simulator directly, without experiment config")

        # Create FullSimConfig from RunSimConfig
        # Extract SimulatorInitConfig from SimulatorConfig
        full_config = FullSimConfig(
            simulator=config.simulator.config,  # Extract .config from SimulatorConfig
            robot=config.robot,
            training=config.training,
            logger=config.logger,
            experiment_dir=None,
        )

        # For compatibility, minimal proxy for TerrainManager since it depends on env
        class EnvProxy:
            def __init__(self, device):
                self.num_envs = 1
                self.device = device

        # For compatibility, wrap in a minimal object that has .sim attribute
        class DirectSimWrapper:
            def __init__(self, simulator):
                self.sim = simulator

            def reset(self):
                # Basic reset - just initialize the simulator if needed
                if hasattr(self.sim, "reset"):
                    self.sim.reset()

            def close(self):
                if hasattr(self.sim, "close"):
                    self.sim.close()

        # Use terrain configuration from RunSimConfig
        terrain_manager = TerrainManager(config.terrain, env=EnvProxy(device), device=device)

        # Create simulator using get_class() to avoid circular imports
        simulator_class = get_class(config.simulator._target_)
        simulator = simulator_class(full_config, terrain_manager, device)

        # Now we have an "env" to return which is actually the direct simulator
        env = DirectSimWrapper(simulator)
        logger.debug("Direct simulator created successfully!")

    else:
        # Original ExperimentConfig path
        env_target = config.env_class
        tyro_env_config = get_tyro_env_config(config)

        logger.info(f"Creating environment: {env_target}")
        env_class = get_class(env_target)
        env = env_class(tyro_env_config, device=device)

        logger.debug("Environment created successfully!")

        # Setup keyboard listener if not headless
        if not config.training.headless:
            setup_keyboard_listener(env)

    return env, device, simulation_app


def close_simulation_app(simulation_app):
    """Close simulation app with workarounds for known issues.

    Parameters
    ----------
    simulation_app : Any
        The simulation app instance returned by init_sim_imports().
        Can be None for simulators that don't have an app (e.g., IsaacGym).
    """
    if simulation_app is not None and get_simulator_type() == SimulatorType.ISAACSIM:
        logger.info("Shutting down simulation app...")
        try:
            # Work-around for IsaacLab hanging headless.
            # Patch the close_stage method to avoid hanging
            import omni.usd

            context = omni.usd.get_context()
            context_class = context.__class__

            # Replace with a no-op version
            def noop_close_stage(self, *args, **kwargs):
                logger.info("Skipping close_stage() to avoid hanging")
                return True

            # Apply the patch
            context_class.close_stage = noop_close_stage
            logger.info("Successfully patched close_stage method")
        except Exception as e:
            logger.warning(f"Could not patch close_stage method: {e}")

        try:
            # Work-around for IsaacLab SimulationContext._app_control_on_stop_handle_fn
            # hanging in an infinite render() loop on shutdown. When simulation_app.close()
            # triggers a timeline STOP event, the callback spins waiting for the timeline to
            # start playing again — which never happens. Disabling the callback prevents this.
            from isaaclab.sim import SimulationContext

            sim_context = SimulationContext.instance()
            if sim_context is not None:
                sim_context._disable_app_control_on_stop_handle = True
                logger.info("Disabled SimulationContext app_control_on_stop_handle to prevent shutdown hang")
        except Exception as e:
            logger.warning(f"Could not disable app_control_on_stop_handle: {e}")

        # Now close the app
        simulation_app.close(wait_for_replicator=False)
        logger.info("Simulation app closed.")
    else:
        logger.info("Simulation app closed.")


class DirectSimulation:
    """Encapsulates direct simulation logic for run_sim.py.

    This class provides a clean interface for running direct simulations without
    training or evaluation environments, handling all initialization,
    loop management, and cleanup logic.

    Can be used as a context manager for resource management.

    Examples
    --------
    >>> with DirectSimulation(config, env, device, simulation_app) as sim:
    ...     sim.run()
    """

    def __init__(self, config: RunSimConfig, env: Any, device: str, simulation_app: Any):
        """Initialize DirectSimulation instance.

        Parameters
        ----------
        config : RunSimConfig
            Configuration containing all simulation settings.
        env : Any
            Environment wrapper containing the simulator.
        device : str
            Device for tensor operations.
        simulation_app : Any
            Simulation app instance (if any).
        """
        self.config = config
        self.env = env
        self.device = device
        self.simulation_app = simulation_app
        self.simulator = env.sim
        self.motion_initial_state: MotionInitialState | None = None

    def __enter__(self) -> Self:
        """Context manager entry - initialize the simulation.

        Returns
        -------
        Self
            Self for use in the with statement.
        """
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - cleanup the simulation.

        Parameters
        ----------
        exc_type : type or None
            Exception type if an exception occurred.
        exc_val : Exception or None
            Exception instance if an exception occurred.
        exc_tb : traceback or None
            Traceback if an exception occurred.
        """
        self.cleanup()

    def initialize(self) -> None:
        """Handle the complete simulator initialization sequence.

        Performs the initialization process required for proper simulator
        lifecycle management. Ideally this is moved into the simulator interface and
        to simplify training, evaluation and direct usage.
        """
        logger.debug("Initializing simulator...")

        # Need to manually set headless since it's in training config currently
        self.simulator.set_headless(False)

        # Step 1: Basic setup
        self.simulator.setup()
        logger.debug("simulator.setup() completed")

        # Step 2: Setup terrain
        self.simulator.setup_terrain()
        logger.debug("simulator.setup_terrain() completed")

        # Step 3: Load assets (this initializes the bridge!)
        self.simulator.load_assets()
        logger.debug("simulator.load_assets() completed - bridge should now be initialized")

        # Step 4: Create environments (need to provide required parameters)
        # Create env_origins (single environment at origin)
        env_origins = torch.zeros(1, 3, device=self.device)

        # Create base_init_state from robot config
        base_init_state = self._create_base_init_state()

        self.simulator.create_envs(1, env_origins, base_init_state)
        logger.debug("simulator.create_envs() completed")

        # Step 5: Prepare simulation
        self.simulator.prepare_sim()
        logger.debug("simulator.prepare_sim() completed")

        if self.config.motion_state_file:
            self.motion_initial_state = load_motion_initial_state(
                self.config.motion_state_file,
                self.config.motion_state_timestep,
                self.simulator.dof_names,
            )
            self._apply_motion_initial_state()

        # Step 5.5: Initialize episode (positions virtual gantry, etc.)
        self.simulator.on_episode_start(env_id=0)
        logger.debug("simulator.on_episode_start() completed")

        # Step 6: Setup viewer if not headless
        if not self.config.training.headless:
            self.simulator.setup_viewer()
            logger.debug("simulator.setup_viewer() completed")

        logger.info("Simulator initialized")

        # Step 7: Toggle start recording if enabled
        if self.simulator.video_recorder and self.simulator.video_recorder.enabled:
            # arbitrary episode ID given this is sim2sim, we may want to
            # actually support toggling recording and with better filenames too
            self.simulator.video_recorder.start_recording(episode_id=0)

    def run(self) -> None:
        """Run the direct simulation loop with viewer sync and FPS logging.

        Manages the complete simulation loop including rate limiting,
        viewer synchronization, FPS logging, and error handling.
        """
        # Setup rate limiting
        sim_frequency = self.config.simulator.config.sim.fps
        rate_limiter = RateLimiter(sim_frequency)

        # Calculate viewer sync frequency
        viewer_steps = self._calculate_viewer_steps()

        logger.info(f"Simulation rate: {sim_frequency} Hz ({1.0 / sim_frequency * 1000:.2f} ms)")
        logger.info(f"Viewer rate: {1 / self.config.viewer_dt:.1f} Hz (sync every {viewer_steps} steps)")
        logger.info("Starting direct simulation loop...")
        logger.info("Press Ctrl+C to stop simulation")

        if self.motion_initial_state is not None and self.config.wait_for_policy_command:
            self._wait_for_policy_command()
            # Re-apply at the hand-off boundary so the first physics step starts
            # from exactly the same state that was published to the policy.
            self._apply_motion_initial_state()

        if (
            self.motion_initial_state is not None
            and self.config.disable_gantry_on_motion_start
            and self.simulator.virtual_gantry is not None
        ):
            self.simulator.virtual_gantry.set_enable(False)
            logger.info("Virtual gantry disabled for motion-state start")

        # Determine refresh strategy based on simulator type
        # IsaacGym/IsaacSim: need pre-step to refresh tensors to sync simulator state
        # MuJoCo: no pre-step refresh needed because we are NOT running an envs/tasks requiring
        #         those tensors e.g, _rigid_body_rot, _rigid_body_vel, etc.
        simulator_type = get_simulator_type()
        if simulator_type in [SimulatorType.ISAACGYM, SimulatorType.ISAACSIM]:
            pre_step_refresh = self.simulator.refresh_sim_tensors
        else:
            pre_step_refresh = lambda: None  # noqa: E731  (No-op for MuJoCo)

        # Direct simulation loop (like holosoma_inference's simulation_thread)
        step_count = 0
        start_time = time.time()
        fps_start_time = start_time

        while True:
            try:
                # Refresh tensors if needed (no-op for MuJoCo)
                pre_step_refresh()

                # Direct simulator step - this triggers bridge.step() inside simulate_at_each_physics_step()
                self.simulator.simulate_at_each_physics_step()

                # Update viewer at display rate
                if step_count % viewer_steps == 0:
                    self.simulator.render()

                # Periodic FPS logging (every 1000 steps)
                if step_count > 0 and step_count % 1000 == 0:
                    fps_start_time = self._log_fps(step_count, fps_start_time)

                step_count += 1
                rate_limiter.sleep()

            except KeyboardInterrupt:  # noqa: PERF203
                logger.info("Simulation interrupted by user (Ctrl+C)")
                break
            except Exception as e:
                logger.error(f"Error during simulation step {step_count}: {e}")
                traceback.print_exc()
                break

        # Final statistics
        total_elapsed = time.time() - start_time
        avg_fps = step_count / total_elapsed if total_elapsed > 0 else 0
        logger.info(f"Simulation completed after {step_count} steps")
        logger.info(f"Average FPS: {avg_fps:.1f} (target: {sim_frequency})")

    def _apply_motion_initial_state(self) -> None:
        """Write the loaded floating-base and joint state into the simulator."""
        state = self.motion_initial_state
        if state is None:
            return

        env_ids = torch.tensor([0], device=self.device, dtype=torch.long)
        root_state_np = state.root_state.copy()
        if get_simulator_type() == SimulatorType.MUJOCO:
            # Holosoma motion files store root angular velocity in world axes;
            # MuJoCo free-joint qvel stores it in the floating body's local axes.
            root_state_np[10:13] = world_to_body_vector_xyzw(root_state_np[10:13], root_state_np[3:7])
        root_state = torch.as_tensor(root_state_np, device=self.device, dtype=torch.float32).unsqueeze(0)
        dof_pos = torch.as_tensor(state.dof_pos, device=self.device, dtype=torch.float32)
        dof_vel = torch.as_tensor(state.dof_vel, device=self.device, dtype=torch.float32)
        dof_state = torch.stack((dof_pos, dof_vel), dim=-1)

        self.simulator.set_actor_root_state_tensor_robots(env_ids, root_state)
        self.simulator.set_dof_state_tensor_robots(env_ids, dof_state)
        logger.info(
            "Applied motion state: timestep={} fps={} root_pos={} max_abs_dof_vel={:.3f}",
            state.timestep,
            state.fps,
            np.round(state.root_state[:3], 4).tolist(),
            float(np.max(np.abs(state.dof_vel))),
        )

    def _wait_for_policy_command(self) -> None:
        """Publish a frozen state/clock until an active DDS policy command arrives."""
        bridge = self.simulator.bridge
        if bridge is None or bridge.robot_bridge is None:
            raise RuntimeError("motion-state arming requires an enabled robot bridge")

        logger.info("Motion-state simulation ARMED: physics is paused at t=0")
        logger.info(
            "Start inference with --task.motion-state-handshake "
            "--task.auto-start-policy --task.auto-start-motion-clip"
        )
        started_at = time.monotonic()
        last_status = started_at
        wait_rate = RateLimiter(200)
        handshake_seen = False

        while True:
            bridge.step()
            command = bridge.robot_bridge.low_cmd
            gains = np.asarray(getattr(command, "kp", []), dtype=np.float32)
            velocity_targets = np.asarray(getattr(command, "dq_target", []), dtype=np.float32)
            is_handshake = (
                velocity_targets.size == self.simulator.num_dof
                and np.isclose(velocity_targets[0], MOTION_STATE_HANDSHAKE_DQ, rtol=0.0, atol=0.1)
                and np.all(np.abs(gains) <= 1e-6)
            )
            if is_handshake and not handshake_seen:
                handshake_seen = True
                logger.info("Motion-state handshake received; waiting for the first active policy command")
            elif handshake_seen and gains.size == self.simulator.num_dof and np.any(np.abs(gains) > 1e-6):
                logger.info("Active policy command received; releasing synchronized physics start")
                return

            now = time.monotonic()
            timeout = self.config.policy_wait_timeout_s
            if timeout > 0 and now - started_at >= timeout:
                raise TimeoutError(f"No active policy command received within {timeout:.1f}s")
            if now - last_status >= 5.0:
                logger.info("Still armed; waiting for active policy command...")
                last_status = now
            wait_rate.sleep()

    def cleanup(self) -> None:
        """Handle simulation cleanup."""
        # Cleanup environment
        if hasattr(self.env, "close"):
            self.env.close()

        if self.simulator.video_recorder:
            self.simulator.video_recorder.cleanup()

        # Cleanup simulation app
        if self.simulation_app:
            close_simulation_app(self.simulation_app)

    def _create_base_init_state(self) -> torch.Tensor:
        """Create base initialization state tensor from robot configuration.

        Returns
        -------
        torch.Tensor
            Base initialization state tensor.
        """
        base_init_state_list = (
            self.config.robot.init_state.pos
            + self.config.robot.init_state.rot
            + self.config.robot.init_state.lin_vel
            + self.config.robot.init_state.ang_vel
        )
        return to_torch(base_init_state_list, device=self.device, requires_grad=False)

    def _calculate_viewer_steps(self) -> int:
        """Calculate viewer synchronization frequency.

        Returns
        -------
        int
            Number of simulation steps between viewer updates.
        """
        viewer_dt = self.config.viewer_dt
        sim_dt = 1.0 / self.config.simulator.config.sim.fps
        return max(1, int(viewer_dt / sim_dt))

    def _log_fps(self, step_count: int, fps_start_time: float) -> float:
        """Log FPS statistics for simulation performance monitoring.

        Parameters
        ----------
        step_count : int
            Current step count.
        fps_start_time : float
            Start time for FPS measurement.

        Returns
        -------
        float
            New start time for next FPS measurement.
        """
        elapsed = time.time() - fps_start_time
        fps = 1000 / elapsed
        root_state = self.simulator.robot_root_states[0]
        root_z = float(root_state[2].item())
        quat_xyzw = root_state[3:7].detach().cpu().numpy()
        body_up_dot_world_up = float(1.0 - 2.0 * (quat_xyzw[0] ** 2 + quat_xyzw[1] ** 2))
        tilt_deg = float(np.degrees(np.arccos(np.clip(body_up_dot_world_up, -1.0, 1.0))))
        logger.info("Simulation FPS: {:.1f} | root_z: {:.3f} m | base_tilt: {:.1f} deg", fps, root_z, tilt_deg)
        return time.time()
