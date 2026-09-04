# X2 WBT Checkpoint 对比 · steps 172000–192000

## 评测设置

- **Run**: `/home/wxy/taichi_deploy/holosoma/logs/WholeBodyTracking/20260903_100921-g1_29dof_wbt_fast_sac_robust_manager-locomotion`
- **Robot**: `/home/wxy/taichi_deploy/holosoma/src/holosoma/holosoma/data/robots/g1/g1_29dof.xml`
- **Motion dir**: `/home/wxy/taichi_deploy/holosoma/eval_results/taichi_g1_danjiao_4_4_onnx_ranking/robust_all_checkpoints_clean_noisy_k10_20260904/_motions`
- **Motions** (1): `taichi_g1_danjiao_4_4_robust_augmented`
- **Seeds (K)**: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
- **Condition**: `noisy`
- **Mode**: policy ONNX × npz reference (`use_npz_ref=True`)
- **Foot support rect (from X2 spheres)**: AP=`[-0.05, 0.12]`, ML=`[-0.0275, 0.0275]`
- **Wall time**: 640s

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
| 172000 | 0% | 100% | 21.90 | 6.77 | 0.222 | -0.827 | -0.702 | 0.344 | 1.057 |
| 174000 | 0% | 100% | 15.50 | 7.74 | 0.182 | -0.920 | -0.827 | 0.252 | 0.753 |
| 176000 | 0% | 100% | 11.70 | 6.33 | 0.257 | -0.737 | -0.678 | 0.156 | 0.931 |
| 178000 | 0% | 100% | 16.50 | 7.25 | 0.261 | -1.002 | -0.747 | 0.497 | 1.040 |
| 180000 | 0% | 100% | 8.40 | 8.20 | 0.253 | -0.725 | -0.609 | 0.220 | 0.723 |
| 182000 | 0% | 100% | 3.80 | 7.99 | 0.357 | -0.811 | -0.673 | 0.185 | 0.911 |
| 184000 | 0% | 100% | 12.40 | 6.75 | 0.343 | -0.889 | -0.791 | 0.271 | 0.920 |
| 186000 | 0% | 100% | 8.30 | 8.36 | 0.308 | -0.763 | -0.632 | 0.257 | 0.762 |
| 188000 | 0% | 100% | 9.90 | 7.48 | 0.253 | -0.784 | -0.677 | 0.311 | 1.050 |
| 190000 | 0% | 100% | 11.90 | 7.81 | 0.282 | -1.029 | -0.758 | 0.395 | 0.867 |
| 192000 | 0% | 100% | 12.10 | 7.39 | 0.271 | -0.940 | -0.644 | 0.259 | 0.711 |

## 排名与结论

- **相对最好**：`model_0182000.onnx` (succ=0%, fall=100%, hop=3.80, ttf=7.99s, comdev=0.357)
- **相对最差**：`model_0172000.onnx` (succ=0%, fall=100%, hop=21.90, ttf=6.77s, comdev=0.222)

### 前半 vs 后半 checkpoint

| 段 | succ | fall | hop | ttf | comdev |
|---|-----:|-----:|----:|----:|-------:|
| early (172000–180000) | 0% | 100% | 14.80 | 7.26 | 0.235 |
| late (182000–192000) | 0% | 100% | 9.73 | 7.63 | 0.303 |

### Top-5（综合排序）

1. `model_0182000` — succ=0% fall=100% hop=3.80 ttf=7.99 comdev=0.357
2. `model_0186000` — succ=0% fall=100% hop=8.30 ttf=8.36 comdev=0.308
3. `model_0180000` — succ=0% fall=100% hop=8.40 ttf=8.20 comdev=0.253
4. `model_0188000` — succ=0% fall=100% hop=9.90 ttf=7.48 comdev=0.253
5. `model_0176000` — succ=0% fall=100% hop=11.70 ttf=6.33 comdev=0.257

### 读数提示

- 本 sweep **成功率全为 0**：比较应看 **ttf / hop / comdev / xCoM**，不要只看 succ。
- 若全体很快摔倒，优先查 sim2sim 植物/obs 对齐与策略是否尚未学会单脚段，而非 checkpoint 细微差距。
- 完整逐动作结果见同目录 `sweep_results.json`。

