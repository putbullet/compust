from datetime import datetime

from sqlalchemy import Boolean, CHAR, DateTime, ForeignKey, Integer, String, Table, Column
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


class ScrapeTarget(Base):
    __tablename__ = "scrape_targets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    url: Mapped[str] = mapped_column(String(1000))
    type: Mapped[str | None] = mapped_column(String(50))
    active: Mapped[bool] = mapped_column(Boolean)
    last_scraped_at: Mapped[datetime | None] = mapped_column(DateTime)
    status: Mapped[str | None] = mapped_column(String(50))
    company: Mapped[Company] = relationship(back_populates="scrape_targets")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"))
    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id"))
    title: Mapped[str] = mapped_column(String(500))
    location: Mapped[str | None] = mapped_column(String(255))
    job_url: Mapped[str] = mapped_column(String(1000))
    description: Mapped[str | None]
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


class JobSkill(Base):
    __tablename__ = "job_skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    skill: Mapped[str] = mapped_column(String(150))
