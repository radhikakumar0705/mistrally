# Python basics

## Lists

A list is an ordered, mutable sequence. You can reverse a list in place with `items.reverse()`, which returns None, or create a reversed copy with slicing: `items[::-1]`. Appending is amortized constant time, while inserting at the front with `items.insert(0, x)` is linear because every element shifts.

## Dictionaries

Dictionaries map keys to values and look keys up in constant time on average. Reading a missing key with square brackets raises KeyError; use `d.get(key, default)` to fall back to a default value instead. Since Python 3.7 dictionaries keep insertion order.

## List comprehensions

A list comprehension builds a new list from an iterable in one expression, for example `[n * n for n in range(10) if n % 2 == 0]`. Prefer a plain loop when the logic needs several statements, because deeply nested comprehensions are hard to read.

## Exceptions

Wrap code that may fail in `try`/`except` and catch the narrowest exception type you can handle. A `finally` block always runs, whether or not an exception happened, which makes it the right place to release resources. Avoid a bare `except:` because it also swallows KeyboardInterrupt.

## Virtual environments

Create an isolated environment per project with `python -m venv .venv`, then activate it before installing packages. Pin exact versions in requirements.txt so every machine installs the same dependencies.

## F-strings

Formatted string literals interpolate expressions directly: `f"{name} scored {score:.1f} points"`. The `:.1f` part is a format specifier that rounds to one decimal place.
