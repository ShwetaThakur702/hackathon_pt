"""NotificationService — prototype implementation creates an in-app record
only (spec section 30). No real SMS/WhatsApp delivery is claimed."""

from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.services.audit_service import audit_service


class NotificationService:
    def notify_customer(self, db: Session, customer_id: str, case_id: str | None, message: str, channel: str = "IN_APP") -> Notification:
        recent_duplicate = (
            db.query(Notification)
            .filter(
                Notification.customer_id == customer_id,
                Notification.case_id == case_id,
                Notification.message == message,
            )
            .first()
        )
        if recent_duplicate:
            return recent_duplicate

        notification = Notification(customer_id=customer_id, case_id=case_id, channel=channel, message=message, status="SENT")
        db.add(notification)
        db.commit()
        db.refresh(notification)

        audit_service.write_event(
            db,
            event_type="NOTIFICATION_SENT",
            actor="SYSTEM",
            case_id=case_id,
            customer_id=customer_id,
            metadata={"channel": channel},
        )
        return notification

    def get_customer_notifications(self, db: Session, customer_id: str) -> list[Notification]:
        return (
            db.query(Notification)
            .filter(Notification.customer_id == customer_id)
            .order_by(Notification.created_at.desc())
            .all()
        )


notification_service = NotificationService()
