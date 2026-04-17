from __future__ import annotations

import importlib
import os


os.environ["APP_MODE"] = "local"

import app as _app_module


if getattr(_app_module, "_SAAS", None):
    _app_module = importlib.reload(_app_module)

app = _app_module.app
