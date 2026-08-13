from __future__ import annotations

from hypothesis import settings

settings.register_profile("default", deadline=None)
settings.register_profile("thorough", deadline=None, max_examples=2000)
settings.load_profile("default")
