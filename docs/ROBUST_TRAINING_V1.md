# G1 WBT 第一版低风险鲁棒训练改进说明

## 1. 目标与边界

本次改进面向单动作 Whole Body Tracking policy，重点降低 5–10 ms 传感器延迟、关节速度噪声以及动作起止站立阶段造成的失稳风险。

本版保持以下部署接口不变：

- actor observation 仍为 463 维；
- action 仍为 29 维关节位置残差；
- 控制频率仍为 50 Hz；
- ONNX 输入输出名称、排列和形状不变；
- 普通 `g1-29dof-wbt-fast-sac` 实验不受影响，改动只接入 robust preset。

本版没有启用整帧 action delay，没有改成 RNN，也没有修改真机通信协议。这些属于下一阶段、风险更高的改动。

## 2. 改进前的主要问题

旧 robust observation 对 50% 环境使用当前关节速度，另外 50% 使用上一控制帧速度，即仅覆盖 0 ms 和 20 ms。实测 policy 在 5 ms 能通过，而 10 ms 已明显失效，因此旧分布没有覆盖最关键的过渡区间。

此外，旧实现只延迟 `dof_vel`，关节位置、IMU相关量和动态 CoM 仍使用当前仿真状态，训练时会产生混合时间戳观测。

## 3. 已实现改动

### 3.1 同步分数帧传感器延迟

新增 `RobustDelayedSensorObservation`，以下 actor observation 共用同一份逐环境延迟：

- base angular velocity；
- joint position；
- joint velocity；
- projected gravity；
- whole-body CoM relative to support center。

延迟通过当前与上一50 Hz样本间插值实现，不改变任何观测维度。每回合采样基础延迟，每步加入 `±1 ms` jitter。评估模式自动关闭训练扰动。

### 3.2 三阶段噪声/延迟课程

| 全局policy step | 主体延迟 | 关节速度白噪声 |
|---:|---:|---:|
| 0–79,999 | 0–2 ms | ±0.02 rad/s |
| 80,000–199,999 | 0–5 ms | ±0.05 rad/s |
| ≥200,000 | 0–8 ms | ±0.10 rad/s |

每阶段另有5%压力环境：延迟从该阶段上限采样到15 ms，关节速度噪声为 `±0.20 rad/s`。关节速度还包含幅值为当前白噪声25%的逐回合固定bias。

训练全局step会写入checkpoint，续训不会错误地回到第一阶段。

### 3.3 起止阶段覆盖

完整从动作开头开始的reset概率从50%提高到60%。原有流程继续保留：

- 2 s前置静止站立；
- 2 s平滑进入动作；
- 2 s平滑退出动作；
- 4 s后置静止站立。

其余40%环境继续使用adaptive RSI集中训练容易失败的动作区段。

### 3.4 新增安全正则项

robust reward新增三项：

- `quiet_double_support_velocity`：只在参考双脚支撑且参考关节速度接近零时，抑制机身角速度和关节残余速度；
- `action_target_soft_limit`：policy目标关节位置进入硬限位85%区域外时惩罚；
- `normalized_torque_usage`：按各关节力矩上限归一化后抑制过大执行器输出。

权重采用保守初值，避免过度平滑导致单脚阶段失去快速平衡修正能力。

### 3.5 接触参数收敛

robust实验的接触随机化调整为：

- static friction：0.5–1.3；
- dynamic friction：0.4–1.1；
- restitution：0–0.1。

相比旧配置，主要去掉不符合普通室内地面和橡胶脚底的高弹性接触，同时仍保留较宽摩擦覆盖。

## 4. 主要代码位置

- 课程和同步延迟：`src/holosoma/holosoma/managers/observation/terms/wbt.py`
- robust actor配置：`src/holosoma/holosoma/config_values/wbt/g1/observation.py`
- 安全reward实现：`src/holosoma/holosoma/managers/reward/terms/wbt.py`
- robust reward配置：`src/holosoma/holosoma/config_values/wbt/g1/reward.py`
- 接触与动力学随机化：`src/holosoma/holosoma/config_values/wbt/g1/randomization.py`
- 起始采样比例：`src/holosoma/holosoma/config_values/wbt/g1/command.py`
- robust preset接线：`src/holosoma/holosoma/config_values/wbt/g1/experiment.py`

## 5. 建议训练流程

先进行10轮冒烟训练，确认配置、显存和reward均正常：

```bash
cd /home/wxy/taichi_deploy/holosoma
source scripts/source_isaacsim_setup.sh

python src/holosoma/holosoma/train_agent.py \
  exp:g1-29dof-wbt-fast-sac-robust \
  --training.seed 42 \
  --training.num-envs 256 \
  --algo.config.num-learning-iterations 10 \
  algo:fast-sac simulator:isaacsim logger:wandb \
  --logger.video.enabled False
```

正式训练前，在 `config_values/wbt/g1/command.py` 的 `robust_motion_config.motion_file` 中确认目标NPZ。5-1动作应为：

```text
/home/wxy/taichi_deploy/holosoma/motions_from_web/5-1-26777-29035_holosoma.npz
```

正式实验至少使用3个seed，例如42、43、44。显存不足时优先使用2048个环境，不要缩短动作前后站立段。

## 6. 验收标准

checkpoint不能只按训练reward或最终step选择。建议每2000 step导出并在MuJoCo执行：

1. clean完整动作；
2. `±0.05 rad/s + 5 ms`，K≥50；
3. `±0.10 rad/s + 5 ms`，K≥50；
4. 0/2/5/8/10/15 ms延迟扫描；
5. 分别统计前置站立、单脚段、后置站立成功率；
6. 同时检查摔倒、摆动脚提前触地、支撑脚hop、滑移、CoM、ZMP、目标关节软限位和目标跳变。

第一阶段合格线建议为：clean 100%，推荐扰动≥98%，后置站立≥98%，且不得出现目标越过真机软限位。上真机前仍须使用部署安全层和吊绳分级测试。

## 7. 尚未解决的风险

- 插值延迟是50 Hz边界样本的近似，不等同于完整200 Hz传感器历史；
- 当前参数尚未由真机日志完成系统辨识；
- 尚未加入电机一阶滞后、电压衰减、通信丢包和逐关节电机强度随机化；
- 本改动不能替代真机端的关节软限位、目标变化率限制、LowState超时保护和安全阻尼退出；
- 必须重新训练并通过跨seed、跨checkpoint评测后，才能判断实际提升幅度。

## 8. 本次实现验证记录

2026-09-05在RTX 3090上完成10轮、256环境的IsaacSim冒烟训练：

- 训练进度：10/10完成；
- actor observation：463维；
- critic observation：593维；
- checkpoint：`logs/WholeBodyTracking/20260905_075401-g1_29dof_wbt_fast_sac_robust_manager-locomotion/model_0000010.pt`；
- ONNX：同目录下`model_0000010.onnx`；
- ONNX检查：输入`obs[1,463]`、`time_step[1,1]`，输出`actions[1,29]`，`onnx.checker`通过；
- 传感器课程、共享step jitter及eval关闭扰动的单元检查通过；
- Python compileall和git diff whitespace检查通过。

IsaacSim启动时仍打印系统已有的inotify `errno=28` change-watch警告，但场景、训练、checkpoint和ONNX导出均成功，未构成本次冒烟训练失败。
