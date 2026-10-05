"""
Compust Safe Guided Data Import & Backup/Restore Service.

Provides:
1. Automated discovery of candidate data sources:
   - Local MySQL server (127.0.0.1:3306/compust)
   - Dev SQLite database (compust_local.db)
2. Read-only inspection and import preview.
3. Transactional import with pre-import backup, conflict resolution,
   and file copying for resumes and documents.
4. Full portable backup export (.zip with database, storage files, and manifest)
   and atomic backup restore.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sqlite3
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from ..database import engine, SessionLocal, init_database_schema
from ..logging import get_logger
from ..paths import (
    get_backups_dir,
    get_database_dir,
    get_database_path,
    get_storage_dir,
    backup_sqlite_database,
)
from ..schemas_data import (
    BackupExportResponse,
    BackupRestoreResponse,
    ImportExecuteRequest,
    ImportExecuteResponse,
    ImportPreviewRequest,
    ImportPreviewResponse,
    ImportSourceInfo,
    ImportSourcesResponse,
    UserDataSummary,
)

logger = get_logger("services.data_manager")


class DataManagerService:
    """Manages data discovery, guided import, and backup/restore."""

    def __init__(self) -> None:
        get_backups_dir().mkdir(parents=True, exist_ok=True)
        get_database_dir().mkdir(parents=True, exist_ok=True)
        get_storage_dir().mkdir(parents=True, exist_ok=True)

    def get_target_stats(self) -> dict[str, int]:
        """Return row counts for key tables in active target database."""
        stats: dict[str, int] = {}
        tables = ["jobs", "companies", "users", "user_applications", "contacts", "resumes"]
        with engine.connect() as conn:
            for t in tables:
                try:
                    res = conn.execute(text(f"SELECT count(*) FROM {t}"))
                    stats[t] = res.scalar() or 0
                except Exception:
                    stats[t] = 0
        return stats

    def discover_sources(self) -> ImportSourcesResponse:
        """Scan system for available data sources (MySQL 3306 & dev SQLite files)."""
        sources: list[ImportSourceInfo] = []

        # 1. Check Local MySQL on 127.0.0.1:3306
        mysql_info = self._probe_mysql_source()
        if mysql_info:
            sources.append(mysql_info)

        # 2. Check Dev SQLite files in workspace
        sqlite_sources = self._probe_sqlite_sources()
        sources.extend(sqlite_sources)

        target_path = str(get_database_path())
        target_stats = self.get_target_stats()
        target_has_data = any(v > 0 for v in target_stats.values())

        return ImportSourcesResponse(
            sources=sources,
            target_database_path=target_path,
            target_database_type="sqlite",
            target_has_data=target_has_data,
            target_stats=target_stats,
        )

    def _probe_mysql_source(self) -> ImportSourceInfo | None:
        """Probe local MySQL database on 127.0.0.1:3306."""
        try:
            import pymysql
            conn = pymysql.connect(
                host="127.0.0.1",
                port=3306,
                user="root",
                password="",
                database="compust",
                connect_timeout=1.5,
                read_timeout=2.0,
                cursorclass=pymysql.cursors.DictCursor,
            )
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT count(*) as cnt FROM jobs")
                    total_jobs = cur.fetchone()["cnt"]

                    cur.execute("SELECT count(*) as cnt FROM companies")
                    total_companies = cur.fetchone()["cnt"]

                    cur.execute("SELECT id, email, first_name, last_name FROM users ORDER BY id ASC")
                    users_raw = cur.fetchall()

                    users_list: list[UserDataSummary] = []
                    for u in users_raw:
                        uid = u["id"]
                        cur.execute("SELECT count(*) as cnt FROM user_applications WHERE user_id = %s", (uid,))
                        app_cnt = cur.fetchone()["cnt"]

                        cur.execute("SELECT count(*) as cnt FROM contacts WHERE user_id = %s", (uid,))
                        con_cnt = cur.fetchone()["cnt"]

                        cur.execute("SELECT count(*) as cnt FROM resumes WHERE user_id = %s", (uid,))
                        res_cnt = cur.fetchone()["cnt"]

                        users_list.append(
                            UserDataSummary(
                                id=uid,
                                email=u["email"],
                                first_name=u["first_name"],
                                last_name=u["last_name"],
                                applications_count=app_cnt,
                                contacts_count=con_cnt,
                                resumes_count=res_cnt,
                            )
                        )

                    return ImportSourceInfo(
                        id="mysql-local-3306",
                        name="Local MySQL Server (compust)",
                        type="mysql",
                        location="127.0.0.1:3306/compust",
                        reachable=True,
                        status_message=f"Connected ({len(users_list)} users, {total_jobs} jobs, {total_companies} companies)",
                        total_jobs=total_jobs,
                        total_companies=total_companies,
                        users=users_list,
                    )
            finally:
                conn.close()
        except Exception as e:
            logger.debug(f"MySQL source probe failed or not running: {e}")
            return None

    def _probe_sqlite_sources(self) -> list[ImportSourceInfo]:
        """Search for candidate dev SQLite database files."""
        candidates = [
            Path("A:/code/compust/important/data/compust_local.db"),
            Path("A:/code/compust/important/data/compust.db"),
            Path(__file__).resolve().parents[4] / "important" / "data" / "compust_local.db",
        ]
        # Also check backups dir
        for p in get_backups_dir().glob("*.db"):
            candidates.append(p)

        found_sources: list[ImportSourceInfo] = []
        seen_paths: set[str] = set()

        for path in candidates:
            if not path.is_file():
                continue
            norm_str = str(path.resolve())
            if norm_str in seen_paths or norm_str == str(get_database_path().resolve()):
                continue
            seen_paths.add(norm_str)

            try:
                con = sqlite3.connect(f"file:{norm_str}?mode=ro", uri=True)
                cur = con.cursor()
                tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]

                total_jobs = 0
                total_companies = 0
                users_list: list[UserDataSummary] = []

                if "jobs" in tables:
                    total_jobs = cur.execute("SELECT count(*) FROM jobs").fetchone()[0]
                if "companies" in tables:
                    total_companies = cur.execute("SELECT count(*) FROM companies").fetchone()[0]

                if "users" in tables:
                    cur.execute("SELECT id, email, first_name, last_name FROM users")
                    for u in cur.fetchall():
                        uid = u[0]
                        app_cnt = cur.execute("SELECT count(*) FROM user_applications WHERE user_id = ?", (uid,)).fetchone()[0] if "user_applications" in tables else 0
                        con_cnt = cur.execute("SELECT count(*) FROM contacts WHERE user_id = ?", (uid,)).fetchone()[0] if "contacts" in tables else 0
                        res_cnt = cur.execute("SELECT count(*) FROM resumes WHERE user_id = ?", (uid,)).fetchone()[0] if "resumes" in tables else 0
                        users_list.append(
                            UserDataSummary(
                                id=uid,
                                email=u[1],
                                first_name=u[2],
                                last_name=u[3],
                                applications_count=app_cnt,
                                contacts_count=con_cnt,
                                resumes_count=res_cnt,
                            )
                        )

                con.close()

                # Only include if has jobs, companies or users
                if total_jobs > 0 or len(users_list) > 0:
                    found_sources.append(
                        ImportSourceInfo(
                            id=f"sqlite-{path.stem}",
                            name=f"SQLite Database: {path.name}",
                            type="sqlite",
                            location=str(path),
                            reachable=True,
                            status_message=f"Found {len(users_list)} users, {total_jobs} jobs, {total_companies} companies",
                            total_jobs=total_jobs,
                            total_companies=total_companies,
                            users=users_list,
                        )
                    )
            except Exception as e:
                logger.debug(f"Failed to probe SQLite candidate {path}: {e}")

        return found_sources

    def preview_import(self, req: ImportPreviewRequest) -> ImportPreviewResponse:
        """Inspect source and return preview statistics without modifying data."""
        sources_resp = self.discover_sources()
        target_source = next((s for s in sources_resp.sources if s.id == req.source_id), None)
        if not target_source:
            raise ValueError(f"Source with id '{req.source_id}' was not found or is currently unreachable.")

        selected_user: UserDataSummary | None = None
        if req.user_id:
            selected_user = next((u for u in target_source.users if u.id == req.user_id), None)
        elif req.email:
            selected_user = next((u for u in target_source.users if u.email.lower() == req.email.lower()), None)
        elif target_source.users:
            # Default to the user with the most applications (typically the owner)
            selected_user = max(target_source.users, key=lambda u: u.applications_count)

        target_stats = self.get_target_stats()

        return ImportPreviewResponse(
            source_id=req.source_id,
            selected_user=selected_user,
            jobs_count=target_source.total_jobs,
            companies_count=target_source.total_companies,
            applications_count=selected_user.applications_count if selected_user else 0,
            contacts_count=selected_user.contacts_count if selected_user else 0,
            resumes_count=selected_user.resumes_count if selected_user else 0,
            target_existing_jobs=target_stats.get("jobs", 0),
            target_existing_applications=target_stats.get("user_applications", 0),
            warning="Target already contains data; existing records with matching keys will be merged." if target_stats.get("jobs", 0) > 0 else None,
        )

    def execute_import(self, req: ImportExecuteRequest) -> ImportExecuteResponse:
        """Execute guided import from selected source into target database."""
        sources_resp = self.discover_sources()
        target_source = next((s for s in sources_resp.sources if s.id == req.source_id), None)
        if not target_source:
            raise ValueError(f"Source with id '{req.source_id}' not found.")

        # Ensure schema is initialized
        init_database_schema()

        # Step 1: Create Safety Backup of Target Database
        target_db_path = get_database_path()
        backup_created: Path | None = None
        if target_db_path.is_file():
            backup_created = backup_sqlite_database(target_db_path)
            logger.info(f"Created pre-import backup at {backup_created}")

        # Determine user to import
        selected_user: UserDataSummary | None = None
        if req.user_id:
            selected_user = next((u for u in target_source.users if u.id == req.user_id), None)
        elif req.email:
            selected_user = next((u for u in target_source.users if u.email.lower() == req.email.lower()), None)
        elif target_source.users:
            selected_user = max(target_source.users, key=lambda u: u.applications_count)

        if not selected_user:
            raise ValueError("No user selected or found in the source database to import.")

        source_user_id = selected_user.id
        source_email = selected_user.email

        # Step 2: Open Source Connection (READ-ONLY)
        if target_source.type == "mysql":
            import pymysql
            src_conn = pymysql.connect(
                host="127.0.0.1",
                port=3306,
                user="root",
                password="",
                database="compust",
                cursorclass=pymysql.cursors.DictCursor,
            )
        else:
            # SQLite source
            src_conn = sqlite3.connect(f"file:{target_source.location}?mode=ro", uri=True)
            src_conn.row_factory = sqlite3.Row

        counts = {
            "users": 0,
            "companies": 0,
            "jobs": 0,
            "applications": 0,
            "contacts": 0,
            "resumes": 0,
            "files": 0,
        }

        try:
            # We will use SQLAlchemy Session on target DB
            db: Session = SessionLocal()
            try:
                # ── 1. User Import / Mapping ──────────────────────────────────────────
                user_check = db.execute(
                    text("SELECT id, email FROM users WHERE email = :email"),
                    {"email": source_email},
                ).mappings().first()

                target_user_id: int
                if user_check:
                    target_user_id = user_check["id"]
                    logger.info(f"Target user already exists: id={target_user_id} ({source_email})")
                else:
                    # Fetch user record from source
                    src_user: dict[str, Any]
                    if target_source.type == "mysql":
                        with src_conn.cursor() as cur:
                            cur.execute("SELECT * FROM users WHERE id = %s", (source_user_id,))
                            src_user = cur.fetchone()
                    else:
                        cur = src_conn.cursor()
                        cur.execute("SELECT * FROM users WHERE id = ?", (source_user_id,))
                        row = cur.fetchone()
                        src_user = dict(row) if row else {}

                    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                    res = db.execute(
                        text(
                            """
                            INSERT INTO users (email, password_hash, first_name, last_name, phone,
                                               date_of_birth, created_at, updated_at, email_verified, is_active)
                            VALUES (:email, :password_hash, :first_name, :last_name, :phone,
                                    :date_of_birth, :created_at, :updated_at, :email_verified, :is_active)
                            """
                        ),
                        {
                            "email": src_user.get("email"),
                            "password_hash": src_user.get("password_hash") or "imported_user_hash",
                            "first_name": src_user.get("first_name"),
                            "last_name": src_user.get("last_name"),
                            "phone": src_user.get("phone"),
                            "date_of_birth": str(src_user.get("date_of_birth")) if src_user.get("date_of_birth") else None,
                            "created_at": str(src_user.get("created_at") or now_str),
                            "updated_at": str(src_user.get("updated_at") or now_str),
                            "email_verified": bool(src_user.get("email_verified", 0)),
                            "is_active": bool(src_user.get("is_active", 1)),
                        },
                    )
                    db.flush()
                    user_created = db.execute(
                        text("SELECT id FROM users WHERE email = :email"),
                        {"email": source_email},
                    ).scalar()
                    target_user_id = int(user_created)
                    counts["users"] += 1
                    logger.info(f"Created target user: id={target_user_id} ({source_email})")

                # ── 2. Countries & Companies Import ───────────────────────────────────
                country_id_map: dict[int, int] = {}
                company_id_map: dict[int, int] = {}

                # Countries
                src_countries = self._query_source(src_conn, target_source.type, "SELECT * FROM countries")
                for c in src_countries:
                    code = (c.get("code") or "US")[:2].upper()
                    existing_c = db.execute(
                        text("SELECT id FROM countries WHERE code = :code"),
                        {"code": code},
                    ).scalar()
                    if existing_c:
                        country_id_map[c["id"]] = existing_c
                    else:
                        db.execute(
                            text("INSERT INTO countries (name, code) VALUES (:name, :code)"),
                            {"name": c.get("name") or code, "code": code},
                        )
                        db.flush()
                        new_c_id = db.execute(text("SELECT id FROM countries WHERE code = :code"), {"code": code}).scalar()
                        country_id_map[c["id"]] = new_c_id

                # Default fallback country
                default_country_id = next(iter(country_id_map.values()), 1)
                existing_default = db.execute(text("SELECT id FROM countries LIMIT 1")).scalar()
                if existing_default:
                    default_country_id = existing_default

                # Companies
                src_companies = self._query_source(src_conn, target_source.type, "SELECT * FROM companies")
                for comp in src_companies:
                    cname = comp.get("name") or "Unknown"
                    existing_comp = db.execute(
                        text("SELECT id FROM companies WHERE name = :name"),
                        {"name": cname},
                    ).scalar()
                    if existing_comp:
                        company_id_map[comp["id"]] = existing_comp
                    else:
                        db.execute(
                            text(
                                """
                                INSERT INTO companies (name, website_url, careers_url, active)
                                VALUES (:name, :website_url, :careers_url, :active)
                                """
                            ),
                            {
                                "name": cname,
                                "website_url": comp.get("website_url") or "",
                                "careers_url": comp.get("careers_url") or "",
                                "active": bool(comp.get("active", True)),
                            },
                        )
                        db.flush()
                        new_comp_id = db.execute(
                            text("SELECT id FROM companies WHERE name = :name"),
                            {"name": cname},
                        ).scalar()
                        company_id_map[comp["id"]] = new_comp_id
                        counts["companies"] += 1

                # ── 3. Jobs Import ────────────────────────────────────────────────────
                job_id_map: dict[int, int] = {}
                src_jobs = self._query_source(src_conn, target_source.type, "SELECT * FROM jobs")
                now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

                for j in src_jobs:
                    src_jid = j["id"]
                    mapped_comp_id = company_id_map.get(j.get("company_id"), 1)
                    mapped_cntry_id = country_id_map.get(j.get("country_id"), default_country_id)
                    job_url = j.get("job_url") or f"https://example.com/job/{src_jid}"

                    existing_job = db.execute(
                        text("SELECT id FROM jobs WHERE job_url = :url"),
                        {"url": job_url},
                    ).scalar()

                    if existing_job:
                        job_id_map[src_jid] = existing_job
                    else:
                        db.execute(
                            text(
                                """
                                INSERT INTO jobs (company_id, country_id, title, location, job_url,
                                                  description, employment_type, remote_type, department,
                                                  source, external_job_id, posted_at, discovered_at,
                                                  last_seen_at, active, created_at, updated_at)
                                VALUES (:company_id, :country_id, :title, :location, :job_url,
                                        :description, :employment_type, :remote_type, :department,
                                        :source, :external_job_id, :posted_at, :discovered_at,
                                        :last_seen_at, :active, :created_at, :updated_at)
                                """
                            ),
                            {
                                "company_id": mapped_comp_id,
                                "country_id": mapped_cntry_id,
                                "title": j.get("title") or "Untitled Position",
                                "location": j.get("location"),
                                "job_url": job_url,
                                "description": j.get("description"),
                                "employment_type": j.get("employment_type"),
                                "remote_type": j.get("remote_type"),
                                "department": j.get("department"),
                                "source": j.get("source") or "imported",
                                "external_job_id": j.get("external_job_id"),
                                "posted_at": str(j.get("posted_at")) if j.get("posted_at") else None,
                                "discovered_at": str(j.get("discovered_at") or now_str),
                                "last_seen_at": str(j.get("last_seen_at")) if j.get("last_seen_at") else None,
                                "active": bool(j.get("active", True)),
                                "created_at": str(j.get("created_at") or now_str),
                                "updated_at": str(j.get("updated_at") or j.get("created_at") or now_str),
                            },
                        )
                        db.flush()
                        new_jid = db.execute(
                            text("SELECT id FROM jobs WHERE job_url = :url"),
                            {"url": job_url},
                        ).scalar()
                        job_id_map[src_jid] = new_jid
                        counts["jobs"] += 1

                # ── 4. User Applications Import ───────────────────────────────────────
                src_apps = self._query_source(
                    src_conn,
                    target_source.type,
                    "SELECT * FROM user_applications WHERE user_id = %s" if target_source.type == "mysql" else "SELECT * FROM user_applications WHERE user_id = ?",
                    (source_user_id,),
                )
                for a in src_apps:
                    src_app_jid = a.get("job_id")
                    target_job_id = job_id_map.get(src_app_jid)
                    if not target_job_id:
                        # Find any valid job or skip
                        first_job = db.execute(text("SELECT id FROM jobs LIMIT 1")).scalar()
                        target_job_id = first_job or 1

                    existing_app = db.execute(
                        text(
                            "SELECT id FROM user_applications WHERE user_id = :uid AND (job_id = :jid OR custom_job_title = :ctitle)"
                        ),
                        {
                            "uid": target_user_id,
                            "jid": target_job_id,
                            "ctitle": a.get("custom_job_title") or "__none__",
                        },
                    ).scalar()

                    if existing_app and req.conflict_strategy == "skip":
                        continue

                    if existing_app and req.conflict_strategy == "overwrite":
                        db.execute(
                            text(
                                """
                                UPDATE user_applications
                                SET status = :status, notes = :notes, applied_at = :applied_at, updated_at = :updated_at
                                WHERE id = :id
                                """
                            ),
                            {
                                "id": existing_app,
                                "status": a.get("status") or "applied",
                                "notes": a.get("notes"),
                                "applied_at": str(a.get("applied_at")) if a.get("applied_at") else None,
                                "updated_at": str(a.get("updated_at") or now_str),
                            },
                        )
                    else:
                        db.execute(
                            text(
                                """
                                INSERT INTO user_applications
                                    (user_id, job_id, status, notes, applied_at, created_at, updated_at,
                                     custom_job_title, custom_company_name, custom_location, custom_country,
                                     custom_job_url, source, salary, employment_type, contact_name,
                                     contact_email, contact_phone, recruiter, referral, priority,
                                     next_follow_up, interview_date)
                                VALUES
                                    (:user_id, :job_id, :status, :notes, :applied_at, :created_at, :updated_at,
                                     :custom_job_title, :custom_company_name, :custom_location, :custom_country,
                                     :custom_job_url, :source, :salary, :employment_type, :contact_name,
                                     :contact_email, :contact_phone, :recruiter, :referral, :priority,
                                     :next_follow_up, :interview_date)
                                """
                            ),
                            {
                                "user_id": target_user_id,
                                "job_id": target_job_id,
                                "status": a.get("status") or "applied",
                                "notes": a.get("notes"),
                                "applied_at": str(a.get("applied_at")) if a.get("applied_at") else None,
                                "created_at": str(a.get("created_at") or now_str),
                                "updated_at": str(a.get("updated_at") or now_str),
                                "custom_job_title": a.get("custom_job_title"),
                                "custom_company_name": a.get("custom_company_name"),
                                "custom_location": a.get("custom_location"),
                                "custom_country": a.get("custom_country"),
                                "custom_job_url": a.get("custom_job_url"),
                                "source": a.get("source"),
                                "salary": a.get("salary"),
                                "employment_type": a.get("employment_type"),
                                "contact_name": a.get("contact_name"),
                                "contact_email": a.get("contact_email"),
                                "contact_phone": a.get("contact_phone"),
                                "recruiter": a.get("recruiter"),
                                "referral": a.get("referral"),
                                "priority": a.get("priority") or "medium",
                                "next_follow_up": str(a.get("next_follow_up")) if a.get("next_follow_up") else None,
                                "interview_date": str(a.get("interview_date")) if a.get("interview_date") else None,
                            },
                        )
                        counts["applications"] += 1

                # ── 5. Contacts Import ────────────────────────────────────────────────
                src_contacts = self._query_source(
                    src_conn,
                    target_source.type,
                    "SELECT * FROM contacts WHERE user_id = %s" if target_source.type == "mysql" else "SELECT * FROM contacts WHERE user_id = ?",
                    (source_user_id,),
                )
                for con in src_contacts:
                    cemail = con.get("email") or ""
                    cname = con.get("name") or f"{con.get('first_name', '')} {con.get('last_name', '')}".strip()
                    existing_con = db.execute(
                        text("SELECT id FROM contacts WHERE user_id = :uid AND (email = :email OR name = :name)"),
                        {"uid": target_user_id, "email": cemail, "name": cname},
                    ).scalar() if (cemail or cname) else None

                    if not existing_con:
                        db.execute(
                            text(
                                """
                                INSERT INTO contacts (user_id, first_name, last_name, name, email, phone,
                                                      company, role, linkedin_url, location, notes, tags,
                                                      created_at, updated_at)
                                VALUES (:user_id, :first_name, :last_name, :name, :email, :phone,
                                        :company, :role, :linkedin_url, :location, :notes, :tags,
                                        :created_at, :updated_at)
                                """
                            ),
                            {
                                "user_id": target_user_id,
                                "first_name": con.get("first_name"),
                                "last_name": con.get("last_name"),
                                "name": cname or "Contact",
                                "email": cemail,
                                "phone": con.get("phone"),
                                "company": con.get("company"),
                                "role": con.get("role"),
                                "linkedin_url": con.get("linkedin_url"),
                                "location": con.get("location"),
                                "notes": con.get("notes"),
                                "tags": con.get("tags"),
                                "created_at": str(con.get("created_at") or now_str),
                                "updated_at": str(con.get("updated_at") or now_str),
                            },
                        )
                        counts["contacts"] += 1

                # ── 6. Resumes Import & Storage File Copy ──────────────────────────────
                src_resumes = self._query_source(
                    src_conn,
                    target_source.type,
                    "SELECT * FROM resumes WHERE user_id = %s" if target_source.type == "mysql" else "SELECT * FROM resumes WHERE user_id = ?",
                    (source_user_id,),
                )
                for r in src_resumes:
                    fname = r.get("filename") or "resume.pdf"
                    existing_r = db.execute(
                        text("SELECT id FROM resumes WHERE user_id = :uid AND filename = :fname"),
                        {"uid": target_user_id, "fname": fname},
                    ).scalar()

                    if not existing_r:
                        parsed_json = r.get("parsed_sections")
                        if isinstance(parsed_json, (dict, list)):
                            parsed_json = json.dumps(parsed_json)
                        db.execute(
                            text(
                                """
                                INSERT INTO resumes (user_id, filename, raw_text, parsed_sections, is_active,
                                                     created_at, updated_at, title, is_default, is_original_upload)
                                VALUES (:user_id, :filename, :raw_text, :parsed_sections, :is_active,
                                        :created_at, :updated_at, :title, :is_default, :is_original_upload)
                                """
                            ),
                            {
                                "user_id": target_user_id,
                                "filename": fname,
                                "raw_text": r.get("raw_text"),
                                "parsed_sections": parsed_json,
                                "is_active": bool(r.get("is_active", True)),
                                "created_at": str(r.get("created_at") or now_str),
                                "updated_at": str(r.get("updated_at") or now_str),
                                "title": r.get("title") or fname,
                                "is_default": bool(r.get("is_default", False)),
                                "is_original_upload": bool(r.get("is_original_upload", True)),
                            },
                        )
                        counts["resumes"] += 1

                # ── 7. Copy storage files if available ────────────────────────────────
                counts["files"] = self._copy_storage_files()

                # Commit all database transactions
                db.commit()
                logger.info(f"Guided data import completed successfully: {counts}")

            except Exception as e:
                db.rollback()
                logger.error(f"Error executing data import, rolling back: {e}", exc_info=True)
                raise
            finally:
                db.close()

        finally:
            src_conn.close()

        return ImportExecuteResponse(
            success=True,
            message=(
                f"Successfully imported data for {source_email}: "
                f"{counts['jobs']} jobs, {counts['companies']} companies, {counts['applications']} applications, "
                f"{counts['contacts']} contacts, {counts['resumes']} resumes."
            ),
            backup_file=str(backup_created) if backup_created else None,
            users_imported=counts["users"],
            companies_imported=counts["companies"],
            jobs_imported=counts["jobs"],
            applications_imported=counts["applications"],
            contacts_imported=counts["contacts"],
            resumes_imported=counts["resumes"],
            files_copied=counts["files"],
        )

    def _query_source(
        self,
        conn: Any,
        source_type: str,
        sql: str,
        params: tuple = (),
    ) -> list[dict[str, Any]]:
        """Helper to run a parameterized query across PyMySQL or sqlite3."""
        if source_type == "mysql":
            with conn.cursor() as cur:
                cur.execute(sql, params)
                return list(cur.fetchall())
        else:
            cur = conn.cursor()
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]

    def _copy_storage_files(self) -> int:
        """Copy existing storage documents from repo storage to local user data storage."""
        copied = 0
        dest_storage = get_storage_dir()
        candidate_roots = [
            Path("A:/code/compust/important/storage"),
            Path(__file__).resolve().parents[4] / "important" / "storage",
        ]
        for croot in candidate_roots:
            if not croot.is_dir():
                continue
            for src_file in croot.rglob("*"):
                if src_file.is_file():
                    rel = src_file.relative_to(croot)
                    dest_path = dest_storage / rel
                    try:
                        dest_path.parent.mkdir(parents=True, exist_ok=True)
                        if not dest_path.exists():
                            shutil.copy2(src_file, dest_path)
                            copied += 1
                    except Exception as e:
                        logger.debug(f"Could not copy storage file {src_file}: {e}")
        return copied

    def export_backup(self) -> BackupExportResponse:
        """Create a complete .zip archive with database, storage files, and manifest."""
        init_database_schema()
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_filename = f"compust_backup_{timestamp}.zip"
        backup_path = get_backups_dir() / backup_filename

        db_path = get_database_path()
        storage_path = get_storage_dir()
        stats = self.get_target_stats()

        manifest = {
            "app": "compust",
            "version": "1.0.2",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "stats": stats,
            "database_file": "compust.db",
        }

        with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # 1. Manifest
            zf.writestr("manifest.json", json.dumps(manifest, indent=2))

            # 2. Database
            if db_path.is_file():
                zf.write(db_path, arcname="compust.db")

            # 3. Storage
            if storage_path.is_dir():
                for f in storage_path.rglob("*"):
                    if f.is_file():
                        rel = f.relative_to(storage_path)
                        zf.write(f, arcname=f"storage/{rel.as_posix()}")

        size = backup_path.stat().st_size
        logger.info(f"Exported backup archive {backup_filename} ({size} bytes)")

        return BackupExportResponse(
            success=True,
            filename=backup_filename,
            size_bytes=size,
            download_url=f"/api/v1/data/backup/download/{backup_filename}",
            created_at=datetime.now(timezone.utc).isoformat(),
            stats=stats,
        )

    def restore_backup(self, zip_path: Path) -> BackupRestoreResponse:
        """Restore database and storage files from a validated backup archive."""
        if not zip_path.is_file():
            raise FileNotFoundError(f"Backup file not found at {zip_path}")

        # Safety: Take backup before restore
        db_path = get_database_path()
        safety_backup = None
        if db_path.is_file():
            safety_backup = backup_sqlite_database(db_path)

        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            if "compust.db" not in names and "manifest.json" not in names:
                raise ValueError("Invalid backup archive: missing 'compust.db' or 'manifest.json'.")

            # Close existing DB connection pool to allow clean replace
            engine.dispose()

            # Extract database
            if "compust.db" in names:
                temp_db = get_database_dir() / "compust_restoring.db"
                with zf.open("compust.db") as zf_db, open(temp_db, "wb") as out:
                    shutil.copyfileobj(zf_db, out)

                # Overwrite primary db
                if db_path.is_file():
                    db_path.unlink()
                shutil.move(temp_db, db_path)

            # Extract storage
            dest_storage = get_storage_dir()
            for member in names:
                if member.startswith("storage/") and not member.endswith("/"):
                    rel = member[len("storage/"):]
                    target_file = dest_storage / rel
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as zf_file, open(target_file, "wb") as out:
                        shutil.copyfileobj(zf_file, out)

        restored_stats = self.get_target_stats()
        logger.info(f"Backup restored successfully from {zip_path.name}: {restored_stats}")

        return BackupRestoreResponse(
            success=True,
            message=f"Backup restored successfully ({restored_stats.get('jobs', 0)} jobs, {restored_stats.get('user_applications', 0)} applications).",
            safety_backup=str(safety_backup) if safety_backup else None,
            restored_stats=restored_stats,
        )


data_manager_service = DataManagerService()
