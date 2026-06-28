"""Flask-WTF forms for authentication.

Using FlaskForm means every POST is CSRF-protected automatically and validated
on the server side.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, EqualTo


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(message="Please enter your username.")])
    password = PasswordField("Password", validators=[DataRequired(message="Please enter your password.")])
    submit = SubmitField("Log in")


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField(
        "Current password",
        validators=[DataRequired(message="Please enter your current password.")],
    )
    new_password = PasswordField(
        "New password",
        validators=[
            DataRequired(message="Please choose a new password."),
            Length(min=8, message="Use at least 8 characters."),
        ],
    )
    confirm_password = PasswordField(
        "Confirm new password",
        validators=[
            DataRequired(message="Please type the new password again."),
            EqualTo("new_password", message="The two passwords do not match."),
        ],
    )
    submit = SubmitField("Change password")
