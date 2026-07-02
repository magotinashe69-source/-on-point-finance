"""Flask-WTF forms for the recording screen (CSRF-protected, server-validated)."""

from datetime import date

from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Optional, Length, ValidationError

from app.money import str_to_cents
from app.constants import PAYMENT_METHODS


class TransactionForm(FlaskForm):
    amount = StringField("Amount (MT)", validators=[DataRequired(message="Please enter an amount.")])
    category = SelectField("Category", coerce=int, validators=[DataRequired(message="Please choose a category.")])
    payment_method = SelectField(
        "Payment method",
        choices=[(m, m) for m in PAYMENT_METHODS],
        validators=[DataRequired(message="Please choose a payment method.")],
    )
    date = DateField("Date", validators=[DataRequired(message="Please choose a date.")], default=date.today)
    description = TextAreaField("Description (optional)", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Save")

    def validate_amount(self, field) -> None:
        """Convert the typed amount to centavos and reject zero/negative."""
        try:
            cents = str_to_cents(field.data)
        except ValueError as exc:
            raise ValidationError(str(exc))
        if cents <= 0:
            raise ValidationError("Amount must be greater than zero.")
        # Stash the validated integer for the route to use.
        self.amount_cents = cents


class StudentIncomeForm(FlaskForm):
    """Smart income: record a fee payment against a stored student (Stage 2).

    `student` and `fee_type` choices are filled by the route. The grade is NOT a
    field here — it comes from the student's stored record, never re-typed.
    """

    student = SelectField("Student", coerce=int,
                          validators=[DataRequired(message="Please choose a student.")])
    fee_type = SelectField("Fee", validators=[DataRequired(message="Please choose a fee.")])
    amount = StringField("Amount (MT)", validators=[DataRequired(message="Please enter an amount.")])
    payment_method = SelectField(
        "Payment method",
        choices=[(m, m) for m in PAYMENT_METHODS],
        validators=[DataRequired(message="Please choose a payment method.")],
    )
    date = DateField("Date", validators=[DataRequired(message="Please choose a date.")], default=date.today)
    description = StringField("Description", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Save income")

    def validate_amount(self, field) -> None:
        """Convert the typed amount to centavos and reject zero/negative."""
        try:
            cents = str_to_cents(field.data)
        except ValueError as exc:
            raise ValidationError(str(exc))
        if cents <= 0:
            raise ValidationError("Amount must be greater than zero.")
        self.amount_cents = cents


class DeleteForm(FlaskForm):
    """Empty form whose only job is to carry the CSRF token for delete buttons."""

    submit = SubmitField("Delete")
