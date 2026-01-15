# SMS Volunteer Coordination

A lightweight web application for coordinating volunteers via SMS messaging. Designed for hyper-local, trusted communities (e.g., AA groups) with a focus on simplicity and privacy.

## Overview

This system enables trusted organizers to:
- Create volunteer events (meetings, activities)
- Send individual SMS invitations to potential volunteers
- Receive and parse SMS responses (YES/NO/custom phrases)
- Select volunteers and notify them
- Track all communications in an audit trail

**Key Features:**
- **No group texts** - all messages sent individually
- **Double opt-in SMS flow** - industry best practices for consent
- **Role-based access** - Admin, Sender, and Receiver roles
- **Reply parsing** - handles YES/NO responses and custom phrases
- **Event-centric** - one active volunteer signup per event
- **Audit trail** - complete logging for transparency
- **Status queries** - users can text STATUS to check their commitment
- **Cancellation handling** - users can text CANCEL to drop out

## Tech Stack

- **Backend**: Python 3.8+ with Flask
- **Database**: SQLite (v1 - sufficient for small deployments)
- **SMS**: Twilio API
- **Frontend**: Bootstrap 5 (no build process)
- **Deployment**: Single VPS (IONOS $2 tier compatible)

## Project Structure

```
sms-volunteer-coordination/
├── app.py                  # Flask application factory
├── config.py              # Configuration management
├── models.py              # Database models (SQLAlchemy)
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── routes/               # Route blueprints
│   ├── auth.py          # Authentication & user registration
│   ├── dashboard.py     # Dashboard & stats
│   ├── events.py        # Event management
│   └── sms_webhook.py   # Twilio webhook handler
├── services/            # Business logic
│   ├── sms_service.py  # Twilio SMS sending
│   └── reply_parser.py # SMS reply parsing
└── templates/           # HTML templates
    ├── base.html
    ├── auth/
    ├── dashboard/
    └── events/
```

## Installation & Setup

### 1. Prerequisites

- Python 3.8+
- Twilio account with phone number
- VPS or local machine for hosting

### 2. Clone and Setup

```bash
# Clone repository
git clone https://github.com/yourusername/sms-volunteer-coordination.git
cd sms-volunteer-coordination

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
nano .env
```

**Required environment variables:**

```bash
# Flask
SECRET_KEY=your-random-secret-key-here-change-this
FLASK_ENV=production

# Database
DATABASE_URL=sqlite:///sms_volunteer.db

# Twilio
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890

# Application URL (for webhooks)
APP_BASE_URL=https://your-domain.com
```

**Generate a secure SECRET_KEY:**

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Initialize Database

```bash
python3 -c "from app import create_app; from models import db; app = create_app(); app.app_context().push(); db.create_all()"
```

### 5. Create First Admin User

```bash
python3 << 'EOF'
from app import create_app
from models import db, User

app = create_app()
with app.app_context():
    admin = User(
        name='Admin User',
        phone_number='+1234567890',  # Your phone number
        is_admin=True,
        is_sender=True,
        is_receiver=True,
        opt_in_confirmed=True  # Pre-confirm for admin
    )
    admin.set_password('change_this_password')
    db.session.add(admin)
    db.session.commit()
    print(f"Created admin user: {admin.name}")
EOF
```

### 6. Configure Twilio Webhook

1. Log into your [Twilio Console](https://console.twilio.com/)
2. Navigate to Phone Numbers → Manage → Active Numbers
3. Select your SMS-enabled phone number
4. Under "Messaging Configuration":
   - **Webhook URL**: `https://your-domain.com/sms/receive`
   - **HTTP Method**: POST
5. Save configuration

**Testing webhooks locally:**

Use ngrok for local development:

```bash
# Install ngrok
brew install ngrok  # macOS
# or download from https://ngrok.com/

# Start ngrok tunnel
ngrok http 5000

# Use the https URL in Twilio webhook config
# Example: https://abc123.ngrok.io/sms/receive
```

## Running the Application

### Development Mode

```bash
# Activate virtual environment
source venv/bin/activate

# Run Flask development server
flask run --host=0.0.0.0 --port=5000
```

Access at: `http://localhost:5000`

### Production Deployment (IONOS VPS)

#### Using Gunicorn

```bash
# Install gunicorn (already in requirements.txt)
pip install gunicorn

# Run with gunicorn
gunicorn -w 2 -b 0.0.0.0:5000 'app:create_app()'
```

#### Systemd Service (Recommended)

Create `/etc/systemd/system/sms-volunteer.service`:

```ini
[Unit]
Description=SMS Volunteer Coordination
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/sms-volunteer-coordination
Environment="PATH=/var/www/sms-volunteer-coordination/venv/bin"
ExecStart=/var/www/sms-volunteer-coordination/venv/bin/gunicorn -w 2 -b 127.0.0.1:5000 'app:create_app()'
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable sms-volunteer
sudo systemctl start sms-volunteer
sudo systemctl status sms-volunteer
```

#### Nginx Reverse Proxy

Create `/etc/nginx/sites-available/sms-volunteer`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/sms-volunteer /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

#### SSL Certificate (Recommended)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Usage

### User Roles

- **Admin**: Creates events, manages users, views all data
- **Sender**: Sends SMS for events, reviews responses, selects volunteers
- **Receiver**: Receives SMS invitations, replies via text

A single user can have multiple roles.

### Workflows

#### 1. Volunteer Signup Flow

1. **Admin creates event** (web UI)
   - Title, date, location, description
   - Select Sender
   - Optionally set max volunteers

2. **Sender invites volunteers** (web UI)
   - Select Receivers from user list
   - System sends individual SMS to each

3. **If user not opted in:**
   - System sends: "You are on the short list for [EVENT]. Reply JOIN to receive updates."
   - User replies: `JOIN`
   - System sends: "Reply YES to confirm."
   - User replies: `YES`
   - System confirms opt-in

4. **Opted-in users receive invitation:**
   ```
   [Event Title]
   Date: [Date/Time]
   Location: [Location]

   [Description]

   Reply YES if available, NO if not.
   ```

5. **Users reply via SMS:**
   - `YES` / `Y` / `AVAILABLE` → Marked as available
   - `NO` / `N` / `CAN'T` → Marked as unavailable
   - Free text like "Yes but only after 6" → Flagged for review

6. **Sender reviews responses** (web UI)
   - See all responses in table
   - Flagged responses shown for manual review
   - Select volunteers (checkbox)

7. **Sender finalizes selection** (web UI)
   - Choose message options:
     - Send to selected only
     - Send to everyone (with optional names/count)
   - System sends individual SMS notifications

#### 2. Meeting Announcement / Reminder

1. Create event without volunteer signup requirements
2. Invite all relevant users
3. Send custom message via web UI

### SMS Commands

Users can text these commands anytime:

- **`STATUS`** - Check current volunteer status
- **`CANCEL`** or `DROP` - Cancel volunteer commitment
- **`STOP`** - Opt out of all messages
- **`JOIN`** - Opt back in (if previously opted out)

### Reply Parsing

**Standard affirmative responses:**
- YES, Y, YEAH, YEP, YUP, SURE, OK, OKAY, AVAILABLE, CAN DO, I CAN, I'M AVAILABLE, COUNT ME IN, I'M IN, SOUNDS GOOD

**Standard negative responses:**
- NO, N, NOPE, NAH, CAN'T, CANNOT, NOT AVAILABLE, UNAVAILABLE, SORRY, UNABLE

**Custom responses:**
- Admins can define custom phrases per event
- Example: "I'll be there", "Busy that day"

**Free text:**
- Anything else is logged as raw text
- Flagged for Sender review
- Example: "Yes but only after 6pm"

## Database Schema

### Key Models

- **User**: Phone number (canonical ID), name, roles, opt-in status
- **Event**: Title, date, location, admin, sender, volunteer settings
- **EventInvitation**: Who was invited to which event
- **VolunteerResponse**: User responses (raw + parsed), selection status
- **SMSMessage**: Complete SMS audit trail (inbound + outbound)
- **AuditLog**: All important actions (create event, select volunteers, etc.)

## Security & Privacy

- **Phone numbers** are canonical identifiers
- **Passwords** optional for Receivers (SMS-only users)
- **No group texts** - all messages individual
- **Opt-in required** - double opt-in flow
- **Opt-out respected** - STOP honored immediately
- **Privacy-first** - phone numbers only shown as last 4 digits in UI
- **Audit trail** - all actions logged for transparency
- **Trusted users only** - no public signup

## Limitations (v1)

This is deliberately a minimal v1. **Not included:**

- Multiple concurrent events per user
- Automatic waitlist promotion
- Recurring events
- Email notifications
- Mobile app
- API
- Advanced scheduling
- Group messaging
- File attachments
- Multi-language support

## Troubleshooting

### SMS not received

1. Check Twilio webhook configuration
2. Verify phone number format (E.164: +1234567890)
3. Check Twilio logs in console
4. Verify APP_BASE_URL is correct
5. Check application logs

### Webhook errors

```bash
# View logs
sudo journalctl -u sms-volunteer -f

# Test webhook locally with ngrok
curl -X POST https://your-ngrok-url.ngrok.io/sms/receive \
  -d "From=+1234567890" \
  -d "To=+1987654321" \
  -d "Body=YES" \
  -d "MessageSid=SM12345"
```

### Database issues

```bash
# Reset database (CAUTION: deletes all data)
rm sms_volunteer.db
python3 -c "from app import create_app; from models import db; app = create_app(); app.app_context().push(); db.create_all()"
```

### Can't login

```bash
# Reset admin password
python3 << 'EOF'
from app import create_app
from models import db, User

app = create_app()
with app.app_context():
    user = User.query.filter_by(phone_number='+1234567890').first()
    if user:
        user.set_password('new_password')
        db.session.commit()
        print('Password reset')
    else:
        print('User not found')
EOF
```

## Contributing

This is a v1 system for trusted, hyper-local use. Contributions welcome for:

- Bug fixes
- Security improvements
- Documentation improvements
- Test coverage

**Not accepting:**
- Feature creep (keep it simple!)
- Over-engineering
- Cloud dependencies
- Complex deployment requirements

## License

[Choose appropriate license - MIT recommended for open source]

## Support

For issues, questions, or feature requests, please open a GitHub issue.

## Acknowledgments

Built for AA volunteer coordination, with privacy and simplicity as core values.
