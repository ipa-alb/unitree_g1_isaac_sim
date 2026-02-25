#!/bin/bash
# Activate the unitree_sim_isaaclab environment
# Usage: source activate_env.sh

eval "$(conda shell.bash hook)"
conda activate unitree_sim_env

export CYCLONEDDS_HOME=/home/alb/workspace/unitree_sim/cyclonedds/install
export LD_LIBRARY_PATH="${CYCLONEDDS_HOME}/lib:${LD_LIBRARY_PATH}"

echo "Environment activated: unitree_sim_env"
echo "  Python: $(python --version)"
echo "  CYCLONEDDS_HOME: ${CYCLONEDDS_HOME}"
