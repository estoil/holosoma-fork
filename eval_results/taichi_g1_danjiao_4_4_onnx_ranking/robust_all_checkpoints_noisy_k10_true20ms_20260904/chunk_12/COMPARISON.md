# X2 WBT Checkpoint 对比 · steps 392000–400000

## 评测设置

- **Run**: `/home/wxy/taichi_deploy/holosoma/logs/WholeBodyTracking/20260903_100921-g1_29dof_wbt_fast_sac_robust_manager-locomotion`
- **Robot**: `/home/wxy/taichi_deploy/holosoma/src/holosoma/holosoma/data/robots/g1/g1_29dof.xml`
- **Motion dir**: `/home/wxy/taichi_deploy/holosoma/eval_results/taichi_g1_danjiao_4_4_onnx_ranking/robust_all_checkpoints_clean_noisy_k10_20260904/_motions`
- **Motions** (1): `taichi_g1_danjiao_4_4_robust_augmented`
- **Seeds (K)**: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
- **Condition**: `noisy`
- **Mode**: policy ONNX × npz reference (`use_npz_ref=True`)
- **Foot support rect (from X2 spheres)**: AP=`[-0.05, 0.12]`, ML=`[-0.0275, 0.0275]`
- **Wall time**: 293s

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
| 392000 | 0% | 100% | 17.60 | 7.71 | 0.294 | -0.897 | -0.763 | 0.360 | 0.923 |
| 394000 | 0% | 100% | 16.20 | 8.09 | 0.235 | -0.863 | -0.769 | 0.358 | 0.754 |
| 396000 | 0% | 100% | 10.10 | 8.75 | 0.232 | -0.897 | -0.764 | 0.273 | 0.748 |
| 398000 | 0% | 100% | 18.20 | 7.57 | 0.368 | -0.967 | -0.906 | 0.425 | 0.835 |
| 400000 | 0% | 100% | 25.30 | 6.34 | 0.305 | -0.766 | -0.783 | 0.505 | 1.025 |

## 排名与结论

- **相对最好**：`model_0396000.onnx` (succ=0%, fall=100%, hop=10.10, ttf=8.75s, comdev=0.232)
- **相对最差**：`model_0400000.onnx` (succ=0%, fall=100%, hop=25.30, ttf=6.34s, comdev=0.305)

### 前半 vs 后半 checkpoint

| 段 | succ | fall | hop | ttf | comdev |
|---|-----:|-----:|----:|----:|-------:|
| early (392000–394000) | 0% | 100% | 16.90 | 7.90 | 0.264 |
| late (396000–400000) | 0% | 100% | 17.87 | 7.55 | 0.302 |

### Top-5（综合排序）

1. `model_0396000` — succ=0% fall=100% hop=10.10 ttf=8.75 comdev=0.232
2. `model_0394000` — succ=0% fall=100% hop=16.20 ttf=8.09 comdev=0.235
3. `model_0392000` — succ=0% fall=100% hop=17.60 ttf=7.71 comdev=0.294
4. `model_0398000` — succ=0% fall=100% hop=18.20 ttf=7.57 comdev=0.368
5. `model_0400000` — succ=0% fall=100% hop=25.30 ttf=6.34 comdev=0.305

### 读数提示

- 本 sweep **成功率全为 0**：比较应看 **ttf / hop / comdev / xCoM**，不要只看 succ。
- 若全体很快摔倒，优先查 sim2sim 植物/obs 对齐与策略是否尚未学会单脚段，而非 checkpoint 细微差距。
- 完整逐动作结果见同目录 `sweep_results.json`。

