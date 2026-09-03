# X2 WBT Checkpoint 对比 · steps 182000–182000

## 评测设置

- **Run**: `holosoma/eval_results/taichi_g1_danjiao_4_4_onnx_ranking/robust_candidates_final/models`
- **Robot**: `/home/wxy/taichi_deploy/holosoma/src/holosoma/holosoma/data/robots/g1/g1_29dof.xml`
- **Motion dir**: `/home/wxy/taichi_deploy/holosoma/motions_from_web`
- **Motions** (1): `taichi_g1_danjiao_4_4_holosoma`
- **Seeds (K)**: [0, 1, 2, 3, 4]
- **Condition**: `clean`
- **Mode**: policy ONNX × npz reference (`use_npz_ref=True`)
- **Foot support rect (from X2 spheres)**: AP=`[-0.05, 0.12]`, ML=`[-0.0275, 0.0275]`
- **Wall time**: 37s

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
| 182000 | 20% | 0% | 1.40 | 19.84 | 0.115 | -0.173 | -0.109 | 0.147 | 0.240 |

## 排名与结论

- **相对最好**：`model_0182000.onnx` (succ=20%, fall=0%, hop=1.40, ttf=19.84s, comdev=0.115)
- **相对最差**：`model_0182000.onnx` (succ=20%, fall=0%, hop=1.40, ttf=19.84s, comdev=0.115)

### 前半 vs 后半 checkpoint

| 段 | succ | fall | hop | ttf | comdev |
|---|-----:|-----:|----:|----:|-------:|
| early (182000–182000) | 20% | 0% | 1.40 | 19.84 | 0.115 |
| late (182000–182000) | 20% | 0% | 1.40 | 19.84 | 0.115 |

### Top-5（综合排序）

1. `model_0182000` — succ=20% fall=0% hop=1.40 ttf=19.84 comdev=0.115

### 读数提示

- 有成功试验时以 **succ + hop 尾部** 为主；comdev 看是否跟上参考平衡意图。
- 完整逐动作结果见同目录 `sweep_results.json`。

