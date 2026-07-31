"""The launch declarations this delivery requires, DECLARED (S1, #149; register C-63).

Sibling of ``appwrite_env`` — that module asserts the launcher assembled the
*environment*; this one asserts it declared the *delivery mode*. Same rule
(ADR-003: authority of declarations over inference), same shape, same failure
style: name what is missing and refuse.

**Why this exists.** Until S1 this package inferred its delivery mode from the
*absence* of config keys. ``configs.get("wire_contract")`` returning ``None``
because the launcher never mentioned it was indistinguishable from a deliberate
``False``, and either quietly selected a retired pandas path that had been kept
"until run 0 proves the contract path live" and never removed. Two independent
axes — ``wire_contract`` and the queryset's ``data_format`` — gave four delivery
modes of which production used one; the other three were reachable only by
omission. That is precisely the inference ADR-003 forbids, in the repository that
authored it.

There is now **one** delivery path. A launcher that has not declared it does not
get a quiet fallback; it gets an error naming the key it left out.

Deliberately dependency-light: no pipeline-core, no pandas, no frames — the
queryset's ``data_format`` arrives as a plain string from the caller, so this
module stays importable (and testable) anywhere.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# The launch-config key that selects the ADR-013 contract delivery. Declared, never
# inferred: `True` is the only accepted value, because the alternative it used to
# select no longer exists.
WIRE_CONTRACT_KEY = "wire_contract"

# The queryset descriptor value that selects the frame-native historical read
# (#126). Read via pipeline-core's `declared_data_format()` — the one gate — and
# passed here as a string so this module needs no pipeline-core import.
FEATURE_FRAME_FORMAT = "feature_frame"


class LaunchConfigError(ValueError):
    """The launcher did not declare the delivery this package implements."""


def assert_contract_mode(configs: dict) -> None:
    """Raise unless the launch config declares ADR-013 contract delivery.

    Args:
        configs: the launcher's config mapping.

    Raises:
        LaunchConfigError: naming the missing or falsy key.
    """
    if not configs.get(WIRE_CONTRACT_KEY):
        err_msg = (
            f"the launcher did not declare {WIRE_CONTRACT_KEY!r} — this package "
            f"delivers only the ADR-013 contract wire. Set "
            f"{WIRE_CONTRACT_KEY}: True in the postprocessor's config_meta. "
            "The pandas delivery this key used to select was retired in #149; "
            "there is no fallback to omit your way into."
        )
        logger.error(err_msg)  # ADR-008: logged persistently AND raised
        raise LaunchConfigError(err_msg)


def assert_frame_native_historical(data_format: str | None) -> None:
    """Raise unless the queryset descriptor declares the frame-native historical read.

    Args:
        data_format: the value of ``declared_data_format(queryset)``.

    Raises:
        LaunchConfigError: naming the expected descriptor value.
    """
    if data_format != FEATURE_FRAME_FORMAT:
        err_msg = (
            f"the queryset declares data_format={data_format!r}; this package "
            f"reads historical actuals only as {FEATURE_FRAME_FORMAT!r} (#126). "
            f"Set data_format: {FEATURE_FRAME_FORMAT!r} in the postprocessor's "
            "config_queryset. The pandas historical read was retired in #149."
        )
        logger.error(err_msg)  # ADR-008: logged persistently AND raised
        raise LaunchConfigError(err_msg)
