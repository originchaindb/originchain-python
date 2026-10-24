import pytest

from tests.e2e_contract import check_ask, expected_ask_status
from originchain import OCAuthError, OCPaymentRequiredError


@pytest.mark.parametrize("value", ["", "0", "201", "401", "503", "skip"])
def test_invalid_ask_profile_is_rejected(value):
    with pytest.raises(ValueError, match="200 or 402"):
        expected_ask_status(value)


def raising(error):
    def fail():
        raise error
    return fail


def test_ask_success_profile_requires_success():
    assert check_ask(lambda: {"rows": []}, expected_ask_status("200")) == {"rows": []}
    with pytest.raises(OCPaymentRequiredError):
        check_ask(raising(OCPaymentRequiredError("unavailable", status=402,
                  body={"error": "ask_unavailable"})), 200)


def test_unavailable_ask_profile_requires_exact_response():
    assert "not validated" in check_ask(raising(OCPaymentRequiredError(
        "unavailable", status=402, body={"error": "ask_unavailable"},
    )), expected_ask_status("402"))
    with pytest.raises(AssertionError):
        check_ask(lambda: {"rows": []}, 402)
    with pytest.raises(AssertionError):
        check_ask(raising(OCPaymentRequiredError("addon", status=402,
                  body={"error": "addon_required"})), 402)
    with pytest.raises(OCAuthError):
        check_ask(raising(OCAuthError("denied", status=401)), 402)
