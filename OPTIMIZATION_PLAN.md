# GUI Optimization Plan

## Completed Optimizations
1.  **Adaptive Layout**: Refactored `CommentTab` and `WarmupTab` to use `grid` layout and `pack(fill=X, expand=YES)` instead of fixed widths. Elements now resize with the window.
2.  **Visual Enhancements**: Increased padding around elements to prevent clutter and improve readability.
3.  **Thread Safety**: Updated `TextHandler` to use `root.after` for thread-safe GUI updates from background threads.
4.  **Window Management**: Added window centering and proper shutdown handling.
5.  **Split Layout**: Implemented `Panedwindow` with `ScrolledFrame` for configuration and fixed bottom buttons to ensure visibility on small screens.
6.  **Panel Sizing**: Adjusted initial panel weights (Left:Right = 2:3) to provide more space for configuration inputs.

## Future Optimization Roadmap

### Phase 1: Stability & Validation (High Priority)
- [ ] **Input Validation**: Implement `validatecommand` for all numeric input fields (e.g., delay, duration) to prevent invalid data entry.
- [ ] **Error Handling**: Add more robust error catching around browser launch and task execution to prevent GUI freezing.
- [ ] **Config Management Refactoring**: Create a `ConfigManager` class to centralize configuration loading, saving, and validation, removing duplicated code in tabs.

### Phase 2: User Experience (Medium Priority)
- [ ] **Tooltips**: Add hover tooltips for complex parameters (e.g., "Strategy", "Strict Match") to explain their function.
- [ ] **Theme Selector**: Add a dropdown to allow users to switch between `ttkbootstrap` themes (e.g., `cosmo`, `journal`, `darkly`) at runtime.
- [ ] **Progress Detail**: Improve the progress bar or status label to show more granular progress (e.g., "Processing video 3/10").

### Phase 3: Advanced Features (Low Priority)
- [ ] **Headless Toggle**: Add a quick toggle for headless mode in the main toolbar.
- [ ] **Log Filtering**: Add checkboxes to filter logs by level (INFO, ERROR, DEBUG).
- [ ] **Task Queue**: Allow queuing multiple search keywords or tasks to run sequentially.
