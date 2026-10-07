import pytest

from flightiran.modules.admin import AdminService


def test_admin_access_audit_and_privacy_safe_pagination():
    service = AdminService({1})
    with pytest.raises(PermissionError):
        service.mutate(2, "delete")
    service.mutate(1, "delete", {"email": "hidden", "record": 3})
    page = service.report([{"id": 1, "email": "hidden"}, {"id": 2, "token": "secret"}], page_size=1)
    assert page.items == (("id", 1),) or page.items[0] == {"id": 1}
    assert service.audit_events[0]["keys"] == ["email", "record"]
