# Deployment Checklist for IONOS VPS

Use this checklist when deploying to your IONOS VPS.

## Pre-Deployment

- [ ] IONOS VPS provisioned and accessible via SSH
- [ ] Domain name configured (or using IP address)
- [ ] Twilio account set up with SMS-enabled phone number
- [ ] Twilio credentials ready (Account SID, Auth Token, Phone Number)

## Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and dependencies
sudo apt install python3 python3-pip python3-venv -y

# Install nginx
sudo apt install nginx -y

# Install certbot for SSL
sudo apt install certbot python3-certbot-nginx -y
```

## Application Deployment

```bash
# Create application directory
sudo mkdir -p /var/www/sms-volunteer-coordination
cd /var/www/sms-volunteer-coordination

# Clone repository (or upload files)
# Option 1: Git clone
sudo git clone https://github.com/yourusername/sms-volunteer-coordination.git .

# Option 2: Upload via SCP
# scp -r ./* user@your-vps:/var/www/sms-volunteer-coordination/

# Set permissions
sudo chown -R www-data:www-data /var/www/sms-volunteer-coordination

# Create virtual environment
sudo -u www-data python3 -m venv venv

# Activate and install dependencies
sudo -u www-data ./venv/bin/pip install -r requirements.txt
```

## Configuration

```bash
# Create .env file
sudo -u www-data cp .env.example .env
sudo -u www-data nano .env
```

**Fill in the following in .env:**
- [ ] SECRET_KEY (generate with: `python3 -c "import secrets; print(secrets.token_hex(32))"`)
- [ ] TWILIO_ACCOUNT_SID
- [ ] TWILIO_AUTH_TOKEN
- [ ] TWILIO_PHONE_NUMBER
- [ ] APP_BASE_URL (your domain or https://your-ip)

## Database Setup

```bash
# Initialize database
sudo -u www-data /var/www/sms-volunteer-coordination/venv/bin/python3 << 'EOF'
from app import create_app
from models import db

app = create_app()
with app.app_context():
    db.create_all()
    print("Database created successfully")
EOF
```

## Create Admin User

```bash
# Create first admin user
sudo -u www-data /var/www/sms-volunteer-coordination/venv/bin/python3 << 'EOF'
from app import create_app
from models import db, User

app = create_app()
with app.app_context():
    admin = User(
        name='Your Name',
        phone_number='+1234567890',  # YOUR PHONE NUMBER
        is_admin=True,
        is_sender=True,
        is_receiver=True,
        opt_in_confirmed=True
    )
    admin.set_password('CHANGE_THIS_PASSWORD')
    db.session.add(admin)
    db.session.commit()
    print(f"Created admin user: {admin.name}")
EOF
```

- [ ] Admin user created
- [ ] Admin password recorded securely

## Systemd Service

```bash
# Create service file
sudo nano /etc/systemd/system/sms-volunteer.service
```

**Paste the following:**
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

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable sms-volunteer
sudo systemctl start sms-volunteer
sudo systemctl status sms-volunteer
```

- [ ] Service running without errors
- [ ] Service set to start on boot

## Nginx Configuration

```bash
# Create nginx config
sudo nano /etc/nginx/sites-available/sms-volunteer
```

**Paste the following (replace your-domain.com):**
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

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/sms-volunteer /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

- [ ] Nginx configuration valid
- [ ] Nginx reloaded successfully

## SSL Certificate

```bash
# Get SSL certificate (replace your-domain.com)
sudo certbot --nginx -d your-domain.com

# Test auto-renewal
sudo certbot renew --dry-run
```

- [ ] SSL certificate installed
- [ ] Auto-renewal configured
- [ ] Site accessible via HTTPS

## Twilio Webhook Configuration

1. Log into [Twilio Console](https://console.twilio.com/)
2. Navigate to: Phone Numbers → Manage → Active Numbers
3. Select your SMS phone number
4. Under "Messaging Configuration":
   - **Webhook URL**: `https://your-domain.com/sms/receive`
   - **HTTP Method**: POST
5. Save configuration

- [ ] Webhook URL configured in Twilio
- [ ] Webhook URL is HTTPS (required by Twilio)

## Testing

```bash
# Test the application is running
curl http://localhost:5000

# Should see HTML response (login page)

# Check logs
sudo journalctl -u sms-volunteer -f
```

### Web UI Testing

- [ ] Access site at https://your-domain.com
- [ ] Login with admin credentials
- [ ] Create a test event
- [ ] Register a test user (your personal phone)
- [ ] Invite yourself to the event
- [ ] Receive SMS invitation
- [ ] Reply YES via SMS
- [ ] Check response appears in web UI
- [ ] Select yourself as volunteer
- [ ] Receive selection notification
- [ ] Test STATUS command via SMS
- [ ] Test CANCEL command via SMS
- [ ] Test STOP command (opt-out)
- [ ] Test JOIN command (opt back in)

### Monitoring

```bash
# Check service status
sudo systemctl status sms-volunteer

# View application logs
sudo journalctl -u sms-volunteer -f

# View nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Check disk usage
df -h

# Check memory usage
free -h
```

- [ ] All services running
- [ ] No errors in logs
- [ ] Resource usage acceptable

## Security Hardening

```bash
# Set up firewall
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable

# Verify firewall
sudo ufw status
```

- [ ] Firewall configured
- [ ] Only necessary ports open
- [ ] .env file not world-readable: `sudo chmod 600 /var/www/sms-volunteer-coordination/.env`
- [ ] Database file not world-readable: `sudo chmod 600 /var/www/sms-volunteer-coordination/*.db`

## Backup Setup

```bash
# Create backup script
sudo nano /usr/local/bin/backup-sms-volunteer.sh
```

**Script content:**
```bash
#!/bin/bash
BACKUP_DIR="/var/backups/sms-volunteer"
DATE=$(date +%Y%m%d_%H%M%S)
DB_PATH="/var/www/sms-volunteer-coordination/sms_volunteer.db"

mkdir -p $BACKUP_DIR
cp $DB_PATH "$BACKUP_DIR/sms_volunteer_$DATE.db"

# Keep only last 7 days
find $BACKUP_DIR -name "sms_volunteer_*.db" -mtime +7 -delete

echo "Backup completed: $DATE"
```

```bash
# Make executable
sudo chmod +x /usr/local/bin/backup-sms-volunteer.sh

# Add to cron (daily at 2 AM)
echo "0 2 * * * /usr/local/bin/backup-sms-volunteer.sh" | sudo crontab -
```

- [ ] Backup script created
- [ ] Daily backup scheduled
- [ ] Test backup manually: `sudo /usr/local/bin/backup-sms-volunteer.sh`

## Post-Deployment

- [ ] Document the admin credentials (securely!)
- [ ] Set up monitoring/alerting (optional)
- [ ] Share access with other admins
- [ ] Update DNS if needed
- [ ] Create initial users
- [ ] Test all workflows end-to-end

## Maintenance Commands

```bash
# Restart application
sudo systemctl restart sms-volunteer

# View logs
sudo journalctl -u sms-volunteer -f

# Update application
cd /var/www/sms-volunteer-coordination
sudo -u www-data git pull
sudo systemctl restart sms-volunteer

# Check database size
du -h /var/www/sms-volunteer-coordination/*.db
```

## Troubleshooting

### Application won't start
```bash
# Check logs
sudo journalctl -u sms-volunteer -xe

# Test manually
cd /var/www/sms-volunteer-coordination
sudo -u www-data ./venv/bin/gunicorn -w 1 -b 127.0.0.1:5000 'app:create_app()'
```

### SMS not received
1. Check Twilio webhook URL is correct and uses HTTPS
2. Check Twilio logs in console for errors
3. Test webhook manually:
```bash
curl -X POST https://your-domain.com/sms/receive \
  -d "From=+1234567890" \
  -d "To=+1234567890" \
  -d "Body=TEST" \
  -d "MessageSid=SM12345"
```

### Can't login
Reset password using the script in README.md "Troubleshooting" section.

## Success Criteria

- [ ] Application accessible via HTTPS
- [ ] Admin can log in
- [ ] Can create events and users
- [ ] SMS invitations work
- [ ] SMS replies are received and parsed
- [ ] Selection notifications work
- [ ] All SMS commands functional (STATUS, CANCEL, STOP, JOIN)
- [ ] Audit trail logging everything
- [ ] Resource usage under control
- [ ] Backups running daily

---

**Deployment Date:** ______________

**Deployed By:** ______________

**Admin Credentials Location:** ______________

**Notes:**
