#!/bin/bash
set -euo pipefail

# Mirror an entire EDGAR dataset tree using lftp.
# Usage: ./download_edgar_dataset.sh [DATASET]
# Example datasets: EDGAR_2024_GHG, v81_FT2022_AP_new, v81_FT2022_VOC_spec

DATASET="${1:-${DATASET:-v81_FT2022_AP_new}}"
EMISSIONS_DATA_ROOT="${EMISSIONS_DATA_ROOT:-/HDD1/Data/emissions}"
LOCAL_DIR="${2:-${EMISSIONS_DATA_ROOT}/EDGAR/${DATASET}/}"

FTP_HOST="https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/EDGAR/datasets/${DATASET}/"
FTP_USER="anonymous"
FTP_PASS=""
REMOTE_DIR=""

if ! command -v lftp &> /dev/null; then
    CONDA_LFTP="${CONDA_LFTP:-/home/osipovs/apps/miniforge3/envs/py311_hermes/bin/lftp}"
    if [ -x "${CONDA_LFTP}" ]; then
        export PATH="$(dirname "${CONDA_LFTP}"):${PATH}"
    fi
fi

if ! command -v lftp &> /dev/null; then
    echo "Error: lftp is not installed. Activate py311_hermes or install lftp."
    exit 1
fi

mkdir -p "${LOCAL_DIR}"

lftp -u "${FTP_USER}","${FTP_PASS}" "${FTP_HOST}" << EOF
  set net:timeout 30
  set net:max-retries 3
  set ftp:ssl-allow yes
  set ftp:passive-mode yes
  mirror --verbose --parallel=5 "${REMOTE_DIR}" "${LOCAL_DIR}"
  quit
EOF

echo "Download completed successfully. Files are in ${LOCAL_DIR}"
