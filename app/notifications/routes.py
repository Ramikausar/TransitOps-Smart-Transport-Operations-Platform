from flask import render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.notifications import notifications_bp
from app.models.system import Notification
from app.extensions import db

@notifications_bp.route('/')
@login_required
def index():
    # Fetch notifications for current user, sorted by date
    # Driver only sees their own; others see global (user_id is Null) + their own.
    if current_user.role == 'Driver':
        notifications = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    else:
        notifications = Notification.query.filter(
            (Notification.user_id == current_user.id) | (Notification.user_id == None)
        ).order_by(Notification.created_at.desc()).all()
        
    return render_template('notifications/index.html', notifications=notifications)

@notifications_bp.route('/read/<int:id>', methods=['POST'])
@login_required
def mark_read(id):
    noti = Notification.query.get_or_404(id)
    # Security check: if specific notification belongs to someone else
    if noti.user_id and noti.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    noti.is_read = True
    db.session.commit()
    return jsonify({'success': True})

@notifications_bp.route('/read-all', methods=['POST'])
@login_required
def read_all():
    if current_user.role == 'Driver':
        unread = Notification.query.filter_by(user_id=current_user.id, is_read=False).all()
    else:
        unread = Notification.query.filter(
            ((Notification.user_id == current_user.id) | (Notification.user_id == None)) & 
            (Notification.is_read == False)
        ).all()
        
    for noti in unread:
        noti.is_read = True
    db.session.commit()
    flash("All notifications marked as read.", "success")
    return redirect(url_for('notifications.index'))

@notifications_bp.route('/api/recent', methods=['GET'])
@login_required
def get_recent():
    # Return count of unread and top 5 recent notifications for navbar dropdown
    if current_user.role == 'Driver':
        unread_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()
        recent = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).limit(5).all()
    else:
        unread_count = Notification.query.filter(
            ((Notification.user_id == current_user.id) | (Notification.user_id == None)) & 
            (Notification.is_read == False)
        ).count()
        recent = Notification.query.filter(
            (Notification.user_id == current_user.id) | (Notification.user_id == None)
        ).order_by(Notification.created_at.desc()).limit(5).all()
        
    return jsonify({
        'unread_count': unread_count,
        'notifications': [{
            'id': n.id,
            'title': n.title,
            'message': n.message[:60] + '...' if len(n.message) > 60 else n.message,
            'category': n.category,
            'is_read': n.is_read,
            'created_at': n.created_at.strftime('%d-%m-%Y %H:%M')
        } for n in recent]
    })
