# `.ctx` fixtures

Real `.ctx` files exercised by the parser tests (Milestone 1.2b onward).

## Layout

```
ctx/
├── valid/      # files that must parse to a Document without error
└── invalid/    # files that must raise ContextOSParseError with a specific signature
```

Each `invalid/` fixture is paired in `test_ctx_parser.py` with an expected
substring of the error message — that's how we verify the diagnostic stays
helpful as the parser evolves.

## Versioning

Fixtures pin `ctx_version` explicitly when they exercise version-specific
behaviour. Otherwise they omit the field and rely on the parser's default
(`"0.3"`).

## Updating

If a fixture causes a test to fail and the new parser output is the
intentional behaviour, update both the fixture (if the input semantics
changed) and the corresponding expectation in `test_ctx_parser.py`. Do not
mass-update fixtures — each change should correspond to a documented
diagnostic shift.
