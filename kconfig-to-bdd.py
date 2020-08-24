#!/usr/bin/env python3

import kconfiglib
import re
import sys
from dd.cudd import BDD


def handle_symbol(symbol):
    depends_on = kconfiglib.expr_str(symbol.direct_dep)

    choices = list()

    for match in re.finditer(r"<choice ([^>]+)>", depends_on):
        choices.append(match.group(1))

    for choice in choices:
        depends_on = re.sub(f"<choice {choice}>", f"_choice_{choice}", depends_on)

    depends_on = re.sub("&& <([^>]+)>", "", depends_on)

    if depends_on == "n":
        return (f"# undefined symbol {symbol.name}", None)

    if depends_on == "y":
        return (symbol.name, f"# yes symbol {symbol.name}")

    sym_type = kconfiglib.TYPE_TO_STR[symbol.type]

    if sym_type != "bool":
        return (f"# non-bool symbol {symbol.name}", None)

    depends_on = re.sub("&&", "&", depends_on)
    depends_on = re.sub("\|\|", "|", depends_on)

    return (symbol.name, f"{symbol.name} -> ({depends_on})")


def main():
    kconf = kconfiglib.standard_kconfig(__doc__)

    kconf.warn = False

    pre_variables = list()
    pre_expressions = list()

    for symbol in kconf.syms.values():
        var, expr = handle_symbol(symbol)
        if var is not None:
            pre_variables.append(var)
        if expr is not None:
            pre_expressions.append(expr)

    for choice in kconf.choices:
        pre_variables.append(f"_choice_{choice.name}")
        symbols = map(lambda sym: sym.name, choice.syms)
        symbols_xor = " ^ ".join(symbols)
        pre_expressions.append(f"_choice_{choice.name} <-> ({symbols_xor})")

    print()
    print("Variables:")
    print("\n".join(pre_variables))
    print()
    print("Expressions:")
    print("\n".join(pre_expressions))
    print()

    variables = list()
    expressions = list()

    bdd = BDD()
    variable_count = 0
    for variable in pre_variables:
        if variable[0] != "#":
            variables.append(variable)
            print(variable)
            variable_count += 1
            bdd.declare(variable)
    print(f"Got {variable_count} variables")

    constraint = "True"
    expression_count = 0
    for expression in pre_expressions:
        if expression[0] != "#":
            expressions.append(expression)
            expression_count += 1
            constraint += f" & ({expression})"
    print(f"Got {expression_count} rules")
    print(f"Constraint: {constraint}")

    constraint = bdd.add_expr(constraint)

    print("Solving ...")

    i = 0
    for solution in bdd.pick_iter(constraint, care_vars=variables):
        i += 1
        with open(f".config.{i}", "w") as sys.stdout:
            for k, v in solution.items():
                if v:
                    print(f"CONFIG_{k}=y")
                else:
                    print(f"# CONFIG_{k} is not set")


if __name__ == "__main__":
    main()
