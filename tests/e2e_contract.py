"""Explicit Ask availability profile for live smoke checks."""

from originchain import OCPaymentRequiredError


def expected_ask_status(value):
    if value not in ("200", "402"):
        raise ValueError("OC_E2E_ASK_STATUS must be 200 or 402")
    return int(value)


def check_ask(call, expected_status):
    try:
        result = call()
    except OCPaymentRequiredError as error:
        if expected_status != 402:
            raise
        assert error.status == 402
        assert isinstance(error.body, dict) and error.body.get("error") == "ask_unavailable", (
            "expected exact ask_unavailable capability response"
        )
        return "HTTP 402 ask_unavailable verified; Ask execution is not validated"
    assert expected_status == 200, "Ask availability changed: expected HTTP 402, received success"
    return result
