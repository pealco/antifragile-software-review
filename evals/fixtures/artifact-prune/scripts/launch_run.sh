#!/usr/bin/env bash
# Start or resume an experiment run on the shared box, then archive it.
#
#   scripts/launch_run.sh <run-name> [trainkit args...]
#   scripts/launch_run.sh --resume <run-name> [trainkit args...]
#
# --resume continues an existing run: trainkit adds new trials to runs/<run-name>/trials/.
set -uo pipefail

resume=()
if [[ "${1:-}" == "--resume" ]]; then
  resume=(--resume)
  shift
fi
run="${1:?usage: launch_run.sh [--resume] <run-name> [trainkit args...]}"
shift

cd "$(dirname "$0")/.."
mkdir -p logs

python -m trainkit.run --out "runs/$run" "${resume[@]}" "$@" 2>&1 | tee -a "logs/$run.launch.log"
status=${PIPESTATUS[0]}

if [[ $status -ne 0 ]]; then
  echo "run $run exited with status $status; not pushing" >&2
  exit "$status"
fi

if ! runstash push "$run"; then
  echo "warning: push of $run failed; run 'runstash push $run' by hand" >&2
fi
