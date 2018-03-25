# This script functions similarly to scripts/kconfig/merge_config.sh from the
# kernel tree, merging multiple configurations fragments to produce a complete
# .config, with unspecified values filled in as for alldefconfig.
#
# The generated .config respects symbol dependencies, and a warning is printed
# if any symbol gets a different value from the assigned value.
#
# Here's a demo:
#
# Kconfig contents:
#
#     config FOO
#         bool "FOO"
#
#     config BAR
#         bool "BAR"
#
#     config BAZ
#         string "BAZ"
#
#     config QAZ
#         bool "QAZ" if n
#
#
# conf1 contents:
#
#     CONFIG_FOO=y
#
#
# conf2 contents:
#
#     CONFIG_BAR=y
#
#
# conf3 contents:
#
#     # Ops... assigned twice
#     # CONFIG_FOO is not set
#
#     # Ops... this symbol doesn't exist
#     CONFIG_OPS=y
#
#     CONFIG_BAZ="baz string"
#
#
# conf4 contents:
#
#     CONFIG_QAZ=y
#
#
# Running:
#
#     $ python(3) merge_config.py Kconfig merged conf1 conf2 conf3 conf4
#     conf3:2: warning: FOO (defined at Kconfig:1) set more than once. Old value: "y", new value: "n".
#     conf3:5: warning: attempt to assign the value "y" to the undefined symbol OPS
#     warning: QAZ (defined at Kconfig:10) was assigned the value "y" but got the value "n" -- check dependencies
#     $ cat merged
#     Generated by Kconfiglib (https://github.com/ulfalizer/Kconfiglib)
#     # CONFIG_FOO is not set
#     CONFIG_BAR=y
#     CONFIG_BAZ="baz string"
from kconfiglib import Kconfig, Symbol, BOOL, TRISTATE, TRI_TO_STR
import sys

if len(sys.argv) < 4:
    print("usage: merge_config.py Kconfig merged_config config1 [config2 ...]")
    sys.exit(1)

kconf = Kconfig(sys.argv[1])

# Enable warnings for assignments to undefined symbols
kconf.enable_undef_warnings()

# (This script uses alldefconfig as the base. Other starting states could be
# set up here as well. The approach in examples/allnoconfig_simpler.py could
# provide an allnoconfig starting state for example.)

# Create a merged configuration by loading the fragments with replace=False
for config in sys.argv[3:]:
    kconf.load_config(config, replace=False)

# Write the merged configuration
kconf.write_config(sys.argv[2])

# Print warnings for symbols whose actual value doesn't match the assigned
# value

def name_and_loc(sym):
    # Helper for printing symbol names and Kconfig file location(s) in warnings

    if not sym.nodes:
        return sym.name + " (undefined)"

    return "{} (defined at {})".format(
        sym.name,
        ", ".join("{}:{}".format(node.filename, node.linenr)
                  for node in sym.nodes))

for sym in kconf.defined_syms:
    # Was the symbol assigned to?
    if sym.user_value is not None:
        # Tristate values are represented as 0, 1, 2. Having them as
        # "n", "m", "y" is more convenient here, so convert.
        if sym.type in (BOOL, TRISTATE):
            user_value = TRI_TO_STR[sym.user_value]
        else:
            user_value = sym.user_value

        if user_value != sym.str_value:
            print('warning: {} was assigned the value "{}" but got the '
                  'value "{}" -- check dependencies'
                  .format(name_and_loc(sym), user_value, sym.str_value))
