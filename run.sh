#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
echo "🖤 Cloud in a Bottle — v1.2.1 Truth Mode"
python3 lab.py "$@"
python3 lab_v1_1_map.py
python3 lab_v1_2_airgap.py
echo "Launching localhost-only app..."
exec python3 app.py