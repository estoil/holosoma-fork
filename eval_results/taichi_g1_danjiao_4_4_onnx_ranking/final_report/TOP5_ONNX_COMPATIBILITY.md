# Top-5 WBT ONNX 部署一致性检查

- 总结：**通过**

| step | ONNX | IO | 29 DoF | motion 992 | 末帧钳制 | iteration | 结果 |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 346000 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **✅** |
| 380000 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **✅** |
| 326000 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **✅** |
| 356000 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **✅** |
| 358000 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **✅** |

## 跨模型一致性

- ✅ `inputs`
- ✅ `outputs`
- ✅ `dof_names`
- ✅ `kp`
- ✅ `kd`
- ✅ `action_scale`
- ✅ `robot_urdf_digest`
- ✅ `experiment_config_digest`
- ✅ `reference_digest`

## 已确认接口

- 输入：`obs [1,463]`、`time_step [1,1]`。
- 输出：`actions [1,29]`、当前关节参考、参考位姿、左右脚支撑相位、5 帧 future support/cmd。
- 内嵌动作：992 帧；超过 991 的 timestep 会钳制到末帧。
- 五个模型的关节顺序、KP/KD、action scale、URDF、实验配置和内嵌动作逐项一致。

## 注意项

- ONNX 元数据没有 `dof_pos_lower/dof_pos_upper`；sim2sim 必须由 G1 robot config/XML 提供并核对关节限位。
- 此检查验证结构与静态数据一致性，不替代闭环 MuJoCo 稳定性测试。

机器可读结果：`top5_onnx_compatibility.json`。
