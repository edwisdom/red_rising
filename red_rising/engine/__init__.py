"""The pure game engine.

Nothing in this package may import FastAPI, do I/O, or use `async`. The engine is
`(state, answer) -> events`, deterministic given its seeded RNG. This is what makes
replay, fuzzing, and a future bot cheap.
"""
