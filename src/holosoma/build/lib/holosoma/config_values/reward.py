"""Default reward manager configurations."""

from holosoma.config_values.loco.g1.reward import g1_29dof_loco, g1_29dof_loco_fast_sac
from holosoma.config_values.loco.t1.reward import t1_29dof_loco, t1_29dof_loco_fast_sac
from holosoma.config_values.loco.x2.reward import x2_31dof_loco, x2_31dof_loco_fast_sac
from holosoma.config_values.wbt.g1.reward import (
    g1_29dof_wbt_fast_sac_reward,
    g1_29dof_wbt_reward,
    g1_29dof_wbt_reward_w_object,
)
from holosoma.config_values.wbt.x2.reward import x2_31dof_wbt_fast_sac_reward, x2_31dof_wbt_reward

none = None

DEFAULTS = {
    "none": none,
    "t1_29dof_loco": t1_29dof_loco,
    "t1_29dof_loco_fast_sac": t1_29dof_loco_fast_sac,
    "g1_29dof_loco": g1_29dof_loco,
    "g1_29dof_loco_fast_sac": g1_29dof_loco_fast_sac,
    "x2_31dof_loco": x2_31dof_loco,
    "x2_31dof_loco_fast_sac": x2_31dof_loco_fast_sac,
    "g1_29dof_wbt": g1_29dof_wbt_reward,
    "g1_29dof_wbt_w_object": g1_29dof_wbt_reward_w_object,
    "g1_29dof_wbt_fast_sac": g1_29dof_wbt_fast_sac_reward,
    "x2_31dof_wbt": x2_31dof_wbt_reward,
    "x2_31dof_wbt_fast_sac": x2_31dof_wbt_fast_sac_reward,
}
