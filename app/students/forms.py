"""Flask-WTF forms for the students area (CSRF-protected, server-validated)."""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Optional, Length


class AddStudentForm(FlaskForm):
    full_name = StringField(
        "Full name",
        validators=[DataRequired(message="Please enter the student's full name."), Length(max=120)],
    )
    class_name = StringField("Class (optional)", validators=[Optional(), Length(max=80)])
    guardian_name = StringField("Guardian name (optional)", validators=[Optional(), Length(max=120)])
    guardian_phone = StringField("Guardian phone (optional)", validators=[Optional(), Length(max=40)])
    student_no = StringField("Student number (optional)", validators=[Optional(), Length(max=60)])
    submit = SubmitField("Save student")


class ImportForm(FlaskForm):
    """Upload a .csv file of students (admin only)."""

    file = FileField(
        "CSV file",
        validators=[
            FileRequired(message="Please choose a .csv file to upload."),
            FileAllowed(["csv"], message="Please upload a .csv file."),
        ],
    )
    submit = SubmitField("Import students")


class ActionForm(FlaskForm):
    """Empty form that carries the CSRF token for the deactivate button."""

    submit = SubmitField("Go")
