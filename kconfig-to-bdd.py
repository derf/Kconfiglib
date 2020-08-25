#!/usr/bin/env python3

import kconfiglib
import re
import sys

cudd = True

if cudd:
    from dd.cudd import BDD
else:
    from dd.autoref import BDD


def handle_symbol(symbol, name=None, is_mandatory=False):
    depends_on = kconfiglib.expr_str(symbol.direct_dep)

    if name is None:
        name = symbol.name

    choices = list()

    for match in re.finditer(r"<choice ([^>]+)>", depends_on):
        choices.append(match.group(1))

    for choice in choices:
        depends_on = re.sub(f"<choice {choice}>", f"_choice_{choice}", depends_on)

    depends_on = re.sub("&& <([^>]+)>", "", depends_on)

    if depends_on == "n":
        return (f"# undefined symbol {name}", None)

    if depends_on == "y":
        return (name, f"# yes symbol {name}")

    sym_type = kconfiglib.TYPE_TO_STR[symbol.type]

    if sym_type != "bool":
        return (f"# non-bool symbol {name}", None)

    depends_on = re.sub("&&", "&", depends_on)
    depends_on = re.sub("\|\|", "|", depends_on)

    # Wie diese Bedingung formuliert ist (A -> B, !A | B, B | !A) hat
    # keinen Einfluss auf die BDD-Struktur
    if is_mandatory:
        return (name, f"{name} <-> ({depends_on})")
    else:
        return (name, f"{name} -> ({depends_on})")


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
        var_name = f"_choice_{choice.name}"
        print(choice.__repr__(), choice.is_optional)
        _, expr = handle_symbol(
            choice, name=var_name, is_mandatory=not choice.is_optional
        )
        if expr:
            pre_expressions.append(expr)
        pre_variables.append(var_name)
        symbols = map(lambda sym: sym.name, choice.syms)
        symbols_xor = " ^ ".join(symbols)
        pre_expressions.append(f"{var_name} <-> ({symbols_xor})")

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

    constraint = bdd.add_expr(constraint)

    if cudd:
        # Egal?
        print("Reordering ...")
        BDD.reorder(bdd)

    else:
        # Wichtig! Lesbarkeit++ falls gedumpt wird, Performance vermutlich auch.
        print("Collecting Garbage ...")
        bdd.collect_garbage()

        print("Dumping to /tmp/bdd.pdf ...")
        bdd.dump("/tmp/bdd.pdf")

    print("Solving ...")

    i = 0
    for solution in bdd.pick_iter(constraint, care_vars=variables):
        i += 1
        # print(solution)
        continue
        with open(f".config.{i}", "w") as f:
            for k, v in solution.items():
                if v:
                    print(f"CONFIG_{k}=y", file=f)
                else:
                    print(f"# CONFIG_{k} is not set", file=f)

    print(f"Found {i} solutions")


if __name__ == "__main__":
    main()
