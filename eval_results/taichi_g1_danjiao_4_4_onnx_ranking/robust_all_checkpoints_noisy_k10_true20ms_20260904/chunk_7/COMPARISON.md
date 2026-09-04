# X2 WBT Checkpoint 对比 · steps 282000–302000

## 评测设置

- **Run**: `/home/wxy/taichi_deploy/holosoma/logs/WholeBodyTracking/20260903_100921-g1_29dof_wbt_fast_sac_robust_manager-locomotion`
- **Robot**: `/home/wxy/taichi_deploy/holosoma/src/holosoma/holosoma/data/robots/g1/g1_29dof.xml`
- **Motion dir**: `/home/wxy/taichi_deploy/holosoma/eval_results/taichi_g1_danjiao_4_4_onnx_ranking/robust_all_checkpoints_clean_noisy_k10_20260904/_motions`
- **Motions** (1): `taichi_g1_danjiao_4_4_robust_augmented`
- **Seeds (K)**: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
- **Condition**: `noisy`
- **Mode**: policy ONNX × npz reference (`use_npz_ref=True`)
- **Foot support rect (from X2 spheres)**: AP=`[-0.05, 0.12]`, ML=`[-0.0275, 0.0275]`
- **Wall time**: 651s

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
| 282000 | 0% | 100% | 5.90 | 6.90 | 0.345 | -0.688 | -0.572 | 0.512 | 0.809 |
| 284000 | 0% | 100% | 15.80 | 7.48 | 0.402 | -0.752 | -0.651 | 0.514 | 0.807 |
| 286000 | 0% | 100% | 10.70 | 8.00 | 0.303 | -0.795 | -0.751 | 0.289 | 0.739 |
| 288000 | 0% | 100% | 19.60 | 6.51 | 0.287 | -0.935 | -0.801 | 0.539 | 0.821 |
| 290000 | 0% | 100% | 17.90 | 8.51 | 0.323 | -0.824 | -0.754 | 0.218 | 0.760 |
| 292000 | 0% | 100% | 22.20 | 7.70 | 0.327 | -1.022 | -0.709 | 0.385 | 0.920 |
| 294000 | 0% | 100% | 14.60 | 6.17 | 0.302 | -0.794 | -0.718 | 0.467 | 1.026 |
| 296000 | 0% | 100% | 13.40 | 8.29 | 0.334 | -0.806 | -0.800 | 0.365 | 0.743 |
| 298000 | 0% | 100% | 13.80 | 8.98 | 0.214 | -0.869 | -0.716 | 0.373 | 0.640 |
| 300000 | 0% | 100% | 9.80 | 7.64 | 0.216 | -0.848 | -0.860 | 0.297 | 0.788 |
| 302000 | 0% | 100% | 14.30 | 7.08 | 0.136 | -0.769 | -0.742 | 0.259 | 0.804 |

## 排名与结论

- **相对最好**：`model_0282000.onnx` (succ=0%, fall=100%, hop=5.90, ttf=6.90s, comdev=0.345)
- **相对最差**：`model_0292000.onnx` (succ=0%, fall=100%, hop=22.20, ttf=7.70s, comdev=0.327)

### 前半 vs 后半 checkpoint

| 段 | succ | fall | hop | ttf | comdev |
|---|-----:|-----:|----:|----:|-------:|
| early (282000–290000) | 0% | 100% | 13.98 | 7.48 | 0.332 |
| late (292000–302000) | 0% | 100% | 14.68 | 7.64 | 0.255 |

### Top-5（综合排序）

1. `model_0282000` — succ=0% fall=100% hop=5.90 ttf=6.90 comdev=0.345
2. `model_0300000` — succ=0% fall=100% hop=9.80 ttf=7.64 comdev=0.216
3. `model_0286000` — succ=0% fall=100% hop=10.70 ttf=8.00 comdev=0.303
4. `model_0296000` — succ=0% fall=100% hop=13.40 ttf=8.29 comdev=0.334
5. `model_0298000` — succ=0% fall=100% hop=13.80 ttf=8.98 comdev=0.214

### 读数提示

- 本 sweep **成功率全为 0**：比较应看 **ttf / hop / comdev / xCoM**，不要只看 succ。
- 若全体很快摔倒，优先查 sim2sim 植物/obs 对齐与策略是否尚未学会单脚段，而非 checkpoint 细微差距。
- 完整逐动作结果见同目录 `sweep_results.json`。

