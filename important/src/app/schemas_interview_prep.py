"""
Pydantic schemas for Compust Interview Prep Knowledge Center.
Supports multilingual behavioral preparation and repository-backed technical interview tracks.
"""

from typing import Any, List, Optional
from pydantic import BaseModel, Field, model_validator, ConfigDict


class STARStep(BaseModel):
    step: str  # Situation, Task, Action, Result
    definition: str
    key_points: List[str]
    example: str


class STARGuide(BaseModel):
    title: str
    what_is_star: str
    when_to_use: str
    how_to_structure: str
    what_makes_answer_strong: List[str]
    common_mistakes: List[str]
    steps: List[STARStep]


class BehavioralQuestionItem(BaseModel):
    id: str
    category: str
    question: str
    intent: str
    recommended_structure: List[str]
    strong_example_answer: str
    common_pitfalls: List[str]
    self_reflection_prompt: str


class BehavioralPrepResponse(BaseModel):
    language: str
    star_guide: STARGuide
    questions: List[BehavioralQuestionItem]
    story_matrix: Optional[dict] = None
    interview_modules: Optional[List[dict]] = None


class InterviewQuestionSummary(BaseModel):
    id: str
    slug: str
    title: str
    category: str
    topic: str
    difficulty: str  # Fundamental, Intermediate, Advanced
    experience_level: Optional[str] = "Mid-Level"  # Entry-Level / Intern, Mid-Level, Senior / Architect
    target_roles: List[str] = Field(default_factory=list)
    estimated_read_time_min: int
    has_code: bool
    has_diagram: bool


class InterviewTopic(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    questions: List[InterviewQuestionSummary]


class InterviewCategory(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    topics: List[InterviewTopic]


class InterviewDomainSummary(BaseModel):
    id: str  # data_engineering, security_engineering, ai_tech_interview
    title: str
    short_title: str
    tagline: str
    description: str
    hero_illustration: str
    total_categories: int
    total_questions: int
    source_repository: str
    source_license: str
    source_url: str


class InterviewDomainTree(BaseModel):
    domain: InterviewDomainSummary
    categories: List[InterviewCategory]


class SourceAttribution(BaseModel):
    repository_name: str
    repository_url: str
    source_path: str
    commit_hash: Optional[str] = None
    license_name: str
    license_notice: str
    imported_at: str


class InterviewQuestionDetail(BaseModel):
    id: str
    slug: str
    domain_id: str
    domain_title: str
    category: str
    topic: str
    title: str
    difficulty: str
    experience_level: Optional[str] = "Mid-Level"
    target_roles: List[str] = Field(default_factory=list)
    markdown_content: str
    raw_content: Optional[str] = None
    estimated_read_time_min: int
    has_code: bool = False
    has_diagram: bool = False
    tags: List[str] = Field(default_factory=list)
    source: SourceAttribution
    educational_diagram: Optional[str] = None
    educational_diagram_alt: Optional[str] = None
    previous_question: Optional[dict] = None  # { "id": str, "title": str, "slug": str }
    next_question: Optional[dict] = None      # { "id": str, "title": str, "slug": str }


class Actor(BaseModel):
    id: str
    role: str = "system"  # legitimate_user | attacker | system | database | client
    label: str
    description: str


class ScenarioStep(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    order: int
    from_actor: str = Field(alias="from")
    to_actor: str = Field(alias="to")
    action: str
    payload: Optional[str] = None
    annotation: Optional[str] = None
    status: str = "normal"  # normal | attack | blocked | secure


class ScenarioVariant(BaseModel):
    label: str
    outcome: str = "success"  # failure | success | partial
    steps: List[ScenarioStep] = Field(default_factory=list)


class Scenario(BaseModel):
    title: str
    variants: List[ScenarioVariant] = Field(default_factory=list)


class CodeExplanationLine(BaseModel):
    line: int
    note: str


class CodeSample(BaseModel):
    language: str = "python"
    code: str
    explanation_lines: List[CodeExplanationLine] = Field(default_factory=list)


class ComparisonRow(BaseModel):
    criterion: str
    option_a: str
    option_b: str


class StructuredAIExplanationPayload(BaseModel):
    concept_summary: str
    analogy: str
    actors: List[Actor] = Field(default_factory=list)
    scenario: Scenario
    code_sample: Optional[CodeSample] = None
    comparison_table: List[ComparisonRow] = Field(default_factory=list)
    takeaways: List[str] = Field(default_factory=list)
    common_mistakes: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_actors_and_lengths(self) -> "StructuredAIExplanationPayload":
        actor_ids = {a.id for a in self.actors}
        for variant in self.scenario.variants:
            for step in variant.steps:
                if step.from_actor not in actor_ids:
                    raise ValueError(f"Step from actor '{step.from_actor}' not in declared actors: {actor_ids}")
                if step.to_actor not in actor_ids:
                    raise ValueError(f"Step to actor '{step.to_actor}' not in declared actors: {actor_ids}")
        return self


class STAREvaluationRequest(BaseModel):
    draft_answer: str
    question_title: Optional[str] = None
    language: str = "en"


class STAREvaluationResponse(BaseModel):
    star_coverage: dict  # {"situation": bool, "task": bool, "action": bool, "result": bool}
    action_proportion_estimate: int
    quantified_metrics_score: int  # 0 to 10
    metrics_detected: List[str] = Field(default_factory=list)
    ownership_ratio: dict  # {"i_count": int, "we_count": int, "i_percentage": float}
    strengths: List[str] = Field(default_factory=list)
    missing_elements: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class QuestionAIExplainRequest(BaseModel):
    mode: str = "simplify"  # simplify, deep_dive, practice_question, mock_feedback
    user_draft_answer: Optional[str] = None
    language: str = "en"


class QuestionAIExplainResponse(BaseModel):
    question_id: str
    mode: str
    explanation: str
    real_world_scenario: Optional[str] = None
    code_sample: Optional[str] = None
    key_interview_takeaways: List[str] = Field(default_factory=list)
    structured_payload: Optional[StructuredAIExplanationPayload] = None
    ai_model_used: str
    is_ai_generated: bool = True
    disclaimer: str = "This explanation was generated by local AI to enhance your preparation and is distinct from the repository source material."


class RepositoryImportRequest(BaseModel):
    domain_id: str
    repository_url: str
    branch: Optional[str] = "main"
    translate_chinese: bool = True
    target_language: str = "en"


class RepositoryImportResponse(BaseModel):
    domain_id: str
    repository_url: str
    status: str
    files_processed: int
    questions_imported: int
    images_resolved: int
    translated_count: int
    content_hash: str
    license_detected: str
    message: str
