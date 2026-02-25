# Unitree Sim IsaacLab — Setup Guide

Tested on: Ubuntu 22.04 LTS, RTX 5090, Driver 590.48.01, 2025-02-17

> RTX 50-series GPUs **require** the Isaac Sim 5.0.0 path (Python 3.11).

## Prerequisites

```bash
sudo apt update
sudo apt install cmake build-essential git-lfs
```

Ensure you have **conda** installed (Miniconda or Anaconda).

---

## Step 1: Clone the repo and submodules

```bash
git clone https://github.com/unitreerobotics/unitree_sim_isaaclab.git
cd unitree_sim_isaaclab
git submodule update --init --depth 1
```

### Fix: teleimager Python version constraint

The `teleimager` submodule restricts Python to `<3.11`, but Isaac Sim 5.0 requires 3.11.
Edit `teleimager/pyproject.toml` line 10:

```diff
- requires-python = ">=3.8,<3.11"
+ requires-python = ">=3.8,<3.12"
```

---

## Step 2: Create conda environment

```bash
conda create -n unitree_sim_env python=3.11 -y
conda activate unitree_sim_env
```

---

## Step 3: Install Isaac Sim 5.0.0

```bash
pip install --upgrade pip
pip install "isaacsim[all,extscache]==5.0.0" --extra-index-url https://pypi.nvidia.com
```

Accept the EULA on first run:

```bash
echo "Yes" | isaacsim --help
```

---

## Step 4: Install Isaac Lab v2.2.0

```bash
git clone https://github.com/isaac-sim/IsaacLab.git /path/to/IsaacLab
cd /path/to/IsaacLab
git checkout v2.2.0
./isaaclab.sh --install
```

> **Important:** The `isaaclab.sh --install` script installs PyTorch 2.7.0+cu128 and
> many sub-packages, but may **skip the core `isaaclab` package**. Verify and install
> it manually if needed:

```bash
pip show isaaclab || pip install --no-build-isolation -e /path/to/IsaacLab/source/isaaclab
```

If `flatdict` fails to build with `ModuleNotFoundError: No module named 'pkg_resources'`,
make sure setuptools is **< 82**:

```bash
pip install "setuptools<82"
pip install --no-build-isolation -e /path/to/IsaacLab/source/isaaclab
```

---

## Step 5: Build CycloneDDS from source

`unitree_sdk2_python` requires CycloneDDS 0.10.x built from source:

```bash
git clone https://github.com/eclipse-cyclonedds/cyclonedds.git
cd cyclonedds
git checkout releases/0.10.x
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$(pwd)/../install -DBUILD_EXAMPLES=OFF
cmake --build . --parallel $(nproc)
cmake --install .
cd ../..
```

Set the environment variable (add to your shell profile):

```bash
export CYCLONEDDS_HOME=/absolute/path/to/cyclonedds/install
export LD_LIBRARY_PATH="${CYCLONEDDS_HOME}/lib:${LD_LIBRARY_PATH}"
```

---

## Step 6: Install unitree_sdk2_python

```bash
git clone https://github.com/unitreerobotics/unitree_sdk2_python
cd unitree_sdk2_python
pip install -e .
cd ..
```

> This will install `cyclonedds==0.10.2` Python bindings using the CycloneDDS you built.
> If it fails with "Could not locate cyclonedds", double-check `CYCLONEDDS_HOME` is set.

---

## Step 7: Install project dependencies

```bash
cd unitree_sim_isaaclab

# Core requirements
pip install -r requirements.txt

# teleimager with server extras (needed for image streaming)
pip install -e "teleimager[server]"

# IK library (pin-pink, NOT "pink" which is a code formatter)
pip install pin-pink "qpsolvers[open_source_solvers]"
```

### Fix: Pin numpy to 1.26.0

Several packages (pinocchio, pin-pink) pull in numpy >= 2.x, but Isaac Sim requires 1.26.0.
**Always run this as the last step after all pip installs:**

```bash
pip install numpy==1.26.0
```

---

## Step 8: Download USD assets

```bash
sudo apt install git-lfs   # if not already installed
cd unitree_sim_isaaclab
. fetch_assets.sh
```

This downloads ~1.2 GB of robot/scene USD models from HuggingFace into `./assets/`.

---

## Running the Simulator

### Activate environment

```bash
conda activate unitree_sim_env
export CYCLONEDDS_HOME=/absolute/path/to/cyclonedds/install
export LD_LIBRARY_PATH="${CYCLONEDDS_HOME}/lib:${LD_LIBRARY_PATH}"
```

Or use the helper script:

```bash
source activate_env.sh
```

### Teleoperation mode

```bash
python sim_main.py --device cpu --enable_cameras \
  --task Isaac-PickPlace-Cylinder-G129-Dex1-Joint \
  --enable_dex1_dds --robot_type g129
```

### Data replay mode

```bash
python sim_main.py --device cpu --enable_cameras \
  --task Isaac-Stack-RgyBlock-G129-Dex1-Joint \
  --enable_dex1_dds --robot_type g129 \
  --replay --file_path "/path/to/dataset"
```

### Data generation (augmentation)

```bash
python sim_main.py --device cpu --enable_cameras \
  --task Isaac-Stack-RgyBlock-G129-Dex1-Joint \
  --enable_dex1_dds --robot_type g129 \
  --replay --file_path "/path/to/dataset" \
  --generate_data --generate_data_dir "./data_out"
```

### Headless mode (no GUI)

Add `--headless` to any command above.

### Keyboard control (for Wholebody tasks only)

```bash
python send_commands_keyboard.py
```

---

## Available Tasks

| Task Name | Robot | Hand | Mobile |
|-----------|-------|------|--------|
| `Isaac-PickPlace-Cylinder-G129-Dex1-Joint` | G1 29-DOF | Gripper | No |
| `Isaac-PickPlace-Cylinder-G129-Dex3-Joint` | G1 29-DOF | Dex3 | No |
| `Isaac-PickPlace-Cylinder-G129-Inspire-Joint` | G1 29-DOF | Inspire | No |
| `Isaac-PickPlace-RedBlock-G129-Dex1-Joint` | G1 29-DOF | Gripper | No |
| `Isaac-PickPlace-RedBlock-G129-Dex3-Joint` | G1 29-DOF | Dex3 | No |
| `Isaac-PickPlace-RedBlock-G129-Inspire-Joint` | G1 29-DOF | Inspire | No |
| `Isaac-Stack-RgyBlock-G129-Dex1-Joint` | G1 29-DOF | Gripper | No |
| `Isaac-Stack-RgyBlock-G129-Dex3-Joint` | G1 29-DOF | Dex3 | No |
| `Isaac-Stack-RgyBlock-G129-Inspire-Joint` | G1 29-DOF | Inspire | No |
| `Isaac-PickRedblockIntoDrawer-G129-Dex1-Joint` | G1 29-DOF | Gripper | No |
| `Isaac-PickRedblockIntoDrawer-G129-Dex3-Joint` | G1 29-DOF | Dex3 | No |
| `Isaac-Move-Cylinder-G129-Dex1-Wholebody` | G1 29-DOF | Gripper | Yes |
| `Isaac-Move-Cylinder-G129-Dex3-Wholebody` | G1 29-DOF | Dex3 | Yes |
| `Isaac-Move-Cylinder-G129-Inspire-Wholebody` | G1 29-DOF | Inspire | Yes |
| `Isaac-PickPlace-Cylinder-H12-27dof-Inspire-Joint` | H1-2 | Inspire | No |
| `Isaac-PickPlace-RedBlock-H12-27dof-Inspire-Joint` | H1-2 | Inspire | No |
| `Isaac-Stack-RgyBlock-H12-27dof-Inspire-Joint` | H1-2 | Inspire | No |

DDS flags: `--enable_dex1_dds` (gripper), `--enable_dex3_dds` (Dex3), `--enable_inspire_dds` (Inspire)

---

## Notes

- **First launch is slow** — Isaac Sim compiles shaders and caches assets.
- After the scene loads, click **PerspectiveCamera → Cameras → PerspectiveCamera** for the main view.
- The simulator uses the **same DDS topics as the real robot** (channel 1). Keep it on a separate network from any real Unitree robot.
- Warp CUDA warnings about `cuDeviceGetUuid` on RTX 5090 are non-fatal and can be ignored.
- The `cmeel-boost` numpy incompatibility warning is cosmetic — pinocchio still works with numpy 1.26.0.

---

## Directory Layout

```
~/workspace/unitree_sim/
├── issac_lab/              # This repo (unitree_sim_isaaclab)
│   ├── sim_main.py         # Main entry point
│   ├── assets/             # USD models (downloaded via fetch_assets.sh)
│   ├── tasks/              # Task definitions
│   ├── dds/                # DDS communication
│   ├── action_provider/    # Action sources
│   ├── robots/             # Robot configs
│   ├── teleimager/         # Image server submodule
│   ├── activate_env.sh     # Environment activation helper
│   └── requirements.txt
├── IsaacLab/               # Isaac Lab v2.2.0
├── unitree_sdk2_python/    # Unitree SDK
└── cyclonedds/             # CycloneDDS (built from source)
    └── install/            # CYCLONEDDS_HOME points here
```

## Verified Package Versions

| Package | Version |
|---------|---------|
| Python | 3.11.14 |
| isaacsim | 5.0.0 |
| isaaclab | 0.44.9 |
| torch | 2.7.0+cu128 |
| numpy | 1.26.0 |
| unitree_sdk2py | 1.0.1 |
| cyclonedds | 0.10.2 |
| pin-pink | 3.1.0 |
| pinocchio (libpinocchio) | 3.9.0 |
| teleimager | 1.5.0 |
