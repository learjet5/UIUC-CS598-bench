#!/usr/bin/env bash
# Run scripts/validate_instance.sh on every instance under instances/ (or a
# subset matched by glob) and emit a CSV summary.
#
# Usage:
#   bash scripts/validate_all.sh              # all instances
#   bash scripts/validate_all.sh 'llama*'     # only llama instances (glob)
#   bash scripts/validate_all.sh --csv out.csv # write CSV to out.csv

set -u

BENCH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PATTERN="*"
CSV_OUT="${BENCH_ROOT}/validation_summary.csv"

while [ $# -gt 0 ]; do
    case "$1" in
        --csv) CSV_OUT="$2"; shift 2 ;;
        *) PATTERN="$1"; shift ;;
    esac
done

cd "${BENCH_ROOT}"

# Header
printf "instance_id,validation_status,duration_sec,build_rc,run_rc,notes\n" > "${CSV_OUT}"

shopt -s nullglob
for inst_dir in instances/${PATTERN}/; do
    [ -f "${inst_dir}/instance.json" ] || continue
    inst_id="$(basename "${inst_dir}")"
    echo "============================================================"
    echo "validate_all: ${inst_id}"
    echo "============================================================"

    t0=$(date +%s)
    bash scripts/validate_instance.sh "${inst_id}" >/dev/null 2>&1
    rc=$?
    t1=$(date +%s)
    duration=$(( t1 - t0 ))

    # Read final status + notes from instance.json
    status="$(python3.12 -c "import json; print(json.loads(open('${inst_dir}/instance.json').read()).get('validation_status','?'))")"
    notes="$(python3.12 -c "import json; print(json.loads(open('${inst_dir}/instance.json').read()).get('validation_notes','').replace(',',';').replace(chr(10),' '))")"
    build_rc="?"
    run_rc="?"
    if [ -f "${inst_dir}/.validation/build.log" ]; then
        # Crude — last line "Built target" means OK; otherwise scan for non-zero
        if grep -qE "(Built target|Linking)" "${inst_dir}/.validation/build.log" && \
           ! grep -qiE "(error:|FAILED)" "${inst_dir}/.validation/build.log"; then
            build_rc=0
        else
            build_rc=1
        fi
    fi
    if [ -f "${inst_dir}/.validation/run.log" ]; then
        run_rc="$(grep -cE "===EXIT" "${inst_dir}/.validation/run.log" || echo unknown)"
    fi
    printf "%s,%s,%s,%s,%s,\"%s\"\n" \
        "${inst_id}" "${status}" "${duration}" "${build_rc}" "${rc}" "${notes}" >> "${CSV_OUT}"
done

echo
echo "Summary written to ${CSV_OUT}:"
column -s, -t < "${CSV_OUT}" | head -50
