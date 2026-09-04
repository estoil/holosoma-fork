# X2 WBT Checkpoint 对比 · steps 238000–258000

## 评测设置

- **Run**: `/home/wxy/taichi_deploy/holosoma/logs/WholeBodyTracking/20260903_100921-g1_29dof_wbt_fast_sac_robust_manager-locomotion`
- **Robot**: `/home/wxy/taichi_deploy/holosoma/src/holosoma/holosoma/data/robots/g1/g1_29dof.xml`
- **Motion dir**: `/home/wxy/taichi_deploy/holosoma/eval_results/taichi_g1_danjiao_4_4_onnx_ranking/robust_all_checkpoints_clean_noisy_k10_20260904/_motions`
- **Motions** (1): `taichi_g1_danjiao_4_4_robust_augmented`
- **Seeds (K)**: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
- **Condition**: `noisy`
- **Mode**: policy ONNX × npz reference (`use_npz_ref=True`)
- **Foot support rect (from X2 spheres)**: AP=`[-0.05, 0.12]`, ML=`[-0.0275, 0.0275]`
- **Wall time**: 642s

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
| 238000 | 0% | 100% | 19.50 | 6.01 | 0.271 | -0.840 | -0.676 | 0.389 | 0.848 |
| 240000 | 0% | 100% | 21.70 | 5.96 | 0.150 | -0.950 | -0.600 | 0.350 | 0.810 |
| 242000 | 0% | 100% | 10.40 | 6.21 | 0.348 | -0.765 | -0.660 | 0.394 | 0.829 |
| 244000 | 0% | 100% | 15.90 | 7.02 | 0.379 | -0.900 | -0.687 | 0.503 | 1.231 |
| 246000 | 0% | 100% | 27.80 | 7.18 | 0.435 | -0.915 | -0.762 | 0.541 | 0.837 |
| 248000 | 0% | 100% | 13.60 | 7.94 | 0.402 | -0.675 | -0.530 | 0.301 | 0.770 |
| 250000 | 0% | 100% | 12.20 | 6.44 | 0.407 | -0.711 | -0.732 | 0.259 | 1.193 |
| 252000 | 0% | 100% | 2.70 | 7.35 | 0.416 | -0.651 | -0.549 | 0.147 | 0.717 |
| 254000 | 0% | 100% | 12.30 | 7.27 | 0.470 | -0.895 | -0.659 | 0.245 | 0.770 |
| 256000 | 0% | 100% | 8.90 | 8.41 | 0.381 | -0.787 | -0.733 | 0.243 | 0.697 |
| 258000 | 0% | 100% | 7.60 | 9.57 | 0.322 | -0.724 | -0.554 | 0.235 | 0.725 |

## 排名与结论

- **相对最好**：`model_0252000.onnx` (succ=0%, fall=100%, hop=2.70, ttf=7.35s, comdev=0.416)
- **相对最差**：`model_0246000.onnx` (succ=0%, fall=100%, hop=27.80, ttf=7.18s, comdev=0.435)

### 前半 vs 后半 checkpoint

| 段 | succ | fall | hop | ttf | comdev |
|---|-----:|-----:|----:|----:|-------:|
| early (238000–246000) | 0% | 100% | 19.06 | 6.48 | 0.317 |
| late (248000–258000) | 0% | 100% | 9.55 | 7.83 | 0.400 |

### Top-5（综合排序）

1. `model_0252000` — succ=0% fall=100% hop=2.70 ttf=7.35 comdev=0.416
2. `model_0258000` — succ=0% fall=100% hop=7.60 ttf=9.57 comdev=0.322
3. `model_0256000` — succ=0% fall=100% hop=8.90 ttf=8.41 comdev=0.381
4. `model_0242000` — succ=0% fall=100% hop=10.40 ttf=6.21 comdev=0.348
5. `model_0250000` — succ=0% fall=100% hop=12.20 ttf=6.44 comdev=0.407

### 读数提示

- 本 sweep **成功率全为 0**：比较应看 **ttf / hop / comdev / xCoM**，不要只看 succ。
- 若全体很快摔倒，优先查 sim2sim 植物/obs 对齐与策略是否尚未学会单脚段，而非 checkpoint 细微差距。
- 完整逐动作结果见同目录 `sweep_results.json`。

