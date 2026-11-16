#!/bin/bash -l
#SBATCH --job-name=hermes_wrf_domain
#SBATCH --output=output.txt
#SBATCH --error=error.txt
#SBATCH --ntasks=24
#SBATCH --hint=nomultithread
#SBATCH --time=01:00:00

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
HERMES_PYTHON="${HERMES_PYTHON:-/home/osipovs/apps/miniforge3/envs/py311_hermes/bin/python}"

if [ ! -x "${HERMES_PYTHON}" ]; then
    HERMES_PYTHON="$(command -v python3 || command -v python)"
fi

exec "${HERMES_PYTHON}" "${REPO_ROOT}/cli/generate_wrfchemi.py" "$@"
