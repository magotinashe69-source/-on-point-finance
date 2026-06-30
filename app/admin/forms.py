"""Flask-WTF forms for the admin area (CSRF-protected, server-validated)."""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Length


class AddUserForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(message="Please enter a name."), Length(max=120)])
    username = StringField("Username", validators=[DataRequired(message="Please enter a username."), Length(max=80)])
    password = PasswordField(
        "Password",
        validators=[DataRequired(message="Please set a password."), Length(min=8, message="Use at least 8 characters.")],
    )
    role = SelectField("Role", choices=[("clerk", "Clerk"), ("admin", "Admin")],
                       validators=[DataRequired()])
    submit = SubmitField("Add user")


class AddCategoryForm(FlaskForm):
    name = StringField("Category name", validators=[DataRequired(message="Please enter a name."), Length(max=80)])
    type = SelectField("Type", choices=[("income", "Income"), ("expense", "Expense")],
                       validators=[DataRequired()])
    submit = SubmitField("Add category")


class ActionForm(FlaskForm):
    """Empty form that carries the CSRF token for toggle/unlock buttons."""

    submit = SubmitField("Go")
