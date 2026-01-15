from flask import Blueprint, request
from models import db, User, Event, VolunteerResponse, SMSMessage, AuditLog
from services.reply_parser import ReplyParser
from services.sms_service import SMSService
from datetime import datetime
import phonenumbers

bp = Blueprint('sms_webhook', __name__, url_prefix='/sms')


@bp.route('/receive', methods=['POST'])
def receive_sms():
    """
    Twilio webhook for receiving SMS messages
    Configure this URL in Twilio console: https://your-domain.com/sms/receive
    """
    # Get Twilio data
    from_number = request.form.get('From')
    to_number = request.form.get('To')
    body = request.form.get('Body', '').strip()
    message_sid = request.form.get('MessageSid')

    # Normalize phone number
    try:
        parsed = phonenumbers.parse(from_number, None)
        normalized_phone = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except:
        normalized_phone = from_number

    # Find user
    user = User.query.filter_by(phone_number=normalized_phone).first()

    # Log incoming message
    incoming_msg = SMSMessage(
        message_sid=message_sid,
        direction='inbound',
        from_number=from_number,
        to_number=to_number,
        body=body,
        status='received',
        receiver_id=user.id if user else None,
        sent_at=datetime.utcnow()
    )
    db.session.add(incoming_msg)

    sms_service = SMSService()

    # Handle opt-out
    if ReplyParser.is_opt_out(body):
        if user:
            user.opted_in = False
            user.opt_in_confirmed = False
            db.session.commit()
            sms_service.send_sms(
                to_number=from_number,
                body="You have been unsubscribed. Reply JOIN to subscribe again.",
                message_type='opt_out'
            )
        db.session.commit()
        return '', 200

    # If user doesn't exist, can't process further
    if not user:
        # Could send "Unknown number" message here if desired
        db.session.commit()
        return '', 200

    # Handle opt-in JOIN
    if ReplyParser.is_opt_in_join(body):
        sms_service.send_opt_in_confirmation(user)
        db.session.commit()
        return '', 200

    # Handle opt-in confirmation
    if user.opt_in_pending and ReplyParser.is_opt_in_confirm(body):
        user.opted_in = True
        user.opt_in_confirmed = True
        user.opt_in_pending = False
        user.opted_in_at = datetime.utcnow()
        db.session.commit()

        sms_service.send_sms(
            to_number=from_number,
            body="Thank you! You are now subscribed to volunteer updates.",
            receiver_id=user.id,
            message_type='opt_in'
        )
        db.session.commit()
        return '', 200

    # Check if user is opted in
    if not user.opt_in_confirmed:
        # User needs to opt in first
        db.session.commit()
        return '', 200

    # Handle status query
    if ReplyParser.is_status_query(body):
        handle_status_query(user, sms_service)
        db.session.commit()
        return '', 200

    # Handle cancellation
    if ReplyParser.is_cancellation(body):
        handle_cancellation(user, sms_service)
        db.session.commit()
        return '', 200

    # Handle volunteer response
    handle_volunteer_response(user, body, incoming_msg, sms_service)
    db.session.commit()

    return '', 200


def handle_status_query(user, sms_service):
    """Handle STATUS query from user"""
    # Find user's most recent volunteer response
    response = VolunteerResponse.query.filter_by(user_id=user.id)\
        .join(Event)\
        .filter(Event.is_active == True)\
        .order_by(VolunteerResponse.responded_at.desc())\
        .first()

    if not response:
        status_text = "You have no active volunteer signups."
    else:
        event = response.event
        status_map = {
            'selected': f"Confirmed for {event.title} on {event.event_datetime.strftime('%b %d at %I:%M %p')}",
            'waitlisted': f"Waitlisted for {event.title}",
            'not_selected': f"Not selected for {event.title}",
            'pending': f"Your response for {event.title} is pending review"
        }
        status_text = status_map.get(response.status, "Status unknown")

    sms_service.send_status_response(user, status_text)


def handle_cancellation(user, sms_service):
    """Handle cancellation request from user"""
    # Find user's selected events
    response = VolunteerResponse.query.filter_by(
        user_id=user.id,
        status='selected'
    ).join(Event).filter(Event.is_active == True).first()

    if response:
        response.status = 'cancelled'
        response.updated_at = datetime.utcnow()

        # Log audit
        audit = AuditLog(
            user_id=user.id,
            event_id=response.event_id,
            action='volunteer_cancelled',
            details=f'{user.name} cancelled via SMS'
        )
        db.session.add(audit)

        # Notify sender
        event = response.event
        sender = event.sender
        if sender:
            sms_service.send_sms(
                to_number=sender.phone_number,
                body=f"ALERT: {user.name} cancelled for {event.title}",
                sender_id=user.id,
                receiver_id=sender.id,
                event_id=event.id,
                message_type='cancellation_alert'
            )

        sms_service.send_sms(
            to_number=user.phone_number,
            body=f"You have been removed from {event.title}. Thank you for letting us know.",
            receiver_id=user.id,
            event_id=event.id,
            message_type='cancellation_confirm'
        )
    else:
        sms_service.send_sms(
            to_number=user.phone_number,
            body="You have no active volunteer commitments to cancel.",
            receiver_id=user.id,
            message_type='cancellation_none'
        )


def handle_volunteer_response(user, body, incoming_msg, sms_service):
    """Handle volunteer availability response"""
    # Find the most recent event invitation for this user
    from models import EventInvitation

    invitation = EventInvitation.query.filter_by(user_id=user.id)\
        .join(Event)\
        .filter(Event.is_active == True)\
        .order_by(EventInvitation.invited_at.desc())\
        .first()

    if not invitation:
        # No active event invitation
        return

    event = invitation.event

    # Get custom response strings
    custom_yes = event.custom_yes_strings.split(',') if event.custom_yes_strings else []
    custom_no = event.custom_no_strings.split(',') if event.custom_no_strings else []

    # Parse response
    parsed_response, requires_review = ReplyParser.parse_response(body, custom_yes, custom_no)

    # Check if user already responded
    existing_response = VolunteerResponse.query.filter_by(
        event_id=event.id,
        user_id=user.id
    ).first()

    if existing_response:
        # Update existing response
        existing_response.raw_response = body
        existing_response.parsed_response = parsed_response
        existing_response.requires_review = requires_review
        existing_response.responded_at = datetime.utcnow()
        existing_response.updated_at = datetime.utcnow()

        # Log audit
        audit = AuditLog(
            user_id=user.id,
            event_id=event.id,
            action='response_updated',
            details=f'{user.name} updated response: {parsed_response}'
        )
        db.session.add(audit)
    else:
        # Create new response
        new_response = VolunteerResponse(
            event_id=event.id,
            user_id=user.id,
            raw_response=body,
            parsed_response=parsed_response,
            requires_review=requires_review,
            status='pending'
        )
        db.session.add(new_response)

        # Log audit
        audit = AuditLog(
            user_id=user.id,
            event_id=event.id,
            action='response_received',
            details=f'{user.name} responded: {parsed_response}'
        )
        db.session.add(audit)

    # Update incoming message with event context
    incoming_msg.event_id = event.id
    incoming_msg.message_type = 'volunteer_response'

    # Send confirmation
    if parsed_response == 'YES':
        confirm_text = f"Got it! We received your YES for {event.title}. You'll hear from us soon."
    elif parsed_response == 'NO':
        confirm_text = f"Thank you for letting us know."
    else:
        confirm_text = f"We received your message. The event organizer will review it."

    sms_service.send_sms(
        to_number=user.phone_number,
        body=confirm_text,
        receiver_id=user.id,
        event_id=event.id,
        message_type='response_confirmation'
    )
