# X2 WBT Checkpoint 对比 · steps 216000–236000

## 评测设置

- **Run**: `/home/wxy/taichi_deploy/holosoma/logs/WholeBodyTracking/20260903_100921-g1_29dof_wbt_fast_sac_robust_manager-locomotion`
- **Robot**: `/home/wxy/taichi_deploy/holosoma/src/holosoma/holosoma/data/robots/g1/g1_29dof.xml`
- **Motion dir**: `/home/wxy/taichi_deploy/holosoma/eval_results/taichi_g1_danjiao_4_4_onnx_ranking/robust_all_checkpoints_clean_noisy_k10_20260904/_motions`
- **Motions** (1): `taichi_g1_danjiao_4_4_robust_augmented`
- **Seeds (K)**: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
- **Condition**: `noisy`
- **Mode**: policy ONNX × npz reference (`use_npz_ref=True`)
- **Foot support rect (from X2 spheres)**: AP=`[-0.05, 0.12]`, ML=`[-0.0275, 0.0275]`
- **Wall time**: 643s

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
| 216000 | 0% | 100% | 13.00 | 7.84 | 0.352 | -0.863 | -0.684 | 0.300 | 0.931 |
| 218000 | 0% | 100% | 11.80 | 8.92 | 0.263 | -0.761 | -0.730 | 0.326 | 0.939 |
| 220000 | 0% | 100% | 15.00 | 9.36 | 0.374 | -0.756 | -0.724 | 0.305 | 0.623 |
| 222000 | 0% | 100% | 13.10 | 6.88 | 0.283 | -0.737 | -0.645 | 0.170 | 0.876 |
| 224000 | 0% | 100% | 8.90 | 8.65 | 0.376 | -0.860 | -0.867 | 0.226 | 0.825 |
| 226000 | 0% | 100% | 17.40 | 8.47 | 0.426 | -0.774 | -0.674 | 0.215 | 0.847 |
| 228000 | 0% | 100% | 4.20 | 8.63 | 0.467 | -0.770 | -0.695 | 0.131 | 0.808 |
| 230000 | 0% | 100% | 14.40 | 7.25 | 0.316 | -0.766 | -0.684 | 0.385 | 0.823 |
| 232000 | 0% | 100% | 5.20 | 5.92 | 0.302 | -0.767 | -0.714 | 0.138 | 0.943 |
| 234000 | 0% | 100% | 8.30 | 7.14 | 0.217 | -0.736 | -0.705 | 0.152 | 0.781 |
| 236000 | 0% | 100% | 13.90 | 8.32 | 0.287 | -0.946 | -0.742 | 0.293 | 0.700 |

## 排名与结论

- **相对最好**：`model_0228000.onnx` (succ=0%, fall=100%, hop=4.20, ttf=8.63s, comdev=0.467)
- **相对最差**：`model_0226000.onnx` (succ=0%, fall=100%, hop=17.40, ttf=8.47s, comdev=0.426)

### 前半 vs 后半 checkpoint

| 段 | succ | fall | hop | ttf | comdev |
|---|-----:|-----:|----:|----:|-------:|
| early (216000–224000) | 0% | 100% | 12.36 | 8.33 | 0.330 |
| late (226000–236000) | 0% | 100% | 10.57 | 7.62 | 0.336 |

### Top-5（综合排序）

1. `model_0228000` — succ=0% fall=100% hop=4.20 ttf=8.63 comdev=0.467
2. `model_0232000` — succ=0% fall=100% hop=5.20 ttf=5.92 comdev=0.302
3. `model_0234000` — succ=0% fall=100% hop=8.30 ttf=7.14 comdev=0.217
4. `model_0224000` — succ=0% fall=100% hop=8.90 ttf=8.65 comdev=0.376
5. `model_0218000` — succ=0% fall=100% hop=11.80 ttf=8.92 comdev=0.263

### 读数提示

- 本 sweep **成功率全为 0**：比较应看 **ttf / hop / comdev / xCoM**，不要只看 succ。
- 若全体很快摔倒，优先查 sim2sim 植物/obs 对齐与策略是否尚未学会单脚段，而非 checkpoint 细微差距。
- 完整逐动作结果见同目录 `sweep_results.json`。

