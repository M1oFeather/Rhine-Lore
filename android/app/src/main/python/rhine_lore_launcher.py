# -*- coding: utf-8 -*-
"""Embedded Rhine-Lore launcher for the Android app (Chaquopy)."""

import os
import threading
from pathlib import Path


def start_server(data_dir, web_root, port=8796):
    os.environ["RHINE_LORE_EMBEDDED"] = "1"
    data_path = Path(data_dir)
    data_path.mkdir(parents=True, exist_ok=True)
    os.environ["RHINE_LORE_DATA_DIR"] = str(data_path)
    web_path = Path(web_root)
    if not web_path.is_dir():
        raise FileNotFoundError(f"web root does not exist: {web_path}")

    from rhine_lore.server import serve

    def run():
        try:
            # Bind all interfaces so the same instance can also be opened as
            # the web version from other devices on the LAN (data stays in sync).
            serve(host="0.0.0.0", port=int(port), web_root=web_path)
        except Exception:
            import traceback

            traceback.print_exc()

    threading.Thread(target=run, daemon=True).start()
