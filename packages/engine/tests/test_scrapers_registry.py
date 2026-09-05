"""
The scraper registry is a Phase 4.1 verification target: exactly the four
kept sources, none of the dropped ones, and every entry callable.
"""

import importlib

import pytest
from recruit_engine.scrapers import SCRAPERS


def test_registry_has_exactly_the_kept_sources():
    assert sorted(SCRAPERS) == ["hackernews", "jobspy", "wellfound", "yc"]


def test_every_registered_scraper_is_callable():
    assert all(callable(fn) for fn in SCRAPERS.values())


@pytest.mark.parametrize("name", ["naukri", "unstop", "internshala", "cutshort"])
def test_dropped_sources_are_gone(name):
    assert name not in SCRAPERS
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(f"recruit_engine.scrapers.{name}_scraper")


def test_serpapi_module_present_but_unregistered():
    # opt-in, user-supplied key — kept in-tree, wired in a later phase
    importlib.import_module("recruit_engine.scrapers.serpapi_scraper")
    assert "serpapi" not in SCRAPERS
