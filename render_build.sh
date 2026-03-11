#!/usr/bin/env bash
# Install CPU-only PyTorch first (much smaller than GPU version)
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-deploy.txt
