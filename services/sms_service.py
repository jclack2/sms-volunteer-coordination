from twilio.rest import Client
from models import db, SMSMessage, User
from datetime import datetime
import os


class SMSService:
    """Service for sending SMS via Twilio"""

    def __init__(self):
        self.client = Client(
            os.environ.get('TWILIO_ACCOUNT_SID'),
            os.environ.get('TWILIO_AUTH_TOKEN')
        )
        self.from_number = os.environ.get('TWILIO_PHONE_NUMBER')

    def send_sms(self, to_number, body, sender_id=None, receiver_id=None, event_id=None, message_type=None):
        """
        Send an SMS message via Twilio

        Args:
            to_number: Recipient phone number
            body: Message text
            sender_id: ID of user sending (optional)
            receiver_id: ID of user receiving (optional)
            event_id: Related event ID (optional)
            message_type: Type of message (optional)

        Returns:
            SMSMessage object or None if failed
        """
        try:
            # Send via Twilio
            message = self.client.messages.create(
                body=body,
                from_=self.from_number,
                to=to_number
            )

            # Log in database
            sms_record = SMSMessage(
                message_sid=message.sid,
                direction='outbound',
                sender_id=sender_id,
                receiver_id=receiver_id,
                from_number=self.from_number,
                to_number=to_number,
                body=body,
                status='sent',
                event_id=event_id,
                message_type=message_type,
                sent_at=datetime.utcnow()
            )

            db.session.add(sms_record)
            db.session.commit()

            return sms_record

        except Exception as e:
            # Log error
            error_record = SMSMessage(
                direction='outbound',
                sender_id=sender_id,
                receiver_id=receiver_id,
                from_number=self.from_number,
                to_number=to_number,
                body=body,
                status='failed',
                error_message=str(e),
                event_id=event_id,
                message_type=message_type,
                sent_at=datetime.utcnow()
            )
            db.session.add(error_record)
            db.session.commit()

            print(f"Failed to send SMS to {to_number}: {e}")
            return None

    def send_opt_in_initial(self, user, event):
        """Send initial opt-in message"""
        body = f"You are on the short list for {event.title}. Reply JOIN to receive updates."

        # Mark user as opt-in pending
        user.opt_in_pending = True
        db.session.commit()

        return self.send_sms(
            to_number=user.phone_number,
            body=body,
            receiver_id=user.id,
            event_id=event.id,
            message_type='opt_in'
        )

    def send_opt_in_confirmation(self, user):
        """Send opt-in confirmation request"""
        body = "Reply YES to confirm."

        return self.send_sms(
            to_number=user.phone_number,
            body=body,
            receiver_id=user.id,
            message_type='opt_in'
        )

    def send_event_invitation(self, user, event, sender):
        """Send event invitation to a user"""
        body = f"{event.title}\n"
        body += f"Date: {event.event_datetime.strftime('%b %d, %Y at %I:%M %p')}\n"
        body += f"Location: {event.location}\n\n"
        body += f"{event.description}\n\n"
        body += "Reply YES if available, NO if not."

        return self.send_sms(
            to_number=user.phone_number,
            body=body,
            sender_id=sender.id,
            receiver_id=user.id,
            event_id=event.id,
            message_type='invite'
        )

    def send_selection_notification(self, user, event, selected=True):
        """Notify user of selection status"""
        if selected:
            body = f"You've been selected for {event.title} on {event.event_datetime.strftime('%b %d at %I:%M %p')}. "
            body += f"Location: {event.location}. See you there!"
        else:
            body = f"Thank you for your interest in {event.title}. We have filled our volunteer slots for this event."

        return self.send_sms(
            to_number=user.phone_number,
            body=body,
            receiver_id=user.id,
            event_id=event.id,
            message_type='selection'
        )

    def send_custom_message(self, user, event, message_body, sender):
        """Send custom message from sender"""
        return self.send_sms(
            to_number=user.phone_number,
            body=message_body,
            sender_id=sender.id,
            receiver_id=user.id,
            event_id=event.id,
            message_type='custom'
        )

    def send_status_response(self, user, status_text):
        """Send status query response"""
        return self.send_sms(
            to_number=user.phone_number,
            body=status_text,
            receiver_id=user.id,
            message_type='status_query'
        )
