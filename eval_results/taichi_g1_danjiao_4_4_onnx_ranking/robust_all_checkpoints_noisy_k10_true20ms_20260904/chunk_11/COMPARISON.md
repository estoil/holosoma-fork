# X2 WBT Checkpoint 对比 · steps 370000–390000

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
| 370000 | 0% | 100% | 16.70 | 6.63 | 0.318 | -0.825 | -0.767 | 0.397 | 1.004 |
| 372000 | 0% | 100% | 11.00 | 8.45 | 0.447 | -0.921 | -0.841 | 0.219 | 0.868 |
| 374000 | 0% | 100% | 6.70 | 8.59 | 0.240 | -0.913 | -0.863 | 0.163 | 0.696 |
| 376000 | 0% | 100% | 14.30 | 7.77 | 0.496 | -0.901 | -0.774 | 0.472 | 0.833 |
| 378000 | 0% | 100% | 10.20 | 7.61 | 0.273 | -0.752 | -0.704 | 0.253 | 0.797 |
| 380000 | 0% | 100% | 7.90 | 7.17 | 0.418 | -0.888 | -0.698 | 0.460 | 1.042 |
| 382000 | 0% | 100% | 7.70 | 8.19 | 0.218 | -0.867 | -0.862 | 0.205 | 0.762 |
| 384000 | 0% | 100% | 17.30 | 7.88 | 0.338 | -0.923 | -0.786 | 0.321 | 0.850 |
| 386000 | 0% | 100% | 18.00 | 8.15 | 0.368 | -0.968 | -0.888 | 0.345 | 0.913 |
| 388000 | 0% | 100% | 14.60 | 8.11 | 0.273 | -0.777 | -0.713 | 0.370 | 0.884 |
| 390000 | 0% | 100% | 17.90 | 6.40 | 0.211 | -0.860 | -0.714 | 0.308 | 0.920 |

## 排名与结论

- **相对最好**：`model_0374000.onnx` (succ=0%, fall=100%, hop=6.70, ttf=8.59s, comdev=0.240)
- **相对最差**：`model_0386000.onnx` (succ=0%, fall=100%, hop=18.00, ttf=8.15s, comdev=0.368)

### 前半 vs 后半 checkpoint

| 段 | succ | fall | hop | ttf | comdev |
|---|-----:|-----:|----:|----:|-------:|
| early (370000–378000) | 0% | 100% | 11.78 | 7.81 | 0.355 |
| late (380000–390000) | 0% | 100% | 13.90 | 7.65 | 0.304 |

### Top-5（综合排序）

1. `model_0374000` — succ=0% fall=100% hop=6.70 ttf=8.59 comdev=0.240
2. `model_0382000` — succ=0% fall=100% hop=7.70 ttf=8.19 comdev=0.218
3. `model_0380000` — succ=0% fall=100% hop=7.90 ttf=7.17 comdev=0.418
4. `model_0378000` — succ=0% fall=100% hop=10.20 ttf=7.61 comdev=0.273
5. `model_0372000` — succ=0% fall=100% hop=11.00 ttf=8.45 comdev=0.447

### 读数提示

- 本 sweep **成功率全为 0**：比较应看 **ttf / hop / comdev / xCoM**，不要只看 succ。
- 若全体很快摔倒，优先查 sim2sim 植物/obs 对齐与策略是否尚未学会单脚段，而非 checkpoint 细微差距。
- 完整逐动作结果见同目录 `sweep_results.json`。

