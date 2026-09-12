from src.app.models import Company, ScrapeTarget
from src.app.scraper.registry import get_strategy_for_target
from src.app.scraper.source_config import load_source_configs


def test_declarative_source_config_loader() -> None:
    configs = load_source_configs()
    assert len(configs) >= 3
    strategy_names = {c.strategy_name for c in configs}
    assert {"orange", "capgemini", "inwi"}.issubset(strategy_names)


def test_registry_resolves_via_declarative_config() -> None:
    # Target with type matching
    target_orange = ScrapeTarget(id=1, company_id=99, url="https://careers.corp.test", type="orange")
    strat_orange = get_strategy_for_target(target_orange)
    assert strat_orange is not None
    assert strat_orange.name == "orange"

    # Target with domain matching without company name
    target_cap = ScrapeTarget(id=2, company_id=99, url="https://www.capgemini.com/jobs", type=None)
    strat_cap = get_strategy_for_target(target_cap)
    assert strat_cap is not None
    assert strat_cap.name == "capgemini"

    # Target with inwi domain
    target_inwi = ScrapeTarget(id=3, company_id=99, url="https://jobs.inwi.ma/portal", type=None)
    strat_inwi = get_strategy_for_target(target_inwi)
    assert strat_inwi is not None
    assert strat_inwi.name == "inwi"
