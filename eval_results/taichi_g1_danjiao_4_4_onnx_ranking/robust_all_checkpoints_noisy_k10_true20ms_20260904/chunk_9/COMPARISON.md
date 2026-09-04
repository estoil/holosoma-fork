# X2 WBT Checkpoint 对比 · steps 326000–346000

## 评测设置

- **Run**: `/home/wxy/taichi_deploy/holosoma/logs/WholeBodyTracking/20260903_100921-g1_29dof_wbt_fast_sac_robust_manager-locomotion`
- **Robot**: `/home/wxy/taichi_deploy/holosoma/src/holosoma/holosoma/data/robots/g1/g1_29dof.xml`
- **Motion dir**: `/home/wxy/taichi_deploy/holosoma/eval_results/taichi_g1_danjiao_4_4_onnx_ranking/robust_all_checkpoints_clean_noisy_k10_20260904/_motions`
- **Motions** (1): `taichi_g1_danjiao_4_4_robust_augmented`
- **Seeds (K)**: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
- **Condition**: `noisy`
- **Mode**: policy ONNX × npz reference (`use_npz_ref=True`)
- **Foot support rect (from X2 spheres)**: AP=`[-0.05, 0.12]`, ML=`[-0.0275, 0.0275]`
- **Wall time**: 627s

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
| 326000 | 0% | 100% | 18.30 | 8.35 | 0.257 | -0.871 | -0.719 | 0.419 | 1.056 |
| 328000 | 0% | 100% | 14.60 | 7.44 | 0.347 | -0.813 | -0.839 | 0.247 | 0.736 |
| 330000 | 0% | 100% | 15.60 | 7.51 | 0.182 | -0.784 | -0.717 | 0.311 | 0.777 |
| 332000 | 0% | 100% | 18.30 | 7.18 | 0.223 | -0.794 | -0.772 | 0.300 | 0.872 |
| 334000 | 0% | 100% | 29.20 | 6.93 | 0.255 | -0.985 | -0.808 | 0.739 | 0.863 |
| 336000 | 0% | 100% | 19.50 | 6.05 | 0.281 | -0.866 | -0.659 | 0.495 | 0.895 |
| 338000 | 0% | 100% | 16.50 | 6.35 | 0.260 | -0.755 | -0.636 | 0.406 | 0.934 |
| 340000 | 0% | 100% | 18.90 | 7.49 | 0.279 | -0.874 | -0.765 | 0.535 | 0.907 |
| 342000 | 0% | 100% | 17.40 | 7.26 | 0.186 | -0.830 | -0.693 | 0.253 | 0.651 |
| 344000 | 0% | 100% | 13.10 | 7.60 | 0.241 | -0.872 | -0.791 | 0.262 | 0.745 |
| 346000 | 0% | 100% | 16.90 | 7.27 | 0.356 | -0.826 | -0.881 | 0.598 | 0.814 |

## 排名与结论

- **相对最好**：`model_0344000.onnx` (succ=0%, fall=100%, hop=13.10, ttf=7.60s, comdev=0.241)
- **相对最差**：`model_0334000.onnx` (succ=0%, fall=100%, hop=29.20, ttf=6.93s, comdev=0.255)

### 前半 vs 后半 checkpoint

| 段 | succ | fall | hop | ttf | comdev |
|---|-----:|-----:|----:|----:|-------:|
| early (326000–334000) | 0% | 100% | 19.20 | 7.48 | 0.253 |
| late (336000–346000) | 0% | 100% | 17.05 | 7.00 | 0.267 |

### Top-5（综合排序）

1. `model_0344000` — succ=0% fall=100% hop=13.10 ttf=7.60 comdev=0.241
2. `model_0328000` — succ=0% fall=100% hop=14.60 ttf=7.44 comdev=0.347
3. `model_0330000` — succ=0% fall=100% hop=15.60 ttf=7.51 comdev=0.182
4. `model_0338000` — succ=0% fall=100% hop=16.50 ttf=6.35 comdev=0.260
5. `model_0346000` — succ=0% fall=100% hop=16.90 ttf=7.27 comdev=0.356

### 读数提示

- 本 sweep **成功率全为 0**：比较应看 **ttf / hop / comdev / xCoM**，不要只看 succ。
- 若全体很快摔倒，优先查 sim2sim 植物/obs 对齐与策略是否尚未学会单脚段，而非 checkpoint 细微差距。
- 完整逐动作结果见同目录 `sweep_results.json`。

