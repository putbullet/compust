import json
from pathlib import Path
from pydantic import BaseModel, Field

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent.parent / "config" / "sources.json"


class SourceConfig(BaseModel):
    source_id: str
    name: str
    strategy_name: str
    domains: list[str] = Field(default_factory=list)
    target_types: list[str] = Field(default_factory=list)
    source_name: str = ""

    def matches(self, target_type: str | None, target_url: str | None) -> bool:
        if target_type:
            cleaned_type = target_type.strip().lower()
            if cleaned_type == self.strategy_name.lower():
                return True
            if any(cleaned_type == t.lower() for t in self.target_types):
                return True
        if target_url:
            url_lower = target_url.lower()
            if any(domain.lower() in url_lower for domain in self.domains):
                return True
        return False


def load_source_configs(custom_path: Path | None = None) -> list[SourceConfig]:
    path = custom_path or CONFIG_PATH
    if not path.exists():
        # Fallback to local default configs if file not found
        return [
            SourceConfig(
                source_id="orange_maroc",
                name="Orange Maroc",
                strategy_name="orange",
                domains=["orange.jobs"],
                target_types=["orange", "orange.jobs", "html_rel_next"],
                source_name="orange.jobs",
            ),
            SourceConfig(
                source_id="capgemini_maroc",
                name="Capgemini Maroc",
                strategy_name="capgemini",
                domains=["capgemini.com"],
                target_types=["capgemini", "capgemini_api", "json_api"],
                source_name="capgemini.com",
            ),
            SourceConfig(
                source_id="inwi_maroc",
                name="Inwi Maroc",
                strategy_name="inwi",
                domains=["jobs.inwi.ma", "inwi.ma"],
                target_types=["inwi", "turbo_stream"],
                source_name="jobs.inwi.ma",
            ),
        ]
    with open(path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    return [SourceConfig.model_validate(item) for item in raw_data]
