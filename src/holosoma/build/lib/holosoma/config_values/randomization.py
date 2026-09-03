"""Default randomization manager configurations."""

from holosoma.config_values.loco.g1.randomization import g1_29dof_randomization
from holosoma.config_values.loco.t1.randomization import t1_29dof_randomization
from holosoma.config_values.loco.x2.randomization import x2_31dof_randomization
from holosoma.config_values.wbt.g1.randomization import g1_29dof_wbt_randomization, g1_29dof_wbt_randomization_w_object
from holosoma.config_values.wbt.x2.randomization import x2_31dof_wbt_randomization

none = None

DEFAULTS = {
    "none": none,
    "t1_29dof": t1_29dof_randomization,
    "g1_29dof": g1_29dof_randomization,
    "x2_31dof": x2_31dof_randomization,
    "g1_29dof_wbt": g1_29dof_wbt_randomization,
    "g1_29dof_wbt_w_object": g1_29dof_wbt_randomization_w_object,
    "x2_31dof_wbt": x2_31dof_wbt_randomization,
}
