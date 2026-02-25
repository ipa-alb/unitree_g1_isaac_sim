# Running the Robot — Orchestration & Control Guide

This document covers every way to move the Unitree G1 humanoid in the Isaac Sim environment: the CLI orchestrator, keyboard teleoperation, gamepad control, and the DDS reset utility.

---

## Prerequisites

**Terminal 1** always runs the simulator. Every other script connects to it.

```bash
cd /home/alb/workspace/unitree_sim/issac_lab
source activate_env.sh
```

---

## 1. Launching the Simulator (`sim_main.py`)

The sim must be running before any control script can send commands. Pick a task that matches what you want to do.

### Arm-only (stationary) tasks

Use these when the robot stands in place and manipulates objects with its arms and grippers.

```bash
# Pick & place a cylinder (2-finger gripper)
python sim_main.py --device cpu --enable_cameras \
  --task Isaac-PickPlace-Cylinder-G129-Dex1-Joint \
  --enable_dex1_dds --robot_type g129

# Pick & place a red block (3-finger dexterous hand)
python sim_main.py --device cpu --enable_cameras \
  --task Isaac-PickPlace-RedBlock-G129-Dex3-Joint \
  --enable_dex3_dds --robot_type g129

# Pick & place with Inspire hand
python sim_main.py --device cpu --enable_cameras \
  --task Isaac-PickPlace-Cylinder-G129-Inspire-Joint \
  --enable_inspire_dds --robot_type g129

# Stack coloured blocks (2-finger gripper)
python sim_main.py --device cpu --enable_cameras \
  --task Isaac-Stack-RgyBlock-G129-Dex1-Joint \
  --enable_dex1_dds --robot_type g129

# Pick red block into drawer (2-finger gripper)
python sim_main.py --device cpu --enable_cameras \
  --task Isaac-Pick-Redblock-Into-Drawer-G129-Dex1-Joint \
  --enable_dex1_dds --robot_type g129
```

### Wholebody (locomotion + arms) tasks

Use these when you also need the robot to walk around. **Only wholebody tasks support the `walk` command.**

```bash
# Walk + manipulate cylinder (2-finger gripper)
python sim_main.py --device cpu --enable_cameras \
  --task Isaac-Move-Cylinder-G129-Dex1-Wholebody \
  --enable_dex1_dds --enable_wholebody_dds --robot_type g129

# Walk + manipulate (3-finger hand)
python sim_main.py --device cpu --enable_cameras \
  --task Isaac-Move-Cylinder-G129-Dex3-Wholebody \
  --enable_dex3_dds --enable_wholebody_dds --robot_type g129

# Walk + manipulate (Inspire hand)
python sim_main.py --device cpu --enable_cameras \
  --task Isaac-Move-Cylinder-G129-Inspire-Wholebody \
  --enable_inspire_dds --enable_wholebody_dds --robot_type g129
```

### Useful optional flags

| Flag | Purpose |
|------|---------|
| `--headless` | Run without the GUI window |
| `--physics_dt 0.005` | Override physics timestep |
| `--render_interval 4` | Render every N steps (higher = faster sim, choppier visuals) |
| `--camera_write_interval 5` | Camera capture frequency (higher = less overhead) |
| `--camera_jpeg_quality 90` | JPEG quality for shared-memory camera frames (1-100) |
| `--step_hz 100` | Control loop frequency (default 100 Hz) |
| `--no_render` | Disable rendering entirely for max throughput |

### Startup sequence

1. GUI window opens (may take 30-60 s for shader compilation on first run)
2. You may need to **left-click the sim window** to unblock rendering
3. Wait for `"create dds success"` and `"start controller success"` in the logs — shared memory is now ready
4. Open a second terminal for control

---

## 2. CLI Orchestrator (`orchestrate/do.py`)

The primary control tool. Communicates via shared memory — no DDS dependency on the client side, fast and simple.

**Open a second terminal:**

```bash
cd /home/alb/workspace/unitree_sim/issac_lab
source activate_env.sh
```

### Read state

```bash
# Full robot joint state + scene object positions + walk command state
python orchestrate/do.py state
```

Returns JSON with joint positions, velocities, object poses, and (for wholebody tasks) the current velocity command.

### Camera snapshots

```bash
python orchestrate/do.py camera head          # save head camera  -> /tmp/sim_camera_head.jpg
python orchestrate/do.py camera left          # left wrist camera -> /tmp/sim_camera_left.jpg
python orchestrate/do.py camera right         # right wrist camera -> /tmp/sim_camera_right.jpg
python orchestrate/do.py camera all           # save all three
```

Requires the sim to be launched with `--enable_cameras`.

### Walk (wholebody tasks only)

Walk commands must be written continuously (~125 Hz) because the sim consumes them once per read. The CLI handles this for you over the given duration.

```bash
python orchestrate/do.py walk forward 2       # walk forward for 2 seconds
python orchestrate/do.py walk backward 1      # walk backward for 1 second
python orchestrate/do.py walk left 1          # strafe left
python orchestrate/do.py walk right 1         # strafe right
python orchestrate/do.py walk turn-left 1.5   # rotate left for 1.5 seconds
python orchestrate/do.py walk turn-right 1    # rotate right
python orchestrate/do.py walk stop            # zero velocity (immediate)
```

**Velocity presets used internally:**

| Direction | `[x_vel, y_vel, yaw_vel, height]` |
|-----------|-----------------------------------|
| forward | `[0.5, 0.0, 0.0, 0.8]` |
| backward | `[-0.4, 0.0, 0.0, 0.8]` |
| left | `[0.0, -0.3, 0.0, 0.8]` |
| right | `[0.0, 0.3, 0.0, 0.8]` |
| turn-left | `[0.0, 0.0, -0.5, 0.8]` |
| turn-right | `[0.0, 0.0, 0.5, 0.8]` |
| stop | `[0.0, 0.0, 0.0, 0.8]` |

### Arm control

#### Preset poses

```bash
python orchestrate/do.py arms up              # both arms raised overhead
python orchestrate/do.py arms down            # arms at rest by sides
python orchestrate/do.py arms forward         # arms extended forward (elbows slightly bent)
python orchestrate/do.py arms t-pose          # arms straight out to the sides
```

#### Individual joint control

The robot has 29 joint positions. **Arm joints are indices 15-28:**

- `[15-21]` — Left arm: shoulder_pitch, shoulder_roll, shoulder_yaw, elbow, wrist_roll, wrist_pitch, wrist_yaw
- `[22-28]` — Right arm: same order, shoulder_roll sign is mirrored

```bash
# Set a single joint: arms set <index> <radians>
python orchestrate/do.py arms set 15 -1.0     # left shoulder pitch up
python orchestrate/do.py arms set 18 -0.8     # left elbow bend

# Set all 7 joints for one arm at once
python orchestrate/do.py arms set-left  -0.8 0.2 0.0 -0.5 0.0 0.0 0.0
python orchestrate/do.py arms set-right -0.8 -0.2 0.0 -0.5 0.0 0.0 0.0
```

When using `set-left` or `set-right`, the other arm keeps its current position.

### Gripper control

```bash
python orchestrate/do.py gripper open         # open both grippers  (position = 0.03)
python orchestrate/do.py gripper close        # close both grippers (position = -0.02)
python orchestrate/do.py gripper 0.01         # set a specific gripper position
```

### Scene reset

```bash
python orchestrate/do.py reset objects        # reset only the manipulated objects
python orchestrate/do.py reset all            # reset the entire scene (robot + objects)
```

---

## 3. Keyboard Teleoperation (`send_commands_keyboard.py`)

Real-time control of locomotion using keyboard keys. Intended for wholebody tasks. Uses DDS directly (not shared memory).

```bash
python send_commands_keyboard.py
```

### Key bindings

| Key | Action | Range |
|-----|--------|-------|
| `W` | Walk forward | 0 to 1.0 m/s |
| `S` | Walk backward | 0 to -0.6 m/s |
| `A` | Strafe left | 0 to -0.5 m/s |
| `D` | Strafe right | 0 to 0.5 m/s |
| `Z` | Rotate left | 0 to -1.57 rad/s |
| `X` | Rotate right | 0 to 1.57 rad/s |
| `C` | Crouch | 0 to -0.5 height offset |
| `Q` | Quit | — |

**Hold** a key to ramp up velocity. **Release** to gradually decelerate back to zero. Velocity updates at 50 Hz with low-pass filtering for smooth motion.

Requires `pynput`:
```bash
pip install pynput
```

---

## 4. Gamepad Teleoperation (`send_commands_8bit.py`)

Control the robot with an 8BitDo (or similar) gamepad. Same locomotion parameters as keyboard but with analog stick precision. Uses DDS directly.

```bash
python send_commands_8bit.py
```

### Stick mapping

| Stick | Axis | Action | Range |
|-------|------|--------|-------|
| Left stick Y | Forward/backward | Walk forward when pushed up, backward when pulled down | -0.6 to 1.0 m/s |
| Left stick X | Lateral | Strafe left/right | -0.5 to 0.5 m/s |
| Right stick X | Rotation | Rotate left/right | -1.57 to 1.57 rad/s |
| Right stick Y | Crouch | Crouch when pushed in any direction | -0.7 to 0 height offset |

Features 5% deadzone, smooth s-curve response, low-pass filtering, and automatic zero-recovery when sticks are released.

Requires `evdev`:
```bash
pip install evdev
```

---

## 5. DDS Reset Test (`reset_pose_test.py`)

Standalone utility to reset scene objects via DDS. Useful for quick testing without the full orchestrator.

```bash
python reset_pose_test.py
```

Publishes a reset category `1` (objects only) to `rt/reset_pose/cmd`. To reset the full scene, modify the script to use category `2`.

---

## Available Tasks — Quick Reference

### G1 (29 DOF)

| Task ID | Activity | Hand | Locomotion |
|---------|----------|------|------------|
| `Isaac-PickPlace-Cylinder-G129-Dex1-Joint` | Pick & place cylinder | 2-finger gripper | No |
| `Isaac-PickPlace-Cylinder-G129-Dex3-Joint` | Pick & place cylinder | 3-finger hand | No |
| `Isaac-PickPlace-Cylinder-G129-Inspire-Joint` | Pick & place cylinder | Inspire hand | No |
| `Isaac-PickPlace-RedBlock-G129-Dex1-Joint` | Pick & place red block | 2-finger gripper | No |
| `Isaac-PickPlace-RedBlock-G129-Dex3-Joint` | Pick & place red block | 3-finger hand | No |
| `Isaac-PickPlace-RedBlock-G129-Inspire-Joint` | Pick & place red block | Inspire hand | No |
| `Isaac-Stack-RgyBlock-G129-Dex1-Joint` | Stack coloured blocks | 2-finger gripper | No |
| `Isaac-Stack-RgyBlock-G129-Dex3-Joint` | Stack coloured blocks | 3-finger hand | No |
| `Isaac-Stack-RgyBlock-G129-Inspire-Joint` | Stack coloured blocks | Inspire hand | No |
| `Isaac-Pick-Redblock-Into-Drawer-G129-Dex1-Joint` | Pick block into drawer | 2-finger gripper | No |
| `Isaac-Pick-Redblock-Into-Drawer-G129-Dex3-Joint` | Pick block into drawer | 3-finger hand | No |
| `Isaac-Move-Cylinder-G129-Dex1-Wholebody` | Walk + manipulate | 2-finger gripper | Yes |
| `Isaac-Move-Cylinder-G129-Dex3-Wholebody` | Walk + manipulate | 3-finger hand | Yes |
| `Isaac-Move-Cylinder-G129-Inspire-Wholebody` | Walk + manipulate | Inspire hand | Yes |

### H1-2 (27 DOF)

| Task ID | Activity | Hand | Locomotion |
|---------|----------|------|------------|
| `Isaac-PickPlace-Cylinder-H12-27dof-Inspire-Joint` | Pick & place cylinder | Inspire hand | No |
| `Isaac-PickPlace-RedBlock-H12-27dof-Inspire-Joint` | Pick & place red block | Inspire hand | No |
| `Isaac-Stack-RgyBlock-H12-27dof-Inspire-Joint` | Stack coloured blocks | Inspire hand | No |

---

## Typical Workflow Examples

### Example 1: Pick up a cylinder

```bash
# Terminal 1 — start the sim
python sim_main.py --device cpu --enable_cameras \
  --task Isaac-PickPlace-Cylinder-G129-Dex1-Joint \
  --enable_dex1_dds --robot_type g129

# Terminal 2 — control the robot
python orchestrate/do.py state                          # check initial state
python orchestrate/do.py camera head                    # see what the robot sees
python orchestrate/do.py arms forward                   # reach forward
python orchestrate/do.py gripper open                   # open gripper
python orchestrate/do.py arms set-left -0.8 0.2 0.0 -0.5 0.0 0.0 0.0   # fine-tune left arm
python orchestrate/do.py gripper close                  # grasp
python orchestrate/do.py arms up                        # lift
python orchestrate/do.py camera head                    # verify pick
```

### Example 2: Walk to an object and pick it up

```bash
# Terminal 1 — start with wholebody task
python sim_main.py --device cpu --enable_cameras \
  --task Isaac-Move-Cylinder-G129-Dex1-Wholebody \
  --enable_dex1_dds --enable_wholebody_dds --robot_type g129

# Terminal 2 — walk then manipulate
python orchestrate/do.py state                          # see where the object is
python orchestrate/do.py walk forward 3                 # approach the object
python orchestrate/do.py walk turn-left 1               # adjust heading
python orchestrate/do.py walk forward 1                 # close the gap
python orchestrate/do.py walk stop                      # halt
python orchestrate/do.py arms forward                   # reach
python orchestrate/do.py gripper close                  # grab
python orchestrate/do.py arms up                        # lift
```

### Example 3: Real-time keyboard control

```bash
# Terminal 1 — start the sim (wholebody task)
python sim_main.py --device cpu --enable_cameras \
  --task Isaac-Move-Cylinder-G129-Dex1-Wholebody \
  --enable_dex1_dds --enable_wholebody_dds --robot_type g129

# Terminal 2 — keyboard teleoperation
python send_commands_keyboard.py
# Hold W to walk forward, A/D to strafe, Z/X to rotate, C to crouch, Q to quit
```

---

## Architecture at a Glance

```
                ┌──────────────────────────┐
                │      Isaac Sim           │
                │   (sim_main.py)          │
                │                          │
                │  Physics ─► DDS Objects  │
                │              │           │
                │        Shared Memory     │
                └──────────┬───────────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │ do.py       │ │  keyboard   │ │  gamepad    │
    │ (shm CLI)   │ │  (DDS)      │ │  (DDS)      │
    └─────────────┘ └─────────────┘ └─────────────┘
```

- **do.py** reads/writes shared memory segments directly — no DDS libraries needed on the client side
- **keyboard / gamepad controllers** publish DDS messages to `rt/run_command/cmd` and require `unitree_sdk2py`
- The sim creates all shared memory segments on startup; client scripts attach to them by name
