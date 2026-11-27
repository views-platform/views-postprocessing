"""#327 clause 2: the audience connection never falls back to the shared shelf.

The rule lives in ``views_postprocessing/contract/audience.py`` and takes primitives, so
these tests need no Appwrite environment, no pipeline-core and no manager — the same
reason ``delivery/coverage.py``'s rule is testable (C-40's consequence (a)).

**Why the equality case carries the weight.** ``appwrite_env.assert_env_declared`` already
refuses an absent coordinate, and that half was never the risk. The shape that actually
happened in this repository is both coordinates **present and equal**: until 2026-11-25
``crafd/managers/crafd.py`` read ``APPWRITE_DATASTORE_PROJECT_ID`` for the shelf AND for
the partner write. Nothing was missing. An absence check cannot see it.
"""

import pytest

from views_postprocessing.contract.audience import (
    AudienceIsolationError,
    assert_audience_is_not_the_shelf,
)

SHELF = "shelf-project-id"
AUDIENCE = "audience-project-id"


def test_two_distinct_projects_are_accepted_and_the_checked_value_is_returned():
    """The happy path, and it must RETURN the value rather than only validate it.

    The caller uses the returned id instead of a second ``os.getenv``. That is not style:
    a second read is a second chance to read the wrong coordinate name, which is the
    whole failure class this module exists for.
    """
    assert assert_audience_is_not_the_shelf(AUDIENCE, SHELF, consumer="un_crafd") == AUDIENCE


def test_an_audience_that_resolves_to_the_shelf_is_refused():
    """The case no absence check can see: both present, both the same."""
    with pytest.raises(AudienceIsolationError, match="SAME"):
        assert_audience_is_not_the_shelf(SHELF, SHELF, consumer="un_crafd")


def test_surrounding_whitespace_does_not_defeat_the_comparison():
    """``" id "`` and ``"id"`` are the same project. An env var picking up a stray space
    from a shell export must not read as isolation."""
    with pytest.raises(AudienceIsolationError, match="SAME"):
        assert_audience_is_not_the_shelf(f"  {SHELF}  ", SHELF, consumer="un_crafd")


@pytest.mark.parametrize("absent", [None, "", "   "])
def test_an_absent_or_blank_audience_project_is_refused(absent):
    """Blank is refused as well as missing: an exported-but-empty coordinate is not an
    assembled environment, and handing it on would make the client address *no* project
    rather than the right one. Same polarity as ``assert_env_declared``'s empty check."""
    with pytest.raises(AudienceIsolationError, match="no audience project declared"):
        assert_audience_is_not_the_shelf(absent, SHELF, consumer="un_crafd")


def test_an_audience_is_accepted_when_the_shelf_is_unset():
    """Refusing here would be wrong. The rule is *isolation from the shelf*, and an unset
    shelf cannot be collided with — the shelf's own absence is
    ``assert_env_declared``'s refusal to make, with its own message naming that
    coordinate. Two rules, two messages: a caller must be able to tell "the audience is
    wrong" from "the shelf is missing" (the C-113 distinction, one layer over)."""
    assert assert_audience_is_not_the_shelf(AUDIENCE, None, consumer="un_crafd") == AUDIENCE


def test_no_refusal_prints_a_project_id():
    """C-89: this repository is public and its CI logs are world-readable. Project ids are
    non-secret coordinates, but the registry forbids copying values and a failure message
    is a copy. The message must name the coordinate, never its value.

    This is the property #242 established for the no-copy scan, applied to a new message
    rather than assumed to be inherited.
    """
    for args in ((SHELF, SHELF), (f" {SHELF} ", SHELF)):
        with pytest.raises(AudienceIsolationError) as caught:
            assert_audience_is_not_the_shelf(*args, consumer="un_crafd")
        assert SHELF not in str(caught.value), "the refusal printed a project id"


def test_the_consumer_name_is_in_every_refusal():
    """Two partners share this rule and the managers are 435-line near-clones, so a
    refusal that does not say WHICH delivery failed sends the reader to the wrong file."""
    for args, _ in (((None, SHELF), 0), ((SHELF, SHELF), 0)):
        with pytest.raises(AudienceIsolationError) as caught:
            assert_audience_is_not_the_shelf(*args, consumer="un_crafd")
        assert "un_crafd" in str(caught.value)
