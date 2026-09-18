"""AuditService — every meaningful action writes an audit event here.

The case timeline UI is generated entirely from these rows; nothing in the
timeline is hardcoded frontend text (see spec section 26/64).
"""

import json

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.services.simulation_clock import simulation_clock_service

SENSITIVE_KEYS = {"otp", "pin", "upi_pin", "card_pin", "secret", "password"}


def _scrub(metadata: dict) -> dict:
    """Defense in depth: never persist a raw credential even if a caller
    accidentally includes one under a sensitive-looking key."""
    return {k: ("[REDACTED]" if k.lower() in SENSITIVE_KEYS else v) for k, v in metadata.items()}


class AuditService:
    def write_event(
        self,
        db: Session,
        event_type: str,
        actor: str,
        case_id: str | None = None,
        customer_id: str | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
        entry = AuditLog(
            case_id=case_id,
            customer_id=customer_id,
            event_type=event_type,
            actor=actor,
            metadata_json=json.dumps(_scrub(metadata or {})),
            timestamp=simulation_clock_service.now(db),
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    def get_case_timeline(self, db: Session, case_id: str) -> list[AuditLog]:
        return (
            db.query(AuditLog)
            .filter(AuditLog.case_id == case_id)
            .order_by(AuditLog.timestamp.asc(), AuditLog.id.asc())
            .all()
        )


audit_service = AuditService()
