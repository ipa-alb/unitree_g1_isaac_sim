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

---

## Claude Orchestration (orchestrate/do.py)

Control the simulation via shared memory from a second terminal (or from Claude Code directly).
The sim must be running and fully initialized (`"start controller success"` visible in the sim log).

```bash
# In a second terminal (same folder, no conda env needed):
cd ~/workspace/unitree_sim/issac_lab
```

### Read State

```bash
python orchestrate/do.py state              # Print robot joints + scene objects as JSON
```

### Camera

```bash
python orchestrate/do.py camera head        # Save head camera to /tmp/sim_camera_head.jpg
python orchestrate/do.py camera left        # Left wrist camera
python orchestrate/do.py camera right       # Right wrist camera
python orchestrate/do.py camera all         # All three cameras
```

### Arm Control

```bash
python orchestrate/do.py arms up            # Both arms raised
python orchestrate/do.py arms down          # Both arms resting
python orchestrate/do.py arms forward       # Both arms extended forward
python orchestrate/do.py arms t-pose        # Both arms out to the sides

python orchestrate/do.py arms set 15 -0.5   # Set a single joint by index (15 = left shoulder pitch)
python orchestrate/do.py arms set-left  0.0 0.2 0.0 -0.5 0.0 0.0 0.0   # 7 joints: shoulder pitch/roll/yaw, elbow, wrist roll/pitch/yaw
python orchestrate/do.py arms set-right 0.0 -0.2 0.0 -0.5 0.0 0.0 0.0
```

### Walking (Wholebody tasks only)

Requires a Wholebody task (e.g., `Isaac-Move-Cylinder-G129-Dex1-Wholebody`).

```bash
python orchestrate/do.py walk forward 2     # Walk forward for 2 seconds
python orchestrate/do.py walk backward 1    # Walk backward for 1 second
python orchestrate/do.py walk left 1        # Strafe left
python orchestrate/do.py walk right 1       # Strafe right
python orchestrate/do.py walk turn-left 1   # Rotate left
python orchestrate/do.py walk turn-right 1  # Rotate right
python orchestrate/do.py walk stop          # Stop immediately
```

### Gripper

```bash
python orchestrate/do.py gripper open       # Open both grippers
python orchestrate/do.py gripper close      # Close both grippers
```

### Reset Scene

```bash
python orchestrate/do.py reset objects      # Reset objects only (keep robot pose)
python orchestrate/do.py reset all          # Reset entire scene
```
