#!/usr/bin/env bash
# Clone first-tier projects into <bench_root>/../repos-sanitizer/<proj>/, then
# create a reference-clone mirror at <bench_root>/../repos-llvm-cov/<proj>/ so
# git objects are shared on disk (build artifacts will diverge naturally).
#
# Usage:
#   bash scripts/clone_all.sh [project ...]
#   bash scripts/clone_all.sh --all
#
# When invoked without args, clones the FIRST_TIER set (cli_binary +
# library_link case projects). Pass project names to clone a subset, or --all
# for everything in PROJECTS.

set -euo pipefail

BENCH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPOS_SAN="$(cd "${BENCH_ROOT}/.." && pwd)/repos-sanitizer"
REPOS_COV="$(cd "${BENCH_ROOT}/.." && pwd)/repos-llvm-cov"

mkdir -p "${REPOS_SAN}" "${REPOS_COV}"

# Project id -> upstream URL. opencv_contrib is required for opencv wechat_qrcode
# vulns; cloned as a sibling so opencv build can point at it via OPENCV_EXTRA_MODULES_PATH.
declare -A PROJECTS=(
  [llama.cpp]="https://github.com/ggml-org/llama.cpp"
  [whisper.cpp]="https://github.com/ggml-org/whisper.cpp"
  [opencv]="https://github.com/opencv/opencv"
  [opencv_contrib]="https://github.com/opencv/opencv_contrib"
  [onnx]="https://github.com/onnx/onnx"
  [onnxruntime]="https://github.com/microsoft/onnxruntime"
  [pytorch]="https://github.com/pytorch/pytorch"
  [tensorflow]="https://github.com/tensorflow/tensorflow"
  [ollama]="https://github.com/ollama/ollama"
)

# First-tier = projects that own at least one cli_binary or library_link case
# in the first round. opencv_contrib piggy-backs on opencv (needed for two
# wechat_qrcode vulns). pytorch/onnxruntime are heavy and only have 1 case each
# in first round; defer until smoke completes.
FIRST_TIER=(llama.cpp whisper.cpp opencv opencv_contrib)

if [ $# -eq 0 ]; then
  TARGETS=("${FIRST_TIER[@]}")
elif [ "$1" = "--all" ]; then
  TARGETS=("${!PROJECTS[@]}")
else
  TARGETS=("$@")
fi

clone_one() {
  local proj="$1"
  local url="${PROJECTS[$proj]:-}"
  if [ -z "${url}" ]; then
    echo "ERROR: unknown project ${proj} (not in PROJECTS map)" >&2
    return 1
  fi

  local san_dir="${REPOS_SAN}/${proj}"
  local cov_dir="${REPOS_COV}/${proj}"

  if [ ! -d "${san_dir}/.git" ]; then
    echo "[clone] ${proj} -> ${san_dir}"
    # Full history (no --depth) since we need to checkout arbitrary historical SHAs.
    # No --recurse-submodules: most projects pin submodules at HEAD; we'll do
    # `git submodule update --init` per-instance after checking out the target SHA.
    git clone "${url}" "${san_dir}"
  else
    echo "[skip ] ${proj} already cloned at ${san_dir}"
  fi

  if [ ! -d "${cov_dir}/.git" ]; then
    echo "[mirror] ${proj} -> ${cov_dir} (--reference, --dissociate=false)"
    # --reference shares packfiles via .git/objects/info/alternates; saves disk
    # while keeping the clone independent. Don't pass --dissociate so we keep
    # the alternate link.
    git clone --reference "${san_dir}" "${url}" "${cov_dir}"
  else
    echo "[skip  ] ${proj} mirror already at ${cov_dir}"
  fi
}

for p in "${TARGETS[@]}"; do
  clone_one "$p"
done

echo
echo "Done. Sanitizer clones: ${REPOS_SAN}"
echo "      Coverage clones:  ${REPOS_COV}"
