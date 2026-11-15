#!/bin/bash -l
#SBATCH --job-name=hermes_mpi_thofa_2023
#SBATCH --account=k10009
#SBATCH --output=output.txt
#SBATCH --error=error.txt
#SBATCH --partition=workq
#SBATCH --ntasks=48
#SBATCH --hint=nomultithread
#SBATCH --time=4:00:00
#SBATCH --mail-type=end
#SBATCH --mail-user=Sergey.Osipov@kaust.edu.sa

set -euo pipefail

# Note: Add voc11 back to EDGARv81_VOC fuel_exploitation when running years other than 2022.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
HERMES_CONF="${1:-${REPO_ROOT}/conf/hermes_THOFA_2023.conf}"
HERMES_PYTHON="${HERMES_PYTHON:-/home/osipovs/apps/miniforge3/envs/py311_hermes/bin/python}"
HERMES_ENTRY="${HERMES_ENTRY:-${REPO_ROOT}/models/hermesv3_gr/hermesv3_gr/hermes.py}"

if [ -x "${HERMES_PYTHON}" ]; then
    ENV_BIN="$(dirname "${HERMES_PYTHON}")"
    export PATH="${ENV_BIN}:${PATH}"
else
    HERMES_PYTHON="$(command -v python)"
fi

if [ -n "${SLURM_JOB_ID:-}" ]; then
    NTASKS="${SLURM_NTASKS:-48}"
    MPI_CMD=(srun -n "${NTASKS}" --hint=nomultithread --cpu_bind=core)
else
    NTASKS="${NTASKS:-8}"
    MPI_CMD=(mpirun -np "${NTASKS}")
fi

export PYTHONPATH="${REPO_ROOT}:${REPO_ROOT}/models/hermesv3_gr:${PYTHONPATH:-}"

echo "hermesv3_gr THOFA 2023"
echo "Using Python: ${HERMES_PYTHON}"
echo "Using config: ${HERMES_CONF}"
"${MPI_CMD[@]}" "${HERMES_PYTHON}" "${HERMES_ENTRY}" -c "${HERMES_CONF}"
echo "DONE"
