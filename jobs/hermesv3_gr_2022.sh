#!/bin/bash -l
#SBATCH --job-name=hermes_mpi_2022
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

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
HERMES_CONF="${1:-${REPO_ROOT}/conf/hermes_2022.conf}"
HERMES_PYTHON="${HERMES_PYTHON:-/home/osipovs/apps/miniforge3/envs/py311_hermes/bin/python}"
HERMES_ENTRY="${HERMES_ENTRY:-${REPO_ROOT}/models/hermesv3_gr/hermesv3_gr/hermes.py}"

if [ -x "${HERMES_PYTHON}" ]; then
    export PATH="$(dirname "${HERMES_PYTHON}"):${PATH}"
else
    HERMES_PYTHON="$(command -v python)"
fi

if [ -n "${SLURM_JOB_ID:-}" ]; then
    NTASKS="${SLURM_NTASKS:-1}"
    MPI_CMD=(srun -n "${NTASKS}" --hint=nomultithread --cpu_bind=core)
else
    NTASKS="${NTASKS:-8}"
    MPI_CMD=(mpirun -np "${NTASKS}")
fi

export PYTHONPATH="${REPO_ROOT}:${REPO_ROOT}/models/hermesv3_gr:${PYTHONPATH:-}"

echo "hermesv3_gr 2022"
"${MPI_CMD[@]}" "${HERMES_PYTHON}" "${HERMES_ENTRY}" -c "${HERMES_CONF}"
echo "DONE"
