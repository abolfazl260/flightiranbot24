import pytest

from flightiran.modules.verification import VerificationService, VerificationStatus


def test_verification_state_and_permission_checks():
    service = VerificationService()
    pending = service.start(1, "telegram", True)
    assert pending.status == VerificationStatus.PENDING
    with pytest.raises(PermissionError):
        service.transition(1, VerificationStatus.APPROVED)
    approved = service.transition(1, VerificationStatus.APPROVED, actor_is_admin=True)
    assert service.can_access_verified_action(1)
    assert "approved" in approved.audit_events
    assert service.revoke(1).status == VerificationStatus.REVOKED
