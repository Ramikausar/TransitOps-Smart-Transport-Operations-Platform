from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.fuel import fuel_bp
from app.fuel.forms import FuelLogForm
from app.models import FuelLog, FuelType, Vehicle, Trip, Expense, ExpenseCategory, ActivityLog, AuditLog, Notification
from app.extensions import db
from app.utils.decorators import role_required

@fuel_bp.route('/')
@login_required
@role_required('Fleet Manager', 'Financial Analyst')
def index():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('search', '', type=str).strip()
    vehicle_filter = request.args.get('vehicle', '', type=str)
    sort_by = request.args.get('sort_by', 'date', type=str)
    sort_order = request.args.get('sort_order', 'desc', type=str)

    query = FuelLog.query.join(Vehicle).outerjoin(Trip)

    if search_query:
        query = query.filter(
            (FuelLog.fuel_station.ilike(f'%{search_query}%')) |
            (Vehicle.registration_number.ilike(f'%{search_query}%')) |
            (Vehicle.name.ilike(f'%{search_query}%')) |
            (Trip.trip_code.ilike(f'%{search_query}%'))
        )

    if vehicle_filter:
        query = query.filter(FuelLog.vehicle_id == vehicle_filter)

    if sort_by == 'registration_number':
        column = Vehicle.registration_number
    elif sort_by == 'trip_code':
        column = Trip.trip_code
    elif hasattr(FuelLog, sort_by):
        column = getattr(FuelLog, sort_by)
    else:
        column = FuelLog.date

    if sort_order == 'desc':
        query = query.order_by(column.desc())
    else:
        query = query.order_by(column.asc())

    pagination = query.paginate(page=page, per_page=10, error_out=False)
    fuel_logs = pagination.items

    vehicles = Vehicle.query.filter(Vehicle.status != 'retired').all()

    return render_template(
        'fuel/index.html',
        fuel_logs=fuel_logs,
        pagination=pagination,
        vehicles=vehicles,
        search=search_query,
        vehicle_filter=vehicle_filter,
        sort_by=sort_by,
        sort_order=sort_order
    )

@fuel_bp.route('/create', methods=['GET', 'POST'])
@login_required
@role_required('Fleet Manager', 'Financial Analyst')
def create():
    form = FuelLogForm()
    
    vehicles = Vehicle.query.filter(Vehicle.status != 'retired').all()
    trips = Trip.query.order_by(Trip.created_date.desc()).limit(50).all()
    
    form.vehicle_id.choices = [(v.id, f"{v.registration_number} - {v.name}") for v in vehicles]
    form.trip_id.choices = [(0, '-- None --')] + [(t.id, f"{t.trip_code} ({t.source} to {t.destination})") for t in trips]
    
    if form.validate_on_submit():
        vehicle = Vehicle.query.get(form.vehicle_id.data)
        
        fuel_log = FuelLog(
            vehicle_id=form.vehicle_id.data,
            trip_id=form.trip_id.data if form.trip_id.data != 0 else None,
            fuel_type_id=form.fuel_type_id.data,
            fuel_quantity=form.fuel_quantity.data,
            fuel_price=form.fuel_price.data,
            fuel_station=form.fuel_station.data.strip(),
            date=form.date.data
        )
        db.session.add(fuel_log)
        db.session.flush() # get ID
        
        # Auto-create Expense under category 'Fuel'
        cat = ExpenseCategory.query.filter_by(name='Fuel').first()
        if not cat:
            cat = ExpenseCategory(name='Fuel', description='Fuel charges')
            db.session.add(cat)
            db.session.flush()
            
        expense = Expense(
            vehicle_id=fuel_log.vehicle_id,
            trip_id=fuel_log.trip_id,
            expense_category_id=cat.id,
            amount=fuel_log.total_cost,
            description=f"Auto-generated fuel expense for Fuel Log #{fuel_log.id} filled at {fuel_log.fuel_station}.",
            date=fuel_log.date
        )
        db.session.add(expense)
        
        ActivityLog.log_activity(
            action=f"Logged fuel fill of {fuel_log.fuel_quantity}L for vehicle {vehicle.registration_number}. Cost: ₹{fuel_log.total_cost}",
            module="Fuel",
            user_id=current_user.id
        )
        AuditLog.log_audit(
            table_name="fuel_logs",
            row_id=fuel_log.id,
            action_type="INSERT",
            new_value=f"Vehicle: {vehicle.registration_number}, Cost: {fuel_log.total_cost}",
            user_id=current_user.id
        )
        
        db.session.commit()
        flash("Fuel transaction logged and expense generated automatically.", "success")
        return redirect(url_for('fuel.index'))
        
    return render_template('fuel/create.html', form=form)

@fuel_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('Fleet Manager', 'Financial Analyst')
def edit(id):
    fuel_log = FuelLog.query.get_or_404(id)
    form = FuelLogForm(obj=fuel_log)
    
    vehicles = Vehicle.query.filter(Vehicle.status != 'retired').all()
    trips = Trip.query.order_by(Trip.created_date.desc()).limit(50).all()
    
    form.vehicle_id.choices = [(v.id, f"{v.registration_number} - {v.name}") for v in vehicles]
    form.trip_id.choices = [(0, '-- None --')] + [(t.id, f"{t.trip_code} ({t.source} to {t.destination})") for t in trips]
    
    if request.method == 'GET':
        form.trip_id.data = fuel_log.trip_id or 0
        
    if form.validate_on_submit():
        old_val = f"Vehicle ID: {fuel_log.vehicle_id}, Cost: {fuel_log.total_cost}"
        
        fuel_log.vehicle_id = form.vehicle_id.data
        fuel_log.trip_id = form.trip_id.data if form.trip_id.data != 0 else None
        fuel_log.fuel_type_id = form.fuel_type_id.data
        fuel_log.fuel_quantity = form.fuel_quantity.data
        fuel_log.fuel_price = form.fuel_price.data
        fuel_log.fuel_station = form.fuel_station.data.strip()
        fuel_log.date = form.date.data
        fuel_log.update_cost()
        
        # Sync Expense under Category 'Fuel'
        cat = ExpenseCategory.query.filter_by(name='Fuel').first()
        if not cat:
            cat = ExpenseCategory(name='Fuel', description='Fuel charges')
            db.session.add(cat)
            db.session.flush()
            
        match_str = f"Fuel Log #{fuel_log.id} "
        existing_expense = Expense.query.filter(
            Expense.vehicle_id == fuel_log.vehicle_id,
            Expense.expense_category_id == cat.id,
            Expense.description.like(f"%{match_str}%")
        ).first()
        
        if existing_expense:
            existing_expense.trip_id = fuel_log.trip_id
            existing_expense.amount = fuel_log.total_cost
            existing_expense.date = fuel_log.date
            existing_expense.description = f"Auto-generated fuel expense for Fuel Log #{fuel_log.id} filled at {fuel_log.fuel_station}."
        else:
            expense = Expense(
                vehicle_id=fuel_log.vehicle_id,
                trip_id=fuel_log.trip_id,
                expense_category_id=cat.id,
                amount=fuel_log.total_cost,
                description=f"Auto-generated fuel expense for Fuel Log #{fuel_log.id} filled at {fuel_log.fuel_station}.",
                date=fuel_log.date
            )
            db.session.add(expense)
            
        ActivityLog.log_activity(
            action=f"Updated fuel log #{fuel_log.id} for vehicle {fuel_log.vehicle.registration_number}",
            module="Fuel",
            user_id=current_user.id
        )
        AuditLog.log_audit(
            table_name="fuel_logs",
            row_id=fuel_log.id,
            action_type="UPDATE",
            old_value=old_val,
            new_value=f"Vehicle ID: {fuel_log.vehicle_id}, Cost: {fuel_log.total_cost}",
            user_id=current_user.id
        )
            
        db.session.commit()
        flash("Fuel log updated and expense sync completed.", "success")
        return redirect(url_for('fuel.index'))
        
    return render_template('fuel/edit.html', form=form, fuel_log=fuel_log)

@fuel_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@role_required('Fleet Manager', 'Financial Analyst')
def delete(id):
    fuel_log = FuelLog.query.get_or_404(id)
    vehicle_reg = fuel_log.vehicle.registration_number
    cost = fuel_log.total_cost
    
    # Delete associated expense
    cat = ExpenseCategory.query.filter_by(name='Fuel').first()
    if cat:
        match_str = f"Fuel Log #{fuel_log.id} "
        expense = Expense.query.filter(
            Expense.vehicle_id == fuel_log.vehicle_id,
            Expense.expense_category_id == cat.id,
            Expense.description.like(f"%{match_str}%")
        ).first()
        if expense:
            db.session.delete(expense)
            
    ActivityLog.log_activity(
        action=f"Deleted fuel log #{fuel_log.id} for vehicle {vehicle_reg} (Value: ₹{cost})",
        module="Fuel",
        user_id=current_user.id
    )
    AuditLog.log_audit(
        table_name="fuel_logs",
        row_id=fuel_log.id,
        action_type="DELETE",
        old_value=f"Vehicle ID: {fuel_log.vehicle_id}, Cost: {fuel_log.total_cost}",
        user_id=current_user.id
    )
        
    db.session.delete(fuel_log)
    db.session.commit()
    flash("Fuel log and linked expense deleted successfully.", "success")
    return redirect(url_for('fuel.index'))
