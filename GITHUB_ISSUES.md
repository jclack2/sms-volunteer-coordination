# GitHub Issues to Create

## Milestone: v1.0 - Initial Release

### Issue 1: Test deployment on IONOS VPS
**Label:** deployment, testing

Test the complete deployment process on a low-resource IONOS VPS:

- [ ] Set up Python environment
- [ ] Install dependencies
- [ ] Configure Twilio webhooks
- [ ] Test database initialization
- [ ] Test with gunicorn
- [ ] Set up systemd service
- [ ] Configure nginx reverse proxy
- [ ] Set up SSL with certbot
- [ ] Test complete volunteer signup workflow
- [ ] Test SMS sending/receiving
- [ ] Monitor resource usage

**Success criteria:**
- App runs on $2 tier VPS
- All SMS workflows function correctly
- Resource usage remains within limits

---

### Issue 2: Add unit tests for reply parser
**Label:** testing, enhancement

Add comprehensive unit tests for the `ReplyParser` service:

- [ ] Test standard YES responses
- [ ] Test standard NO responses
- [ ] Test custom response strings
- [ ] Test opt-in/opt-out keywords
- [ ] Test status queries
- [ ] Test cancellation requests
- [ ] Test edge cases (empty strings, special characters)
- [ ] Test case-insensitive matching

**Acceptance criteria:**
- 90%+ code coverage for reply_parser.py
- All edge cases handled correctly

---

### Issue 3: Add database migration support
**Label:** enhancement

Implement database migrations using Flask-Migrate/Alembic to handle schema changes:

- [ ] Add Flask-Migrate to dependencies
- [ ] Initialize Alembic
- [ ] Create initial migration
- [ ] Document migration workflow in README
- [ ] Test upgrade/downgrade

**Why:** Schema changes currently require database recreation. Migrations enable safe updates in production.

---

### Issue 4: Implement opt-out confirmation
**Label:** enhancement, compliance

When a user texts STOP, send a confirmation message:

- [ ] Add opt-out confirmation message
- [ ] Update audit log for opt-outs
- [ ] Add test cases

**Message:** "You have been unsubscribed. Reply JOIN to subscribe again."

---

### Issue 5: Add event edit/delete functionality
**Label:** feature

Currently events can only be created. Add edit and soft-delete:

- [ ] Create edit event route and template
- [ ] Add "is_active" toggle (soft delete)
- [ ] Update event list to show inactive events differently
- [ ] Add audit logging for edits/deletes
- [ ] Test that deleted events don't send messages

---

### Issue 6: Add user profile page
**Label:** enhancement

Allow users to view/update their own information:

- [ ] Create user profile route
- [ ] Show opt-in status
- [ ] Show upcoming events they're selected for
- [ ] Allow password change
- [ ] Show message history

---

### Issue 7: Improve error handling in webhook
**Label:** bug, enhancement

The SMS webhook should handle more edge cases gracefully:

- [ ] Handle missing Twilio parameters
- [ ] Handle invalid phone numbers
- [ ] Handle database errors (retry logic)
- [ ] Log all errors with context
- [ ] Return appropriate Twilio error responses
- [ ] Add webhook signature verification

---

### Issue 8: Add message templates
**Label:** enhancement

Create reusable message templates for common scenarios:

- [ ] Template model in database
- [ ] UI for creating/editing templates
- [ ] Variable substitution ({{name}}, {{event_title}}, etc.)
- [ ] Apply templates when sending messages

---

### Issue 9: Add search and filtering
**Label:** enhancement

Add search/filter capabilities:

- [ ] Filter events by date range
- [ ] Search users by name/phone
- [ ] Filter messages by type/status
- [ ] Filter audit logs by action/user

---

### Issue 10: Add rate limiting
**Label:** security, enhancement

Prevent abuse of SMS sending:

- [ ] Add rate limiting per user/event
- [ ] Configurable limits in .env
- [ ] Alert admins when limits hit
- [ ] Track SMS costs/usage

---

### Issue 11: Create backup/restore script
**Label:** operations

Add database backup and restore utilities:

- [ ] Backup script (SQLite → file)
- [ ] Restore script
- [ ] Automated daily backups
- [ ] Document in README

---

### Issue 12: Add Dockerfile (optional)
**Label:** enhancement, deployment

While not required for v1, a Dockerfile would help with:

- [ ] Create Dockerfile
- [ ] Create docker-compose.yml
- [ ] Update README with Docker instructions
- [ ] Keep simple - single container

**Note:** Only if requested. v1 focuses on direct VPS deployment.

---

## Milestone: v1.1 - Polish

### Issue 13: UI improvements
**Label:** enhancement, ui

Polish the user interface:

- [ ] Add loading spinners for async actions
- [ ] Improve mobile responsiveness
- [ ] Add confirmation dialogs for destructive actions
- [ ] Better form validation
- [ ] Toast notifications instead of flash messages

---

### Issue 14: Add export functionality
**Label:** enhancement

Allow exporting data for reporting:

- [ ] Export event responses to CSV
- [ ] Export message log to CSV
- [ ] Export audit log to CSV
- [ ] Add date range filters for exports

---

### Issue 15: Improve documentation
**Label:** documentation

Enhance documentation:

- [ ] Add architecture diagram
- [ ] Add database schema diagram
- [ ] Add workflow diagrams
- [ ] Create video walkthrough
- [ ] Add FAQ section

---

## Future Considerations (Not v1)

These are explicitly NOT for v1 but documented for future reference:

- **Recurring events** - Would add complexity
- **Multi-tenancy** - Out of scope for trusted community use
- **Email notifications** - SMS-only for v1
- **API** - No external integrations needed
- **Mobile app** - Web-first approach
- **Automatic waitlist** - Manual selection enforced
- **Group messaging** - Individual only by design

---

## Notes

- All issues should be created with appropriate labels
- Link issues to the v1.0 milestone
- Prioritize deployment testing and critical bug fixes first
- Enhancement requests should maintain v1 philosophy: simple, focused, no feature creep
