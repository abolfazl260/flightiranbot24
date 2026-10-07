"""Consent-aware verification state machine with role checks."""

from dataclasses import dataclass, replace
from enum import StrEnum


class VerificationStatus(StrEnum):
    NOT_STARTED = "not_started"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVOKED = "revoked"


@dataclass(frozen=True)
class Verification:
    user_id: int
    status: VerificationStatus = VerificationStatus.NOT_STARTED
    consent: bool = False
    method: str | None = None
    audit_events: tuple[str, ...] = ()


class VerificationService:
    def __init__(self) -> None:
        self._records: dict[int, Verification] = {}

    def start(self, user_id: int, method: str, consent: bool) -> Verification:
        if not consent:
            raise ValueError("verification consent is required")
        record = Verification(user_id, VerificationStatus.PENDING, True, method, ("started",))
        self._records[user_id] = record
        return record

    def transition(
        self, user_id: int, status: VerificationStatus, *, actor_is_admin: bool = False
    ) -> Verification:
        record = self._records.get(user_id)
        if record is None:
            raise KeyError(user_id)
        if (
            status in {VerificationStatus.APPROVED, VerificationStatus.REJECTED}
            and not actor_is_admin
        ):
            raise PermissionError("admin verification required")
        updated = replace(record, status=status, audit_events=record.audit_events + (status.value,))
        self._records[user_id] = updated
        return updated

    def revoke(self, user_id: int) -> Verification:
        return self.transition(user_id, VerificationStatus.REVOKED, actor_is_admin=True)

    def can_access_verified_action(self, user_id: int) -> bool:
        return self._records.get(user_id, Verification(0)).status == VerificationStatus.APPROVED
