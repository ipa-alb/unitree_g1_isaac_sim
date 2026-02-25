#!/usr/bin/env python3
"""
Orchestration CLI for Isaac Sim — lets Claude Code (or any agent) control the
simulation through shared memory.

Usage:
    python orchestrate/do.py state                    # read robot + scene state
    python orchestrate/do.py camera head              # save head camera to /tmp/
    python orchestrate/do.py camera all               # save all cameras

    python orchestrate/do.py walk forward 2           # walk forward for 2 s
    python orchestrate/do.py walk backward 1          # walk backward for 1 s
    python orchestrate/do.py walk left 1              # strafe left
    python orchestrate/do.py walk right 1             # strafe right
    python orchestrate/do.py walk turn-left 1         # rotate left
    python orchestrate/do.py walk turn-right 1        # rotate right
    python orchestrate/do.py walk stop                # stop (write zero vel)

    python orchestrate/do.py arms up                  # raise both arms
    python orchestrate/do.py arms down                # lower both arms (rest)
    python orchestrate/do.py arms forward             # extend forward
    python orchestrate/do.py arms set 15 -0.5         # set position[15] = -0.5
    python orchestrate/do.py arms set-left  0.0 0.2 0.0 -0.5 0.0 0.0 0.0
    python orchestrate/do.py arms set-right 0.0 -0.2 0.0 -0.5 0.0 0.0 0.0

    python orchestrate/do.py gripper open             # open both grippers
    python orchestrate/do.py gripper close            # close both grippers

    python orchestrate/do.py reset objects            # reset objects only
    python orchestrate/do.py reset all                # reset entire scene
"""

import sys
import os
import json
import time
import struct
import ctypes
import argparse
from multiprocessing import shared_memory, resource_tracker


def _untrack_shm(name: str):
    """Stop Python's resource tracker from destroying shared memory we don't own."""
    try:
        resource_tracker.unregister(f"/{name}", "shared_memory")
    except Exception:
        pass

# ---------------------------------------------------------------------------
# Shared memory helpers (matching the sim's format exactly)
# ---------------------------------------------------------------------------

def shm_read_json(name: str):
    """Read JSON data from a named shared memory segment (sim format:
    4-byte timestamp, 4-byte length, then JSON bytes)."""
    try:
        shm = shared_memory.SharedMemory(name=name)
        _untrack_shm(name)
    except FileNotFoundError:
        return None, f"shm '{name}' not found (is the sim running?)"
    try:
        ts = int.from_bytes(shm.buf[0:4], "little")
        dlen = int.from_bytes(shm.buf[4:8], "little")
        if dlen == 0:
            return None, "empty"
        raw = bytes(shm.buf[8 : 8 + dlen])
        data = json.loads(raw.decode("utf-8"))
        data["_shm_timestamp"] = ts
        return data, None
    except Exception as e:
        return None, str(e)
    finally:
        shm.close()


def shm_write_json(name: str, data: dict, size: int = 3072):
    """Write JSON data to a named shared memory segment."""
    try:
        shm = shared_memory.SharedMemory(name=name)
        _untrack_shm(name)
    except FileNotFoundError:
        print(f"ERROR: shm '{name}' not found — is the sim running?")
        return False
    try:
        raw = json.dumps(data).encode("utf-8")
        if len(raw) > size - 8:
            print(f"ERROR: data too large ({len(raw)} > {size - 8})")
            return False
        ts = int(time.time()) & 0xFFFFFFFF
        shm.buf[0:4] = ts.to_bytes(4, "little")
        shm.buf[4:8] = len(raw).to_bytes(4, "little")
        shm.buf[8 : 8 + len(raw)] = raw
        return True
    finally:
        shm.close()


# ---------------------------------------------------------------------------
# Camera shared memory reader (matching SimpleImageHeader from the sim)
# ---------------------------------------------------------------------------

class SimpleImageHeader(ctypes.LittleEndianStructure):
    _fields_ = [
        ("timestamp", ctypes.c_uint64),
        ("height", ctypes.c_uint32),
        ("width", ctypes.c_uint32),
        ("channels", ctypes.c_uint32),
        ("image_name", ctypes.c_char * 16),
        ("data_size", ctypes.c_uint32),
        ("encoding", ctypes.c_uint32),   # 0=raw, 1=JPEG
        ("quality", ctypes.c_uint32),
    ]


def read_camera(cam_name: str, save_path: str | None = None):
    """Read one camera frame from its dedicated shared memory."""
    shm_name = f"isaac_{cam_name}_image_shm"
    try:
        shm = shared_memory.SharedMemory(name=shm_name)
        _untrack_shm(shm_name)
    except FileNotFoundError:
        print(f"Camera shm '{shm_name}' not found")
        return None
    try:
        hdr_size = ctypes.sizeof(SimpleImageHeader)
        hdr = SimpleImageHeader.from_buffer_copy(bytes(shm.buf[:hdr_size]))
        payload = bytes(shm.buf[hdr_size : hdr_size + hdr.data_size])

        if save_path is None:
            save_path = f"/tmp/sim_camera_{cam_name}.jpg"

        if hdr.encoding == 1:  # JPEG
            with open(save_path, "wb") as f:
                f.write(payload)
        else:  # raw BGR
            import numpy as np
            import cv2
            img = np.frombuffer(payload, dtype=np.uint8).reshape(
                hdr.height, hdr.width, hdr.channels
            )
            cv2.imwrite(save_path, img)

        print(f"Saved {cam_name} ({hdr.width}x{hdr.height}) -> {save_path}")
        return save_path
    finally:
        shm.close()


# ---------------------------------------------------------------------------
# Command: state
# ---------------------------------------------------------------------------

def cmd_state(_args):
    """Print current robot state and scene state."""
    robot, err = shm_read_json("isaac_robot_state")
    if robot:
        print("=== Robot State (isaac_robot_state) ===")
        print(json.dumps(robot, indent=2))
    else:
        print(f"Robot state: {err}")

    scene, err = shm_read_json("isaac_sim_state")
    if scene:
        print("\n=== Scene State (isaac_sim_state) ===")
        print(json.dumps(scene, indent=2))
    else:
        print(f"Scene state: {err}")

    # Also try to read the current run command state (for wholebody)
    run_state, err = shm_read_json("isaac_run_command_state")
    if run_state:
        print("\n=== Run Command State (isaac_run_command_state) ===")
        print(json.dumps(run_state, indent=2))


# ---------------------------------------------------------------------------
# Command: camera
# ---------------------------------------------------------------------------

def cmd_camera(args):
    cam = args.camera_name
    if cam == "all":
        for c in ["head", "left", "right"]:
            read_camera(c)
    else:
        read_camera(cam)


# ---------------------------------------------------------------------------
# Command: walk
# ---------------------------------------------------------------------------

WALK_PRESETS = {
    "forward":    [0.5, 0.0, 0.0, 0.8],
    "backward":   [-0.4, 0.0, 0.0, 0.8],
    "left":       [0.0, -0.3, 0.0, 0.8],
    "right":      [0.0, 0.3, 0.0, 0.8],
    "turn-left":  [0.0, 0.0, -0.5, 0.8],
    "turn-right": [0.0, 0.0, 0.5, 0.8],
    "stop":       [0.0, 0.0, 0.0, 0.8],
}


def cmd_walk(args):
    direction = args.direction
    duration = args.duration

    if direction not in WALK_PRESETS:
        print(f"Unknown direction: {direction}")
        print(f"Available: {', '.join(WALK_PRESETS.keys())}")
        return

    vel = WALK_PRESETS[direction]
    print(f"Walking '{direction}' with vel={vel} for {duration}s ...")

    # Walk commands are consumed once per read, so we need to keep writing.
    # The wholebody action provider reads ~100Hz from shm.
    interval = 0.008  # ~125Hz write rate
    end_time = time.time() + duration

    while time.time() < end_time:
        shm_write_json(
            "isaac_run_command_cmd",
            {"run_command": str(vel)},
            size=512,
        )
        time.sleep(interval)

    # Stop after duration
    shm_write_json(
        "isaac_run_command_cmd",
        {"run_command": str([0.0, 0.0, 0.0, 0.8])},
        size=512,
    )
    print("Done.")


# ---------------------------------------------------------------------------
# Command: arms
# ---------------------------------------------------------------------------

# Arm joint indices inside the 29-element DDS positions array:
#   Left arm  = positions[15:22]  (7 joints)
#   Right arm = positions[22:29]  (7 joints)
# Joint order per arm: shoulder_pitch, shoulder_roll, shoulder_yaw,
#                       elbow, wrist_roll, wrist_pitch, wrist_yaw

ARM_POSES = {
    # [left_arm_7_joints, right_arm_7_joints]
    "up": {
        "left":  [-1.5, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0],
        "right": [-1.5, -0.2, 0.0, 0.0, 0.0, 0.0, 0.0],
    },
    "down": {
        "left":  [0.0, 0.2, 0.0, 0.0, 0.0, 0.0, 0.0],
        "right": [0.0, -0.2, 0.0, 0.0, 0.0, 0.0, 0.0],
    },
    "forward": {
        "left":  [-0.8, 0.2, 0.0, -0.5, 0.0, 0.0, 0.0],
        "right": [-0.8, -0.2, 0.0, -0.5, 0.0, 0.0, 0.0],
    },
    "t-pose": {
        "left":  [0.0, 1.4, 0.0, 0.0, 0.0, 0.0, 0.0],
        "right": [0.0, -1.4, 0.0, 0.0, 0.0, 0.0, 0.0],
    },
}


def _build_arm_cmd(left_7, right_7):
    """Build a dds_robot_cmd compatible dict from 7-element arm arrays."""
    positions = [0.0] * 29
    positions[15:22] = left_7
    positions[22:29] = right_7
    return {
        "motor_cmd": {
            "positions": positions,
            "velocities": [0.0] * 29,
            "torques": [0.0] * 29,
            "kp": [0.0] * 29,
            "kd": [0.0] * 29,
        }
    }


def cmd_arms(args):
    subcmd = args.arm_subcmd

    if subcmd in ARM_POSES:
        pose = ARM_POSES[subcmd]
        cmd = _build_arm_cmd(pose["left"], pose["right"])
        ok = shm_write_json("dds_robot_cmd", cmd)
        print(f"Arms -> '{subcmd}' : {'OK' if ok else 'FAIL'}")
        return

    if subcmd == "set":
        # Set a single position index: arms set <idx> <value>
        idx = int(args.extra[0])
        val = float(args.extra[1])
        # Read current cmd first
        current, _ = shm_read_json("dds_robot_cmd")
        if current and "motor_cmd" in current:
            current["motor_cmd"]["positions"][idx] = val
        else:
            cmd = _build_arm_cmd([0.0]*7, [0.0]*7)
            cmd["motor_cmd"]["positions"][idx] = val
            current = cmd
        # Remove internal keys
        current.pop("_shm_timestamp", None)
        current.pop("_timestamp", None)
        ok = shm_write_json("dds_robot_cmd", current)
        print(f"Set positions[{idx}] = {val} : {'OK' if ok else 'FAIL'}")
        return

    if subcmd == "set-left":
        vals = [float(x) for x in args.extra[:7]]
        if len(vals) < 7:
            vals += [0.0] * (7 - len(vals))
        # Keep right arm from current state or zero
        current, _ = shm_read_json("dds_robot_cmd")
        right = [0.0] * 7
        if current and "motor_cmd" in current:
            right = current["motor_cmd"]["positions"][22:29]
        cmd = _build_arm_cmd(vals, right)
        ok = shm_write_json("dds_robot_cmd", cmd)
        print(f"Left arm set to {vals} : {'OK' if ok else 'FAIL'}")
        return

    if subcmd == "set-right":
        vals = [float(x) for x in args.extra[:7]]
        if len(vals) < 7:
            vals += [0.0] * (7 - len(vals))
        current, _ = shm_read_json("dds_robot_cmd")
        left = [0.0] * 7
        if current and "motor_cmd" in current:
            left = current["motor_cmd"]["positions"][15:22]
        cmd = _build_arm_cmd(left, vals)
        ok = shm_write_json("dds_robot_cmd", cmd)
        print(f"Right arm set to {vals} : {'OK' if ok else 'FAIL'}")
        return

    print(f"Unknown arm command: {subcmd}")
    print(f"Available: {', '.join(ARM_POSES.keys())}, set, set-left, set-right")


# ---------------------------------------------------------------------------
# Command: gripper
# ---------------------------------------------------------------------------

def cmd_gripper(args):
    action = args.gripper_action
    # Gripper joint range: 0.03 (open) to -0.02 (closed) in Isaac Lab
    if action == "open":
        pos = 0.03
    elif action == "close":
        pos = -0.02
    else:
        pos = float(action)

    cmd = {
        "left_gripper_cmd": {
            "positions": [pos],
            "velocities": [0.0],
            "torques": [0.0],
            "kp": [0.0],
            "kd": [0.0],
        },
        "right_gripper_cmd": {
            "positions": [pos],
            "velocities": [0.0],
            "torques": [0.0],
            "kp": [0.0],
            "kd": [0.0],
        },
    }
    ok = shm_write_json("isaac_gripper_cmd", cmd, size=512)
    print(f"Gripper -> '{action}' (pos={pos}) : {'OK' if ok else 'FAIL'}")


# ---------------------------------------------------------------------------
# Command: reset
# ---------------------------------------------------------------------------

def cmd_reset(args):
    cat = args.reset_type
    cat_code = "1" if cat == "objects" else "2"
    ok = shm_write_json(
        "isaac_reset_pose_cmd",
        {"reset_category": cat_code},
        size=512,
    )
    print(f"Reset '{cat}' (category={cat_code}) : {'OK' if ok else 'FAIL'}")


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Isaac Sim orchestration CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # state
    sub.add_parser("state", help="Read robot + scene state")

    # camera
    p_cam = sub.add_parser("camera", help="Save camera frame to /tmp/")
    p_cam.add_argument("camera_name", choices=["head", "left", "right", "all"],
                        default="head", nargs="?")

    # walk
    p_walk = sub.add_parser("walk", help="Walk in a direction")
    p_walk.add_argument("direction",
                        choices=list(WALK_PRESETS.keys()))
    p_walk.add_argument("duration", type=float, nargs="?", default=1.0,
                        help="seconds (default 1.0)")

    # arms
    p_arms = sub.add_parser("arms", help="Control arm positions")
    p_arms.add_argument("arm_subcmd",
                        help="Pose name or: set, set-left, set-right")
    p_arms.add_argument("extra", nargs="*", help="Extra args for set commands")

    # gripper
    p_grip = sub.add_parser("gripper", help="Open / close grippers")
    p_grip.add_argument("gripper_action",
                        help="open | close | <float value>")

    # reset
    p_reset = sub.add_parser("reset", help="Reset scene")
    p_reset.add_argument("reset_type", choices=["objects", "all"],
                          default="objects", nargs="?")

    args = parser.parse_args()

    dispatch = {
        "state": cmd_state,
        "camera": cmd_camera,
        "walk": cmd_walk,
        "arms": cmd_arms,
        "gripper": cmd_gripper,
        "reset": cmd_reset,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
