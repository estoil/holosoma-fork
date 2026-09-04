# X2 WBT Checkpoint 对比 · steps 386000–400000

## 评测设置

- **Run**: `/home/wxy/taichi_deploy/holosoma/logs/WholeBodyTracking/20260903_100921-g1_29dof_wbt_fast_sac_robust_manager-locomotion`
- **Robot**: `/home/wxy/taichi_deploy/holosoma/src/holosoma/holosoma/data/robots/g1/g1_29dof.xml`
- **Motion dir**: `/home/wxy/taichi_deploy/holosoma/eval_results/taichi_g1_danjiao_4_4_onnx_ranking/robust_all_checkpoints_clean_noisy_k10_20260904/_motions`
- **Motions** (1): `taichi_g1_danjiao_4_4_robust_augmented`
- **Seeds (K)**: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
- **Condition**: `clean`
- **Mode**: policy ONNX × npz reference (`use_npz_ref=True`)
- **Foot support rect (from X2 spheres)**: AP=`[-0.05, 0.12]`, ML=`[-0.0275, 0.0275]`
- **Wall time**: 995s

指标说明：
- **succ**：0 hop 且未摔且摆动脚未触地的试验比例（主）
- **fall / hop / ttf**：摔倒率、支撑脚 hop 均值、平均撑住时长（越大越好）
- **comdev**：相对参考的 CoM 偏差（主平衡；越小越好）
- **ml / ap**：xCoM 裕度最差值（诊断；越大越好；负=出界）
- **jerk / epos**：动作 jerk、关键点跟踪误差（次要）

> 训练 reward 仍可能用 G1 窄脚多边形；此处 xCoM 按真实 X2 脚球 AABB，**勿与训练 log 数值直接对齐**。

## 总表（按 step）

| step | succ | fall | hop↓ | ttf↑ | comdev↓ | ml_worst↑ | ap_worst↑ | jerk | Epos |
|-----:|-----:|-----:|-----:|-----:|--------:|----------:|----------:|-----:|-----:|
| 386000 | 100% | 0% | 0.00 | 29.84 | 0.112 | +0.012 | +0.013 | 0.007 | 0.094 |
| 388000 | 100% | 0% | 0.00 | 29.84 | 0.111 | +0.012 | +0.019 | 0.007 | 0.110 |
| 390000 | 100% | 0% | 0.00 | 29.84 | 0.111 | +0.012 | +0.016 | 0.008 | 0.106 |
| 392000 | 100% | 0% | 0.00 | 29.84 | 0.113 | -0.023 | -0.035 | 0.008 | 0.100 |
| 394000 | 100% | 0% | 0.00 | 29.84 | 0.111 | +0.012 | +0.036 | 0.007 | 0.097 |
| 396000 | 100% | 0% | 0.00 | 29.84 | 0.115 | +0.015 | +0.030 | 0.007 | 0.095 |
| 398000 | 100% | 0% | 0.00 | 29.84 | 0.114 | +0.011 | +0.017 | 0.008 | 0.104 |
| 400000 | 100% | 0% | 0.00 | 29.84 | 0.116 | +0.016 | +0.019 | 0.007 | 0.094 |

## 排名与结论

- **相对最好**：`model_0390000.onnx` (succ=100%, fall=0%, hop=0.00, ttf=29.84s, comdev=0.111)
- **相对最差**：`model_0400000.onnx` (succ=100%, fall=0%, hop=0.00, ttf=29.84s, comdev=0.116)

### 前半 vs 后半 checkpoint

| 段 | succ | fall | hop | ttf | comdev |
|---|-----:|-----:|----:|----:|-------:|
| early (386000–392000) | 100% | 0% | 0.00 | 29.84 | 0.112 |
| late (394000–400000) | 100% | 0% | 0.00 | 29.84 | 0.114 |

### Top-5（综合排序）

1. `model_0390000` — succ=100% fall=0% hop=0.00 ttf=29.84 comdev=0.111
2. `model_0394000` — succ=100% fall=0% hop=0.00 ttf=29.84 comdev=0.111
3. `model_0388000` — succ=100% fall=0% hop=0.00 ttf=29.84 comdev=0.111
4. `model_0386000` — succ=100% fall=0% hop=0.00 ttf=29.84 comdev=0.112
5. `model_0392000` — succ=100% fall=0% hop=0.00 ttf=29.84 comdev=0.113

### 读数提示

- 有成功试验时以 **succ + hop 尾部** 为主；comdev 看是否跟上参考平衡意图。
- 完整逐动作结果见同目录 `sweep_results.json`。

