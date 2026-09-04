# X2 WBT Checkpoint 对比 · steps 260000–280000

## 评测设置

- **Run**: `/home/wxy/taichi_deploy/holosoma/logs/WholeBodyTracking/20260903_100921-g1_29dof_wbt_fast_sac_robust_manager-locomotion`
- **Robot**: `/home/wxy/taichi_deploy/holosoma/src/holosoma/holosoma/data/robots/g1/g1_29dof.xml`
- **Motion dir**: `/home/wxy/taichi_deploy/holosoma/eval_results/taichi_g1_danjiao_4_4_onnx_ranking/robust_all_checkpoints_clean_noisy_k10_20260904/_motions`
- **Motions** (1): `taichi_g1_danjiao_4_4_robust_augmented`
- **Seeds (K)**: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
- **Condition**: `noisy`
- **Mode**: policy ONNX × npz reference (`use_npz_ref=True`)
- **Foot support rect (from X2 spheres)**: AP=`[-0.05, 0.12]`, ML=`[-0.0275, 0.0275]`
- **Wall time**: 644s

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
| 260000 | 0% | 100% | 8.20 | 7.06 | 0.414 | -0.722 | -0.708 | 0.285 | 0.872 |
| 262000 | 0% | 100% | 6.90 | 8.70 | 0.456 | -0.790 | -0.600 | 0.157 | 0.676 |
| 264000 | 0% | 100% | 19.20 | 7.72 | 0.306 | -0.781 | -0.757 | 0.288 | 0.754 |
| 266000 | 0% | 100% | 16.20 | 5.76 | 0.353 | -0.763 | -0.709 | 0.246 | 0.837 |
| 268000 | 0% | 100% | 9.50 | 8.90 | 0.346 | -0.799 | -0.744 | 0.264 | 0.652 |
| 270000 | 0% | 100% | 18.80 | 6.32 | 0.292 | -0.796 | -0.870 | 0.452 | 0.781 |
| 272000 | 0% | 100% | 11.50 | 5.91 | 0.291 | -0.787 | -0.716 | 0.266 | 0.929 |
| 274000 | 0% | 100% | 14.40 | 7.28 | 0.361 | -0.883 | -0.786 | 0.260 | 0.780 |
| 276000 | 0% | 100% | 13.00 | 8.16 | 0.343 | -0.906 | -1.013 | 0.352 | 0.981 |
| 278000 | 0% | 100% | 12.70 | 7.42 | 0.266 | -0.798 | -0.728 | 0.275 | 0.684 |
| 280000 | 0% | 100% | 12.10 | 7.24 | 0.353 | -0.740 | -0.698 | 0.231 | 0.878 |

## 排名与结论

- **相对最好**：`model_0262000.onnx` (succ=0%, fall=100%, hop=6.90, ttf=8.70s, comdev=0.456)
- **相对最差**：`model_0264000.onnx` (succ=0%, fall=100%, hop=19.20, ttf=7.72s, comdev=0.306)

### 前半 vs 后半 checkpoint

| 段 | succ | fall | hop | ttf | comdev |
|---|-----:|-----:|----:|----:|-------:|
| early (260000–268000) | 0% | 100% | 12.00 | 7.63 | 0.375 |
| late (270000–280000) | 0% | 100% | 13.75 | 7.06 | 0.318 |

### Top-5（综合排序）

1. `model_0262000` — succ=0% fall=100% hop=6.90 ttf=8.70 comdev=0.456
2. `model_0260000` — succ=0% fall=100% hop=8.20 ttf=7.06 comdev=0.414
3. `model_0268000` — succ=0% fall=100% hop=9.50 ttf=8.90 comdev=0.346
4. `model_0272000` — succ=0% fall=100% hop=11.50 ttf=5.91 comdev=0.291
5. `model_0280000` — succ=0% fall=100% hop=12.10 ttf=7.24 comdev=0.353

### 读数提示

- 本 sweep **成功率全为 0**：比较应看 **ttf / hop / comdev / xCoM**，不要只看 succ。
- 若全体很快摔倒，优先查 sim2sim 植物/obs 对齐与策略是否尚未学会单脚段，而非 checkpoint 细微差距。
- 完整逐动作结果见同目录 `sweep_results.json`。

