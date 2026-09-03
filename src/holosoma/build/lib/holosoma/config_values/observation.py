"""Default observation manager configurations."""

from holosoma.config_values.loco.g1.observation import g1_29dof_loco_single_wolinvel
from holosoma.config_values.loco.t1.observation import t1_29dof_loco_single_wolinvel
from holosoma.config_values.loco.x2.observation import x2_31dof_loco_single_wolinvel
from holosoma.config_values.wbt.g1.observation import g1_29dof_wbt_observation, g1_29dof_wbt_observation_w_object
from holosoma.config_values.wbt.x2.observation import x2_31dof_wbt_observation

none = None

DEFAULTS = {
    "none": none,
    "t1_29dof_loco_single_wolinvel": t1_29dof_loco_single_wolinvel,
    "g1_29dof_loco_single_wolinvel": g1_29dof_loco_single_wolinvel,
    "x2_31dof_loco_single_wolinvel": x2_31dof_loco_single_wolinvel,
    "g1_29dof_wbt": g1_29dof_wbt_observation,
    "g1_29dof_wbt_w_object": g1_29dof_wbt_observation_w_object,
    "x2_31dof_wbt": x2_31dof_wbt_observation,
}
