# X2 WBT Checkpoint 对比 · steps 304000–324000

## 评测设置

- **Run**: `/home/wxy/taichi_deploy/holosoma/logs/WholeBodyTracking/20260903_100921-g1_29dof_wbt_fast_sac_robust_manager-locomotion`
- **Robot**: `/home/wxy/taichi_deploy/holosoma/src/holosoma/holosoma/data/robots/g1/g1_29dof.xml`
- **Motion dir**: `/home/wxy/taichi_deploy/holosoma/eval_results/taichi_g1_danjiao_4_4_onnx_ranking/robust_all_checkpoints_clean_noisy_k10_20260904/_motions`
- **Motions** (1): `taichi_g1_danjiao_4_4_robust_augmented`
- **Seeds (K)**: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
- **Condition**: `noisy`
- **Mode**: policy ONNX × npz reference (`use_npz_ref=True`)
- **Foot support rect (from X2 spheres)**: AP=`[-0.05, 0.12]`, ML=`[-0.0275, 0.0275]`
- **Wall time**: 641s

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
| 304000 | 0% | 100% | 9.00 | 7.96 | 0.254 | -0.843 | -0.730 | 0.226 | 0.862 |
| 306000 | 0% | 100% | 10.00 | 7.32 | 0.362 | -0.803 | -0.716 | 0.338 | 0.940 |
| 308000 | 0% | 100% | 9.70 | 9.27 | 0.229 | -0.931 | -0.881 | 0.268 | 0.696 |
| 310000 | 0% | 100% | 14.60 | 6.78 | 0.265 | -0.759 | -0.711 | 0.286 | 0.857 |
| 312000 | 0% | 100% | 13.80 | 8.31 | 0.286 | -0.785 | -0.758 | 0.374 | 0.789 |
| 314000 | 0% | 100% | 20.20 | 6.54 | 0.259 | -0.813 | -0.649 | 0.439 | 0.777 |
| 316000 | 0% | 100% | 9.70 | 8.20 | 0.367 | -0.855 | -0.693 | 0.359 | 0.771 |
| 318000 | 0% | 100% | 16.90 | 8.53 | 0.333 | -0.875 | -0.776 | 0.369 | 0.730 |
| 320000 | 0% | 100% | 11.30 | 7.77 | 0.427 | -0.769 | -0.798 | 0.232 | 0.711 |
| 322000 | 0% | 100% | 11.10 | 7.94 | 0.328 | -0.861 | -0.692 | 0.262 | 0.754 |
| 324000 | 0% | 100% | 13.70 | 6.19 | 0.255 | -0.758 | -0.647 | 0.872 | 1.032 |

## 排名与结论

- **相对最好**：`model_0304000.onnx` (succ=0%, fall=100%, hop=9.00, ttf=7.96s, comdev=0.254)
- **相对最差**：`model_0314000.onnx` (succ=0%, fall=100%, hop=20.20, ttf=6.54s, comdev=0.259)

### 前半 vs 后半 checkpoint

| 段 | succ | fall | hop | ttf | comdev |
|---|-----:|-----:|----:|----:|-------:|
| early (304000–312000) | 0% | 100% | 11.42 | 7.93 | 0.279 |
| late (314000–324000) | 0% | 100% | 13.82 | 7.53 | 0.328 |

### Top-5（综合排序）

1. `model_0304000` — succ=0% fall=100% hop=9.00 ttf=7.96 comdev=0.254
2. `model_0308000` — succ=0% fall=100% hop=9.70 ttf=9.27 comdev=0.229
3. `model_0316000` — succ=0% fall=100% hop=9.70 ttf=8.20 comdev=0.367
4. `model_0306000` — succ=0% fall=100% hop=10.00 ttf=7.32 comdev=0.362
5. `model_0322000` — succ=0% fall=100% hop=11.10 ttf=7.94 comdev=0.328

### 读数提示

- 本 sweep **成功率全为 0**：比较应看 **ttf / hop / comdev / xCoM**，不要只看 succ。
- 若全体很快摔倒，优先查 sim2sim 植物/obs 对齐与策略是否尚未学会单脚段，而非 checkpoint 细微差距。
- 完整逐动作结果见同目录 `sweep_results.json`。

