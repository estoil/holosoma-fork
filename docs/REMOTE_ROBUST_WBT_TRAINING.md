# 在另一台机器复现 G1 太极 Robust WBT 训练

## 1. 拉取代码与动作文件

```bash
git clone git@github.com:estoil/holosoma-fork.git
cd holosoma-fork
git checkout main
git pull --ff-only origin main

sha256sum motions_from_web/taichi_g1_danjiao_4_4_holosoma.npz
```

动作文件的预期 SHA-256：

```text
bc3a34be172fce3902d28ec1ba752f0d3c16e32454a37e8c7d8c4ada95bed39d
```

如果仓库已经存在，在执行 `git pull --ff-only` 前先用 `git status` 确认没有未提交修改。

## 2. 安装 Isaac Sim 训练环境

推荐 Ubuntu 22.04、NVIDIA GPU 和足够的磁盘空间。首次安装执行：

```bash
cd /path/to/holosoma-fork
OMNI_KIT_ACCEPT_EULA=1 bash scripts/setup_isaacsim.sh
source scripts/source_isaacsim_setup.sh
```

验证：

```bash
python -c "import torch; print(torch.__version__); print(torch.cuda.get_device_name(0))"
```

## 3. 先运行10次迭代冒烟训练

```bash
cd /path/to/holosoma-fork
source scripts/source_isaacsim_setup.sh

python src/holosoma/holosoma/train_agent.py \
  exp:g1-29dof-wbt-fast-sac-robust \
  --training.seed 42 \
  --algo.config.num-learning-iterations 10 \
  algo:fast-sac \
  simulator:isaacsim \
  logger:wandb \
  --logger.video.enabled False
```

冒烟训练应能加载：

```text
motions_from_web/taichi_g1_danjiao_4_4_holosoma.npz
```

并生成类似以下目录：

```text
logs/WholeBodyTracking/<timestamp>-g1_29dof_wbt_fast_sac_robust_manager-locomotion/
```

## 4. 启动完整训练

```bash
cd /path/to/holosoma-fork
source scripts/source_isaacsim_setup.sh

python src/holosoma/holosoma/train_agent.py \
  exp:g1-29dof-wbt-fast-sac-robust \
  --training.seed 42 \
  algo:fast-sac \
  simulator:isaacsim \
  logger:wandb \
  --logger.video.enabled False
```

默认配置使用4096个环境和384步 replay buffer，面向约24 GB显存。训练前运行 `nvidia-smi`，确保没有其他进程大量占用显存。

若显存不足，可先降为2048个环境：

```bash
python src/holosoma/holosoma/train_agent.py \
  exp:g1-29dof-wbt-fast-sac-robust \
  --training.seed 42 \
  --training.num-envs 2048 \
  algo:fast-sac \
  simulator:isaacsim \
  logger:wandb \
  --logger.video.enabled False
```

## 5. 常见问题

- `FileNotFoundError ...taichi_g1_danjiao_4_4_holosoma.npz`：确认动作文件存在并且 SHA-256 一致，同时必须从仓库根目录启动命令。
- `CUDA out of memory`：结束其他 GPU 进程，或将 `--training.num-envs` 降为2048/1024；不要首先增大 replay buffer。
- `--logger.video.no-enabled` 无法识别：正确写法是 `--logger.video.enabled False`。
- W&B 尚未登录：先运行 `wandb login`，或设置 `WANDB_MODE=offline` 后再启动。
- 训练日志与 checkpoint 位于 `logs/WholeBodyTracking/`；该目录默认不提交到 Git。
