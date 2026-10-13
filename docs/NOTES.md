# ROS 2 Workspace Notes: Overlays, Dependencies, Building and Testing

Notes from getting `vision_package` (YOLO + usb_cam on ROS 2 Jazzy, Raspberry Pi) running for the first time.
Throughout, ROS concepts are compared with **pip + venv** and **uv** to map them onto something familiar.

---

## 1. The big picture

| Python world | ROS 2 world |
|---|---|
| Your project folder | A **workspace** (`vision_ws/`) |
| A Python package | A **ROS package** (`src/vision_package/`) |
| `requirements.txt` / `pyproject.toml` | **`package.xml`** |
| `pip install -r requirements.txt` / `uv sync` | **`rosdep install`** |
| `pip install -e .` / `uv build` | **`colcon build`** |
| `source .venv/bin/activate` | **`source install/setup.bash`** |
| System Python itself | The ROS install in `/opt/ros/jazzy` |

---

## 2. Underlays and overlays (the "activate" step)

### Python analogy
- **pip:** you create a venv (`python3 -m venv .venv`), then `source .venv/bin/activate`.
  Until you activate, `python` and anything installed in the venv aren't visible to your shell.
- **uv:** `uv init` creates the project and `uv sync` creates `.venv`. `uv run <cmd>` activates it for you for one command.

### ROS
ROS has **two layers** you "activate", in this order:

1. **Underlay:** ROS itself. This gives you the `ros2` command and all the official packages.
   ```bash
   source /opt/ros/jazzy/setup.bash
   ```
2. **Overlay:** your workspace, layered on top of the underlay.
   ```bash
   source ~/Engineering/Robotics/vision_ws/install/setup.bash
   ```

Think of it as a venv that sits on top of another venv. Your overlay can add packages, or override ones from the underlay, because it's searched first.

### What went wrong the first time
- `ros2: command not found` meant **the underlay wasn't sourced**. Without it, the `ros2` command doesn't exist in that shell.
- `install/setup.bash` only links back to the underlay if **the underlay was sourced when you ran `colcon build`**.
  Built without ROS sourced → the overlay doesn't know ROS exists → sourcing it doesn't give you `ros2`.
- Fix: open a fresh terminal → source the underlay → build → source the overlay.

### Every new terminal
```bash
source /opt/ros/jazzy/setup.bash                               # underlay (or put this in ~/.bashrc)
source ~/Engineering/Robotics/vision_ws/install/setup.bash     # overlay
```
Like a venv, sourcing only affects **the current terminal**. Each new tab starts with nothing active.

---

## 3. `package.xml` vs `requirements.txt`

### Python analogy
- **pip:** `requirements.txt` lists what to install, e.g. `ultralytics`, `numpy<2`.
- **uv:** `pyproject.toml` lists dependencies. You edit it indirectly with `uv add ultralytics` / `uv remove ultralytics`.

### ROS
`package.xml` lists what your package needs, but **it doesn't install anything by itself**. It's just a declaration.

```xml
<depend>rclpy</depend>                       <!-- needed to build AND run -->
<depend>cv_bridge</depend>
<exec_depend>usb_cam</exec_depend>           <!-- only needed at runtime -->
<exec_depend>vision_msgs</exec_depend>
<exec_depend>python3-ultralytics-pip</exec_depend>   <!-- a rosdep "key" that maps to pip -->
<test_depend>python3-pytest</test_depend>    <!-- only needed for tests -->
```

| Tag | Python equivalent |
|---|---|
| `<depend>` | a normal dependency |
| `<build_depend>` | build-time only (like `[build-system] requires`) |
| `<exec_depend>` | runtime only |
| `<test_depend>` | dev/test dependency (`uv add --dev`, or `requirements-dev.txt`) |

**Key difference:** names in `package.xml` are **rosdep keys**, not apt or pip names.
rosdep translates each key into the right installer for your OS:

```
usb_cam                  → apt: ros-jazzy-usb-cam
vision_msgs              → apt: ros-jazzy-vision-msgs
cv_bridge                → apt: ros-jazzy-cv-bridge
python3-ultralytics-pip  → pip: ultralytics
```
Check what a key resolves to with: `rosdep resolve <key>`

> **Lesson:** adding `usb_cam` to `package.xml` and running `colcon build` does **not** install usb_cam.
> That's like adding a line to `requirements.txt` and never running `pip install -r`.

---

## 4. Installing dependencies: `rosdep`

### Python analogy
- **pip:** `pip install -r requirements.txt`
- **uv:** `uv sync`. It reads the dependency list and installs whatever is missing.

### ROS
```bash
# one-time setup per machine
sudo rosdep init
rosdep update

# install everything listed in every package.xml under src/
cd ~/Engineering/Robotics/vision_ws
rosdep install --from-paths src --ignore-src -r -y
```
- `--from-paths src`: scan the packages in `src/` (like pointing pip at a requirements file)
- `--ignore-src`: don't try to install packages that are *already in your workspace*
- `-r`: keep going if one fails
- `-y`: answer yes to prompts

Check without installing:
```bash
rosdep check --from-paths src --ignore-src
```

### Big difference from a venv
`rosdep` installs **system-wide** (apt + `sudo pip`). There's no isolated environment by default.
That's why pip packages clash with apt packages in ROS, as covered next.

---

## 5. pip inside ROS: what went wrong and why

On Ubuntu 24.04 the system Python is **"externally managed"** (PEP 668). pip refuses to install into it so it can't break apt's Python packages.
In a normal Python project you'd just use a venv or uv and never hit this. ROS uses the system Python, so you do.

### Problem 1: PEP 668 refusal
```
rosdep installation of pip packages requires ... PIP_BREAK_SYSTEM_PACKAGES=1
```
Fix: allow pip to install alongside apt packages.
```bash
export PIP_BREAK_SYSTEM_PACKAGES=1      # export = visible to programs you run (rosdep, pip)
```
> **Shell lesson:** `VAR=1` on its own line is visible **only to the shell**, not to programs you start.
> Use `export VAR=1`, or put it on the same line: `VAR=1 rosdep install ...`

### Problem 2: pip can't uninstall apt's packages
```
ERROR: Cannot uninstall typing_extensions 4.10.0, RECORD file not found. Hint: The package was installed by debian.
```
pip wanted a newer version, but apt "owns" the old one. Fix: install pip's copy *alongside* apt's, as a separate command:
```bash
sudo -H pip3 install --break-system-packages --ignore-installed typing_extensions
```
> `--ignore-installed` is an on/off switch for the **whole command**, not for one package, so run it separately.

### Problem 3: wrong PyTorch build (about 3 GB of NVIDIA CUDA libraries)
The default ARM PyTorch on PyPI comes with CUDA support for NVIDIA boards (e.g. Jetson). A Raspberry Pi has no NVIDIA GPU.
Fix: use the CPU-only index.
```bash
sudo -H pip3 install --break-system-packages torch torchvision --index-url https://download.pytorch.org/whl/cpu
```
- **pip equivalent:** `pip install torch --index-url https://download.pytorch.org/whl/cpu`
- **uv equivalent:** add a `[[tool.uv.index]]` for the CPU wheel URL in `pyproject.toml`, then `uv add torch`

### Problem 4: numpy 2 would break ROS
ROS's `cv_bridge` (and other compiled packages) were built against apt's **numpy 1.x**. Upgrading to numpy 2 can crash them on import.
Fix: pin it, just like you would in `requirements.txt`.
```bash
sudo -H pip3 install --break-system-packages "numpy<2" ultralytics
```
- **pip:** `numpy<2` in `requirements.txt`
- **uv:** `uv add "numpy<2"`

### Verify the Python side
```bash
python3 -c "import numpy; print(numpy.__version__)"          # expect 1.x
python3 -c "import torch; print(torch.__version__)"          # expect ...+cpu
python3 -c "import ultralytics; print(ultralytics.__version__)"
python3 -c "from cv_bridge import CvBridge; import cv2; print('ok', cv2.__version__)"
```

---

## 6. Building: `colcon build`

### Python analogy
- **pip:** `pip install .` (or `pip install -e .`) builds your package and installs it into the venv.
- **uv:** `uv build` / `uv sync` installs your project into `.venv`.

### ROS
```bash
cd ~/Engineering/Robotics/vision_ws     # always build from the workspace ROOT, not src/
colcon build
```
colcon creates three folders:
| Folder | What it is | Python analogy |
|---|---|---|
| `build/` | intermediate build files | `build/`, `*.egg-info` |
| `install/` | the finished, runnable packages + `setup.bash` | the `.venv` |
| `log/` | build logs | — |

All three can be deleted at any time to start clean:
```bash
rm -rf build install log
```

### What colcon does NOT do
- It doesn't download or install dependencies (that's rosdep).
- It doesn't pick up code changes without a rebuild. Use `colcon build --symlink-install` so edits to Python files in `src/` take effect without rebuilding (like `pip install -e .`).

### How files get into `install/`
In `setup.py`, `data_files` tells colcon which non-Python files to copy:
```python
('share/' + package_name + '/launch', ['launch/vision_launch.py']),
('share/' + package_name + '/models', ['models/yolov8n.pt']),
```
At runtime the node reads from `install/.../share/vision_package/models/`, **not** from `src/`.

### Gotcha we hit: "I replaced the file but it still uses the old one"
The first `yolov8n.pt` was actually a **saved Hugging Face web page** (`file yolov8n.pt` → "HTML document").
After downloading the real one, the rebuild **still** used the broken copy. Why:
- The downloaded file kept its **original date (Jan 2024)**.
- The broken copy in `install/` was dated **today**.
- When copying data files, colcon skips any file where the installed copy is newer than the source.

Fix: delete that package's build output and rebuild.
```bash
rm -rf build/vision_package install/vision_package
colcon build
```
Useful checks:
```bash
file <path>          # what is this file really? (a real model shows "Zip archive")
ls -lh <path>        # size sanity check (yolov8n.pt ≈ 6 MB, not 170 KB)
```

---

## 7. Testing a successful build

### Python analogy
- **pip / uv:** `python -c "import mypkg"`, `pip show mypkg`, `uv pip list`, run the CLI entry point.

### ROS: does ROS see my package?
```bash
ros2 pkg list | grep vision_package          # is the package found?
ros2 pkg executables vision_package          # → vision_package vision_node
ros2 pkg prefix vision_package               # → .../vision_ws/install/vision_package
```
If these work, your overlay is sourced correctly.

### Common mistake: using topics to check the build
`ros2 topic list` shows **topics of nodes that are running right now**, not installed packages.
With nothing running you'll only ever see:
```
/parameter_events
/rosout
```
That's normal and **says nothing about whether your overlay works**.
Python analogy: `pip list` shows what's installed. `ps aux` shows what's running. `topic list` is like `ps`.

### Launching
```bash
ros2 launch vision_package vision_launch.py                  # by package name (uses install/)
ros2 launch src/vision_package/launch/vision_launch.py       # by file path (uses src/, skips install)
```
Prefer the package-name form. It only works if the overlay is active, so it also tests your setup.

### Now you'll see new topics (in a second terminal)
```bash
source /opt/ros/jazzy/setup.bash
source ~/Engineering/Robotics/vision_ws/install/setup.bash

ros2 topic list                    # /image_raw, /detections, /annotated_image, ...
ros2 topic hz /image_raw           # is the camera publishing, and how fast?
ros2 topic hz /detections          # how fast is YOLO keeping up?
ros2 topic echo /detections        # what is actually being published?
ros2 node list                     # /vision_node, /usb_camera_node
ros2 node info /vision_node        # its subscriptions and publications
```

---

## 8. Debugging the code itself

### Check message definitions instead of guessing
Message layouts change between ROS versions. Always check the version you have installed:
```bash
ros2 interface show vision_msgs/msg/BoundingBox2D
ros2 interface show vision_msgs/msg/Pose2D
ros2 interface show vision_msgs/msg/ObjectHypothesisWithPose
```
Python analogy: `help(SomeClass)` or reading the library's type hints.

### Make errors tell you the real line
A broad `except Exception` with a fixed message hides the real problem:
```python
import traceback
...
except Exception:
    self.get_logger().error(traceback.format_exc())
```

### Read the pattern in the logs
- Frames with **0 detections** succeeded; frames **with detections** failed.
  → the bug is in the code that only runs inside the detection loop.
- Timestamps about 0.4 s apart → about 2–3 FPS. That's the speed of YOLO on the Pi CPU, not a bug.

### Harmless log noise from usb_cam
- `camera calibration file not found`: camera not calibrated (only matters for real-world measurements).
- `unknown control 'exposure_auto'` etc.: your webcam doesn't support that setting.
- `No accelerated colorspace conversion`: a performance note, not an error.
- usb_cam needing SIGTERM/SIGKILL on Ctrl+C: a known quirk. If `/dev/video0` says busy later, check `ps aux | grep usb_cam`.

### Shutdown error on Ctrl+C
```
RCLError: failed to shutdown: rcl_shutdown already called
```
In Jazzy, rclpy handles Ctrl+C itself and has already shut down by the time your `finally:` runs.
Calling `rclpy.shutdown()` again raises an error. Look for a shutdown call that tolerates this, or check `rclpy.ok()` first.

---

## 9. Full "from scratch" checklist

```bash
# 0. fresh terminal
cd ~/Engineering/Robotics/vision_ws

# 1. clean (like deleting .venv)
rm -rf build install log

# 2. underlay (like having Python installed)
source /opt/ros/jazzy/setup.bash

# 3. dependencies (like pip install -r requirements.txt / uv sync)
export PIP_BREAK_SYSTEM_PACKAGES=1
rosdep install --from-paths src --ignore-src -r -y
rosdep check --from-paths src --ignore-src

# 4. build (like pip install -e . / uv sync)
colcon build --symlink-install

# 5. overlay (like source .venv/bin/activate)
source install/setup.bash

# 6. check the install (like pip show / import check)
ros2 pkg executables vision_package

# 7. run
ros2 launch vision_package vision_launch.py

# 8. check it's running (second terminal, source both again)
ros2 topic list
ros2 topic echo /detections
```

## 10. One-line summary of each tool

| Tool | Job | pip / uv equivalent |
|---|---|---|
| `source /opt/ros/jazzy/setup.bash` | activate ROS itself (underlay) | having Python on your PATH |
| `package.xml` | declare dependencies | `requirements.txt` / `pyproject.toml` |
| `rosdep install` | install those dependencies | `pip install -r` / `uv sync` |
| `colcon build` | build your workspace into `install/` | `pip install .` / `uv build` |
| `source install/setup.bash` | activate your workspace (overlay) | `source .venv/bin/activate` |
| `ros2 pkg ...` | inspect installed packages | `pip list` / `pip show` |
| `ros2 topic / node ...` | inspect the running system | `ps`, logs |
| `ros2 interface show` | inspect message definitions | `help()` / type hints |


## 11. Running and visualizing results via FoxGlove

```bash
ros2 launch foxglove_bridge foxglove_bridge_launch.xml
```