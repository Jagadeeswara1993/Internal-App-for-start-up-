"""PM forms — Projects, Tasks, Milestones, Epics."""

from flask_wtf import FlaskForm
from wtforms import (StringField, TextAreaField, DateField, SelectField,
                     SubmitField, FloatField)
from wtforms.validators import DataRequired, Optional, Length


class ProjectForm(FlaskForm):
    name = StringField('Project Name', validators=[DataRequired(), Length(2, 150)])
    description = TextAreaField('Description', validators=[Optional()])
    start_date = DateField('Start Date', validators=[Optional()])
    end_date = DateField('End Date', validators=[Optional()])
    deadline = DateField('Deadline', validators=[Optional()])
    estimated_hours = FloatField('Estimated Hours', validators=[Optional()])
    status = SelectField('Status', choices=[
        ('Not Started', 'Not Started'),
        ('In Progress', 'In Progress'),
        ('On Hold', 'On Hold'),
        ('Completed', 'Completed')
    ])
    assigned_pm = SelectField('Assign to Project Manager', coerce=int,
                              validators=[Optional()])
    submit = SubmitField('Save Project')


class TaskForm(FlaskForm):
    title = StringField('Task Title', validators=[DataRequired(), Length(2, 200)])
    description = TextAreaField('Description', validators=[Optional()])
    task_type = SelectField('Type', choices=[
        ('Task', 'Task'), ('Story', 'Story'), ('Bug', 'Bug')
    ])
    assigned_to = SelectField('Assign To', coerce=int, validators=[Optional()])
    priority = SelectField('Priority', choices=[
        ('Low', 'Low'), ('Medium', 'Medium'),
        ('High', 'High'), ('Critical', 'Critical')
    ])
    status = SelectField('Status', choices=[
        ('Pending', 'Pending'), ('In Progress', 'In Progress'), ('Done', 'Done')
    ])
    estimated_hours = FloatField('Estimated Hours', validators=[Optional()])
    due_date = DateField('Due Date', validators=[Optional()])
    epic_id = SelectField('Epic', coerce=int, validators=[Optional()])
    parent_task_id = SelectField('Parent Task (makes this a Sub-task)', coerce=int,
                                 validators=[Optional()])
    submit = SubmitField('Save Task')


class MilestoneForm(FlaskForm):
    title = StringField('Milestone Title', validators=[DataRequired(), Length(2, 200)])
    description = TextAreaField('Description', validators=[Optional()])
    deadline = DateField('Deadline', validators=[Optional()])
    status = SelectField('Status', choices=[
        ('Pending', 'Pending'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed')
    ])
    submit = SubmitField('Save Milestone')


class EpicForm(FlaskForm):
    title = StringField('Epic Title', validators=[DataRequired(), Length(2, 200)])
    description = TextAreaField('Description', validators=[Optional()])
    status = SelectField('Status', choices=[
        ('To Do', 'To Do'),
        ('In Progress', 'In Progress'),
        ('Done', 'Done')
    ])
    color_label = StringField('Color', validators=[Optional()], default='#6366f1')
    submit = SubmitField('Save Epic')
