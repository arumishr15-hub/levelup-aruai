"""Question templates. Each one builds a fresh, randomized snippet.

A template returns the code plus *likely wrong answers*, each tagged with the
misconception that leads to it, so the Teacher can explain a wrong pick.
The correct answer is never written here: the Question Agent runs the code.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable

WORDS = ["python", "rocket", "galaxy", "pixel", "dragon", "banana", "planet", "wizard"]
NAMES = ["Aru", "Mia", "Leo", "Zoe", "Kai", "Ivy"]
FRUITS = ["apple", "mango", "kiwi", "grape", "lemon", "peach"]


@dataclass(frozen=True)
class Template:
    key: str
    topic: str
    level: int
    concept: str
    build: Callable[[random.Random], dict]


TEMPLATES: list[Template] = []


def template(key: str, topic: str, level: int, concept: str):
    def deco(fn):
        TEMPLATES.append(Template(key, topic, level, concept, fn))
        return fn
    return deco


# ---------------------------------------------------------------- variables
@template("var_reassign", "variables", 1, "assignment")
def _(r):
    a, b = r.randint(2, 9), r.randint(2, 9)
    return {
        "code": f"a = {a}\nb = {b}\na = a + b\nprint(a)",
        "wrong": [(str(a), "a keeps its first value forever"),
                  (str(b), "mixing up which variable gets the new value"),
                  ("a + b", "thinking print shows the formula, not the result")],
        "hint": "The right side is worked out first, then stored in the name on the left.",
        "why": f"`a + b` is {a} + {b} = {a + b}, and that new value replaces the old `a`.",
    }


@template("var_swap", "variables", 2, "tuple_swap")
def _(r):
    x, y = r.sample(range(1, 20), 2)
    return {
        "code": f"a, b = {x}, {y}\na, b = b, a\nprint(a, b)",
        "wrong": [(f"{x} {y}", "the swap line does nothing"),
                  (f"{y} {y}", "a is overwritten before b reads it"),
                  (f"({y}, {x})", "print shows a tuple when given two values")],
        "hint": "Python builds the whole right-hand side `(b, a)` before assigning anything.",
        "why": f"The right side becomes ({y}, {x}) first, then unpacks into a and b, so they swap.",
    }


@template("var_augmented", "variables", 3, "augmented_assignment")
def _(r):
    n, k, m, j = r.randint(2, 6), r.randint(1, 5), r.randint(2, 3), r.randint(1, 4)
    return {
        "code": f"x = {n}\nx += {k}\nx *= {m}\nx -= {j}\nprint(x)",
        "wrong": [(str(n + k * m - j), "doing the steps with maths precedence instead of top to bottom"),
                  (str((n + k) * m), "forgetting the last line"),
                  (str(n), "thinking += makes a copy and leaves x alone")],
        "hint": "Run each line in order. `x += 3` means `x = x + 3`.",
        "why": f"{n} → +{k} = {n + k} → ×{m} = {(n + k) * m} → −{j} = {(n + k) * m - j}.",
    }


# ---------------------------------------------------------------- strings
@template("str_index", "strings", 1, "indexing")
def _(r):
    w = r.choice(WORDS)
    i = r.randint(1, len(w) - 2)
    return {
        "code": f's = "{w}"\nprint(s[{i}])',
        "wrong": [(w[i - 1], "counting from 1 instead of 0"),
                  (w[i + 1], "skipping one letter"),
                  (w[:i], "thinking [i] gives everything before it"),
                  (w[i:i + 2], "thinking [i] grabs two characters"),
                  (w[-1 - i], "counting from the end instead of the start")],
        "hint": "The first character is at index 0.",
        "why": f"Counting from 0 in \"{w}\": index {i} is '{w[i]}'.",
    }


@template("str_slice", "strings", 2, "slicing")
def _(r):
    w = r.choice(WORDS)
    a = r.randint(0, 2)
    b = r.randint(a + 2, len(w) - 1)
    return {
        "code": f's = "{w}"\nprint(s[{a}:{b}])',
        "wrong": [(w[a:b + 1], "thinking the end index is included"),
                  (w[a + 1:b + 1], "counting from 1 instead of 0"),
                  (w[a:], "ignoring the stop number"),
                  (w[a:b - 1], "stopping one character too early"),
                  (w[a + 1:b], "skipping the start character")],
        "hint": "A slice [start:stop] includes start but stops *before* stop.",
        "why": f"Indexes {a} up to (not including) {b} give '{w[a:b]}'.",
    }


@template("str_methods", "strings", 3, "string_methods")
def _(r):
    w = r.choice(WORDS)
    return {
        "code": f's = "{w}"\nt = s.upper()[::-1]\nprint(t)',
        "wrong": [(w.upper(), "thinking [::-1] does nothing"),
                  (w[::-1], "thinking upper() changes nothing"),
                  (w[::-1].capitalize(), "mixing up upper() with capitalize()")],
        "hint": "Work left to right: first .upper(), then [::-1] reverses it.",
        "why": f"\"{w}\".upper() is '{w.upper()}', and [::-1] reverses it to '{w.upper()[::-1]}'.",
    }


# ---------------------------------------------------------------- lists
@template("list_negative", "lists", 1, "list_indexing")
def _(r):
    nums = r.sample(range(1, 30), 5)
    return {
        "code": f"nums = {nums}\nprint(nums[-1] + nums[0])",
        "wrong": [(str(nums[-2] + nums[0]), "thinking -1 is the second-to-last item"),
                  (str(nums[0] + nums[1]), "thinking -1 means 'one after the start'"),
                  ("IndexError", "thinking negative indexes are not allowed")],
        "hint": "nums[-1] counts from the end: it is the last item.",
        "why": f"nums[-1] is {nums[-1]} (last) and nums[0] is {nums[0]} (first): {nums[-1] + nums[0]}.",
    }


@template("list_mutate", "lists", 2, "list_methods")
def _(r):
    nums = r.sample(range(1, 10), 3)
    x = r.randint(10, 20)
    after = nums + [x]
    after.pop(0)
    return {
        "code": f"nums = {nums}\nnums.append({x})\nnums.pop(0)\nprint(nums)",
        "wrong": [(str(nums + [x]), "thinking pop(0) only reads the item"),
                  (str((nums + [x])[:-1]), "thinking pop(0) removes the last item"),
                  (str([x] + nums[1:]), "thinking append adds to the front")],
        "hint": "append adds to the END; pop(0) removes the item at index 0.",
        "why": f"After append: {nums + [x]}. pop(0) takes away {nums[0]}, leaving {after}.",
    }


@template("list_comprehension", "lists", 3, "comprehensions")
def _(r):
    nums = r.sample(range(1, 13), 6)
    k = r.randint(2, 4)
    right = [n * k for n in nums if n % 2 == 0]
    return {
        "code": f"nums = {nums}\nresult = [n * {k} for n in nums if n % 2 == 0]\nprint(result)",
        "wrong": [(str([n * k for n in nums if n % 2 == 1]), "mixing up even and odd"),
                  (str([n * k for n in nums]), "ignoring the if filter"),
                  (str([n for n in nums if n % 2 == 0]), "forgetting the multiply part")],
        "hint": "Read it as: for each n in nums, keep it if even, then put n * k in the new list.",
        "why": f"Even numbers are {[n for n in nums if n % 2 == 0]}; each times {k} gives {right}.",
    }


# ---------------------------------------------------------------- loops
@template("loop_range_sum", "loops", 1, "for_range")
def _(r):
    n = r.randint(3, 7)
    return {
        "code": f"total = 0\nfor i in range({n}):\n    total += i\nprint(total)",
        "wrong": [(str(sum(range(n + 1))), "thinking range(n) includes n"),
                  (str(n - 1), "thinking total only keeps the last i"),
                  (str(n), "thinking total counts the loops")],
        "hint": f"range({n}) gives 0, 1, ..., {n - 1}. It never includes {n}.",
        "why": f"0 + 1 + ... + {n - 1} = {sum(range(n))}.",
    }


@template("loop_while", "loops", 2, "while_loop")
def _(r):
    start, step = r.randint(1, 3), r.randint(2, 4)
    limit = r.randint(12, 25)
    count, x = 0, start
    while x < limit:
        x += step
        count += 1
    return {
        "code": f"x = {start}\ncount = 0\nwhile x < {limit}:\n    x += {step}\n    count += 1\nprint(x, count)",
        "wrong": [(f"{x - step} {count - 1}", "stopping one loop early"),
                  (f"{x + step} {count + 1}", "running one extra loop"),
                  (f"{limit} {count}", "thinking x lands exactly on the limit"),
                  (f"{x} {count + 1}", "counting the final check as a loop"),
                  (f"{start} {count}", "thinking x is reset after the loop")],
        "hint": "The condition is checked before each loop. Track x and count on paper.",
        "why": f"x grows by {step} until it is no longer < {limit}: it ends at {x} after {count} loops.",
    }


@template("loop_nested", "loops", 3, "nested_loops")
def _(r):
    a, b = r.randint(2, 4), r.randint(2, 4)
    return {
        "code": f"count = 0\nfor i in range({a}):\n    for j in range({b}):\n        count += 1\nprint(count)",
        "wrong": [(str(a + b), "adding the loops instead of multiplying"),
                  (str(b), "thinking the outer loop runs once"),
                  (str((a + 1) * (b + 1)), "thinking range includes its end")],
        "hint": "The inner loop runs completely for every turn of the outer loop.",
        "why": f"{a} outer turns × {b} inner turns = {a * b} increments.",
    }


# ---------------------------------------------------------------- conditionals
@template("if_else", "conditionals", 1, "if_else")
def _(r):
    x, k = r.randint(1, 20), r.randint(5, 15)
    return {
        "code": f'x = {x}\nif x > {k}:\n    print("big")\nelse:\n    print("small")',
        "wrong": [("big" if x <= k else "small", "reading the comparison backwards"),
                  ("big\nsmall", "thinking both branches run"),
                  ("True", "thinking print shows the condition")],
        "hint": f"Is {x} > {k}? Only one branch runs.",
        "why": f"{x} > {k} is {x > k}, so the {'if' if x > k else 'else'} branch runs.",
    }


@template("if_elif", "conditionals", 2, "elif_chain")
def _(r):
    score = r.randint(40, 100)
    grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D"
    others = [g for g in "ABCD" if g != grade]
    return {
        "code": (f"score = {score}\nif score >= 90:\n    print(\"A\")\nelif score >= 75:\n"
                 f"    print(\"B\")\nelif score >= 60:\n    print(\"C\")\nelse:\n    print(\"D\")"),
        "wrong": [(others[0], "checking the conditions in the wrong order"),
                  (others[1], "misreading >= as >"),
                  (others[2], "thinking the last true condition wins")],
        "hint": "Python checks from the top and stops at the FIRST condition that is True.",
        "why": f"With score {score}, the first true check gives '{grade}'.",
    }


@template("bool_logic", "conditionals", 3, "boolean_logic")
def _(r):
    a, b = r.randint(1, 10), r.randint(1, 10)
    c = r.choice([True, False])
    val = (a > b and c) or not c
    return {
        "code": f"a, b = {a}, {b}\nc = {c}\nprint((a > b and c) or not c)",
        "wrong": [(str(not val), "evaluating `or` before `and`"),
                  ("1" if val else "0", "thinking Python prints 1/0 for booleans"),
                  ("None", "thinking a comparison without if gives nothing")],
        "hint": "Solve the brackets first: is a > b? Then apply and, then or.",
        "why": f"a > b is {a > b}; ({a > b} and {c}) is {a > b and c}; or not {c} ({not c}) gives {val}.",
    }


# ---------------------------------------------------------------- functions
@template("func_return", "functions", 1, "return_values")
def _(r):
    x, k = r.randint(2, 12), r.randint(2, 5)
    return {
        "code": f"def boost(n):\n    return n * {k}\n\nprint(boost({x}))",
        "wrong": [(str(x), "thinking the function changes nothing"),
                  (str(x + k), "adding instead of multiplying"),
                  ("None", "thinking a function never gives back a value")],
        "hint": "return sends a value back to where the function was called.",
        "why": f"boost({x}) returns {x} * {k} = {x * k}, and print shows it.",
    }


@template("func_default", "functions", 2, "default_args")
def _(r):
    name = r.choice(NAMES)
    x = r.randint(2, 4)
    return {
        "code": (f'def cheer(name, times=2):\n    return (name + "!") * times\n\n'
                 f'print(cheer("{name}"))\nprint(cheer("{name}", {x}))'),
        "wrong": [(f"{name}!\n{(name + '!') * x}", "thinking the default is 1"),
                  (f"{name}!{name}!\n{name}!{name}!", "thinking the default can't be replaced"),
                  (f"{name}!\n{name}!", "thinking * repeats nothing for strings"),
                  (f"{name}!2\n{name}!{x}", "thinking * glues the number onto the string"),
                  (f"{name}{name}\n{name * x}", "forgetting the '!' is added before repeating")],
        "hint": "If you leave out `times`, Python uses its default of 2.",
        "why": f"First call uses times=2 → '{(name + '!') * 2}'. Second passes {x} → '{(name + '!') * x}'.",
    }


@template("func_recursion", "functions", 3, "recursion")
def _(r):
    n = r.randint(3, 6)
    fact = 1
    for i in range(2, n + 1):
        fact *= i
    return {
        "code": f"def fact(n):\n    if n <= 1:\n        return 1\n    return n * fact(n - 1)\n\nprint(fact({n}))",
        "wrong": [(str(fact // n), "stopping one call too early"),
                  (str(sum(range(1, n + 1))), "adding instead of multiplying"),
                  ("RecursionError", "thinking a function can't call itself")],
        "hint": "fact(n) waits for fact(n-1), all the way down to fact(1) = 1.",
        "why": f"fact({n}) = {' × '.join(str(i) for i in range(n, 0, -1))} = {fact}.",
    }


# ---------------------------------------------------------------- dictionaries
@template("dict_lookup", "dictionaries", 1, "dict_basics")
def _(r):
    fruits = r.sample(FRUITS, 3)
    prices = r.sample(range(1, 9), 3)
    d = dict(zip(fruits, prices))
    pick = r.choice(fruits)
    other = [f for f in fruits if f != pick][0]
    return {
        "code": f"prices = {d}\nprint(prices[\"{pick}\"])",
        "wrong": [(str(d[other]), "reading the wrong key"),
                  (pick, "thinking it prints the key"),
                  (f"('{pick}', {d[pick]})", "thinking it prints the pair")],
        "hint": "d[key] gives back the value stored under that key.",
        "why": f"The key \"{pick}\" maps to {d[pick]}.",
    }


@template("dict_get", "dictionaries", 2, "dict_get")
def _(r):
    fruits = r.sample(FRUITS, 3)
    stock = dict(zip(fruits[:2], r.sample(range(1, 9), 2)))
    missing = fruits[2]
    dflt = r.randint(0, 3) * 5
    return {
        "code": f"stock = {stock}\nprint(stock.get(\"{missing}\", {dflt}))",
        "wrong": [("KeyError", "thinking .get() crashes like [] does"),
                  ("None", "forgetting the second argument is the default"),
                  (missing, "thinking it prints the key")],
        "hint": f"Is \"{missing}\" in the dict? .get(key, default) never crashes.",
        "why": f"\"{missing}\" is not a key, so .get returns the default {dflt}.",
    }


@template("dict_items", "dictionaries", 3, "dict_loop")
def _(r):
    names = r.sample(NAMES, 3)
    pts = r.sample(range(1, 15), 3)
    d = dict(zip(names, pts))
    lim = sorted(pts)[1]
    right = [n for n, p in d.items() if p >= lim]
    return {
        "code": (f"points = {d}\nwinners = []\nfor name, p in points.items():\n"
                 f"    if p >= {lim}:\n        winners.append(name)\nprint(winners)"),
        "wrong": [(str([n for n, p in d.items() if p > lim]), "treating >= as >"),
                  (str([p for n, p in d.items() if p >= lim]), "thinking .items() gives values first"),
                  (str(names), "ignoring the if inside the loop")],
        "hint": ".items() gives (key, value) pairs in insertion order.",
        "why": f"Only names with points ≥ {lim} are kept: {right}.",
    }


TOPICS = sorted({t.topic for t in TEMPLATES})
