"""re-export for cli and one-off scripts."""

from .aas import aas_exec_plan, pk3_bsp_load_sort_key, run_deferred_aas_phase
from .compat import q3_compat
from .pk3 import convert_pk3

_deferred_aas_exec_plan = aas_exec_plan
