"""A dated tripwire for the platform key expiry (register C-84, issue #224).

**What this is not.** C-84 considered a key-validity preflight and rejected it: *"this
is a date to act on, not a mechanism to build, and inventing a mechanism would be
building the wrong thing to feel busy."* That verdict stands, and this is not that.
There is no authenticated call here, no credential, and no network — only a calendar.

**What this is.** C-84's trigger reads *"act when the un_fao delivery is next scheduled
within a month of it, or when anyone plans a rotation, whichever is first."* That is a
trigger nobody can notice: it fires in someone's memory or not at all, and this
repository has written down more than once that a trigger nobody can notice is a wish
(ADR-014 §4; the third arm of C-94's trigger was withdrawn for exactly this). The date
is known 90 days in advance and the consequence is a total, foreseeable outage of every
identity on the seam. So the trigger is made to fire on its own.

**Why the date is declared here rather than read from anywhere.** It cannot be derived:
the coordinate registry records secret *slots*, never values or their lifetimes, which
is #224's closing observation — no amount of drift detection will surface this one. The
values below come from an operator console read on 2026-08-05, recorded in views-appwrite
registry v1.4.4 and in C-84.

**When this fails, there are exactly two honest responses**, and both are stated in the
failure: rotate the keys and update the dates below, or — if a key was replaced early —
update the dates below to the new expiry. Deleting the test is the third option and it
is the one that produces the outage.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

#: The platform keys this repository's deliveries authenticate with, and when they die.
#: Read from the operator console 2026-08-05 (þing-02 A3(i)); recorded in views-appwrite
#: coordinate registry v1.4.4 and in register C-84. Both of this repo's paths — the FAO
#: delivery and the CRAF'd delivery — run under `VIEWS Pipeline Core`, the earlier one.
KEY_EXPIRY: dict[str, datetime] = {
    "VIEWS Pipeline Core": datetime(2026, 11, 17, 12, 35),
    "UN FAO": datetime(2026, 11, 17, 16, 10),
}

#: How long before the earliest expiry this starts failing. A month, because that is the
#: window C-84's own trigger names, and because rotation needs an overlap period that
#: has to be scheduled with an operator rather than squeezed in on the day.
LEAD_DAYS = 30


def test_the_platform_keys_are_not_about_to_expire():
    """Fails 30 days out, so the date cannot pass unnoticed (C-84, #224)."""
    earliest_name = min(KEY_EXPIRY, key=lambda k: KEY_EXPIRY[k])
    earliest = KEY_EXPIRY[earliest_name]
    days_left = (earliest.date() - date.today()).days
    if days_left > LEAD_DAYS:
        return

    spread = max(KEY_EXPIRY.values()) - min(KEY_EXPIRY.values())
    listing = "\n".join(
        f"    {name:22} {when:%Y-%m-%d %H:%M}" for name, when in sorted(KEY_EXPIRY.items(), key=lambda kv: kv[1])
    )
    pytest.fail(
        f"the platform Appwrite keys expire in {days_left} days:\n{listing}\n\n"
        f"Both of this repository's delivery paths — un_fao and crafd — authenticate "
        f"with {earliest_name!r}, the earlier one. The two keys are "
        f"{spread} apart, which is not a stagger: neither can carry traffic while the "
        "other is replaced, so a rotation that assumes a window has none. After the "
        "later time every identity on the seam is dead at once — model and ensemble "
        "writes, both partner deliveries, and FAO's own read access.\n\n"
        "This repository cannot rotate anything and must not hold credentials "
        "(þing-01 D3). Issuing and installing keys is an operator console action "
        "(views-appwrite#12); the key split is views-faoapi#338.\n\n"
        "Two honest ways to make this pass: rotate, then update KEY_EXPIRY above; or, "
        "if a key was replaced early, update KEY_EXPIRY to the new expiry. Deleting "
        "this test is the third way and it is the one that produces the outage "
        "(register C-84, issue #224)."
    )


def test_the_recorded_expiries_are_the_ones_C_84_names():
    """The dates are load-bearing, so a typo must fail here rather than silently.

    A tripwire keyed to a date nobody re-checked is worth very little; this pins the
    two values against the entry that sourced them, so editing one without the other
    is a failure rather than a drift.
    """
    assert KEY_EXPIRY["VIEWS Pipeline Core"] == datetime(2026, 11, 17, 12, 35)
    assert KEY_EXPIRY["UN FAO"] == datetime(2026, 11, 17, 16, 10)
    gap = KEY_EXPIRY["UN FAO"] - KEY_EXPIRY["VIEWS Pipeline Core"]
    assert gap.total_seconds() == 3 * 3600 + 35 * 60, (
        "C-84's finding is the 3h35m gap, not the dates themselves — if these move, "
        "re-read the entry rather than adjusting the constant to match"
    )
