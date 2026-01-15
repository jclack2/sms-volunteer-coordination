from flask import Blueprint, render_template, redirect, url_for, request, flash, jsonify
from flask_login import login_required, current_user
from models import db, Event, User, EventInvitation, VolunteerResponse, AuditLog
from services.sms_service import SMSService
from datetime import datetime

bp = Blueprint('events', __name__, url_prefix='/events')


@bp.route('/')
@login_required
def list_events():
    """List all events"""
    if current_user.is_admin:
        events = Event.query.order_by(Event.event_datetime.desc()).all()
    elif current_user.is_sender:
        events = Event.query.filter_by(sender_id=current_user.id)\
            .order_by(Event.event_datetime.desc()).all()
    else:
        flash('You do not have permission to view events', 'error')
        return redirect(url_for('dashboard.index'))

    return render_template('events/list.html', events=events)


@bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_event():
    """Create a new event"""
    if not current_user.is_admin:
        flash('Admin access required', 'error')
        return redirect(url_for('events.list_events'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        location = request.form.get('location')
        event_datetime = datetime.strptime(request.form.get('event_datetime'), '%Y-%m-%dT%H:%M')
        signup_cutoff = datetime.strptime(request.form.get('signup_cutoff'), '%Y-%m-%dT%H:%M')
        max_volunteers = request.form.get('max_volunteers')
        sender_id = request.form.get('sender_id')
        custom_yes = request.form.get('custom_yes_strings', '')
        custom_no = request.form.get('custom_no_strings', '')

        # Convert max_volunteers
        if max_volunteers:
            max_volunteers = int(max_volunteers)
        else:
            max_volunteers = None

        # Create event
        event = Event(
            title=title,
            description=description,
            location=location,
            event_datetime=event_datetime,
            signup_cutoff=signup_cutoff,
            max_volunteers=max_volunteers,
            admin_id=current_user.id,
            sender_id=sender_id,
            custom_yes_strings=custom_yes,
            custom_no_strings=custom_no
        )

        db.session.add(event)
        db.session.commit()

        # Log audit
        audit = AuditLog(
            user_id=current_user.id,
            event_id=event.id,
            action='event_created',
            details=f'Created event: {title}'
        )
        db.session.add(audit)
        db.session.commit()

        flash(f'Event "{title}" created successfully', 'success')
        return redirect(url_for('events.view_event', event_id=event.id))

    # Get all senders for dropdown
    senders = User.query.filter_by(is_sender=True).all()
    return render_template('events/create.html', senders=senders)


@bp.route('/<int:event_id>')
@login_required
def view_event(event_id):
    """View event details"""
    event = Event.query.get_or_404(event_id)

    # Check permissions
    if not (current_user.is_admin or event.sender_id == current_user.id):
        flash('You do not have permission to view this event', 'error')
        return redirect(url_for('dashboard.index'))

    # Get responses
    responses = VolunteerResponse.query.filter_by(event_id=event_id)\
        .join(User)\
        .order_by(VolunteerResponse.responded_at.desc())\
        .all()

    # Get invitations
    invitations = EventInvitation.query.filter_by(event_id=event_id)\
        .join(User)\
        .all()

    return render_template('events/view.html',
                         event=event,
                         responses=responses,
                         invitations=invitations)


@bp.route('/<int:event_id>/invite', methods=['GET', 'POST'])
@login_required
def invite_volunteers(event_id):
    """Invite volunteers to an event"""
    event = Event.query.get_or_404(event_id)

    # Check permissions
    if not (current_user.is_admin or event.sender_id == current_user.id):
        flash('You do not have permission to manage this event', 'error')
        return redirect(url_for('events.view_event', event_id=event_id))

    if request.method == 'POST':
        selected_users = request.form.getlist('users')

        if not selected_users:
            flash('Please select at least one user to invite', 'error')
            return redirect(url_for('events.invite_volunteers', event_id=event_id))

        sms_service = SMSService()
        invited_count = 0

        for user_id in selected_users:
            user = User.query.get(int(user_id))
            if not user:
                continue

            # Check if already invited
            existing = EventInvitation.query.filter_by(
                event_id=event_id,
                user_id=user.id
            ).first()

            if existing:
                continue

            # Create invitation
            invitation = EventInvitation(
                event_id=event_id,
                user_id=user.id
            )
            db.session.add(invitation)

            # Check opt-in status
            if not user.opt_in_confirmed:
                # Send opt-in message
                sms_service.send_opt_in_initial(user, event)
            else:
                # Send invitation
                sms_service.send_event_invitation(user, event, event.sender)

            invited_count += 1

        db.session.commit()

        # Log audit
        audit = AuditLog(
            user_id=current_user.id,
            event_id=event.id,
            action='invitations_sent',
            details=f'Invited {invited_count} volunteers'
        )
        db.session.add(audit)
        db.session.commit()

        flash(f'Invited {invited_count} volunteers', 'success')
        return redirect(url_for('events.view_event', event_id=event_id))

    # Get all receivers who are opted in
    available_users = User.query.filter_by(
        is_receiver=True,
        opt_in_confirmed=True
    ).all()

    # Get already invited users
    invited_user_ids = [inv.user_id for inv in event.invited_users]

    return render_template('events/invite.html',
                         event=event,
                         available_users=available_users,
                         invited_user_ids=invited_user_ids)


@bp.route('/<int:event_id>/select', methods=['POST'])
@login_required
def select_volunteers(event_id):
    """Select volunteers for an event"""
    event = Event.query.get_or_404(event_id)

    # Check permissions
    if not (current_user.is_admin or event.sender_id == current_user.id):
        return jsonify({'error': 'Permission denied'}), 403

    selected_user_ids = request.json.get('selected_users', [])
    send_selected_msg = request.json.get('send_selected_msg', False)
    send_everyone_msg = request.json.get('send_everyone_msg', False)
    selected_message = request.json.get('selected_message', '')
    everyone_message = request.json.get('everyone_message', '')
    include_names = request.json.get('include_names', False)
    include_phone = request.json.get('include_phone', False)

    # Update selections
    all_responses = VolunteerResponse.query.filter_by(event_id=event_id).all()

    for response in all_responses:
        if response.user_id in selected_user_ids:
            response.status = 'selected'
            response.selected_at = datetime.utcnow()
            response.selected_by_id = current_user.id
        elif response.status == 'pending' or response.status == 'selected':
            response.status = 'not_selected'

        response.updated_at = datetime.utcnow()

    db.session.commit()

    # Send messages
    sms_service = SMSService()

    if send_selected_msg and selected_message:
        for user_id in selected_user_ids:
            user = User.query.get(user_id)
            if user:
                sms_service.send_custom_message(user, event, selected_message, current_user)

    if send_everyone_msg and everyone_message:
        # Build message with optional names
        message_body = everyone_message

        if include_names:
            selected_users = User.query.filter(User.id.in_(selected_user_ids)).all()
            names = []
            for user in selected_users:
                if include_phone:
                    phone_last4 = user.phone_number[-4:]
                    names.append(f"{user.name} ({phone_last4})")
                else:
                    names.append(user.name)
            message_body += "\n\nSelected volunteers:\n" + "\n".join(names)

        # Send to all invited users
        for invitation in event.invited_users:
            user = invitation.user
            sms_service.send_custom_message(user, event, message_body, current_user)

    # Log audit
    audit = AuditLog(
        user_id=current_user.id,
        event_id=event.id,
        action='volunteers_selected',
        details=f'Selected {len(selected_user_ids)} volunteers'
    )
    db.session.add(audit)
    db.session.commit()

    return jsonify({'success': True, 'selected_count': len(selected_user_ids)})
