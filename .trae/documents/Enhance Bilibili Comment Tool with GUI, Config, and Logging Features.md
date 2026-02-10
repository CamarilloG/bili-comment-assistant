I will implement the requested features in the following order:

1. **Update Configuration & Selectors (`config.yaml`,** **`core/selectors.py`)**

   * Add `comment.enable_image`, `browser.path`, and `browser.port` to `config.yaml`.

   * Add CSS selectors for video metadata (Title, Views, Date, Up Name) to `core/selectors.py`.

2. **Enhance Search Logic (`core/search.py`)**

   * Modify `search_videos` to extract full video metadata (Title, BV, Views, Date) instead of just URLs.

   * Return a list of dictionaries containing this data.

3. **Update Backend Logic (`main.py`)**

   * **Browser Config**: Update `playwright.launch` to use the custom `executable_path` and `args` for the debugging port if provided.

   * **Image Toggle**: Skip image upload logic if `enable_image` is False.

   * **Data Callback**: Add a callback mechanism to pass found video data back to the GUI for display.

   * **Local Logging**: Implement a `csv` logger to append comment execution results (Time, BV, Title, Status) to `comment_history.csv`.

4. **Refactor GUI (`gui.py`)**

   * **Layout**: Split the main window into two columns using `ttk.PanedWindow`.

     * **Left Panel**: Configuration controls (existing + new).

     * **Right Panel**: A new `ttk.Treeview` to display the video list (Title, BV, Views, Comments, Date).

   * **New Controls**:

     * Add "Enable Image Upload" checkbox.

     * Add "Browser Path" file picker and "Debug Port" input field.

   * **Integration**: Connect the backend callback to update the `Treeview` in real-time.

5. **Verify & Test**

   * Run the application to ensure the new layout works.

   * Test the image upload toggle.

   * Test custom browser path launching.

   * Verify data is populating in the list and logging to CSV.

