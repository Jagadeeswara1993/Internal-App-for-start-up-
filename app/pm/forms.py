"""PM forms."""

from flask_wtf import FlaskForm
from wtforms import (StringField, TextAreaField, DateField, SelectField,
                     SubmitField)
from wtforms.validators import DataRequired, Optional, Length


class ProjectForm(FlaskForm):
    name = StringField('Project Name', validators=[DataRequired(), Length(2, 150)])
    description = TextAreaField('Description', validators=[Optional()])
    start_date = DateField('Start Date', validators=[Optional()])
    end_date = DateField('End Date', validators=[Optional()])
    status = SelectField('Status', choices=[
        ('Planning', 'Planning'),
        ('In Progress', 'In Progress'),
        ('On Hold', 'On Hold'),
        ('Completed', 'Completed')
    ])
    submit = SubmitField('Save Project')


class TaskForm(FlaskForm):
    title = StringField('Task Title', validators=[DataRequired(), Length(2, 200)])
    description = TextAreaField('Description', validators=[Optional()])
    assigned_to = SelectField('Assign To', coerce=int, validators=[Optional()])
    priority = SelectField('Priority', choices=[
        ('Low', 'Low'), ('Medium', 'Medium'),
        ('High', 'High'), ('Critical', 'Critical')
    ])
    status = SelectField('Status', choices=[
        ('To Do', 'To Do'), ('In Progress', 'In Progress'), ('Done', 'Done')
    ])
    due_date = DateField('Due Date', validators=[Optional()])
    submit = SubmitField('Save Task')
