# PoC Coverage Summary

> **Stale snapshot — last refreshed 2026-04-07 against the Phase-1 catalogue (35 vulns).**
> Phase-2/3 added 10 vulns (7 llama.cpp, 2 ncnn, 1 tensorflow ISSUE-115308)
> and validated several previously "no public PoC" cases via bench-internal
> PoC synthesis. Per-vuln editorial state is in `projects/<proj>/vulns/*.yaml`;
> bench-runnable state (validated / invalidated / pending) is in
> `README.md` "Ready instances" + `validation_summary.csv`. The per-project
> tables below are *not* re-derived; only the No-PoC table at the bottom
> has been corrected.

**Phase-1 catalogue: 7 projects · 35 vulnerabilities · 30 with PoC · 5 without PoC**

Legend:
- **Inline code** — `poc_code` field contains a runnable snippet in the YAML
- **Link only** — `poc_link` points to an external advisory / gist / writeup with code
- **No PoC** — no public exploit or reproducer found

---

## llama.cpp — 3 / 5 with PoC

| ID | Type | Severity | PoC |
|----|------|----------|-----|
| [CVE-2024-42477](projects/llama.cpp/vulns/CVE-2024-42477.yaml) | out-of-bounds-read | HIGH | Inline code — pwn `GET_TENSOR` with type=0x100 → `ggml_type_size[]` OOB; [advisory](https://github.com/ggml-org/llama.cpp/security/advisories/GHSA-mqp6-7pv6-fqjf) |
| [CVE-2024-42479](projects/llama.cpp/vulns/CVE-2024-42479.yaml) | write-what-where | CRITICAL | Inline code — pwn `SET_TENSOR` with data=0xdeadbeef → arbitrary write; [advisory](https://github.com/ggml-org/llama.cpp/security/advisories/GHSA-wcr5-566p-9cwj) · [pwner.gg RCE chain](https://pwner.gg/blog/2024-10-03-llama-cpp-cves) |
| [GHSA-vgg9-87g3-85w8](projects/llama.cpp/vulns/GHSA-vgg9-87g3-85w8.yaml) | integer-overflow | HIGH | Inline summary + [C generator on HuggingFace](https://huggingface.co/yuuoniy/overflow/blob/main/generate_poc.c) — crafts GGUF with uint64 ctx→size overflow |
| GHSA-8wwf-w4qm-gpqr | heap-buffer-overflow | HIGH | **No PoC** — requires >2 GB GGUF token; advisory description only |
| TALOS-2024-1913 | heap-buffer-overflow | HIGH | **No PoC** — Talos advisory (403); crash trace exists but no public file |

---

## ollama — 5 / 5 with PoC

| ID | Type | Severity | PoC |
|----|------|----------|-----|
| [CVE-2024-39720](projects/ollama/vulns/CVE-2024-39720.yaml) | out-of-bounds-read | HIGH | Link — [Oligo Security blog](https://www.oligo.security/blog/more-models-more-probllms) with HTTP request sequences; 4-byte GGUF triggers SIGSEGV |
| [SONAR-2025-MLLAMA-RCE](projects/ollama/vulns/SONAR-2025-MLLAMA-RCE.yaml) | out-of-bounds-write | CRITICAL | Link — [Sonar blog](https://www.sonarsource.com/blog/ollama-remote-code-execution-securing-the-code-that-runs-llms/); crafted GGUF → vtable overwrite → RCE |
| [CVE-2025-15514](projects/ollama/vulns/CVE-2025-15514.yaml) | null-ptr-deref | HIGH | Link — [huntr bounty](https://huntr.com/bounties/172df98b-07cd-41ea-a628-366f8cd525c0); malformed image in `/api/chat` |
| [CVE-2024-12055](projects/ollama/vulns/CVE-2024-12055.yaml) | null-ptr-deref | HIGH | Link — [huntr bounty](https://huntr.com/bounties/7b111d55-8215-4727-8807-c5ed4cf1bfbe); crafted GGUF → nil deref crash |
| [CVE-2025-66959](projects/ollama/vulns/CVE-2025-66959.yaml) | integer-overflow | HIGH | Inline code — Python upload script; GGUF string length=0xFFFF… → `make([]byte, n)` panic; [blog](https://zero.shotlearni.ng/blog/cve-2025-66959panic-dos-via-unchecked-length-in-gguf-decoder-copy/) |

---

## onnx — 4 / 4 with PoC

| ID | Type | Severity | PoC |
|----|------|----------|-----|
| [CVE-2022-25882](projects/onnx/vulns/CVE-2022-25882.yaml) | path-traversal | HIGH | Inline code — Python model builder setting `external_data.location = "../../../etc/passwd"`; [gist](https://gist.github.com/jnovikov/02a9aff9bf2188033e77bd91ff062856) |
| [CVE-2024-27318](projects/onnx/vulns/CVE-2024-27318.yaml) | path-traversal | HIGH | Inline code — bypass via `model/../../../etc/passwd` nested path; [GHSA](https://github.com/advisories/GHSA-whh8-fjgc-qp73) · [HiddenLayer advisory](https://hiddenlayer.com/sai-security-advisory/2024-02-onnx/) |
| [CVE-2024-5187](projects/onnx/vulns/CVE-2024-5187.yaml) | arbitrary-file-write | HIGH | Link — [huntr bounty](https://huntr.com/bounties/50235ebd-3410-4ada-b064-1a648e11237e); malicious tar overwrites `~/.ssh/authorized_keys` |
| [ORT-2024-HIDDENLAYER](projects/onnx/vulns/ORT-2024-HIDDENLAYER.yaml) | out-of-bounds-read | MEDIUM | Inline code — ONNX model with 2048-byte domain string → `barf()` OOB read; [HiddenLayer advisory](https://hiddenlayer.com/sai-security-advisory/2024-02-onnx/) |

---

## opencv — 4 / 5 with PoC

| ID | Type | Severity | PoC |
|----|------|----------|-----|
| [CVE-2019-5063](projects/opencv/vulns/CVE-2019-5063.yaml) | heap-buffer-overflow | HIGH | Link — [TALOS-2019-0852](https://talosintelligence.com/vulnerability_reports/TALOS-2019-0852); crafted JSON with long repeated-character entity |
| [CVE-2019-5064](projects/opencv/vulns/CVE-2019-5064.yaml) | heap-buffer-overflow | HIGH | Link — [TALOS-2019-0853](https://talosintelligence.com/vulnerability_reports/TALOS-2019-0853); XML variant of same persistence bug |
| [CVE-2023-2617](projects/opencv/vulns/CVE-2023-2617.yaml) | null-ptr-deref | MEDIUM | Inline code — Python QR crafter overrides `BitBuffer.put()` with fake length=233; [gist](https://gist.github.com/GZTimeWalker/3ca70a8af2f5830711e9cccc73fb5270) |
| [CVE-2025-53644](projects/opencv/vulns/CVE-2025-53644.yaml) | heap-buffer-overflow | HIGH | Inline code — C++ with raw JPEG2000 / JP2 binary arrays; 5-call sequence triggers heap-UAF; [GHSL-2025-057](https://securitylab.github.com/advisories/GHSL-2025-057_OpenCV/) |
| CVE-2023-2618 | memory-leak | MEDIUM | **No PoC** — sibling bug to CVE-2023-2617; no reproducer released for this variant |

---

## pytorch — 4 / 4 with PoC

| ID | Type | Severity | PoC |
|----|------|----------|-----|
| [CVE-2024-31580](projects/pytorch/vulns/CVE-2024-31580.yaml) | heap-buffer-overflow | HIGH | Link — [gist](https://gist.github.com/1047524396/038c78f2f007345e6f497698ace2aa3d) (NVD-tagged exploit reference); vararg buffer overflow |
| [CVE-2024-31583](projects/pytorch/vulns/CVE-2024-31583.yaml) | use-after-free | HIGH | Link — [gist](https://gist.github.com/1047524396/43e19a41f2b36503a4a228c32cdbc176) (NVD-tagged exploit reference); mobile JIT OOB |
| [CVE-2024-31584](projects/pytorch/vulns/CVE-2024-31584.yaml) | out-of-bounds-read | HIGH | Inline code — Python script to patch `mobile_ivalue_size` in `.ptl` flatbuffer; derived from [fix commit](https://github.com/pytorch/pytorch/commit/7c35874ad664e74c8e4252d67521f3986eadb0e6) |
| [CVE-2024-48063](projects/pytorch/vulns/CVE-2024-48063.yaml) | deserialization-rce | CRITICAL | Link — [gist](https://gist.github.com/hexian2001/c046c066895a963ecc0a2cf9e1180065) + [Notion writeup](https://rumbling-slice-eb0.notion.site/Distributed-RPC-Framework-RemoteModule-has-Deserialization-RCE-in-pytorch-pytorch-111e3cda9e8c8021a7d3cbc61ee1a20c); RemoteModule RCE |

---

## tensorflow — 8 / 8 with PoC

All TensorFlow entries have inline Python code embedded directly in the YAML files, extracted from GitHub security advisories.

| ID | Type | Severity | PoC |
|----|------|----------|-----|
| [CVE-2022-21740](projects/tensorflow/vulns/CVE-2022-21740.yaml) | heap-buffer-overflow | HIGH | Inline code — `tf.raw_ops.SparseCountSparseOutput` with indices=[[-1,-1]], weights=[1]; [GHSA-44qp-9wwf-734r](https://github.com/tensorflow/tensorflow/security/advisories/GHSA-44qp-9wwf-734r) |
| [CVE-2022-29210](projects/tensorflow/vulns/CVE-2022-29210.yaml) | heap-buffer-overflow | MEDIUM | Inline code — `tf.lookup.MutableHashTable` with long string key triggers `TensorKey` OOB; derived from [GHSA-hc2f-7r5r-r2hg](https://github.com/tensorflow/tensorflow/security/advisories/GHSA-hc2f-7r5r-r2hg) |
| [CVE-2022-35939](projects/tensorflow/vulns/CVE-2022-35939.yaml) | out-of-bounds-write | HIGH | Inline code — TFLite `scatter_nd` with OOB index via TFLite interpreter; derived from [GHSA-ffjm-4qwc-7cmf](https://github.com/tensorflow/tensorflow/security/advisories/GHSA-ffjm-4qwc-7cmf) |
| [CVE-2022-41910](projects/tensorflow/vulns/CVE-2022-41910.yaml) | heap-buffer-overflow | HIGH | Inline code — `@tf.function` calling `QuantizeAndDequantizeV2` with axis=0x7fffffff; [GHSA-frqp-wp83-qggv](https://github.com/tensorflow/tensorflow/security/advisories/GHSA-frqp-wp83-qggv) |
| [CVE-2023-25664](projects/tensorflow/vulns/CVE-2023-25664.yaml) | heap-buffer-overflow | HIGH | Inline code — `AvgPoolGrad` with ksize=[1,40,128,1], strides=[1,128,128,30]; [GHSA-6hg6-5c2q-7rcr](https://github.com/tensorflow/tensorflow/security/advisories/GHSA-6hg6-5c2q-7rcr) |
| [CVE-2023-25668](projects/tensorflow/vulns/CVE-2023-25668.yaml) | out-of-bounds-read | HIGH | Inline code — `@tf.function` calling `QuantizeAndDequantizeV2` with axis=0x7fffffff; [GHSA-gw97-ff7c-9v96](https://github.com/tensorflow/tensorflow/security/advisories/GHSA-gw97-ff7c-9v96) |
| [GHSA-pg59-2f92-5cph](projects/tensorflow/vulns/GHSA-pg59-2f92-5cph.yaml) | heap-buffer-overflow | HIGH | Inline code — `SparseCountSparseOutput` with weights=[1.0] (fewer than values); derived from [advisory](https://github.com/tensorflow/tensorflow/security/advisories/GHSA-pg59-2f92-5cph) |
| [GHSA-v6r6-84gr-92rm](projects/tensorflow/vulns/GHSA-v6r6-84gr-92rm.yaml) | heap-buffer-overflow | HIGH | Inline code — `AvgPool3DGrad` with orig_input_shape=[10,6,3,7,7] vs grad [3,1,1,1,1]; [GHSA-v6r6-84gr-92rm](https://github.com/advisories/GHSA-v6r6-84gr-92rm) |

---

## whisper.cpp — 2 / 4 with PoC

| ID | Type | Severity | PoC |
|----|------|----------|-----|
| [CVE-2025-14569](projects/whisper.cpp/vulns/CVE-2025-14569.yaml) | use-after-free | MEDIUM | Inline code — 44-byte WAV binary at [oneafter/InvalidFree/repro](https://github.com/oneafter/InvalidFree/blob/main/repro); single CLI command triggers ASan invalid-free; [issue #3501](https://github.com/ggml-org/whisper.cpp/issues/3501) |
| [GHSA-ggml-2025-parser](projects/whisper.cpp/vulns/GHSA-ggml-2025-parser.yaml) | out-of-bounds-read | MEDIUM | Inline code — Python GGUF crafter setting n_dims=255 (>GGML_MAX_DIMS=4) → OOB read in ne[] array |
| TALOS-2024-1914 | heap-buffer-overflow | HIGH | **No PoC** — Talos advisory (403); no public GGUF file released |
| TALOS-2024-1914B | stack-buffer-overflow | HIGH | **No PoC** — provisional entry; no public exploit; requires >30 min audio |

---

## Summary by Project

| Project | Total | With PoC | Inline Code | Link Only | No PoC |
|---------|-------|----------|-------------|-----------|--------|
| llama.cpp | 5 | 3 | 3 | 0 | 2 |
| ollama | 5 | 5 | 1 | 4 | 0 |
| onnx | 4 | 4 | 3 | 1 | 0 |
| opencv | 5 | 4 | 2 | 2 | 1 |
| pytorch | 4 | 4 | 1 | 3 | 0 |
| tensorflow | 8 | 8 | 8 | 0 | 0 |
| whisper.cpp | 4 | 2 | 2 | 0 | 2 |
| **Total** | **35** | **30** | **20** | **10** | **5** |

---

## No-PoC Entries — current (2026-05-03)

After Phase-2/3 the bench synthesises its own PoCs for several cases that
were originally "no PoC" (TALOS-2024-1913 / 1914, etc.).  The remaining
truly-no-PoC instances (env-only, marked `invalidated_no_poc` in the bench)
are:

| Instance | Project | Reason |
|----|---------|--------|
| `llama.cpp.GHSA-8wwf-w4qm-gpqr` | llama.cpp | Requires GGUF vocab token > INT32_MAX bytes; impractical to distribute |
| `llama.cpp.CVE-2024-42478` | llama.cpp | Bench-internal RPC PoC didn't match ALLOC_BUFFER reply offset; env reused from CVE-2024-42477 |
| `llama.cpp.CVE-2025-52566` | llama.cpp | Needs jinja template producing > INT32_MAX tokens |
| `opencv.CVE-2023-2618` | opencv | Memory-leak only (CWE-401); advisory describes class only, no reproducer |
| `whisper.cpp.TALOS-2024-1914B` | whisper.cpp | `whisper_full_parallel` refactored to `std::vector`; requires >30 min audio + specific config |

Cases originally listed as no-PoC that are now **validated** with
bench-synthesised PoCs:

| Instance | What changed |
|---|---|
| `llama.cpp.TALOS-2024-1913` | bench ships `craft_fread_str_overflow.py` → ASAN heap-buffer-overflow in `gguf_fread_str` |
| `whisper.cpp.TALOS-2024-1914` | same crafted GGUF (cross-applicable from shared ggml code path) |

For Phase-2/3 entries (ncnn / tensorflow.ISSUE-115308 / onnx.CVE-2022-25882 /
onnx.CVE-2024-27318), see `README.md` "Ready instances" — all have inline
PoCs sourced from the upstream issue tracker / GHSA.

---

*Last refreshed: 2026-05-03 (Phase-1 tables retained; banner + No-PoC
table updated for current state).*
