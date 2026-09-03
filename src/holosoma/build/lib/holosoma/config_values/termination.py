"""Default termination manager configurations."""

from holosoma.config_values.loco.g1.termination import g1_29dof_termination
from holosoma.config_values.loco.t1.termination import t1_29dof_termination
from holosoma.config_values.loco.x2.termination import x2_31dof_termination
from holosoma.config_values.wbt.g1.termination import g1_29dof_wbt_termination
from holosoma.config_values.wbt.x2.termination import x2_31dof_wbt_termination

none = None

DEFAULTS = {
    "none": none,
    "t1_29dof": t1_29dof_termination,
    "g1_29dof": g1_29dof_termination,
    "x2_31dof": x2_31dof_termination,
    "g1_29dof_wbt": g1_29dof_wbt_termination,
    "x2_31dof_wbt": x2_31dof_wbt_termination,
}
