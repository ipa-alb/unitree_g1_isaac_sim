# Quick Start — Unitree G1 Simulation

## Activate Environment

```bash
cd ~/workspace/unitree_sim/issac_lab
source activate_env.sh
```

## Run the Simulation

```bash
python sim_main.py --device cpu --enable_cameras \
  --task Isaac-PickPlace-Cylinder-G129-Dex1-Joint \
  --enable_dex1_dds --robot_type g129
```

> First launch takes 2-5 min (shader compilation). After the window opens, click
> **PerspectiveCamera -> Cameras -> PerspectiveCamera** for the main view.

## Switch Tasks

Replace `--task` and the matching `--enable_<hand>_dds` flag:

| Task | DDS Flag |
|------|----------|
| `Isaac-PickPlace-Cylinder-G129-Dex1-Joint` | `--enable_dex1_dds` |
| `Isaac-PickPlace-Cylinder-G129-Dex3-Joint` | `--enable_dex3_dds` |
| `Isaac-PickPlace-Cylinder-G129-Inspire-Joint` | `--enable_inspire_dds` |
| `Isaac-PickPlace-RedBlock-G129-Dex1-Joint` | `--enable_dex1_dds` |
| `Isaac-Stack-RgyBlock-G129-Dex1-Joint` | `--enable_dex1_dds` |
| `Isaac-PickRedblockIntoDrawer-G129-Dex1-Joint` | `--enable_dex1_dds` |
| `Isaac-Move-Cylinder-G129-Dex1-Wholebody` | `--enable_dex1_dds` |

Wholebody tasks enable locomotion — control with `python send_commands_keyboard.py` in a second terminal.

## Replay a Dataset

```bash
python sim_main.py --device cpu --enable_cameras \
  --task Isaac-Stack-RgyBlock-G129-Dex1-Joint \
  --enable_dex1_dds --robot_type g129 \
  --replay --file_path "/path/to/dataset"
```

## Generate Augmented Data

```bash
python sim_main.py --device cpu --enable_cameras \
  --task Isaac-Stack-RgyBlock-G129-Dex1-Joint \
  --enable_dex1_dds --robot_type g129 \
  --replay --file_path "/path/to/dataset" \
  --generate_data --generate_data_dir "./augmented_data"
```

## Headless (no GUI)

Add `--headless` to any command above.
