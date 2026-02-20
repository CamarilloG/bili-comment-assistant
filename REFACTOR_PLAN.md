# Frontend Refactoring Plan: GUI Layout Optimization

## Problem Analysis
- **Issue**: On smaller screens or when window height is reduced, the bottom control buttons (Start/Stop) in the Left Panel are pushed out of view.
- **Root Cause**: The Left Panel stacks all configuration groups and buttons vertically without a scrollable container. Fixed vertical space requirements exceed available height.

## Proposed Solution
Refactor the **Left Panel** (Configuration Side) in both `CommentTab` and `WarmupTab` to use a **Split Layout**:
1.  **Scrollable Configuration Area (Top/Center)**: Contains all configuration groups (Basic, Parameters, Filters, etc.). This area will consume available remaining space and provide a scrollbar if content overflows.
2.  **Fixed Control Area (Bottom)**: Contains the critical "Action Buttons" (Start, Stop) and Status Label. This area will be "docked" to the bottom of the panel so it is **always visible**, regardless of scrolling.

## Implementation Steps

### 1. Refactor `gui_tabs/comment_tab.py`
-   **Import**: Ensure `ScrolledFrame` is available (from `ttkbootstrap.scrolled`).
-   **Structure Change**:
    -   Replace the direct packing of `left_frame` contents.
    -   Create `control_frame` docked at the bottom (`pack(side=BOTTOM, fill=X)`).
    -   Create `config_frame` (ScrolledFrame) filling the rest (`pack(side=TOP, fill=BOTH, expand=YES)`).
-   **Migration**:
    -   Move `Basic Config`, `Parameters`, `Search Filters`, `Browser Config`, `Account` groups into `config_frame`.
    -   Move `Start`, `Stop`, and `Progress` widgets into `control_frame`.

### 2. Refactor `gui_tabs/warmup_tab.py`
-   **Import**: Ensure `ScrolledFrame` is available.
-   **Structure Change**:
    -   Apply the same Split Layout (Scrollable Config + Fixed Control).
-   **Migration**:
    -   Move `Basic Control`, `Playback Behavior`, `Comment Behavior`, `Video Source` groups into `config_frame`.
    -   Move `Start`, `Stop`, and `Progress` widgets into `control_frame`.

### 3. Verification
-   Run `python gui.py`.
-   Resize window to a smaller height.
-   Verify that:
    -   Configuration options show a scrollbar when needed.
    -   Start/Stop buttons remain pinned to the bottom and visible.
