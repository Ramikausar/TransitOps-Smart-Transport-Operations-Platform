from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Length, Optional, ValidationError
from app.models.user import User

class ProfileForm(FlaskForm):
    name = StringField('Display Name', validators=[
        DataRequired(message="Name is required.")
    ])
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required."),
        Email(message="Please enter a valid email.")
    ])
    password = PasswordField('New Password (leave blank to keep current)', validators=[
        Optional(),
        Length(min=6, message="Password must be at least 6 characters.")
    ])
    submit = SubmitField('Update Profile')

    def __init__(self, user_id, *args, **kwargs):
        super(ProfileForm, self).__init__(*args, **kwargs)
        self.user_id = user_id

    def validate_email(self, field):
        existing = User.query.filter_by(email=field.data.strip().lower()).first()
        if existing and existing.id != self.user_id:
            raise ValidationError("Email address is already in use by another user.")


class UserCreateForm(FlaskForm):
    name = StringField('Full Name', validators=[
        DataRequired(message="Name is required.")
    ])
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required."),
        Email(message="Please enter a valid email.")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required."),
        Length(min=6, message="Password must be at least 6 characters.")
    ])
    role = SelectField('User Role', choices=[
        ('Fleet Manager', 'Fleet Manager'),
        ('Driver', 'Driver'),
        ('Safety Officer', 'Safety Officer'),
        ('Financial Analyst', 'Financial Analyst')
    ], validators=[DataRequired()])
    
    submit = SubmitField('Create User Account')

    def validate_email(self, field):
        existing = User.query.filter_by(email=field.data.strip().lower()).first()
        if existing:
            raise ValidationError("Email address is already registered.")
