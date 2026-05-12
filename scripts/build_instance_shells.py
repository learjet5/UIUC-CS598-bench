#!/usr/bin/env python3.12
"""Build instance.json shells for the first-tier 14 cases.

For each first-tier case (cli_binary or library_link triggerable_class), create
instances/<project>.<id>/ containing:
  - instance.json with project-default build_sh / harness_command, validation
    status pending, and TODO markers in fields that need human review
  - repro/SOURCE.md stub (if poc_available)
  - notes.md with a 5-step path-to-validated checklist

Skips instances/<id>/ if it already exists.

This script is the "scaffold a new instance" tool. After it runs, each shell
typically needs:
  1. Correct fix_commit + vulnerable_commit (run audit + derive_vuln_commit).
  2. Correct vuln_location <file>:<line>.
  3. Project-specific harness/build customization.
  4. PoC dropped into repro/ + SOURCE.md updated.

Usage:
    python3.12 scripts/build_instance_shells.py
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

BENCH = Path(__file__).resolve().parent.parent

PROJECT_DEFAULTS = {
    "llama.cpp": {
        "lang": "cpp",
        "build_sh_sanitizer": (
            "set -e\n"
            "mkdir -p build-asan && cd build-asan\n"
            "cmake .. -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ "
            "-DLLAMA_SANITIZE_ADDRESS=ON -DLLAMA_SANITIZE_UNDEFINED=ON "
            "-DGGML_BACKEND_DL=OFF -DCMAKE_BUILD_TYPE=Debug "
            "-DGGML_CUDA=OFF -DGGML_METAL=OFF -DGGML_VULKAN=OFF -DGGML_OPENMP=OFF "
            "-DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_SERVER=OFF\n"
            "cmake --build . --target llama-cli -j$(nproc)"
        ),
        "build_sh_cov": (
            "set -e\n"
            "mkdir -p build-cov && cd build-cov\n"
            "cmake .. -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ "
            "-DCMAKE_C_FLAGS='-fprofile-instr-generate -fcoverage-mapping' "
            "-DCMAKE_CXX_FLAGS='-fprofile-instr-generate -fcoverage-mapping' "
            "-DCMAKE_EXE_LINKER_FLAGS='-fprofile-instr-generate -fcoverage-mapping' "
            "-DGGML_BACKEND_DL=OFF -DCMAKE_BUILD_TYPE=Debug "
            "-DGGML_CUDA=OFF -DGGML_METAL=OFF -DGGML_VULKAN=OFF -DGGML_OPENMP=OFF "
            "-DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_SERVER=OFF\n"
            "cmake --build . --target llama-cli -j$(nproc)"
        ),
        "build_target": "build-asan/bin/llama-cli",
        "harness_command": "${REPO}/build-asan/bin/llama-cli -m <path/to/testcase> -no-cnv -p 'hi' -n 1",
    },
    "whisper.cpp": {
        "lang": "cpp",
        "build_sh_sanitizer": (
            "set -e\n"
            "mkdir -p build-asan && cd build-asan\n"
            "cmake .. -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ "
            "-DGGML_SANITIZE_ADDRESS=ON -DGGML_SANITIZE_UNDEFINED=ON "
            "-DGGML_CUDA=OFF -DGGML_METAL=OFF -DGGML_VULKAN=OFF -DGGML_OPENMP=OFF "
            "-DCMAKE_BUILD_TYPE=Debug -DWHISPER_BUILD_TESTS=OFF\n"
            "cmake --build . --target whisper-cli -j$(nproc)"
        ),
        "build_sh_cov": (
            "set -e\n"
            "mkdir -p build-cov && cd build-cov\n"
            "cmake .. -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ "
            "-DCMAKE_C_FLAGS='-fprofile-instr-generate -fcoverage-mapping' "
            "-DCMAKE_CXX_FLAGS='-fprofile-instr-generate -fcoverage-mapping' "
            "-DCMAKE_EXE_LINKER_FLAGS='-fprofile-instr-generate -fcoverage-mapping' "
            "-DGGML_CUDA=OFF -DGGML_METAL=OFF -DGGML_VULKAN=OFF -DGGML_OPENMP=OFF "
            "-DCMAKE_BUILD_TYPE=Debug -DWHISPER_BUILD_TESTS=OFF\n"
            "cmake --build . --target whisper-cli -j$(nproc)"
        ),
        "build_target": "build-asan/bin/whisper-cli",
        "harness_command": "${REPO}/build-asan/bin/whisper-cli -m ${POC_DIR}/model.bin -f <path/to/testcase>",
    },
    "opencv": {
        "lang": "cpp",
        "build_sh_sanitizer": (
            "set -e\n"
            "mkdir -p build-asan && cd build-asan\n"
            "cmake .. -DCMAKE_C_COMPILER=clang -DCMAKE_CXX_COMPILER=clang++ "
            "-DCMAKE_BUILD_TYPE=Debug "
            "-DCMAKE_C_FLAGS='-fsanitize=address,undefined -g' "
            "-DCMAKE_CXX_FLAGS='-fsanitize=address,undefined -g' "
            "-DCMAKE_EXE_LINKER_FLAGS='-fsanitize=address,undefined' "
            "-DCMAKE_SHARED_LINKER_FLAGS='-fsanitize=address,undefined' "
            "-DBUILD_LIST=imgcodecs,core "
            "-DBUILD_opencv_apps=OFF -DBUILD_TESTS=OFF -DBUILD_PERF_TESTS=OFF -DBUILD_EXAMPLES=OFF "
            "-DWITH_FFMPEG=OFF -DWITH_GTK=OFF -DWITH_QT=OFF\n"
            "cmake --build . --target opencv_imgcodecs opencv_core -j$(nproc)"
        ),
        "build_sh_cov": "TODO: cov build for opencv (use -fprofile-instr-generate -fcoverage-mapping)",
        "build_target": "TODO: build/lib/libopencv_imgcodecs.so or a wrapper harness",
        "harness_command": "TODO: small C++ that uses cv::imread/cv::FileStorage <path/to/testcase>",
    },
    "onnx": {
        "lang": "cpp",
        "build_sh_sanitizer": "TODO: onnxruntime cmake build with sanitizers",
        "build_sh_cov": "TODO",
        "build_target": "TODO",
        "harness_command": "TODO: small C++ harness linking onnxruntime",
    },
    "pytorch": {
        "lang": "cpp",
        "build_sh_sanitizer": "TODO: pytorch local build (mobile interpreter target)",
        "build_sh_cov": "TODO",
        "build_target": "TODO",
        "harness_command": "TODO: small C++ harness using torch::jit::mobile",
    },
}

TRIG_CLASS = {
    "CVE-2024-42477": "server",
    "CVE-2024-42479": "server",
    "GHSA-vgg9-87g3-85w8": "library_link",
    "GHSA-8wwf-w4qm-gpqr": "cli_binary",
    "TALOS-2024-1913": "cli_binary",
    "CVE-2025-14569": "cli_binary",
    "GHSA-ggml-2025-parser": "cli_binary",
    "TALOS-2024-1914": "cli_binary",
    "TALOS-2024-1914B": "cli_binary",
    "CVE-2019-5063": "cli_binary",
    "CVE-2019-5064": "cli_binary",
    "CVE-2023-2617": "library_link",
    "CVE-2023-2618": "library_link",
}

FIRST_TIER = sorted(k for k, v in TRIG_CLASS.items() if v in ("cli_binary", "library_link"))


def main():
    n_built = 0
    for ypath in sorted(BENCH.glob("projects/*/vulns/*.yaml")):
        d = yaml.safe_load(ypath.read_text())
        vid = d["id"]
        proj = d["project"]
        if vid not in FIRST_TIER:
            continue

        defaults = PROJECT_DEFAULTS.get(proj, {})
        affected = d.get("affected_component", "")
        # Best-effort vuln_location: pull file path, default line=1
        vuln_loc = "src/TODO.cpp:1"
        if affected and any(ext in affected for ext in (".cpp", ".c", ".h")):
            file_path = affected.split(";")[0].strip().split(" ")[0]
            vuln_loc = f"{file_path}:1"

        vuln_commit = (d.get("vulnerable_commit") or "").strip()
        if not vuln_commit:
            vuln_commit = "TODO_set_vulnerable_commit"

        inst = {
            "instance_id": f"{proj}.{vid}",
            "project_name": proj,
            "lang": defaults.get("lang", "cpp"),
            "base_commit": vuln_commit,
            "build_sh_sanitizer": defaults.get("build_sh_sanitizer", "TODO"),
            "build_sh_cov": defaults.get("build_sh_cov", "TODO"),
            "build_target": defaults.get("build_target", "TODO"),
            "harness_command": defaults.get("harness_command", "TODO"),
            "vuln_location": vuln_loc,
            "poc_input_path": "" if not d.get("poc_available") else "TODO_see_repro_SOURCE_md",
            "expected_fingerprint": "",
            "triggerable_class": TRIG_CLASS[vid],
            "validation_status": "pending",
            "validation_notes": "stub — see notes.md | vuln_location placeholder line=1, replace with advisory line",
        }

        out_dir = BENCH / "instances" / f"{proj}.{vid}"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "repro").mkdir(exist_ok=True)
        out_path = out_dir / "instance.json"
        if out_path.exists():
            print(f"SKIP {out_path} (already exists)")
            continue
        out_path.write_text(json.dumps(inst, indent=2) + "\n")

        src_md = out_dir / "repro" / "SOURCE.md"
        if not src_md.exists() and d.get("poc_available"):
            src_md.write_text(
                f"# PoC source provenance — {proj}.{vid}\n\n"
                f"TODO: fetch the PoC and record source URL, hash, license here.\n\n"
                f"Reference (from yaml): {d.get('poc_link') or '(no poc_link in yaml)'}\n"
            )

        notes_md = out_dir / "notes.md"
        if not notes_md.exists():
            poc_status = "available" if d.get("poc_available") else "MISSING (no PoC public)"
            notes_md.write_text(
                f"# Notes — {proj}.{vid}\n\n"
                f"## Status\n\n"
                f"- triggerable_class: {TRIG_CLASS[vid]}\n"
                f"- PoC: {poc_status}\n"
                f"- vulnerable_commit: {'set' if d.get('vulnerable_commit') else 'TODO'}\n\n"
                f"## What this stub needs to become validated\n\n"
                "1. Verify or fix the `fix_commit` field in the yaml (run `scripts/audit_fix_commits.py`).\n"
                "2. Set `base_commit` in `instance.json` (run `scripts/derive_vuln_commit.py --apply`).\n"
                "3. Customize `build_sh_sanitizer` / `build_target` / `harness_command` for this case.\n"
                "4. Drop a working PoC into `repro/` and update `repro/SOURCE.md`.\n"
                "5. Run `bash scripts/validate_instance.sh " + f"{proj}.{vid}" + "` until it returns `validated`.\n"
            )
        n_built += 1
        print(f"BUILT {out_path}")

    print(f"\nbuilt {n_built} instance shells")


if __name__ == "__main__":
    main()
