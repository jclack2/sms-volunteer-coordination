from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from models import Event, User, VolunteerResponse, SMSMessage, AuditLog
from datetime import datetime, timedelta

bp = Blueprint('dashboard', __name__)


@bp.route('/')
@login_required
def index():
    """Dashboard home"""
    # Get upcoming events
    if current_user.is_admin:
        upcoming_events = Event.query.filter(
            Event.event_datetime >= datetime.utcnow(),
            Event.is_active == True
        ).order_by(Event.event_datetime).limit(5).all()
    elif current_user.is_sender:
        upcoming_events = Event.query.filter(
            Event.sender_id == current_user.id,
            Event.event_datetime >= datetime.utcnow(),
            Event.is_active == True
        ).order_by(Event.event_datetime).limit(5).all()
    else:
        upcoming_events = []

    # Get recent activity
    recent_responses = []
    if current_user.is_admin or current_user.is_sender:
        recent_responses = VolunteerResponse.query\
            .join(Event)\
            .filter(Event.sender_id == current_user.id if current_user.is_sender else True)\
            .order_by(VolunteerResponse.responded_at.desc())\
            .limit(10).all()

    # Get stats
    stats = {}
    if current_user.is_admin or current_user.is_sender:
        stats['total_events'] = Event.query.filter(
            Event.sender_id == current_user.id if current_user.is_sender else True
        ).count()

        stats['active_events'] = Event.query.filter(
            Event.is_active == True,
            Event.sender_id == current_user.id if current_user.is_sender else True
        ).count()

        stats['total_users'] = User.query.filter_by(is_receiver=True).count()

        stats['opted_in_users'] = User.query.filter_by(
            is_receiver=True,
            opt_in_confirmed=True
        ).count()

        # Recent messages (last 7 days)
        week_ago = datetime.utcnow() - timedelta(days=7)
        stats['recent_messages'] = SMSMessage.query.filter(
            SMSMessage.sent_at >= week_ago
        ).count()

    return render_template('dashboard/index.html',
                         upcoming_events=upcoming_events,
                         recent_responses=recent_responses,
                         stats=stats)


@bp.route('/users')
@login_required
def users():
    """Manage users"""
    if not current_user.is_admin:
        return redirect(url_for('dashboard.index'))

    all_users = User.query.order_by(User.name).all()
    return render_template('dashboard/users.html', users=all_users)


@bp.route('/messages')
@login_required
def messages():
    """View message log"""
    if not (current_user.is_admin or current_user.is_sender):
        return redirect(url_for('dashboard.index'))

    # Get recent messages
    message_query = SMSMessage.query

    if current_user.is_sender and not current_user.is_admin:
        message_query = message_query.filter_by(sender_id=current_user.id)

    messages = message_query.order_by(SMSMessage.sent_at.desc()).limit(100).all()

    return render_template('dashboard/messages.html', messages=messages)


@bp.route('/audit')
@login_required
def audit():
    """View audit log"""
    if not current_user.is_admin:
        return redirect(url_for('dashboard.index'))

    logs = AuditLog.query.order_by(AuditLog.created_at.desc()).limit(100).all()

    return render_template('dashboard/audit.html', logs=logs)
