"""Store construction, called without a manager — register C-40's consequence (a).

C-40's first stated consequence is that *"the FAO logic cannot be instantiated or
unit-tested without the full framework + Appwrite env + viewser."* For the store
construction that was literally true until 2026-08-05: building the production-forecasts
datastore meant calling ``self._prod_forecasts_datastore()``, which meant having a
manager, which meant a views-models path manager and a live environment.

Nothing about that code needed any of it. It read one value out of ``self.configs`` and
assigned a local to ``self.ensemble_path_manager`` that nothing ever read back. Turning
the three store builders into module-level functions with declared arguments removed the
requirement entirely — and this file is the proof, because every test here runs with no
manager instance and with the Appwrite variables explicitly *removed* from the
environment.

**What this does not test.** That a real store connects, or that the credentials work.
That needs the production Appwrite project, which þing-02 D2 forbids testing against and
which is the only project that exists (A3(h), answered 2026-08-05). What is testable
offline is the part that was previously untestable at any price: the refusals, their
ordering, and the fact that the environment contract is checked *before* anything is
constructed.
"""

from __future__ import annotations

import pytest

from tests.conftest import PARTNER_PACKAGES

#: Every Appwrite name any partner's builders read. Cleared before each test so a
#: maintainer's populated shell cannot make these pass for the wrong reason — the
#: failure mode a laptop-only run has already produced twice in this repo (C-81).
_APPWRITE_PREFIX = "APPWRITE_"


@pytest.fixture
def no_appwrite_env(monkeypatch):
    """A deliberately empty Appwrite environment."""
    import os

    for name in [k for k in os.environ if k.startswith(_APPWRITE_PREFIX)]:
        monkeypatch.delenv(name, raising=False)


def _managers(partner: str):
    pytest.importorskip(
        "views_pipeline_core",
        reason="the builders construct pipeline-core objects; it is a declared "
        "dependency, so this skip means a broken environment rather than a valid one",
    )
    return __import__(
        f"views_postprocessing.{partner}.managers.{partner}",
        fromlist=["_build_prod_forecasts_store"],
    )


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_the_builders_are_functions_not_methods(partner):
    """The structural claim C-40's fix rests on. Assert it, do not assume it.

    If these ever migrate back onto the class, every test below would still pass while
    silently requiring a manager again — the guard has to check the shape, not just the
    behaviour.
    """
    import inspect

    module = _managers(partner)
    for name in ("_build_prod_forecasts_store", "_build_partner_store",
                 "_partner_appwrite_config"):
        fn = getattr(module, name, None)
        assert fn is not None, (
            f"[{partner}] {name} is gone from the module namespace. If it moved back "
            "onto the manager class, C-40's consequence (a) is back with it."
        )
        assert inspect.isfunction(fn), f"[{partner}] {name} is not a module-level function"
        params = list(inspect.signature(fn).parameters)
        assert "self" not in params, (
            f"[{partner}] {name} takes `self` — it is a method wearing a function's "
            "name, and still cannot be called without a manager."
        )


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_a_missing_ensemble_name_is_refused_before_anything_is_built(
    partner, no_appwrite_env
):
    """The launch-config error, raised with no manager and no environment.

    This is the whole point of the extraction in one assertion: the refusal is
    observable by calling a function with an argument.
    """
    module = _managers(partner)
    with pytest.raises(ValueError, match="ensemble"):
        module._build_prod_forecasts_store(None)


@pytest.mark.parametrize("bad", ["", None], ids=["empty-string", "none"])
@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_an_empty_ensemble_name_is_refused_too(partner, bad, no_appwrite_env):
    """`""` and `None` are both "not configured", and both used to reach `configs.get`.

    A launch config with `ensemble: ""` is a plausible typo and must not be treated as
    a name — `EnsemblePathManager("")` would resolve to something, and what it resolves
    to is not this delivery's ensemble.
    """
    module = _managers(partner)
    with pytest.raises(ValueError, match="ensemble"):
        module._build_prod_forecasts_store(bad)


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_the_environment_contract_is_checked_before_a_store_is_constructed(
    partner, no_appwrite_env
):
    """Ordering, not just presence — and the ordering is the fail-loud guarantee.

    ``assert_env_declared`` must run before ``AppwriteConfig``/``DatastoreModule`` are
    built, so a missing coordinate produces the declared error naming what is absent
    rather than whatever the client raises when handed ``None`` for an endpoint. þing-01
    #134 turned this repo's environment handling from an implicit borrow into a declared
    contract; an unchecked construction path would quietly undo that.

    The error must also name the store, because two different stores read two different
    variable sets and "some Appwrite variable is missing" sends an operator to the wrong
    half of the environment.
    """
    module = _managers(partner)
    with pytest.raises(Exception) as excinfo:
        module._build_prod_forecasts_store("some_ensemble")
    message = str(excinfo.value)
    assert "production_forecasts" in message, (
        f"[{partner}] the refusal does not name which store's environment is "
        f"incomplete: {message!r}"
    )


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_the_partner_store_names_its_own_environment_when_it_refuses(
    partner, no_appwrite_env
):
    """The outbound store reads a different variable set from the inbound one."""
    module = _managers(partner)
    with pytest.raises(Exception) as excinfo:
        module._partner_appwrite_config(model_path=None)
    assert "datastore" in str(excinfo.value).lower()


@pytest.mark.parametrize("partner", PARTNER_PACKAGES)
def test_no_coordinate_value_is_baked_into_the_builders(partner):
    """The repo is PUBLIC and the registry is referenced, never copied (þing-01 S6).

    The builders read every coordinate through ``os.getenv`` by declared NAME. A literal
    bucket id or endpoint appearing here would be a value copy in a public repository —
    the platform's original failure. The repo-wide guard covers this too; asserted at
    the seam as well because this is the file where such a literal would be most
    tempting to paste while debugging.
    """
    import inspect

    module = _managers(partner)
    source = "".join(
        inspect.getsource(getattr(module, name))
        for name in ("_build_prod_forecasts_store", "_partner_appwrite_config")
    )
    for line in source.splitlines():
        if "os.getenv(" in line:
            assert "os.getenv(\"APPWRITE_" in line or "os.getenv('APPWRITE_" in line, (
                f"[{partner}] a coordinate is read by something other than a declared "
                f"APPWRITE_ name: {line.strip()!r}"
            )
        assert "https://" not in line or "#" in line.split("https://")[0], (
            f"[{partner}] a literal endpoint appears in the builders: {line.strip()!r}"
        )
