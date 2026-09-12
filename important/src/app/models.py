from datetime import datetime

from sqlalchemy import Boolean, CHAR, Date, DateTime, ForeignKey, Integer, JSON, Numeric, String, Table, Column, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


company_countries = Table(
    "company_countries",
    Base.metadata,
    Column("company_id", ForeignKey("companies.id"), primary_key=True),
    Column("country_id", ForeignKey("countries.id"), primary_key=True),
)


class Country(Base):
    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    code: Mapped[str] = mapped_column(CHAR(2), unique=True)


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    website_url: Mapped[str] = mapped_column(String(500))
    careers_url: Mapped[str | None] = mapped_column(String(500))
    active: Mapped[bool] = mapped_column(Boolean)
    countries: Mapped[list[Country]] = relationship(
        secondary=company_countries,
        lazy="selectin",
    )
    scrape_targets: Mapped[list["ScrapeTarget"]] = relationship(
        back_populates="company",
        lazy="selectin",
    )
    scraping_runs: Mapped[list["ScrapingRun"]] = relationship(
        back_populates="company",
        lazy="selectin",
        cascade="all, delete-orphan",
    )


class ScrapeTarget(Base):
    __tablename__ = "scrape_targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    url: Mapped[str] = mapped_column(String(1000))
    type: Mapped[str | None] = mapped_column(String(50))
    active: Mapped[bool] = mapped_column(Boolean)
    last_scraped_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str | None] = mapped_column(String(50))
    cooldown_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    robots_txt_allowed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    robots_txt_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    company: Mapped[Company] = relationship(back_populates="scrape_targets")


class ScrapingRun(Base):
    __tablename__ = "scraping_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, running, success, failed, partial
    started_at: Mapped[datetime] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    jobs_found: Mapped[int] = mapped_column(Integer, default=0)
    jobs_added: Mapped[int] = mapped_column(Integer, default=0)
    jobs_updated: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    company: Mapped[Company] = relationship(back_populates="scraping_runs")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id"))
    title: Mapped[str] = mapped_column(String(500))
    location: Mapped[str | None] = mapped_column(String(255))
    job_url: Mapped[str] = mapped_column(String(1000))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(100))
    remote_type: Mapped[str | None] = mapped_column(String(100))
    department: Mapped[str | None] = mapped_column(String(255))
    source: Mapped[str | None] = mapped_column(String(255))
    external_job_id: Mapped[str | None] = mapped_column(String(255))
    posted_at: Mapped[datetime | None] = mapped_column(DateTime)
    discovered_at: Mapped[datetime] = mapped_column(DateTime)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime)
    active: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    salary_min: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    salary_max: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    salary_currency: Mapped[str | None] = mapped_column(CHAR(3), nullable=True)
    salary_period: Mapped[str | None] = mapped_column(String(20), nullable=True)
    scrape_target_id: Mapped[int | None] = mapped_column(ForeignKey("scrape_targets.id"), nullable=True)
    scrape_target: Mapped["ScrapeTarget | None"] = relationship(foreign_keys=[scrape_target_id])
    translations: Mapped[list["JobTranslation"]] = relationship(
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class JobTranslation(Base):
    __tablename__ = "job_translations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    language: Mapped[str] = mapped_column(String(10))
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_language: Mapped[str] = mapped_column(String(10), default="auto")
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)

    job: Mapped["Job"] = relationship(back_populates="translations")


class JobSkill(Base):
    __tablename__ = "job_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    skill: Mapped[str] = mapped_column(String(150))


user_country_preferences = Table(
    "user_country_preferences",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("country_id", ForeignKey("countries.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    date_of_birth: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    preferences: Mapped["UserPreference | None"] = relationship(
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    skills: Mapped[list["UserSkill"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    education: Mapped[list["UserEducation"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    experience: Mapped[list["UserExperience"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    languages: Mapped[list["UserLanguage"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    applications: Mapped[list["UserApplication"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    country_preferences: Mapped[list[Country]] = relationship(
        secondary=user_country_preferences,
        lazy="selectin",
    )
    resumes: Mapped[list["Resume"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="desc(Resume.created_at)",
    )


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    preferred_job_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    preferred_work_mode: Mapped[str | None] = mapped_column(String(100), nullable=True)
    preferred_location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    min_salary: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    max_salary: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    salary_currency: Mapped[str | None] = mapped_column(CHAR(3), nullable=True)
    user: Mapped[User] = relationship(back_populates="preferences")


class UserSkill(Base):
    __tablename__ = "user_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    skill: Mapped[str] = mapped_column(String(150))
    proficiency: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user: Mapped[User] = relationship(back_populates="skills")


class UserEducation(Base):
    __tablename__ = "user_education"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    institution: Mapped[str] = mapped_column(String(255))
    degree: Mapped[str | None] = mapped_column(String(255), nullable=True)
    field_of_study: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    user: Mapped[User] = relationship(back_populates="education")


class UserExperience(Base):
    __tablename__ = "user_experience"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(255))
    company_name: Mapped[str] = mapped_column(String(255))
    experience_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    user: Mapped[User] = relationship(back_populates="experience")


class UserLanguage(Base):
    __tablename__ = "user_languages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    language: Mapped[str] = mapped_column(String(100))
    proficiency: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user: Mapped[User] = relationship(back_populates="languages")


class UserApplication(Base):
    __tablename__ = "user_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    status: Mapped[str] = mapped_column(String(50), default="saved")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    applied_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)

    user: Mapped[User] = relationship(back_populates="applications")
    job: Mapped[Job] = relationship(lazy="selectin")


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(255), default="My Resume")
    filename: Mapped[str] = mapped_column(String(255), default="")
    raw_text: Mapped[str] = mapped_column(Text, default="")
    parsed_sections: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    structured_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    settings: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    target_job_id: Mapped[int | None] = mapped_column(ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True)
    source_resume_id: Mapped[int | None] = mapped_column(ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)

    user: Mapped[User] = relationship(back_populates="resumes")
    target_job: Mapped["Job | None"] = relationship(foreign_keys=[target_job_id], lazy="selectin")
    source_resume: Mapped["Resume | None"] = relationship(remote_side=[id], foreign_keys=[source_resume_id], lazy="selectin")


class CustomizedResume(Base):
    __tablename__ = "customized_resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    base_resume_id: Mapped[int] = mapped_column(ForeignKey("resumes.id"))
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    pdf_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    docx_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text)
    parsed_sections: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ats_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    recommendations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)

    user: Mapped[User] = relationship()
    base_resume: Mapped[Resume] = relationship()
    job: Mapped[Job] = relationship()

