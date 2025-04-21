#!/bin/bash

# 1) 심볼릭 링크를 고려하여, 실제 스크립트 파일 경로 추적
SCRIPT_FILE="$(readlink -f "$0")"
SCRIPT_DIR="$(dirname "$SCRIPT_FILE")"

# 2) 스크립트의 실제 위치로 이동
cd "$SCRIPT_DIR"

streamlit run streamlit_app.py --server.headless true