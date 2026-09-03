# Holosoma WBT 观测 / 奖励 / 终止项复现文档

本文档用于在**另一份干净 Holosoma 代码库**上，复现本仓库（`holosoma-cpuload-for-train`）针对 G1 29DoF Whole-Body Tracking（WBT）的**观测、奖励、终止**改动。

主实验：`exp:g1-29dof-wbt-fast-sac`  
环境类：`holosoma.envs.wbt.wbt_manager.WholeBodyTrackingManager`  
推荐基线配置：以 **20260705** 跑通且评测最优的配方为准（见 §7）。

---

## 0. 改动总览

相对上游 vanilla Holosoma WBT，本仓库在 obs / reward / termination 上的增量可分为三类：

| 类别 | 内容 | 是否必须 |
|------|------|----------|
| **A. 支撑相位前瞻** | Actor/Critic 增加 `reference_support_phase`、`future_support_phase(K=5)`、`future_cmd(K=5)` | 是（平衡/防跳依赖） |
| **B. 可部署平衡观测** | Actor：`whole_body_com_rel_support_center`（4 维）；Critic 特权：`whole_body_xcom_rel_support_center`（2 维） | 是（Actor 部署必对齐） |
| **C. 平衡/防跳奖励** | 5 个自定义惩罚项（接触失配、xCoM 多边形裕度、TTB、单脚滑移、支撑踝 action-rate） | 是 |
| **D. 终止** | `timeout` + `BadTrackingZOnly`（与 vanilla 基本一致，阈值如下） | 按表核对 |
| **E. 配套（非本文核心）** | motion npz 需含 `reference_support_phase/state`；推理侧 obs 顺序与维度对齐；可选 CPU motion 加载 | 见 §5、§6 |

**不在本文范围**：`motion_load_device=cpu`（Route A，只影响显存，不改变 obs/reward/term 语义）。详见 `ROUTE_A_CPU_LOADING.md`。

---

## 1. 需要同步的文件清单

在目标 Holosoma 上，按路径对照拷贝或合并（路径均相对 `src/holosoma/holosoma/`）：

### 1.1 配置（定义用哪些 term、权重、参数）

| 文件 | 作用 |
|------|------|
| `config_values/wbt/g1/observation.py` | Actor / Critic 观测组 |
| `config_values/wbt/g1/reward.py` | 奖励项与权重（含 FastSAC 变体） |
| `config_values/wbt/g1/termination.py` | 终止项与阈值 |
| `config_values/wbt/g1/experiment.py` | 实验组装：`observation` / `reward` / `termination` 挂到 `g1_29dof_wbt_fast_sac` |
| `config_values/wbt/g1/command.py` | 启动相位等（影响训练是否“被 RSI 救援”，间接影响平衡学习） |

并确认 re-export 已导出：

- `config_values/observation.py` → `g1_29dof_wbt_observation`
- `config_values/reward.py` → `g1_29dof_wbt_fast_sac_reward`
- `config_values/termination.py` → `g1_29dof_wbt_termination`

### 1.2 实现（真正计算）

| 文件 | 作用 |
|------|------|
| `managers/observation/terms/wbt.py` | 全部 obs term，含支撑相位、future_cmd、CoM/xCoM 相对支撑中心 |
| `managers/reward/terms/wbt.py` | 追踪奖励 + 5 个平衡类惩罚 + 辅助函数（全身 CoM、xCoM、支撑多边形） |
| `managers/termination/terms/wbt.py` | `BadTracking` / `BadTrackingZOnly` |
| `managers/termination/terms/common.py` | `timeout_exceeded`（通常已有） |
| `managers/command/terms/wbt.py` | 加载/暴露 `reference_support_phase`、`reference_support_state`、`future_*` |

### 1.3 部署对齐（若要导出 ONNX / 真机）

| 文件 | 作用 |
|------|------|
| `src/holosoma_inference/.../config/config_values/observation.py` | Actor obs 名、维度、scale |
| `src/holosoma_inference/.../policies/wbt.py` | 拼 obs 时计算 `whole_body_com_rel_support_center` |
| `src/holosoma_inference/.../policies/wbt_utils.py` | FK 重建 CoM-rel-support（与训练高度规则一致） |

---

## 2. 观测（Observation）

### 2.1 设计原则

1. **Actor 可部署**：只用编码器 + IMU（角速度 / 投影重力）能重建的量；**不要**把依赖世界系线速度的 xCoM 放进 Actor。
2. **Critic 可用特权**：`base_lin_vel`、全身 body pos/ori、`whole_body_xcom_rel_support_center` 仅训练用。
3. **拼接顺序**：ObservationManager 在 `concatenate=True` 时按 **term 名字母序** `sorted(keys)` 拼接。部署侧必须同一顺序。
4. **支撑脚选择规则必须 train=deploy**：Actor 的 CoM-rel 用**脚高度**判支撑（非接触力），避免仿真力与真机力差异造成 gap。

### 2.2 Actor 观测组（`actor_obs_shared`）

配置：`config_values/wbt/g1/observation.py`  
实现：`managers/observation/terms/wbt.py`

| Term 名 | 维度 | noise | noise | 含义 |
|---------|------|-------|-------|------|
| `actions` | 29 | 1.0 | 0.0 | 上一步动作 |
| `base_ang_vel` | 3 | 1.0 | 0.2 | 基座角速度（body） |
| `dof_pos` | 29 | 1.0 | 0.01 | 关节位置 |
| `dof_vel` | 29 | 1.0 | 0.5 | 关节速度 |
| `future_cmd` | 290 | 1.0 | 0.0 | 未来 K=5 帧参考 `[q, qd]`，每帧 58 维 |
| `future_support_phase` | 10 | 1.0 | 0.0 | 未来 K=5 帧支撑相位，每帧 2 维 |
| `motion_command` | 58 | 1.0 | 0.0 | 当前参考 `[joint_pos, joint_vel]` |
| `motion_ref_ori_b` | 6 | 1.0 | 0.05 | 参考相对基座朝向（旋转矩阵前两列） |
| `projected_gravity` | 3 | 1.0 | 0.03 | 投影重力 |
| `reference_support_phase` | 2 | 1.0 | 0.0 | 当前参考支撑相位 `[left, right]∈[0,1]` |
| `whole_body_com_rel_support_center` | **4** | 1.0 | **0.015** | **可部署平衡量**：base 系下 CoM 相对支撑中心的 xy 位置 + 相对速度 |

**Actor 总维数：463**（字母序拼接）。

`enable_noise=True`，`history_length=1`，`concatenate=True`。

#### 关键自定义项说明

**`reference_support_phase` / `future_support_phase`**

- 数据来自 motion npz 的 `reference_support_phase`，形状 `(T, 2)`，列顺序 **[left, right]**。
- `future_support_phase(num_future_frames=5)` → 拼 `t+1 … t+5`，输出 `(N, 10)`。
- 若 npz **没有**该字段，Command 侧会 fallback 为全 1（双脚始终接触），接触失配奖励与支撑相关 obs **失效**。

**`future_cmd(num_future_frames=5)`**

- 每帧：`cat(future_joint_pos(k), future_joint_vel(k))`，G1 29DoF → 每帧 58，共 290。
- 越界帧 clamp 到当前 clip 末尾。

**`whole_body_com_rel_support_center`（Actor，4 维）**

```
输出 = [pos_b_xy (2), vel_b_xy (2)]
pos_w = CoM_xy - support_center_xy
vel_w = CoM_vel_xy - support_center_vel_xy
再旋转到 base 系取 xy
```

- 全身 CoM：各 link 世界位姿/速度按质量加权（`simulator.get_body_masses()`）。
- 支撑中心：按 `_support_height_mask`——**更低的脚为支撑**；两脚高度差 `< 0.03 m` 则双支撑，取均值。
- 相对量使 base 线速度在差分中抵消 → 真机可用 FK + IMU 重建（见 inference `wbt_utils.py`）。

### 2.3 Critic 观测组（`critic_obs_shared_terms`）

| Term 名 | 维度（约） | 说明 |
|---------|------------|------|
| 与 Actor 共享的项 | （同名） | `motion_command`、`motion_ref_ori_b`、`base_ang_vel`、`dof_*`、`actions`、`projected_gravity`、support/future 系列 |
| `motion_ref_pos_b` | 3 | 参考相对位置（特权） |
| `robot_body_pos_b` | 14×3 | 跟踪 body 相对位置 |
| `robot_body_ori_b` | 14×6 | 跟踪 body 相对朝向 |
| `base_lin_vel` | 3 | 基座线速度（特权） |
| `whole_body_xcom_rel_support_center` | **2** | **Critic 专属**：xCoM 相对支撑中心（base xy） |

`enable_noise=False`。

**`whole_body_xcom_rel_support_center`（Critic only）**

```
xcom_xy = com_xy + com_vel_xy / ω,  ω = sqrt(g / h), h = max(com_z, 0.25)
支撑中心 = 接触力加权脚心（无接触则双脚均值）
rel → base 系 xy
```

依赖世界系 CoM 速度 → **禁止进 Actor**。

带物体变体 `g1_29dof_wbt_observation_w_object` 在 Critic 上再加 `obj_pos_b / obj_ori_b / obj_lin_vel_b`。

### 2.4 移植检查清单（观测）

- [ ] `observation.py` 中 Actor 含全部 11 个 term（含 `whole_body_com_rel_support_center`）
- [ ] Critic 含 `whole_body_xcom_rel_support_center`，且 **不在** Actor
- [ ] `future_*` 的 `num_future_frames=5`
- [ ] `managers/observation/terms/wbt.py` 实现齐全；高度支撑规则与 deploy 一致
- [ ] 训练打印 / 导出时 Actor dim = **463**
- [ ] Inference `obs_dict` 名字与字母序一致；`whole_body_com_rel_support_center: 4`

---

## 3. 奖励（Reward）

### 3.1 结构

- 基础集：`g1_29dof_wbt_reward`
- FastSAC 变体：`g1_29dof_wbt_fast_sac_reward` = 基础集 + 若干权重覆盖（主实验用这个）
- 实际回报贡献：`Episode/rew_X ≈ weight × dt × raw`，默认 `dt=0.02 s`

配置：`config_values/wbt/g1/reward.py`  
实现：`managers/reward/terms/wbt.py`

### 3.2 运动跟踪项（正奖励）

| Term | σ | `g1_29dof_wbt` weight | **FastSAC weight** | 说明 |
|------|---|----------------------|--------------------|------|
| `motion_global_ref_position_error_exp` | 0.3 | 0.5 | **1.0** | 全局参考位置 |
| `motion_global_ref_orientation_error_exp` | 0.4 | 0.5 | 0.5 | 全局参考朝向 |
| `motion_relative_body_position_error_exp` | 0.3 | 1.0 | **2.0** | 相对 body 位置 |
| `motion_relative_body_orientation_error_exp` | 0.4 | 1.0 | 1.0 | 相对 body 朝向 |
| `motion_global_body_lin_vel` | 1.0 | 1.0 | 1.0 | 线速度跟踪 |
| `motion_global_body_ang_vel` | 3.14 | 1.0 | 1.0 | 角速度跟踪（σ 宜松，给平衡自由度） |

形式均为指数核：`exp(-error² / σ²)` 一类（与实现一致即可）。

### 3.3 常规正则（负奖励）

| Term | FastSAC weight | params | 说明 |
|------|----------------|--------|------|
| `action_rate_l2` | **-1.0**（基础为 -0.1） | — | `‖a_t - a_{t-1}‖²` |
| `limits_dof_pos` | -10.0 | `soft_dof_pos_limit=0.9` | 软限位 |
| `undesired_contacts` | -0.1 | `threshold=1.0` + body 名正则 | 非脚/腕等接触惩罚 |

`undesired_contacts_body_names` 正则排除：

`left/right_foot_contact_point`、`left/right_wrist_yaw_link`、`left/right_ankle_roll_link`。

### 3.4 平衡 / 防跳五项（本仓库核心增量）

以下 raw 均为 **非负惩罚幅度**；负号来自 `weight`。

#### (1) `reference_support_contact_mismatch_penalty`

- **类**：`ReferenceSupportContactMismatchPenalty`
- **weight**：`-2.0`
- **params**：

```python
force_threshold=5.0
force_tau=0.5
stance_miss_weight=1.0
swing_extra_contact_weight=1.0
```

- **逻辑**：脚底法向力经 sigmoid 得 `actual∈[0,1]`，与参考 `reference_support_phase` 做双边失配；`certainty=|2*ref-1|` 加权。
  - stance-miss：参考要踩、实际腾空 → **防单脚跳**
  - swing-extra：参考要摆、实际着地

#### (2) `support_xcom_polygon_margin`

- **类**：`SupportXcomPolygonMarginPenalty`
- **weight**：`-50.0`
- **params**（推荐基线）：

```python
threshold=1.0                    # 接触力范数阈值（N）
single_support_safety_margin=0.02
double_support_safety_margin=0.03
gravity=9.81
com_height_floor=0.25
max_penalty=0.04
penalty_power=1.0                # 线性 hinge；勿用平方（米级 margin 梯度过小）
```

- **逻辑**：`penalty = relu(safety - signed_margin)^power`，再 clamp 到 `max_penalty`。
- **脚多边形**（踝坐标系，G1 共用）：

```python
_G1_FOOT_SUPPORT_POLYGON = (
    (-0.05, -0.025, -0.03),
    (0.12,  -0.030, -0.03),
    (0.12,   0.030, -0.03),
    (-0.05,  0.025, -0.03),
)
```

- 支撑多边形由**实际接触力**选脚（单脚 / 双脚凸包）。

#### (3) `xcom_ttb`

- **类**：`XcomTtbPenalty`
- **weight**：`-15.0`
- **params**：

```python
threshold=1.0
single_support_ttb_threshold=0.30  # 秒
double_support_ttb_threshold=0.20
v_min=0.01
gravity=9.81
com_height_floor=0.25
max_penalty=0.09
```

- **逻辑**：`ttb = margin / max(ω · ‖xcom - center‖, v_min)`；`penalty = relu(ttb_th - ttb)²`，再 clamp。

#### (4) `single_support_foot_slip_penalty`

- **类**：`SingleSupportFootSlipPenalty`
- **weight**：`-1.0`
- **params**：`force_threshold=1.0`
- **逻辑**：参考 `reference_support_state` 为单脚（1=左 / 2=右）且该脚实际接触时，惩罚支撑脚水平速度平方。

#### (5) `stance_ankle_action_rate`

- **类**：`StanceAnkleActionRatePenalty`
- **weight**：`-0.3`（**勿放松**；实验证明降到 -0.2 会显著更抖、更易跳）
- **params**：

```python
left_joint_names=["left_ankle_pitch_joint", "left_ankle_roll_joint"]
right_joint_names=["right_ankle_pitch_joint", "right_ankle_roll_joint"]
threshold=1.0
joint_weights=[1.0, 1.0]
```

- **逻辑**：按**实际单脚接触**门控，惩罚支撑侧踝关节 `Δaction²`。

### 3.5 FastSAC 相对基础集的权重差（必须对齐）

在复制 `g1_29dof_wbt_reward` 后，FastSAC 覆盖：

| Term | 覆盖为 |
|------|--------|
| `action_rate_l2` | `-1.0` |
| `motion_global_ref_position_error_exp` | `1.0` |
| `motion_relative_body_position_error_exp` | `2.0` |

其余与基础集相同（含五项平衡惩罚）。

### 3.6 实现依赖（奖励侧）

`managers/reward/terms/wbt.py` 需提供（可整文件移植）：

- `_FOOT_BODY_NAMES = ("left_ankle_roll_link", "right_ankle_roll_link")`
- `_whole_body_com_state` / `_xcom_xy` / `_support_contact_mask` / `_support_height_mask`
- `_foot_support_vertices_xy_w` / `_convex_hull_halfspace_margin` / `_support_polygon_margin`
- 五个 Penalty 类

仿真器需暴露：

- `get_body_masses()`
- `_rigid_body_pos` / `_rigid_body_vel` / `_rigid_body_rot`
- `contact_forces_history`
- `body_names` / `dof_names`

### 3.7 移植检查清单（奖励）

- [ ] 跟踪 6 项 + 正则 3 项 + 平衡 5 项全部注册
- [ ] FastSAC 权重表与 §3.5 一致
- [ ] `penalty_power=1.0`（多边形项）
- [ ] `stance_ankle_action_rate.weight = -0.3`
- [ ] 平衡三项权重保持 `-50 / -15 / -2`，**不要盲目 ×1.5**（见 §7）
- [ ] motion 含 `reference_support_phase` 与 `reference_support_state`

---

## 4. 终止（Termination）

配置：`config_values/wbt/g1/termination.py`  
实现：`managers/termination/terms/wbt.py`

### 4.1 启用的项

| Term | func | `is_timeout` | 说明 |
|------|------|--------------|------|
| `timeout` | `common:timeout_exceeded` | True | 超过 `max_episode_length_s`（本实验 **10.0 s**） |
| `bad_tracking` | `wbt:BadTrackingZOnly` | False | 跟踪失败提前重置 |

### 4.2 `BadTrackingZOnly` 阈值

相对 `BadTracking`：**位置只比 Z 轴**（与 BM Wo-State-Estimation 对齐）。

| 参数 | 值 | 含义 |
|------|-----|------|
| `bad_ref_pos_threshold` | **0.5** | 参考根位置 Z 误差 |
| `bad_ref_ori_threshold` | **0.8** | 投影重力 z 分量差 |
| `bad_motion_body_pos_threshold` | **0.25** | 指定 body 的 Z 误差 |
| `bad_object_pos_threshold` | 0.25 | 仅 `has_object` |
| `bad_object_ori_threshold` | 0.8 | 仅 `has_object` |

**Z 误差检查的 body**（`bad_motion_body_pos_body_names`）：

```text
left_ankle_roll_link, right_ankle_roll_link,
left_wrist_yaw_link, right_wrist_yaw_link
```

**`body_names_to_track`**（须与 `command.motion_config.body_names_to_track` **完全一致**）：

```text
pelvis, left_hip_roll_link, left_knee_link, left_ankle_roll_link,
right_hip_roll_link, right_knee_link, right_ankle_roll_link,
torso_link,
left_shoulder_roll_link, left_elbow_link, left_wrist_yaw_link,
right_shoulder_roll_link, right_elbow_link, right_wrist_yaw_link
```

### 4.3 行为注意

- `bad_tracking` 会触发自适应采样器更新（若开启）；本仓库推荐配置里 `use_adaptive_timesteps_sampler=False`。
- 可视化想看完整动作时，可临时放大阈值，或使用改过 termination 的 checkpoint；**训练复现请保持上表**。

### 4.4 移植检查清单（终止）

- [ ] 使用 `BadTrackingZOnly` 而非全位置 `BadTracking`
- [ ] 阈值 0.5 / 0.8 / 0.25
- [ ] `body_names_to_track` 与 command 配置一致
- [ ] `max_episode_length_s=10.0`

---

## 5. 数据与 Command 前置条件

### 5.1 Motion NPZ 字段

每个训练动作文件需包含（由离线脚本写入；本仓注释提及 `add_reference_support_phase.py`）：

| 字段 | 形状 | 含义 |
|------|------|------|
| `reference_support_phase` | `(T, 2)` float | 软接触 `[left, right]∈[0,1]` |
| `reference_support_state` | `(T,)` long | `0=双支撑, 1=左, 2=右, 3=飞行` |

缺失时 Loader fallback：`phase=1`、`state=0` → **接触失配与单脚滑移奖励基本无效**。

### 5.2 与平衡学习强相关的 Command 超参

文件：`config_values/wbt/g1/command.py`（当前推荐）：

```python
use_adaptive_timesteps_sampler=False
start_at_timestep_zero_prob=1.0   # 100% 从第 0 帧起步，避免“中段 RSI 救援”掩盖单脚失败
```

历史笔记曾用 `0.2` 逼练整条动作；当前代码注释选择回到 `1.0`。复现时与目标 run 的 `holosoma_config.yaml` 对齐即可。

### 5.3 域随机（辅助，非 obs/reward 本体）

`randomization.py` 中对质心 obs 有帮助的项（建议一并带上）：

- `randomize_mass_startup`：连杆质量 ×`[0.9, 1.1]`
- `randomize_base_com_startup`
- Actor 上 `whole_body_com_rel_support_center` 的 `noise=0.015`

当前基线 **关闭** IMU OU 变体（`base_ang_vel` / `projected_gravity` 用普通 term，不用 `_ou`）。

---

## 6. 部署侧对齐摘要

Inference Actor obs 列表（须与训练字母序一致）：

```text
actions, base_ang_vel, dof_pos, dof_vel,
future_cmd, future_support_phase,
motion_command, motion_ref_ori_b, projected_gravity,
reference_support_phase, whole_body_com_rel_support_center
```

关键维度：

| 名 | dim |
|----|-----|
| `motion_command` | 58 |
| `future_support_phase` | 10 |
| `future_cmd` | 290 |
| `whole_body_com_rel_support_center` | 4 |
| **Actor 合计** | **463** |

部署重建 CoM-rel 时：支撑脚用**重力对齐高度**规则（`double_support_height_diff=0.03`），与训练 `_support_height_mask` 一致。

---

## 7. 推荐复现配方与反例

### 7.1 推荐基线（20260705，全 500 动作评测峰值 ~71.8%）

| 项 | 值 |
|----|-----|
| 实验 | `g1_29dof_wbt_fast_sac` |
| OU IMU DR | **关** |
| `support_xcom_polygon_margin` | weight **-50** |
| `xcom_ttb` | weight **-15** |
| `reference_support_contact_mismatch` | weight **-2** |
| `stance_ankle_action_rate` | weight **-0.3** |
| `action_rate_l2` | **-1.0** |

### 7.2 已验证的负优化（20260712）

| 改动 | 结果 |
|------|------|
| 平衡三项权重 ×1.5（-75 / -22.5 / -3） | 成功率显著下降 |
| `stance_ankle_action_rate` -0.3 → **-0.2** | jerk↑、脚活动面积↑、跳/摔↑ |

结论：**不要用“加重平衡罚”换稳定**；防抖踝罚不要放松。

### 7.3 量级直觉（dt=0.02）

- 跟踪奖励合计每步约 **+0.01**
- 真跳一步：接触失配 + xCoM 等可到约 **-0.08/步**（已远大于跟踪）
- 若仍跳：优先检查是否从 frame0 自主撑过单脚段、以及数据是否含 support phase，而非无限加重 xCoM

---

## 8. 目标库上的最小合并步骤

1. **拷贝实现**：`managers/{observation,reward,termination}/terms/wbt.py`（及 command 中 support_phase 相关属性）。
2. **拷贝配置**：`config_values/wbt/g1/{observation,reward,termination}.py`，并在 `experiment.py` 挂上 `g1_29dof_wbt_fast_sac` 的 obs/reward/term。
3. **确认 motion**：训练集 npz 含 `reference_support_phase` / `reference_support_state`。
4. **冒烟**：起一个短训，检查 log 中存在  
   `rew_reference_support_contact_mismatch_penalty`、`rew_support_xcom_polygon_margin`、`rew_xcom_ttb`、`rew_single_support_foot_slip_penalty`、`rew_stance_ankle_action_rate`。
5. **核对 Actor dim=463**；导出 ONNX 前对齐 inference obs。
6. **（可选）** 同步 `command.py` 的 `start_at_timestep_zero_prob` 与 randomization。

---

## 9. 源文件索引（本仓库绝对路径前缀）

根目录：`holosoma-main/src/holosoma/holosoma/`

```
config_values/wbt/g1/observation.py
config_values/wbt/g1/reward.py
config_values/wbt/g1/termination.py
config_values/wbt/g1/experiment.py
config_values/wbt/g1/command.py
managers/observation/terms/wbt.py
managers/reward/terms/wbt.py
managers/termination/terms/wbt.py
managers/command/terms/wbt.py
```

推理：

```
src/holosoma_inference/holosoma_inference/config/config_values/observation.py
src/holosoma_inference/holosoma_inference/policies/wbt.py
src/holosoma_inference/holosoma_inference/policies/wbt_utils.py
```

补充阅读：`EXPERIMENT_REPORT_500motion.md`、`single_leg_balance_tuning.md`。

---

## 附录：迁入本仓库并适配 X2 的改动说明（2026-07-16）

本附录记录将 `tmp/src` 中的 OBD / 平衡 WBT 栈合并进 `holosoma/src`，并为 **X2 31DoF** 新增 WBT 实验入口的过程。原文 G1 复现说明（§0–§9）保持不变。

### 1. 从 tmp 迁入 / 合并的文件

| 路径（相对 `holosoma/src/...`） | 方式 |
|--------------------------------|------|
| `holosoma/managers/reward/terms/wbt.py` | **以 tmp 为底**，并保留 holosoma 的 `ZMPSupportRegionReward` |
| `holosoma/managers/observation/terms/wbt.py` | **tmp 覆盖**（支撑相位 / future_* / CoM-rel / xCoM-rel） |
| `holosoma/managers/command/terms/wbt.py` | **合并**：加载与暴露 `reference_support_phase/state`、`future_*`；**保留** `RandomSubsetMultiMotionLoader` 等 |
| `holosoma/simulator/{base_simulator,isaacgym,isaacsim}/*.py` | 增加 `get_body_masses()` |
| `holosoma/envs/wbt/wbt_manager.py` | tmp 覆盖（含 IMU OU buffer；默认 `IMU_OU_ENABLED=False`） |
| `holosoma/eval_agent.py` | 合并 ONNX 按 motion 打 tag；保留 video cleanup |
| `holosoma/utils/inference_helpers.py` | tmp 覆盖（ONNX 导出 support / future_cmd） |
| `holosoma_inference/.../observation.py` / `policies/wbt.py` / `wbt_utils.py` | **tmp 覆盖**（部署对齐） |
| `config_values/wbt/g1/{observation,reward,randomization}.py` | 启用五项平衡 + 支撑相位 obs；reward **额外保留 ZMP weight=0.5** |
| `config_values/wbt/g1/{command,experiment}.py` | 合并 `start_at_timestep_zero_prob=1.0`、采样器关闭、save_interval |

**未回退**（diff 后确认与 OBD 无关，保留 holosoma 本地改动）：`agents/ppo|fast_sac|base_algo` 的 play 进度条 / 连续录像、`video_recorder` 手动录制 API、X2 locomotion 配置。

### 2. 明确保留的能力

- **ZMP**：`ZMPSupportRegionReward` 实现 + G1/X2 reward 配置项 `zmp_support_region_exp`（weight=0.5）
- **RandomSubsetMultiMotionLoader** 及 motion 缓存 / 子集 manifest
- **X2 locomotion**：`config_values/loco/x2/`、`robot.x2_31dof` 未改动

### 3. 新增 `config_values/wbt/x2/` 与 G1 的关键差异

| 项 | G1 | X2 |
|----|----|----|
| Robot | `robot.g1_29dof` | `robot.x2_31dof` |
| DoF | 29 | 31 |
| Actor 总维 | 463 | **493**（`future_cmd` 290→310，`motion_command` 58→62，dof/actions +2×3） |
| Foot bodies | `left/right_ankle_roll_link` | 同名（与 X2 资产一致） |
| Foot polygon | `_G1_FOOT_SUPPORT_POLYGON` | **先复用 G1 多边形常量**（代码内注释标明；可按 X2 脚底球再调） |
| undesired contacts | foot_contact / ankle_roll / wrist_yaw | 另放行 `wrist_roll_link`（X2 腕链） |
| 实验名 | `g1_29dof_wbt(_fast_sac)` | `x2_31dof_wbt` / `x2_31dof_wbt_fast_sac` |
| 父级 DEFAULTS | 已有 | 已注册到 observation/reward/termination/command/curriculum/randomization/experiment |

### 4. X2 训练命令示例

```bash
python src/holosoma/holosoma/train_agent.py \
  exp:x2-31dof-wbt-fast-sac \
  --command.setup_terms.motion_command.params.motion_config.motion_file \
=/path/to/x2_31dof_motion_with_reference_support_phase.npz
```

PPO 变体：`exp:x2-31dof-wbt`。

### 5. 检查清单

- [x] `import` 配置：`x2_31dof_wbt_fast_sac` / `g1_29dof_wbt_fast_sac` 可解析（无 isaacsim / tensordict 环境下配置 DEFAULTS 已通过）
- [ ] motion npz 含 `reference_support_phase` / `reference_support_state`
- [ ] 短训 log 出现五项：`rew_reference_support_contact_mismatch_penalty`、`rew_support_xcom_polygon_margin`、`rew_xcom_ttb`、`rew_single_support_foot_slip_penalty`、`rew_stance_ankle_action_rate`
- [x] G1 Actor dim=463；X2 Actor dim=493（按 term 维数算术核对）
- [ ] 部署 inference obs 字母序与训练一致；CoM-rel 用高度规则 `double_support_height_diff=0.03`
- [x] X2 loco（`exp:x2-31dof` / `exp:x2-31dof-fast-sac`）仍注册在 DEFAULTS、未被本次 WBT 改动回退

---

*文档版本：基于 2026-07-15 代码与评测结论整理，面向跨仓复现 obs / reward / termination；附录记录 2026-07-16 迁入与 X2 适配。*

