"""The application layer: FastAPI transport around the pure engine.

This package may use FastAPI, async, and I/O. It translates WebSocket messages
into engine `Answer`s and engine state into per-viewer `PlayerView`s. It holds no
game rules — those all live in `red_rising.engine`.
"""
