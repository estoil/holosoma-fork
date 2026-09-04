# Robust Top-5 MuJoCo 视频（修正版 true 20 ms）

## 视频设置

- 排名来自修正后的 true-20 ms、K=10全 checkpoint 稳定性报告。
- 每个 checkpoint 各录制一条 clean 和 noisy 视频，统一使用 seed 0。
- clean：无观测噪声、无观测延迟、无外力。
- noisy：29维关节速度逐关节、逐控制帧加入 `Uniform(-0.20,+0.20) rad/s`，并固定延迟一个50 Hz控制帧（20 ms）；无外力。
- 每条视频均为完整29.84秒、H.264、1280×720、25 fps、746帧。
- 地面棋盘材质、天空背景和灯光仅影响渲染，不改变物理参数。

## 视频索引

| 修正排名 | checkpoint | clean seed 0 | noisy seed 0 | noisy首次摔倒 | clean视频 | noisy视频 |
|---:|---:|---|---|---:|---|---|
| 1 | 196000 | 成功，无摔倒、无hop | 失败，摔倒、2次hop | 5.68 s | [clean](rank_01_step_0196000_clean_seed00.mp4) | [noisy](rank_01_step_0196000_noisy_seed00.mp4) |
| 2 | 252000 | 成功，无摔倒、无hop | 失败，摔倒、6次hop | 8.74 s | [clean](rank_02_step_0252000_clean_seed00.mp4) | [noisy](rank_02_step_0252000_noisy_seed00.mp4) |
| 3 | 182000 | 成功，无摔倒、无hop | 失败，摔倒、6次hop | 10.16 s | [clean](rank_03_step_0182000_clean_seed00.mp4) | [noisy](rank_03_step_0182000_noisy_seed00.mp4) |
| 4 | 228000 | 成功，无摔倒、无hop | 失败，摔倒、2次hop | 8.76 s | [clean](rank_04_step_0228000_clean_seed00.mp4) | [noisy](rank_04_step_0228000_noisy_seed00.mp4) |
| 5 | 206000 | 成功，无摔倒、无hop | 失败，摔倒、14次hop | 7.72 s | [clean](rank_05_step_0206000_clean_seed00.mp4) | [noisy](rank_05_step_0206000_noisy_seed00.mp4) |

> 视频是单个 seed 的可视化样本，正式成功率与排名仍应引用K=10或K=20量化报告。
