# ⚠️ 旧版视频：noisy 实际延迟约 0.5 ms

这些视频中的 noisy 标签写为 20 ms，但录像时旧实现实际只延迟了一个 2000 Hz 物理子步（约 0.5 ms）。clean 视频不受影响；noisy 视频不能作为 true-20 ms 结果使用。

# Robust Top-5 MuJoCo 视频索引

## 录像设置

- 完整动作时长：29.84 s（2 s 初始站立 + 2 s 进入动作 + 19.84 s 原动作 + 2 s 返回站姿 + 4 s 结束站立）
- 视频：H.264，1280×720，25 fps，746 帧
- clean：无观测噪声、无观测延迟
- noisy：关节速度观测均匀噪声 ±0.20 rad/s，延迟 20 ms
- 视频统一使用 seed 0，以保证模型间可直接比较；排名成功率来自每个条件 10 个种子的完整测试，而非单个录像。

## 视频

| 排名 | checkpoint | K=10 clean | K=10 noisy | seed 0 录像结果 | clean 视频 | noisy 视频 |
|---:|---:|---:|---:|---|---|---|
| 1 | 268000 | 100% | 90% | 两者成功、无摔倒、无 hop | [clean](rank_01_step_0268000_clean_seed00.mp4) | [noisy](rank_01_step_0268000_noisy_seed00.mp4) |
| 2 | 250000 | 100% | 90% | 两者成功、无摔倒、无 hop | [clean](rank_02_step_0250000_clean_seed00.mp4) | [noisy](rank_02_step_0250000_noisy_seed00.mp4) |
| 3 | 210000 | 100% | 80% | 两者成功、无摔倒、无 hop | [clean](rank_03_step_0210000_clean_seed00.mp4) | [noisy](rank_03_step_0210000_noisy_seed00.mp4) |
| 4 | 292000 | 100% | 80% | 两者成功、无摔倒、无 hop | [clean](rank_04_step_0292000_clean_seed00.mp4) | [noisy](rank_04_step_0292000_noisy_seed00.mp4) |
| 5 | 314000 | 100% | 80% | 两者成功、无摔倒、无 hop | [clean](rank_05_step_0314000_clean_seed00.mp4) | [noisy](rank_05_step_0314000_noisy_seed00.mp4) |

> seed 0 恰好是五个候选的成功样本。报告中应同时展示 K=10 成功率，避免把单次成功录像解读为 100% 鲁棒性。
