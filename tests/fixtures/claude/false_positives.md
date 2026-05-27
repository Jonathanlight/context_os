# FalsePositives

This file has bullet lists *outside* of a Rules section. They should
NOT be extracted as rules — only items under a recognized H2 (per the
target mapping) count.

- This bullet is just narrative.
- So is this one.

## Some Random Heading

This H2 is not in the alias table for any section, so its contents
are dropped. The parser must not accidentally pick up these bullets:

- Not a rule.
- Also not a rule.

## Rules

- Use type hints on public APIs.
- Never disable a test to make CI pass.
