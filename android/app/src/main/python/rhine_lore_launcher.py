# -*- coding: utf-8 -*-
"""Embedded Rhine-Lore launcher for the Android app (Chaquopy)."""

import os
import threading


def start_server(data_dir, web_root, port=8796):
    os.environ["RHINE_LORE_EMBEDDED"] = "1"
    os.environ["RHINE_LORE_DATA_DIR"] = str(data_dir)

    from rhine_lore.server import serve

    def run():
        serve(host="127.0.0.1", port=int(port), web_root=web_root)

    threading.Thread(target=run, daemon=True).start()
