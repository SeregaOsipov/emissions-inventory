#!/bin/bash -l
#SBATCH --job-name=gfas_12_preproc_batch
#SBATCH --partition=workq  # shared
#SBATCH --account=k10009
#SBATCH --ntasks=192
#SBATCH --hint=nomultithread
#SBATCH --time=8:00:00
#SBATCH --mail-type=FAIL         # send email if job fails
#SBATCH --mail-user=Sergey.Osipov@kaust.edu.sa

source /project/k10066/osipovs/.commonrc; gogomamba; mamba activate py311_hermes

echo "gfas_12_preproc_batch.sh"

input_folder_path=/project/k10048/osipovs/Data/emissions/CAMS-GFAS/
output_folder_path=/scratch/osipovs/bandwidth/Data/emissions/CAMS-GFAS/hermesv3_gr_pp/

MAX_JOBS=192  # Semaphore implementation
RUNNING_JOBS=0

for file in $input_folder_path/ga_2021*.grb  # EDIT YEAR HERE
do
	file_base_name="$(basename ${file})"
  file_date=$(echo "$file_base_name" | cut -d'_' -f2 | cut -d'.' -f1)
  echo "Processing file: $file (Date: $file_date)."

#  if [[ "$file_date" < "2021-02-01" ]]; then  # apply filter if needed
#        echo "Skipping"
#        continue
#  fi

	out_file_path=$output_folder_path/${file_base_name}

	# Check if the number of running jobs has reached the limit
  if [ $RUNNING_JOBS -ge $MAX_JOBS ]; then
      wait -n  # Wait for any background job to finish
      ((RUNNING_JOBS--))  # Decrease the counter
  fi

	# it is very important to specify memory per job to run in parallel
	srun -N 1 -n 1 --hint=nomultithread --cpus-per-task=2 --mem=32G --exclusive python -u ${HERMES_v3}/preproc/gfas12_preproc.py --in_file_path=${file} --output_folder_path=${output_folder_path} &

  ((RUNNING_JOBS++))  # Increment the running jobs counter
done

wait  # Wait for all remaining background jobs to complete

echo "DONE"