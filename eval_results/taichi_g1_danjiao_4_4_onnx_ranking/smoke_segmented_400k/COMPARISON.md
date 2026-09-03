# X2 WBT Checkpoint 对比 · steps 400000–400000

## 评测设置

- **Run**: `holosoma/logs/WholeBodyTracking/20260901_072339-g1_29dof_wbt_fast_sac_manager-locomotion`
- **Robot**: `/home/wxy/taichi_deploy/holosoma/src/holosoma/holosoma/data/robots/g1/g1_29dof.xml`
- **Motion dir**: `/home/wxy/taichi_deploy/holosoma/motions_from_web`
- **Motions** (1): `taichi_g1_danjiao_4_4_holosoma`
- **Seeds (K)**: [0]
- **Condition**: `clean`
- **Mode**: policy ONNX × npz reference (`use_npz_ref=True`)
- **Foot support rect (from X2 spheres)**: AP=`[-0.05, 0.12]`, ML=`[-0.0275, 0.0275]`
- **Wall time**: 4s

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
| 400000 | 0% | 0% | 8.00 | 19.84 | 0.114 | -0.117 | -0.069 | 0.137 | 0.159 |

## 排名与结论

- **相对最好**：`model_0400000.onnx` (succ=0%, fall=0%, hop=8.00, ttf=19.84s, comdev=0.114)
- **相对最差**：`model_0400000.onnx` (succ=0%, fall=0%, hop=8.00, ttf=19.84s, comdev=0.114)

### 前半 vs 后半 checkpoint

| 段 | succ | fall | hop | ttf | comdev |
|---|-----:|-----:|----:|----:|-------:|
| early (400000–400000) | 0% | 0% | 8.00 | 19.84 | 0.114 |
| late (400000–400000) | 0% | 0% | 8.00 | 19.84 | 0.114 |

### Top-5（综合排序）

1. `model_0400000` — succ=0% fall=0% hop=8.00 ttf=19.84 comdev=0.114

### 读数提示

- 本 sweep **成功率全为 0**：比较应看 **ttf / hop / comdev / xCoM**，不要只看 succ。
- 若全体很快摔倒，优先查 sim2sim 植物/obs 对齐与策略是否尚未学会单脚段，而非 checkpoint 细微差距。
- 完整逐动作结果见同目录 `sweep_results.json`。

