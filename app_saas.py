from __future__ import annotations

import importlib
import os


os.environ["APP_MODE"] = "saas"

import app as _app_module


if getattr(_app_module, "_SAAS", None) is False:
    _app_module = importlib.reload(_app_module)

app = _app_module.app
