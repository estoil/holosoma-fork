# X2 WBT Checkpoint 对比 · steps 150000–170000

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
| 150000 | 0% | 100% | 9.50 | 8.12 | 0.290 | -0.734 | -0.620 | 0.184 | 0.965 |
| 152000 | 0% | 100% | 9.20 | 7.85 | 0.251 | -0.848 | -0.578 | 0.199 | 0.820 |
| 154000 | 0% | 100% | 27.30 | 6.65 | 0.145 | -0.904 | -0.733 | 0.326 | 0.853 |
| 156000 | 0% | 100% | 18.00 | 7.86 | 0.192 | -0.782 | -0.710 | 0.254 | 0.707 |
| 158000 | 0% | 100% | 25.10 | 7.06 | 0.166 | -0.862 | -0.711 | 0.274 | 0.774 |
| 160000 | 0% | 100% | 16.40 | 7.30 | 0.163 | -0.826 | -0.748 | 0.154 | 0.621 |
| 162000 | 0% | 100% | 18.00 | 7.29 | 0.184 | -0.728 | -0.690 | 0.258 | 0.884 |
| 164000 | 0% | 100% | 12.90 | 8.00 | 0.212 | -0.763 | -0.685 | 0.183 | 0.891 |
| 166000 | 0% | 100% | 17.70 | 7.41 | 0.198 | -0.792 | -0.656 | 0.214 | 0.778 |
| 168000 | 0% | 100% | 14.10 | 8.42 | 0.296 | -0.972 | -0.774 | 0.273 | 0.825 |
| 170000 | 0% | 100% | 15.50 | 8.09 | 0.299 | -0.936 | -0.744 | 0.301 | 0.790 |

## 排名与结论

- **相对最好**：`model_0152000.onnx` (succ=0%, fall=100%, hop=9.20, ttf=7.85s, comdev=0.251)
- **相对最差**：`model_0154000.onnx` (succ=0%, fall=100%, hop=27.30, ttf=6.65s, comdev=0.145)

### 前半 vs 后半 checkpoint

| 段 | succ | fall | hop | ttf | comdev |
|---|-----:|-----:|----:|----:|-------:|
| early (150000–158000) | 0% | 100% | 17.82 | 7.51 | 0.209 |
| late (160000–170000) | 0% | 100% | 15.77 | 7.75 | 0.225 |

### Top-5（综合排序）

1. `model_0152000` — succ=0% fall=100% hop=9.20 ttf=7.85 comdev=0.251
2. `model_0150000` — succ=0% fall=100% hop=9.50 ttf=8.12 comdev=0.290
3. `model_0164000` — succ=0% fall=100% hop=12.90 ttf=8.00 comdev=0.212
4. `model_0168000` — succ=0% fall=100% hop=14.10 ttf=8.42 comdev=0.296
5. `model_0170000` — succ=0% fall=100% hop=15.50 ttf=8.09 comdev=0.299

### 读数提示

- 本 sweep **成功率全为 0**：比较应看 **ttf / hop / comdev / xCoM**，不要只看 succ。
- 若全体很快摔倒，优先查 sim2sim 植物/obs 对齐与策略是否尚未学会单脚段，而非 checkpoint 细微差距。
- 完整逐动作结果见同目录 `sweep_results.json`。

