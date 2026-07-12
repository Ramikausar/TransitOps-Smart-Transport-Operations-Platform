from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.settings import settings_bp
from app.settings.forms import ProfileForm, UserCreateForm
from app.models.user import User
from app.extensions import db
from app.utils.decorators import role_required

@settings_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    form = ProfileForm(user_id=current_user.id, obj=current_user)
    
    if form.validate_on_submit():
        current_user.name = form.name.data.strip()
        current_user.email = form.email.data.strip().lower()
        if form.password.data:
            current_user.set_password(form.password.data)
        
        db.session.commit()
        flash("Your profile settings have been updated.", "success")
        return redirect(url_for('settings.index'))
        
    return render_template('settings/index.html', form=form)

@settings_bp.route('/users')
@login_required
@role_required('Fleet Manager')
def users_list():
    users = User.query.all()
    return render_template('settings/users.html', users=users)

@settings_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@role_required('Fleet Manager')
def users_create():
    form = UserCreateForm()
    if form.validate_on_submit():
        user = User(
            name=form.name.data.strip(),
            email=form.email.data.strip().lower(),
            role=form.role.data,
            is_active=True
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash(f"User account created for {user.name} ({user.role}).", "success")
        return redirect(url_for('settings.users_list'))
        
    return render_template('settings/users_create.html', form=form)

@settings_bp.route('/users/toggle/<int:id>', methods=['POST'])
@login_required
@role_required('Fleet Manager')
def toggle_user(id):
    if current_user.id == id:
        flash("You cannot deactivate your own administrative account.", "danger")
        return redirect(url_for('settings.users_list'))
        
    user = User.query.get_or_404(id)
    user.is_active = not user.is_active
    db.session.commit()
    
    state = "activated" if user.is_active else "deactivated"
    flash(f"User account for {user.name} has been {state}.", "success")
    return redirect(url_for('settings.users_list'))
