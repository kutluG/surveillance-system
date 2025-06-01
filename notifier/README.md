```markdown
# Notifier Service

Multi-channel notification service that delivers alerts via email, Slack, SMS, and webhooks.

## Supported Channels

- **Email**: SMTP-based email delivery
- **Slack**: Webhook-based Slack notifications with rich formatting
- **SMS**: Twilio-based SMS notifications
- **Webhook**: Generic HTTP webhook notifications

## Configuration

Copy and edit `.env`:

```bash
# Database
DATABASE_URL=postgresql://user:password@postgres:5432/events_db

# Email (SMTP)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=security@company.com

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX

# SMS (Twilio)
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_FROM_NUMBER=+1234567890

# Webhook
WEBHOOK_URL=https://your-webhook-endpoint.com/notifications
WEBHOOK_SECRET=your-webhook-secret
```

## Build & Run

```bash
docker-compose up --build notifier
```

## Endpoints

- POST `/send` - Send notification through specified channel
- GET `/notifications/{id}` - Get notification status
- GET `/notifications` - List notification history
- POST `/test/{channel}` - Send test notification
- GET `/health` - Health check

## Example Usage

Send an email notification:
```bash
curl -X POST http://localhost:8000/send \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "email",
    "recipients": ["security@company.com"],
    "subject": "Security Alert",
    "message": "Person detected in restricted area",
    "metadata": {
      "camera_id": "cam01",
      "clip_links": ["https://cdn.example.com/clips/event123.mp4"]
    }
  }'
```

Send a Slack notification:
```bash
curl -X POST http://localhost:8000/send \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "slack",
    "recipients": ["#security-alerts"],
    "subject": "Security Alert",
    "message": "Unauthorized access detected at main entrance"
  }'
```

Test a channel:
```bash
curl -X POST http://localhost:8000/test/email \
  -H "Content-Type: application/json" \
  -d '["test@company.com"]'
```
```