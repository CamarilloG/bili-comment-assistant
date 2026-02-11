I will implement the requested GUI changes and the new "Warmup Mode" (养号模式).

### 1. File Structure Changes
- Create a new directory `gui_tabs/` to organize the GUI components.
- **`gui_tabs/comment_tab.py`**: Will contain the refactored "Auto Comment" interface (migrated from the current `gui.py`).
- **`gui_tabs/warmup_tab.py`**: Will contain the new "Warmup Mode" interface.
- **`core/warmup.py`**: Will contain the backend logic for the warmup task.

### 2. GUI Refactoring (`gui.py` & `gui_tabs/`)
- **`gui.py`**:
    - Will be simplified to be the main entry point.
    - Will use `ttk.Notebook` to manage two tabs: "Auto Comment" and "Warmup Mode".
    - Will handle global log redirection to the active tab.
- **`gui_tabs/comment_tab.py`**:
    - Encapsulate the existing UI logic into a `CommentTab` class.
    - Preserve all existing functionality (Search, Comment, Video List, Logs).
- **`gui_tabs/warmup_tab.py`**:
    - Implement `WarmupTab` class.
    - **Left Panel (Config)**:
        - Basic: Enable/Disable, Duration, Max Videos.
        - Behavior: Watch time range, Random Scroll/Pause/View Comments.
        - Comment: Random comment probability, Template selection (AI disabled for now).
        - Source: Homepage Recommendation.
    - **Right Panel (Status)**:
        - Display current video info, stats (watched count, time), and shared Log area.

### 3. Configuration (`config.yaml`)
- Add a new `warmup` section to `config.yaml` to persist warmup settings.
- Example structure:
  ```yaml
  warmup:
    basic:
      duration_minutes: 30
      max_videos: 20
    behavior:
      watch_time_min: 20
      watch_time_max: 240
      scroll: true
      ...
  ```

### 4. Backend Logic (`core/warmup.py` & `main.py`)
- **`core/warmup.py`**:
    - Implement `WarmupManager` to handle the "watch video" logic.
    - Simulate human behavior: scrolling, pausing, watching for a random duration.
- **`main.py`**:
    - Add `run_warmup_task` function to bridge the GUI and the `WarmupManager`.
    - Ensure tasks are mutually exclusive (running one disables the other).

### 5. Execution Steps
1.  Create `gui_tabs` directory and files.
2.  Refactor `gui.py` code into `gui_tabs/comment_tab.py`.
3.  Implement `gui_tabs/warmup_tab.py`.
4.  Update `gui.py` to assemble the tabs.
5.  Create `core/warmup.py` and update `main.py`.
6.  Update `config.yaml`.
