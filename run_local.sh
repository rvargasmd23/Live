#!/usr/bin/env bash
set -e
python3 -m pip install -r requirements.txt
python3 update_master.py --real-epg
python3 -m http.server 8080
