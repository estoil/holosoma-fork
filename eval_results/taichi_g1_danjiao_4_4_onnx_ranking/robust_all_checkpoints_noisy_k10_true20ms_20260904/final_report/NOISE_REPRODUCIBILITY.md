# MuJoCo noisy 条件复现报告（true 20 ms）

## 结论摘要

本报告对应修正后的正式 noisy 条件。126 个 checkpoint 均以固定种子 0–9 运行 10 次，共 1260 次 noisy rollout；clean 数据另有 1260 次。修正后，126 个模型在 noisy 条件下均为 0% 成功率、100% 摔倒率。这说明当前 policy 对一帧关节速度延迟极其敏感，不能把旧的 0.5 ms 延迟排名用于真机决策。

消融实验表明，主要问题是 **20 ms 延迟**，不是 ±0.20 rad/s 白噪声：

| checkpoint | 条件 | 成功率 | 摔倒率 | hop 均值 | 平均摔倒时间 |
|---:|---|---:|---:|---:|---:|
| 196000 | clean | 100% | 0% | 0.00 | 29.84 s |
| 196000 | 仅 ±0.20 噪声 | 70% | 0% | 0.00 | 29.84 s |
| 196000 | 仅 20 ms 延迟 | 0% | 100% | 8.00 | 5.42 s |
| 196000 | 噪声 + 20 ms 延迟 | 0% | 100% | 1.80 | 5.85 s |
| 268000 | clean | 100% | 0% | 0.00 | 29.84 s |
| 268000 | 仅 ±0.20 噪声 | 80% | 0% | 0.00 | 29.84 s |
| 268000 | 仅 20 ms 延迟 | 0% | 100% | 9.00 | 8.94 s |
| 268000 | 噪声 + 20 ms 延迟 | 0% | 100% | 9.50 | 8.90 s |

## noisy 的精确定义

控制频率为 50 Hz，控制周期 `Δt = 0.02 s`。MuJoCo 物理步长为 `0.0005 s`，每个控制周期执行 40 个物理子步。

对第 `t` 个控制帧、第 `j` 个关节：

```text
u[t,j] ~ Uniform(0, 1)
epsilon[t,j] = 0.20 * (2*u[t,j] - 1) rad/s

t = 0:  dof_vel_obs[t,j] = dof_vel[t,j]   + epsilon[t,j]
t >= 1: dof_vel_obs[t,j] = dof_vel[t-1,j] + epsilon[t,j]
```

具体语义：

- 仅污染 actor observation 中的 29 维 `dof_vel`。
- 每个关节、每个控制帧独立采样均匀噪声 `[-0.20,+0.20] rad/s`。
- 延迟固定为上一控制帧，即严格 20 ms；首帧没有历史，因此使用当前速度。
- 随机数生成器为 NumPy `RandomState(seed)`（MT19937）。每次 rollout 重新初始化。
- 全量排名固定使用 seeds `[0,1,2,3,4,5,6,7,8,9]`。
- 不对关节位置、IMU 角速度、重力方向、动作历史、参考动作或 CoM 观测额外加噪声。
- 不施加外力，不随机化初始姿态、质量、摩擦或电机参数。
- 完整 actor observation 在推理前裁剪到 `[-100,100]`；action 同样裁剪到 `[-100,100]`。
- 腰部姿态估计使用 EMA，`alpha=0.5`。

clean 条件为：`dof_vel_noise=0.0`、`dof_vel_delay=0`、`push=None`，因此 `dof_vel_obs[t]=dof_vel[t]`。

## 动作与成功判定

- 动作总长 1492 帧，即 29.84 s。
- 时序为：2 s 初始站立、2 s 进入动作、19.84 s 原动作、2 s 返回站姿、4 s 结束站立。
- 摔倒判定覆盖完整 29.84 s：基座高度低于初始高度的 50%，或倾角大于 1 rad。
- 支撑脚接触阈值为机器人重量的 5%。连续至少 3 个控制帧失去支撑接触记为 hop。
- 单次成功要求：全程不摔倒，所有参考单脚段无 hop，摆动脚不提前触地。
- MuJoCo 地面摩擦参数为 `0.7 0.005 0.001`；录像所加棋盘材质和灯光只影响渲染，不改变物理参数。

## 与 robust 训练噪声的区别

训练时的关节速度噪声也是均匀 `±0.20 rad/s`，但一帧延迟按 episode 以 50% 概率启用；本评测对 noisy 的每次试验都固定启用一帧延迟，因此属于更严格的压力测试。

robust 训练的 actor 每个控制帧还会独立叠加下列均匀白噪声：

| actor 观测项 | 均匀噪声半宽 |
|---|---:|
| `motion_ref_ori_b` | 0.05 |
| `base_ang_vel` | 0.20 rad/s |
| `dof_pos` | 0.01 rad |
| `dof_vel` | 0.20 rad/s |
| `projected_gravity` | 0.03 |
| `whole_body_com_rel_support_center` | 0.015 |

其中 `base_ang_vel` 与 `projected_gravity` 还共享同一个三维、时间相关的 IMU 姿态误差：`e[t] = 0.9*e[t-1] + 0.012*N(0,1)`，其稳态标准差约为 0.0275 rad。训练同时启用摩擦、基座 CoM、连杆质量、编码器偏置、PD 增益和外推速度扰动等物理域随机化；这些均不属于本报告的 MuJoCo `noisy` 条件。本 noisy 基准刻意只改变关节速度观测，以便隔离失效原因。

## 完整复现命令

```bash
cd /home/wxy/taichi_deploy/Evaluate/evaluation

PY=/home/wxy/.holosoma_deps/miniconda3/envs/hsmujoco/bin/python
RUN=/home/wxy/taichi_deploy/holosoma/logs/WholeBodyTracking/20260903_100921-g1_29dof_wbt_fast_sac_robust_manager-locomotion
OUT=/tmp/holosoma_true20ms_reproduction

export WBT_EVAL_ROBOT_XML=/home/wxy/taichi_deploy/holosoma/src/holosoma/holosoma/data/robots/g1/g1_29dof.xml
export WBT_EVAL_MOTION_DIR=/home/wxy/taichi_deploy/holosoma/eval_results/taichi_g1_danjiao_4_4_onnx_ranking/robust_all_checkpoints_clean_noisy_k10_20260904/_motions
export WBT_EVAL_MOTION_GLOB=taichi_g1_danjiao_4_4_robust_augmented_mj.npz
export WBT_ORT_THREADS=1

export WBT_EVAL_SWEEP_OUT="$OUT/clean"
$PY sweep_checkpoints.py "$RUN" 150000 400000 10 clean

export WBT_EVAL_SWEEP_OUT="$OUT/noisy"
$PY sweep_checkpoints.py "$RUN" 150000 400000 10 noisy

$PY combine_clean_noisy_sweeps.py \
  "$OUT/clean/sweep_results.json" \
  "$OUT/final_report" \
  "$OUT/noisy/sweep_results.json"
```

复现两个 checkpoint 的消融实验：

```bash
$PY ablate_noise_delay.py \
  "$RUN/model_0196000.onnx" \
  taichi_g1_danjiao_4_4_robust_augmented --k 10

$PY ablate_noise_delay.py \
  "$RUN/model_0268000.onnx" \
  taichi_g1_danjiao_4_4_robust_augmented --k 10
```

## 软件版本

| 软件 | 版本 |
|---|---|
| Python | 3.10.20 |
| NumPy | 1.26.4 |
| MuJoCo | 3.9.0 |
| ONNX | 1.21.0 |
| ONNX Runtime | 1.23.2 |

## 审计哈希（SHA-256）

```text
25b96571e2dd4207c6ee0504939b38b04d3305543808c8e068d743f4178926a1  wbt_rollout.py
ec8556d6a82274f5e0d7135f3e5e3a73025f189034d50145188fc9b234a3750a  evaluate.py
9e966c8c832ff3663c7474a2fda4c2af46da03b0d567dac37d502d946e762601  metrics.py
29985b09f31b55016da2e79c3567fabd5e7058914e93d9414b858179a09d2f1e  sweep_checkpoints.py
79b3b6d24b2bf0c71b31e7556697a9d738a0d801f32d7593dad22b6018b598c9  rank_stability_trials.py
eff1f6582c3b7b7372ead013f69ef2760cec0bfa1876ae9682bd924405d05835  combine_clean_noisy_sweeps.py
35f5fd6c83474ed8bd4c0cde1badb235ca399b162cc4904821e017f74a07c35a  ablate_noise_delay.py
732beb417f5b3a288aaa6dbad4ce73d3157b1c53dc6ed63e2d424a973fee9d09  taichi_g1_danjiao_4_4_robust_augmented_mj.npz
8a23e1bdf85ac488d5dbd4912b476370d6fca57a3169812b8883fd496183af7c  g1_29dof.xml
c8baa7420923f09b205eceb5a92340e0cb0fc48d2c41c483c5c56b1f4852386d  sweep_results.json
```

## 历史结果更正

旧实现将 `dof_vel_delay=1` 索引到 MuJoCo 物理子步历史，因此实际延迟约为 0.5 ms，但旧报告和视频错误标注为 20 ms。旧目录保留用于审计，但不能与本报告的 true-20 ms 结果混用。正式结果以本目录中的 `STABILITY_REPORT.md`、`all_model_stability.csv` 和 `sweep_results.json` 为准。
