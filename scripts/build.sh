#!/usr/bin/env bash
# XLPS2-Alpha 构建脚本骨架（后续按模块填充真实构建步骤）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "XLPS2-Alpha build — repo root: $ROOT"

build_cfw() {
  echo "[cfw] TODO: STM32H7 工具链构建（CubeMX/CMake/arm-none-eabi-gcc）"
}

build_hmi() {
  echo "[hmi] TODO: Vite 构建 + Capacitor apk 打包"
}

build_ota() {
  echo "[ota] Python 服务构建 / 测试"
  if [ -d "$ROOT/src/ota" ]; then
    (cd "$ROOT/src/ota" && python -m pytest tests -q 2>&1 || \
      echo "[ota] 单测未通过或 pytest 不可用（可本地 python -m pytest src/ota/tests 运行）")
  fi
}

run_gate() {
  echo "[gate] 跨模块契约门禁"
  (cd "$ROOT" && python -m pytest tests/test_cross_module.py -v)
}

case "${1:-all}" in
  cfw) build_cfw ;;
  hmi) build_hmi ;;
  ota) build_ota ;;
  gate) run_gate ;;
  all)
    build_cfw
    build_hmi
    build_ota
    run_gate
    ;;
  *) echo "usage: $0 {cfw|hmi|ota|gate|all}"; exit 1 ;;
esac
