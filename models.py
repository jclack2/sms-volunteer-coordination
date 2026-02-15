from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model - can have multiple roles"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    phone_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(200))  # Optional for Receivers

    # Roles (a user can have multiple roles)
    is_admin = db.Column(db.Boolean, default=False)
    is_sender = db.Column(db.Boolean, default=False)
    is_receiver = db.Column(db.Boolean, default=True)  # All users can receive

    # Opt-in status
    opted_in = db.Column(db.Boolean, default=False)
    opt_in_confirmed = db.Column(db.Boolean, default=False)
    opt_in_pending = db.Column(db.Boolean, default=False)
    opted_in_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    sent_messages = db.relationship('SMSMessage', foreign_keys='SMSMessage.sender_id', backref='sender', lazy=True)
    received_messages = db.relationship('SMSMessage', foreign_keys='SMSMessage.receiver_id', backref='receiver', lazy=True)
    volunteer_responses = db.relationship('VolunteerResponse', foreign_keys='VolunteerResponse.user_id', backref='volunteer', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.name} ({self.phone_number})>'


class Event(db.Model):
    """Event model"""
    __tablename__ = 'events'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(200))

    event_datetime = db.Column(db.DateTime, nullable=False)
    signup_cutoff = db.Column(db.DateTime, nullable=False)

    # Volunteer slots
    max_volunteers = db.Column(db.Integer)  # NULL = unlimited

    # Who manages this event
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Status
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Custom reply strings for this event
    custom_yes_strings = db.Column(db.Text)  # Comma-separated
    custom_no_strings = db.Column(db.Text)   # Comma-separated

    # Relationships
    admin = db.relationship('User', foreign_keys=[admin_id], backref='administered_events')
    sender = db.relationship('User', foreign_keys=[sender_id], backref='managed_events')
    volunteer_responses = db.relationship('VolunteerResponse', foreign_keys='VolunteerResponse.event_id', backref='event', lazy=True, cascade='all, delete-orphan')
    invited_users = db.relationship('EventInvitation', backref='event', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Event {self.title}>'


class EventInvitation(db.Model):
    """Tracks who was invited to an event"""
    __tablename__ = 'event_invitations'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    invited_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='invitations')

    __table_args__ = (
        db.UniqueConstraint('event_id', 'user_id', name='unique_event_user'),
    )


class VolunteerResponse(db.Model):
    """Volunteer response to event signup"""
    __tablename__ = 'volunteer_responses'

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Response data
    raw_response = db.Column(db.Text)  # Original SMS text
    parsed_response = db.Column(db.String(20))  # YES, NO, UNKNOWN
    requires_review = db.Column(db.Boolean, default=False)  # Flag for manual review

    # Selection status
    status = db.Column(db.String(20), default='pending')  # pending, selected, not_selected, waitlisted, cancelled
    selected_at = db.Column(db.DateTime)
    selected_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Timestamps
    responded_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    selected_by = db.relationship('User', foreign_keys=[selected_by_id])

    def __repr__(self):
        return f'<VolunteerResponse Event:{self.event_id} User:{self.user_id} Status:{self.status}>'


class SMSMessage(db.Model):
    """Audit trail for all SMS messages"""
    __tablename__ = 'sms_messages'

    id = db.Column(db.Integer, primary_key=True)

    # Twilio data
    message_sid = db.Column(db.String(100), unique=True, index=True)

    # Direction
    direction = db.Column(db.String(20))  # outbound, inbound

    # Participants
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # NULL for inbound
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id'))  # NULL for system messages

    from_number = db.Column(db.String(20), nullable=False)
    to_number = db.Column(db.String(20), nullable=False)

    # Message content
    body = db.Column(db.Text, nullable=False)

    # Status
    status = db.Column(db.String(20))  # queued, sent, delivered, failed, received
    error_message = db.Column(db.Text)

    # Context
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'))
    message_type = db.Column(db.String(50))  # opt_in, invite, reminder, selection, reply, status_query

    # Timestamps
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    delivered_at = db.Column(db.DateTime)

    event = db.relationship('Event', backref='messages')

    def __repr__(self):
        return f'<SMSMessage {self.direction} {self.from_number} -> {self.to_number}>'


class AuditLog(db.Model):
    """Audit log for important actions"""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)

    # Who did what
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)

    # Context
    event_id = db.Column(db.Integer, db.ForeignKey('events.id'))

    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='audit_logs')
    event = db.relationship('Event', backref='audit_logs')

    def __repr__(self):
        return f'<AuditLog {self.action} at {self.created_at}>'
