# Walkthrough: Epic Hierarchy & Kanban Board

All the requested features for the Jira-inspired project management system have been successfully implemented, and the development server is currently running on your machine at `http://127.0.0.1:5000`.

## Features Implemented
*   **Epic Management**: You can now create Epics to group features together. Each Epic has a title, description, status, and a customizable color label that displays on the board.
*   **Task Hierarchy**: Tasks now support being classified as an `Epic`, `Story`, `Bug`, `Task`, or `Sub-task`. Sub-tasks can be nested beneath parent tasks.
*   **Kanban Board**: A drag-and-drop Kanban board view has been added to each project. You can drag tasks between "Pending", "In Progress", and "Done". The board has filters for Epic, Assignee, and Priority.

## Manual Verification Steps

To manually verify the changes in the application, please follow these steps:

1.  **Open the App**: Navigate to `http://127.0.0.1:5000` in your web browser and log in with an Admin or Project Manager account.
2.  **Navigate to a Project**: Click on the **PM** module and navigate to the **Projects** list. Open an existing project or create a new one.
3.  **Test Epics**:
    *   On the project detail page, look for the new **Epics** panel in the left sidebar.
    *   Click **Add** to create a new Epic. Give it a title and a color.
    *   Verify the Epic appears in the list.
4.  **Test Task Hierarchy**:
    *   Click **Add Task** from the top of the Tasks panel.
    *   Notice the new fields: **Type** and **Epic**.
    *   Create a "Task" or "Story" and assign it to the Epic you just created.
    *   Create another task, but this time select the task you just created from the **Parent Task** dropdown. Notice that the **Type** automatically changes to "Sub-task".
    *   Verify that the task table now shows the top-level task with the sub-task correctly indented beneath it.
5.  **Test the Kanban Board**:
    *   At the top of the Tasks panel, click the **Board** toggle button (next to Table).
    *   You should now see the Kanban board with columns for Pending, In Progress, and Done.
    *   Drag a task card from one column to another. You should see a green success toast notification indicating the status was updated.
    *   Test the dropdown filters at the top of the board (Epic, Assignee, Priority) to ensure the cards filter correctly.
6.  **Test Subtask Auto-completion**:
    *   If you created a parent task with sub-tasks, move all the sub-tasks to the "Done" column on the board (or change their status via the Edit form).
    *   Verify that the parent task automatically changes its status to "Done".

If you encounter any issues during testing, please let me know!
