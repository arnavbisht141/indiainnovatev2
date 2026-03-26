#!/bin/bash
# Run the Neo4j seed script
cd "$(dirname "${BASH_SOURCE[0]}")"
pip install -q -r requirements.txt
python3 seed_graph.py
