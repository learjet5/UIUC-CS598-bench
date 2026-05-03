#!/usr/bin/env bash
# Validate one instance end-to-end: clone (if needed) + checkout vulnerable
# commit + run build_sh_sanitizer + run harness_command on poc_input_path +
# fingerprint-match against expected_fingerprint.
#
# Updates instance.json::validation_status in place and appends a row to
# validation_report.md.
#
# Usage:
#   bash scripts/validate_instance.sh <project>.<id>
#
# Example:
#   bash scripts/validate_instance.sh llama.cpp.GHSA-vgg9-87g3-85w8

set -u  # do NOT set -e — we want to capture failures and write status
INSTANCE_ID="${1:?instance_id required}"

BENCH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INST_DIR="${BENCH_ROOT}/instances/${INSTANCE_ID}"
INST_JSON="${INST_DIR}/instance.json"

if [ ! -f "${INST_JSON}" ]; then
    echo "ERROR: ${INST_JSON} not found" >&2
    exit 1
fi

# Pull fields we need with python (jq might not be installed; python3.12 + json
# is universal).
read -r PROJECT_NAME BASE_COMMIT BUILD_TARGET TRIG_CLASS POC_INPUT_PATH STATUS_PRE < <(
    python3.12 - <<EOF
import json, sys
d = json.loads(open("${INST_JSON}").read())
print(d["project_name"], d["base_commit"], d["build_target"],
      d["triggerable_class"], d.get("poc_input_path", "") or "_",
      d.get("validation_status", ""))
EOF
)
# Translate placeholder back
[ "${POC_INPUT_PATH}" = "_" ] && POC_INPUT_PATH=""

# Skip cases that explicitly have no PoC or whose recipe still has TODO markers.
# These should not be reset to `pending` by re-running validate.
SKIP_REASON=""
if [ "${STATUS_PRE}" = "invalidated_no_poc" ]; then
    SKIP_REASON="status=invalidated_no_poc (no public PoC; env recipe stays as-is)"
elif [ -z "${POC_INPUT_PATH}" ]; then
    SKIP_REASON="poc_input_path is empty (no PoC artefact)"
elif printf '%s' "${BASE_COMMIT}${BUILD_TARGET}" | grep -qE '^TODO|TODO_'; then
    SKIP_REASON="base_commit or build_target is still a TODO marker"
fi
if [ -n "${SKIP_REASON}" ]; then
    echo "[validate] SKIP ${INSTANCE_ID}: ${SKIP_REASON}"
    exit 0
fi

REPO_SAN="${BENCH_ROOT}/../repos-sanitizer/${PROJECT_NAME}"
if [ ! -d "${REPO_SAN}" ]; then
    echo "ERROR: sanitizer clone missing at ${REPO_SAN}; run scripts/clone_all.sh ${PROJECT_NAME}" >&2
    exit 2
fi

LOG_DIR="${INST_DIR}/.validation"
mkdir -p "${LOG_DIR}"
DATE_NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo "[validate] instance=${INSTANCE_ID} project=${PROJECT_NAME} base=${BASE_COMMIT} class=${TRIG_CLASS}"

# 1) Checkout the vulnerable commit. Skip for python_api or any project
# whose REPO_SAN dir isn't actually a git checkout (placeholder dir for
# Python-only / pip-resolved bench instances).
if [ "${TRIG_CLASS}" = "python_api" ] || [ ! -d "${REPO_SAN}/.git" ]; then
    echo "[validate] skipping git checkout (class=${TRIG_CLASS}, .git=$( [ -d "${REPO_SAN}/.git" ] && echo yes || echo no ))"
else
    ( cd "${REPO_SAN}" && git checkout -q "${BASE_COMMIT}" ) || {
        echo "FAIL  checkout of ${BASE_COMMIT} in ${REPO_SAN}"
        python3.12 -c "
import json, sys
p='${INST_JSON}'; d=json.loads(open(p).read())
d['validation_status']='invalidated_poc_failed'
d['validation_notes']='checkout ${BASE_COMMIT} failed (${DATE_NOW})'
open(p,'w').write(json.dumps(d, indent=2)+'\n')
"
        exit 3
    }
fi

# 2) Run build_sh_sanitizer (pulled from instance.json) in repo
BUILD_LOG="${LOG_DIR}/build.log"
echo "[validate] running build_sh_sanitizer (log: ${BUILD_LOG})"
python3.12 -c "import json; print(json.loads(open('${INST_JSON}').read())['build_sh_sanitizer'])" > "${LOG_DIR}/build.sh"
# Export POC_DIR/REPO so build_sh can reference them via $POC_DIR / $REPO.
# Both build_sh_* and harness_command use the same convention.
( cd "${REPO_SAN}" && \
  POC_DIR="${INST_DIR}/repro" REPO="${REPO_SAN}" \
  ASAN_OPTIONS=use_sigaltstack=0 bash "${LOG_DIR}/build.sh" \
) >"${BUILD_LOG}" 2>&1
BUILD_RC=$?
if [ "${BUILD_RC}" -ne 0 ] || [ ! -f "${REPO_SAN}/${BUILD_TARGET}" ]; then
    echo "FAIL  build (rc=${BUILD_RC}, missing target=${BUILD_TARGET})"
    python3.12 -c "
import json
p='${INST_JSON}'; d=json.loads(open(p).read())
d['validation_status']='invalidated_poc_failed'
d['validation_notes']='build_sh_sanitizer failed rc=${BUILD_RC} or missing build_target (${DATE_NOW})'
open(p,'w').write(json.dumps(d, indent=2)+'\n')
"
    exit 4
fi

# 3) Run harness_command. Substitute <path/to/testcase> + ${REPO} + ${POC_DIR}
RUN_LOG="${LOG_DIR}/run.log"
POC_ABS="${INST_DIR}/repro/${POC_INPUT_PATH}"
HARNESS="$(python3.12 -c "import json; print(json.loads(open('${INST_JSON}').read())['harness_command'])")"
HARNESS="${HARNESS//<path\/to\/testcase>/${POC_ABS}}"
HARNESS="${HARNESS//\$\{REPO\}/${REPO_SAN}}"
HARNESS="${HARNESS//\$\{POC_DIR\}/${INST_DIR}/repro}"

echo "[validate] running harness: ${HARNESS}"
# Export REPO / POC_DIR into the harness env too — wrappers like run_rpc_poc.sh
# reference them via ${REPO:?...} bash parameter expansion.
( cd "${REPO_SAN}" && \
  REPO="${REPO_SAN}" POC_DIR="${INST_DIR}/repro" \
  ASAN_OPTIONS=use_sigaltstack=0:abort_on_error=0:halt_on_error=1:print_summary=1:detect_leaks=0 \
  UBSAN_OPTIONS=print_stacktrace=1:halt_on_error=1 \
  timeout 60 bash -c "${HARNESS}" ) >"${RUN_LOG}" 2>&1
RUN_RC=$?

# 4) Fingerprint match
EXPECTED_FP="$(python3.12 -c "import json; print(json.loads(open('${INST_JSON}').read()).get('expected_fingerprint',''))")"
FP_OK=true
if [ -n "${EXPECTED_FP}" ]; then
    while IFS= read -r FP_LINE; do
        [ -z "${FP_LINE}" ] && continue
        if ! grep -qF -- "${FP_LINE}" "${RUN_LOG}"; then
            echo "  fingerprint missing: ${FP_LINE:0:80}"
            FP_OK=false
        fi
    done <<< "${EXPECTED_FP}"
fi

if [ "${FP_OK}" = true ] && [ -n "${EXPECTED_FP}" ]; then
    NEW_STATUS=validated
    NOTE="all fingerprint lines matched (${DATE_NOW})"
elif [ "${RUN_RC}" -ne 0 ] && [ -z "${EXPECTED_FP}" ]; then
    # No fingerprint set, and runner returned non-zero — likely crashed.
    NEW_STATUS=pending
    NOTE="harness returned rc=${RUN_RC}; expected_fingerprint empty, can't auto-validate (${DATE_NOW})"
else
    NEW_STATUS=invalidated_poc_failed
    NOTE="harness rc=${RUN_RC}; fingerprint check ${FP_OK} (${DATE_NOW})"
fi

echo "[validate] result=${NEW_STATUS} (${NOTE})"

python3.12 -c "
import json
p='${INST_JSON}'; d=json.loads(open(p).read())
d['validation_status']='${NEW_STATUS}'
d['validation_notes']='''${NOTE}'''
open(p,'w').write(json.dumps(d, indent=2)+'\n')
"

# Append to validation_report.md
REPORT="${BENCH_ROOT}/validation_report.md"
if [ ! -f "${REPORT}" ]; then
    cat > "${REPORT}" <<EOF
# Validation report

Auto-generated by \`scripts/validate_instance.sh\`. Each row records the latest
validation attempt for one instance.

| date | instance_id | status | rc | notes |
|---|---|---|---|---|
EOF
fi
printf "| %s | %s | %s | %s | %s |\n" \
    "${DATE_NOW}" "${INSTANCE_ID}" "${NEW_STATUS}" "${RUN_RC}" "${NOTE}" \
    >> "${REPORT}"

if [ "${NEW_STATUS}" = "validated" ]; then exit 0; else exit 1; fi
