from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, FloatField, DateField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional
from app.models.vehicle import Vehicle
from app.models.trip import Trip
from app.models.expense import ExpenseCategory

class ExpenseForm(FlaskForm):
    vehicle_id = SelectField('Vehicle', coerce=int, validators=[
        DataRequired(message="Please select a vehicle.")
    ])
    trip_id = SelectField('Linked Trip (Optional)', coerce=int, validators=[
        Optional()
    ])
    expense_category_id = SelectField('Expense Category', coerce=int, validators=[
        DataRequired(message="Please select an expense category.")
    ])
    
    amount = FloatField('Expense Amount (₹)', validators=[
        DataRequired(message="Amount is required."),
        NumberRange(min=0.01, message="Amount must be greater than 0.")
    ])
    description = TextAreaField('Description', validators=[
        DataRequired(message="Please enter a description.")
    ])
    date = DateField('Date (YYYY-MM-DD)', format='%Y-%m-%d', validators=[
        DataRequired(message="Date is required.")
    ])
    
    submit = SubmitField('Log Expense')

    def __init__(self, *args, **kwargs):
        super(ExpenseForm, self).__init__(*args, **kwargs)
        self.vehicle_id.choices = [(0, '-- Select Vehicle --')] + [(v.id, f"{v.registration_number} - {v.name}") for v in Vehicle.query.filter(Vehicle.status != 'retired').all()]
        self.expense_category_id.choices = [(0, '-- Select Expense Category --')] + [(c.id, c.name) for c in ExpenseCategory.query.order_by(ExpenseCategory.name.asc()).all()]
        
        recent_trips = Trip.query.order_by(Trip.created_date.desc()).limit(50).all()
        self.trip_id.choices = [(0, '-- None --')] + [(t.id, f"{t.trip_code} ({t.source} to {t.destination})") for t in recent_trips]
