import hashlib
import hmac
import time
from urllib.parse import urlencode

import pytest

from flightiran.modules.webapp import WebAppAuthenticator, WebAppService


def init_data(token: str) -> str:
    values = {"auth_date": str(int(time.time())), "query_id": "q1", "user": "{}"}
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    check = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    values["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(values)


def test_webapp_rejects_bad_data_and_accepts_signed_data():
    auth = WebAppAuthenticator("token")
    assert auth.validate(init_data("token"))["query_id"] == "q1"
    with pytest.raises(ValueError):
        auth.validate(init_data("wrong"))


def test_webapp_feature_flag_and_fallback():
    service = WebAppService(WebAppAuthenticator("token"), enabled=False)
    with pytest.raises(RuntimeError):
        service.session(init_data("token"))
    assert "Telegram" in service.fallback()
