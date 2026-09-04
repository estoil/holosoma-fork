# X2 WBT Checkpoint 对比 · steps 194000–214000

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
| 194000 | 0% | 100% | 20.30 | 6.75 | 0.283 | -0.780 | -0.708 | 0.216 | 0.809 |
| 196000 | 0% | 100% | 1.80 | 5.85 | 0.379 | -0.722 | -0.631 | 0.114 | 0.945 |
| 198000 | 0% | 100% | 18.70 | 6.22 | 0.346 | -0.707 | -0.689 | 0.249 | 0.882 |
| 200000 | 0% | 100% | 11.70 | 6.54 | 0.352 | -0.830 | -0.737 | 0.265 | 0.847 |
| 202000 | 0% | 100% | 14.00 | 7.51 | 0.226 | -0.975 | -0.806 | 0.226 | 0.809 |
| 204000 | 0% | 100% | 14.50 | 8.56 | 0.279 | -0.834 | -0.642 | 0.436 | 0.614 |
| 206000 | 0% | 100% | 5.00 | 7.12 | 0.326 | -0.907 | -0.680 | 0.193 | 0.748 |
| 208000 | 0% | 100% | 7.50 | 8.92 | 0.165 | -0.828 | -0.700 | 0.166 | 0.719 |
| 210000 | 0% | 100% | 10.40 | 7.77 | 0.197 | -0.913 | -0.689 | 0.247 | 0.715 |
| 212000 | 0% | 100% | 15.00 | 8.05 | 0.150 | -0.923 | -0.718 | 0.132 | 0.695 |
| 214000 | 0% | 100% | 9.40 | 9.57 | 0.269 | -0.765 | -0.825 | 0.198 | 0.771 |

## 排名与结论

- **相对最好**：`model_0196000.onnx` (succ=0%, fall=100%, hop=1.80, ttf=5.85s, comdev=0.379)
- **相对最差**：`model_0194000.onnx` (succ=0%, fall=100%, hop=20.30, ttf=6.75s, comdev=0.283)

### 前半 vs 后半 checkpoint

| 段 | succ | fall | hop | ttf | comdev |
|---|-----:|-----:|----:|----:|-------:|
| early (194000–202000) | 0% | 100% | 13.30 | 6.57 | 0.317 |
| late (204000–214000) | 0% | 100% | 10.30 | 8.33 | 0.231 |

### Top-5（综合排序）

1. `model_0196000` — succ=0% fall=100% hop=1.80 ttf=5.85 comdev=0.379
2. `model_0206000` — succ=0% fall=100% hop=5.00 ttf=7.12 comdev=0.326
3. `model_0208000` — succ=0% fall=100% hop=7.50 ttf=8.92 comdev=0.165
4. `model_0214000` — succ=0% fall=100% hop=9.40 ttf=9.57 comdev=0.269
5. `model_0210000` — succ=0% fall=100% hop=10.40 ttf=7.77 comdev=0.197

### 读数提示

- 本 sweep **成功率全为 0**：比较应看 **ttf / hop / comdev / xCoM**，不要只看 succ。
- 若全体很快摔倒，优先查 sim2sim 植物/obs 对齐与策略是否尚未学会单脚段，而非 checkpoint 细微差距。
- 完整逐动作结果见同目录 `sweep_results.json`。

