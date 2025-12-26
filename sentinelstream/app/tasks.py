"""Celery tasks for asynchronous operations"""
import httpx
from celery import Celery
from app.config import settings

# Initialize Celery
celery_app = Celery(
    "sentinelstream",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30,
    task_soft_time_limit=25,
)


@celery_app.task(bind=True, max_retries=3)
def send_webhook(self, webhook_url: str, payload: dict, transaction_id: str):
    """
    Send webhook notification asynchronously.
    Retries on failure.
    """
    try:
        with httpx.Client(timeout=settings.WEBHOOK_TIMEOUT) as client:
            response = client.post(webhook_url, json=payload)
            response.raise_for_status()
            
            return {
                "status": "success",
                "status_code": response.status_code,
                "transaction_id": transaction_id
            }
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)


@celery_app.task
def send_fraud_alert_email(user_id: str, transaction_id: str, risk_score: float):
    """
    Send email alert for high-risk transactions.
    In production, integrate with email service (SendGrid, SES, etc.)
    """
    # Placeholder for email sending
    # In production: use SendGrid, AWS SES, or similar
    print(f"[EMAIL ALERT] High-risk transaction detected:")
    print(f"  User ID: {user_id}")
    print(f"  Transaction ID: {transaction_id}")
    print(f"  Risk Score: {risk_score:.2f}")
    
    return {
        "status": "sent",
        "user_id": user_id,
        "transaction_id": transaction_id
    }


@celery_app.task
def update_user_profile(user_id: str, transaction_data: dict):
    """
    Update user profile statistics asynchronously.
    This can be used to update averages, counts, etc. without blocking the transaction.
    """
    # Placeholder for profile update
    # In production: update database with aggregated statistics
    print(f"[PROFILE UPDATE] Updating profile for user {user_id}")
    
    return {
        "status": "updated",
        "user_id": user_id
    }

