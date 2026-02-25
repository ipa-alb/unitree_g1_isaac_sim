# Lessons Learned — Claude Orchestration of Isaac Sim

## Overview

We built a system where Claude Code directly orchestrates the Unitree G1 humanoid robot in Isaac Sim through shared memory — no API loop, no extra process, no cost beyond normal Claude Code usage.

## Architecture

```
You (natural language) → Claude Code → orchestrate/do.py → shared memory → Isaac Sim
```

The simulation already uses Python `multiprocessing.shared_memory` as its internal bus between DDS and the control loop. We bypass DDS entirely and write/read the same shared memory segments.

### Shared Memory Map

| Segment | Direction | Purpose |
|---------|-----------|---------|
| `dds_robot_cmd` | write | Arm joint targets (29-element positions array, indices 15-28 = arms) |
| `isaac_gripper_cmd` | write | Gripper open/close commands |
| `isaac_run_command_cmd` | write | Locomotion velocity `[x_vel, y_vel, yaw_vel, height]` (wholebody tasks only) |
| `isaac_reset_pose_cmd` | write | Reset scene (category 1 = objects, 2 = all) |
| `isaac_robot_state` | read | Current joint positions, velocities, torques, IMU |
| `isaac_sim_state` | read | Full scene state as JSON (object positions, robot root pose) |
| `isaac_{head,left,right}_image_shm` | read | Camera frames (JPEG or raw BGR with ctypes header) |

### Shared Memory Format

**JSON segments** (robot state, commands): 4-byte little-endian timestamp + 4-byte data length + UTF-8 JSON bytes.

**Image segments**: `SimpleImageHeader` ctypes struct (timestamp, width, height, channels, encoding, data_size) followed by raw payload.

## Bugs Found & Fixed

### 1. SharedMemoryManager created segments with random names

**File**: `dds/sharedmemorymanager.py`

**Problem**: When a named shared memory segment didn't exist yet, the code created one with a **random name** instead of the requested name:

```python
# BEFORE (broken):
except FileNotFoundError:
    self.shm = shared_memory.SharedMemory(create=True, size=size)  # random name!

# AFTER (fixed):
except FileNotFoundError:
    self.shm = shared_memory.SharedMemory(create=True, size=size, name=name)  # correct name
```

**Impact**: External processes (like our orchestration script) couldn't find the shared memory because the actual name was something like `psm_abc123` instead of `dds_robot_cmd`.

### 2. Python resource tracker destroys shared memory on script exit

**File**: `orchestrate/do.py`

**Problem**: Python's `multiprocessing.shared_memory` registers every opened segment with a resource tracker. When our short-lived CLI script exits, the tracker **unlinks (destroys)** the segment — even though the sim still needs it. The first `do.py` call works, the second fails because the shm was deleted.

```python
# FIX: unregister from the tracker immediately after opening
from multiprocessing import resource_tracker

def _untrack_shm(name: str):
    try:
        resource_tracker.unregister(f"/{name}", "shared_memory")
    except Exception:
        pass
```

**Impact**: Without this fix, the first command works but every subsequent command fails with `shm not found`. This is a well-known Python footgun with `shared_memory` across processes.

### 3. Teleimager DEBUG log spam floods the sim terminal

**File**: `sim_main.py`

**Problem**: The teleimager image server logs every camera frame at DEBUG level (~30Hz), making the sim terminal unreadable.

```python
# FIX: suppress before importing
import logging
logging.getLogger("teleimager").setLevel(logging.WARNING)
from teleimager.image_server import run_isaacsim_server
```

## Key Timing Details

- The sim takes **30-60 seconds** to fully initialize (shader compilation, scene creation, DDS setup)
- Shared memory segments only exist **after** `"create dds success"` appears in the sim log
- Camera shared memory (`isaac_*_image_shm`) is created earlier than DDS shared memory
- The `"Please left-click on the Sim window"` is **not** just informational — the sim may block on rendering until you click the window

## Arm Joint Mapping

For the G1 29-DOF robot, the DDS command `positions` array maps as:

| Index | Joint | Notes |
|-------|-------|-------|
| 0-14 | Legs / torso | Ignored in arm-only (Joint) tasks |
| 15 | left_shoulder_pitch | Negative = forward/up |
| 16 | left_shoulder_roll | Positive = outward |
| 17 | left_shoulder_yaw | |
| 18 | left_elbow | Negative = bend |
| 19-21 | left_wrist (roll, pitch, yaw) | |
| 22-28 | right arm (same order) | Roll sign is mirrored |

## Walking (Wholebody Tasks Only)

- Requires starting the sim with a `Wholebody` task (e.g., `Isaac-Move-Cylinder-G129-Dex1-Wholebody`)
- Velocity commands are **consumed once and reset to zero** by the action provider
- To sustain walking, commands must be written repeatedly (~100Hz)
- Format: `{"run_command": "[x_vel, y_vel, yaw_vel, height]"}` where height default = 0.8
- Velocity ranges: x=[-0.6, 1.0], y=[-0.5, 0.5], yaw=[-1.57, 1.57]

## Camera Names

The sim creates three cameras, but their shared memory names differ from their scene names:

| Scene name | Shared memory name |
|------------|-------------------|
| `front_camera` | `isaac_head_image_shm` |
| `left_wrist_camera` | `isaac_left_image_shm` |
| `right_wrist_camera` | `isaac_right_image_shm` |

## Debug Spam (Fixed)

The teleimager `image_server.py` produces very verbose DEBUG-level output (`head_camera - concatenated binocular frame`). Fixed by setting `logging.getLogger("teleimager").setLevel(logging.WARNING)` in `sim_main.py` before importing the image server.

## What's Next

- Tune arm pose presets (current `up`/`down`/`forward` angles are initial guesses)
- Add IK solver (pin-pink is installed) for Cartesian end-effector control
- Test wholebody walking orchestration
- Build higher-level task primitives (pick, place, stack) on top of the low-level commands
