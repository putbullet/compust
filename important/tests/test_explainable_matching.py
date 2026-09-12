import pytest
from datetime import date, datetime
from src.app.models import Job, User, UserEducation, UserExperience, UserLanguage, UserPreference, UserSkill, Resume, Country
from src.app.matching.matcher import calculate_job_match


def make_test_user(user_id: int = 1, email: str = "applicant@test.com") -> User:
    return User(
        id=user_id,
        email=email,
        password_hash="fakehash",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        email_verified=True,
        is_active=True,
    )


# Case A: Perfect Alignment
def test_case_a_perfect_alignment():
    user = make_test_user()
    user.skills = [
        UserSkill(skill="Python"),
        UserSkill(skill="FastAPI"),
        UserSkill(skill="Docker"),
        UserSkill(skill="PostgreSQL"),
    ]
    user.experience = [
        UserExperience(
            title="Senior Python Engineer",
            company_name="Tech Corp",
            experience_type="professional",
            start_date=date(2019, 1, 1),
            end_date=date(2023, 12, 31),
        )
    ]
    user.education = [
        UserEducation(
            institution="University of Engineering",
            degree="Master of Computer Science",
            field_of_study="Software Engineering",
        )
    ]
    user.country_preferences = [Country(id=3, code="DE", name="Germany")]
    user.preferences = UserPreference(
        preferred_work_mode="Hybrid",
        preferred_location="Berlin",
        min_salary=70000.0,
        salary_currency="EUR",
    )

    job = Job(
        id=1,
        company_id=10,
        country_id=3,
        title="Senior Python Engineer",
        location="Berlin, Germany",
        job_url="https://example.com/job/1",
        remote_type="Hybrid",
        salary_min=75000.0,
        description="We are seeking a Senior Python Engineer. Master's or Bachelor degree in Computer Science required.",
        active=True,
        discovered_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    job_skills = ["Python", "FastAPI", "Docker", "PostgreSQL"]

    result = calculate_job_match(job, job_skills, user)
    assert result.score >= 85
    assert result.category_scores["skills"] == 100
    assert result.category_scores["experience"] == 100
    assert result.category_scores["education"] == 100
    assert result.category_scores["location"] == 100
    assert any("Matched skills" in f for f in result.positive_factors)
    assert any("Meets seniority requirement" in f for f in result.positive_factors)
    assert any("Meets education requirement" in f for f in result.positive_factors)
    assert len(result.missing_factors) == 0


# Case B: Partial Skill Alignment
def test_case_b_partial_skill_alignment():
    user = make_test_user()
    user.skills = [
        UserSkill(skill="Python"),
        UserSkill(skill="FastAPI"),
    ]

    job = Job(
        id=2,
        company_id=10,
        country_id=1,
        title="Full Stack Engineer",
        location="Paris, France",
        job_url="https://example.com/job/2",
        active=True,
        discovered_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    job_skills = ["Python", "FastAPI", "React", "TypeScript"]

    result = calculate_job_match(job, job_skills, user)
    # 2 out of 4 skills matched -> 50% skills category score
    assert result.category_scores["skills"] == 50
    assert any("Matched skills: FastAPI, Python" in f for f in result.positive_factors)
    assert any("Missing job skills: React, TypeScript" in f for f in result.missing_factors)


# Case C: Completely Different Job Domain
def test_case_c_different_job_domain():
    user = make_test_user()
    user.skills = [UserSkill(skill="SEO"), UserSkill(skill="Content Writing")]
    user.experience = [
        UserExperience(
            title="Content Marketing Manager",
            company_name="Media Co",
            experience_type="professional",
            start_date=date(2021, 1, 1),
            end_date=date(2023, 1, 1),
        )
    ]

    job = Job(
        id=3,
        company_id=10,
        country_id=1,
        title="Senior Rust Kernel Developer",
        location="Paris, France",
        job_url="https://example.com/job/3",
        active=True,
        discovered_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    job_skills = ["Rust", "C", "Linux Kernel", "Assembly"]

    result = calculate_job_match(job, job_skills, user)
    assert result.score < 50
    assert result.category_scores["skills"] == 0
    assert any("Missing job skills" in f for f in result.missing_factors)


# Case D: Incompatible Core Requirements (Senior vs Intern)
def test_case_d_incompatible_seniority():
    user = make_test_user()
    user.skills = [UserSkill(skill="Java")]
    user.experience = [
        UserExperience(
            title="Software Intern",
            company_name="Startup",
            experience_type="internship",
            start_date=date(2023, 6, 1),
            end_date=date(2023, 12, 1),
        )
    ]

    job = Job(
        id=4,
        company_id=10,
        country_id=1,
        title="Lead Principal Architect",
        description="Senior leadership role requiring 10+ years of large-scale architecture experience.",
        job_url="https://example.com/job/4",
        active=True,
        discovered_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    result = calculate_job_match(job, ["Java", "Architecture"], user)
    assert result.category_scores["experience"] <= 40
    assert any("Senior roles require substantive professional career tenure" in f for f in result.missing_factors)


# Case E: French Company with German Job
def test_case_e_french_company_with_german_job():
    user = make_test_user()
    germany = Country(id=3, code="DE", name="Germany")
    user.country_preferences = [germany]
    user.preferences = UserPreference(preferred_location="Berlin")

    # Company is French (company_id=10), but the job is in Berlin (country_id=3)
    job = Job(
        id=5,
        company_id=10,
        country_id=3,
        title="DevOps Engineer",
        location="Berlin, Germany",
        job_url="https://example.com/job/5",
        active=True,
        discovered_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    result = calculate_job_match(job, [], user)
    # The candidate's target country is Germany, and the job is in Berlin, Germany -> 100% location score!
    assert result.category_scores["location"] == 100
    assert any("Matches location: Berlin" in f or "Matches target country: Germany" in f for f in result.positive_factors)


# Case F: Unmentioned Education and Requirements Not Penalized
def test_case_f_unmentioned_requirements_not_penalized():
    user = make_test_user()
    user.skills = [UserSkill(skill="Python")]
    user.education = []  # No degree listed in profile

    # Job description mentions NOTHING about degrees or languages
    job = Job(
        id=6,
        company_id=10,
        country_id=1,
        title="Python Developer",
        description="Build microservices and APIs with modern Python.",
        job_url="https://example.com/job/6",
        active=True,
        discovered_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    result = calculate_job_match(job, ["Python"], user)
    # Unmentioned education must receive 100% score (NOT penalized!)
    assert result.category_scores["education"] == 100
    # Unmentioned languages must receive 100% score (NOT penalized!)
    assert result.category_scores["languages"] == 100
    assert not any("degree" in f.lower() for f in result.missing_factors)


# Case G: Structured Resume Skills Integration
def test_case_g_structured_resume_skills_integration():
    user = make_test_user()
    user.skills = []  # Empty profile skills

    # Active resume has structured skills
    user.resumes = [
        Resume(
            id=10,
            user_id=user.id,
            is_active=True,
            structured_data={
                "skills": [{"name": "FastAPI"}, {"name": "PostgreSQL"}, {"name": "Docker"}]
            },
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    ]

    job = Job(
        id=7,
        company_id=10,
        country_id=1,
        title="Backend Engineer",
        job_url="https://example.com/job/7",
        active=True,
        discovered_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    job_skills = ["FastAPI", "PostgreSQL"]

    result = calculate_job_match(job, job_skills, user)
    # Matcher should successfully pull skills from the structured resume
    assert result.category_scores["skills"] == 100
    assert any("Matched skills: FastAPI, PostgreSQL" in f for f in result.positive_factors)


# Case H: Structured Resume Experience & Education Integration
def test_case_h_resume_experience_and_education_integration():
    user = make_test_user()
    user.experience = []
    user.education = []

    user.resumes = [
        Resume(
            id=11,
            user_id=user.id,
            is_active=True,
            structured_data={
                "experience": [
                    {
                        "title": "Lead Software Architect",
                        "company": "Enterprise Systems",
                        "type": "professional",
                        "start_date": "2018-01-01",
                        "end_date": "2023-01-01",
                    }
                ],
                "education": [
                    {
                        "degree": "Diplôme d'Ingénieur en Informatique",
                        "institution": "ENSEIRB-MATMECA",
                    }
                ],
            },
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
    ]

    job = Job(
        id=8,
        company_id=10,
        country_id=1,
        title="Lead Software Architect",
        description="Senior leadership role requiring engineering degree.",
        job_url="https://example.com/job/8",
        active=True,
        discovered_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    result = calculate_job_match(job, [], user)
    assert result.category_scores["experience"] == 100
    assert result.category_scores["education"] == 100
    assert any("Meets seniority requirement" in f for f in result.positive_factors)
    assert any("Diplôme d'Ingénieur" in f for f in result.positive_factors)


# Case I: Semantic Equivalence & Synonyms
def test_case_i_semantic_equivalences_and_synonyms():
    user = make_test_user()
    user.skills = [
        UserSkill(skill="React.js"),
        UserSkill(skill="PostgreSQL"),
        UserSkill(skill="TypeScript"),
    ]

    job = Job(
        id=9,
        company_id=10,
        country_id=1,
        title="Frontend Specialist",
        job_url="https://example.com/job/9",
        active=True,
        discovered_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    # Job specifies aliases: React, Postgres, TS
    job_skills = ["React", "Postgres", "TS"]

    result = calculate_job_match(job, job_skills, user)
    assert result.category_scores["skills"] == 100
    assert any("Matched skills" in f for f in result.positive_factors)


# Case J: Deterministic Output Stability
def test_case_j_deterministic_stability():
    user = make_test_user()
    user.skills = [UserSkill(skill="Python"), UserSkill(skill="FastAPI")]
    user.country_preferences = [Country(id=1, code="FR", name="France")]

    job = Job(
        id=10,
        company_id=10,
        country_id=1,
        title="Backend Developer",
        location="Paris, France",
        job_url="https://example.com/job/10",
        active=True,
        discovered_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    job_skills = ["Python", "FastAPI", "Docker"]

    initial = calculate_job_match(job, job_skills, user)
    for _ in range(10):
        subsequent = calculate_job_match(job, job_skills, user)
        assert subsequent.score == initial.score
        assert subsequent.category_scores == initial.category_scores
        assert subsequent.positive_factors == initial.positive_factors
        assert subsequent.missing_factors == initial.missing_factors
