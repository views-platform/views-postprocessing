"""The declared FAO product (unfao/product.py) — ADR-013 §4.2a/§6/§4.1a/§11.4 pins."""

from views_postprocessing.unfao import product


def test_targets_are_the_pinned_wire_vocabulary():
    # §7a: wire names, never internal model names; order stable for manifests.
    assert product.TARGETS == ("lr_ged_sb", "lr_ged_ns", "lr_ged_os")


def test_s_min_is_the_walking_skeleton_floor():
    assert product.S_MIN == 2


def test_consumer_document_name_is_the_faoapi_pin():
    # §4.1a: any other name is invisible to faoapi's unconditional name filter.
    assert product.CONSUMER_DOCUMENT_NAME == "un_fao"


def test_upload_interlock_defaults_off():
    # §11.4: the default configuration must be unable to touch the live bucket.
    assert product.UPLOAD_ENABLED is False
