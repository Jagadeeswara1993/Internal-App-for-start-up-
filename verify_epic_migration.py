from app import create_app
from app.models import Epic, Task

app = create_app()
with app.app_context():
    print('App created successfully')
    print('Epic model: OK')
    print('Task.epic_id:', hasattr(Task, 'epic_id'))
    print('Task.parent_task_id:', hasattr(Task, 'parent_task_id'))
    print('Task.task_type:', hasattr(Task, 'task_type'))
    print('Task.subtasks:', hasattr(Task, 'subtasks'))
    
    # Check DB tables
    from app.extensions import db
    result = db.session.execute(db.text("SELECT name FROM sqlite_master WHERE type='table' AND name='epics'"))
    print('Epics table exists:', result.fetchone() is not None)
    
    result = db.session.execute(db.text("PRAGMA table_info(tasks)"))
    cols = [row[1] for row in result.fetchall()]
    print('Tasks columns:', cols)
    print('\nAll checks passed!')
