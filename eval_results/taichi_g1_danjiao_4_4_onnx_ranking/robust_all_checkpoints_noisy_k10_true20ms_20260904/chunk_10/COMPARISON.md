# X2 WBT Checkpoint 对比 · steps 348000–368000

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
| 348000 | 0% | 100% | 12.80 | 8.54 | 0.437 | -0.869 | -0.717 | 0.238 | 0.732 |
| 350000 | 0% | 100% | 25.70 | 7.33 | 0.388 | -0.969 | -0.948 | 0.411 | 1.423 |
| 352000 | 0% | 100% | 16.60 | 7.47 | 0.288 | -0.961 | -0.881 | 0.268 | 1.019 |
| 354000 | 0% | 100% | 18.10 | 7.64 | 0.316 | -0.986 | -1.022 | 0.371 | 0.859 |
| 356000 | 0% | 100% | 7.00 | 9.04 | 0.360 | -0.767 | -0.766 | 0.360 | 0.760 |
| 358000 | 0% | 100% | 13.10 | 7.94 | 0.383 | -0.896 | -0.800 | 0.337 | 0.917 |
| 360000 | 0% | 100% | 18.20 | 8.98 | 0.375 | -0.920 | -0.906 | 0.302 | 0.779 |
| 362000 | 0% | 100% | 19.30 | 9.12 | 0.339 | -0.892 | -0.749 | 0.319 | 0.861 |
| 364000 | 0% | 100% | 18.60 | 8.94 | 0.276 | -0.968 | -0.832 | 0.258 | 0.762 |
| 366000 | 0% | 100% | 22.90 | 6.53 | 0.286 | -0.831 | -0.750 | 0.399 | 1.118 |
| 368000 | 0% | 100% | 14.30 | 8.25 | 0.263 | -0.817 | -0.832 | 0.328 | 0.873 |

## 排名与结论

- **相对最好**：`model_0356000.onnx` (succ=0%, fall=100%, hop=7.00, ttf=9.04s, comdev=0.360)
- **相对最差**：`model_0350000.onnx` (succ=0%, fall=100%, hop=25.70, ttf=7.33s, comdev=0.388)

### 前半 vs 后半 checkpoint

| 段 | succ | fall | hop | ttf | comdev |
|---|-----:|-----:|----:|----:|-------:|
| early (348000–356000) | 0% | 100% | 16.04 | 8.00 | 0.358 |
| late (358000–368000) | 0% | 100% | 17.73 | 8.29 | 0.320 |

### Top-5（综合排序）

1. `model_0356000` — succ=0% fall=100% hop=7.00 ttf=9.04 comdev=0.360
2. `model_0348000` — succ=0% fall=100% hop=12.80 ttf=8.54 comdev=0.437
3. `model_0358000` — succ=0% fall=100% hop=13.10 ttf=7.94 comdev=0.383
4. `model_0368000` — succ=0% fall=100% hop=14.30 ttf=8.25 comdev=0.263
5. `model_0352000` — succ=0% fall=100% hop=16.60 ttf=7.47 comdev=0.288

### 读数提示

- 本 sweep **成功率全为 0**：比较应看 **ttf / hop / comdev / xCoM**，不要只看 succ。
- 若全体很快摔倒，优先查 sim2sim 植物/obs 对齐与策略是否尚未学会单脚段，而非 checkpoint 细微差距。
- 完整逐动作结果见同目录 `sweep_results.json`。

