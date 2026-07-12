from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, FloatField, DateField, SubmitField
from wtforms.validators import DataRequired, NumberRange, Optional
from app.models.vehicle import Vehicle, FuelType
from app.models.trip import Trip

class FuelLogForm(FlaskForm):
    vehicle_id = SelectField('Vehicle', coerce=int, validators=[
        DataRequired(message="Please select a vehicle.")
    ])
    trip_id = SelectField('Linked Trip (Optional)', coerce=int, validators=[
        Optional()
    ])
    fuel_type_id = SelectField('Fuel Type', coerce=int, validators=[
        DataRequired(message="Please select a fuel type.")
    ])
    fuel_quantity = FloatField('Fuel Quantity (Litres / KG)', validators=[
        DataRequired(message="Quantity is required."),
        NumberRange(min=0.1, message="Quantity must be greater than 0.")
    ])
    fuel_price = FloatField('Fuel Price (₹ / Unit)', validators=[
        DataRequired(message="Fuel price is required."),
        NumberRange(min=0.01, message="Price must be greater than 0.")
    ])
    fuel_station = StringField('Fuel Station Name', validators=[
        DataRequired(message="Fuel station is required.")
    ])
    date = DateField('Log Date (YYYY-MM-DD)', format='%Y-%m-%d', validators=[
        DataRequired(message="Date is required.")
    ])
    
    submit = SubmitField('Log Fuel Fill')

    def __init__(self, *args, **kwargs):
        super(FuelLogForm, self).__init__(*args, **kwargs)
        self.vehicle_id.choices = [(0, '-- Select Vehicle --')] + [(v.id, f"{v.registration_number} - {v.name}") for v in Vehicle.query.filter(Vehicle.status != 'retired').all()]
        self.fuel_type_id.choices = [(0, '-- Select Fuel Type --')] + [(f.id, f.name) for f in FuelType.query.order_by(FuelType.name.asc()).all()]
        
        recent_trips = Trip.query.order_by(Trip.created_date.desc()).limit(50).all()
        self.trip_id.choices = [(0, '-- None (Direct Fill) --')] + [(t.id, f"{t.trip_code} ({t.source} to {t.destination})") for t in recent_trips]
