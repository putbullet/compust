import io
from datetime import datetime, timezone
from typing import Any
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from ..models import Company, Country, Job, User, UserApplication, UserApplicationHistory
from ..schemas_applications import (
    ApplicationCreate,
    ApplicationStatsRead,
    ApplicationUpdate,
    ManualApplicationCreate,
    SankeyDataRead,
    SankeyLink,
    SankeyNode,
)


def log_application_history(
    db: Session,
    application_id: int,
    from_status: str | None,
    to_status: str,
    notes: str | None = None,
) -> UserApplicationHistory:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    history = UserApplicationHistory(
        application_id=application_id,
        from_status=from_status,
        to_status=to_status,
        changed_at=now,
        notes=notes,
    )
    db.add(history)
    return history


def save_or_update_application(
    db: Session,
    user: User,
    job_id: int,
    data: ApplicationCreate,
) -> UserApplication:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    existing = db.scalar(
        select(UserApplication).where(
            UserApplication.user_id == user.id,
            UserApplication.job_id == job_id,
        )
    )

    if existing:
        old_status = existing.status
        existing.status = data.status
        if data.notes is not None:
            existing.notes = data.notes
        if data.status == "applied" and not existing.applied_at:
            existing.applied_at = now
        existing.updated_at = now

        if old_status != data.status:
            log_application_history(
                db,
                application_id=existing.id,
                from_status=old_status,
                to_status=data.status,
                notes="Status updated via Opportunities",
            )

        db.commit()
        db.refresh(existing)
        return existing

    applied_at = now if data.status == "applied" else None
    app = UserApplication(
        user_id=user.id,
        job_id=job_id,
        status=data.status,
        notes=data.notes,
        source=data.source or "Compust",
        applied_at=applied_at,
        created_at=now,
        updated_at=now,
    )
    db.add(app)
    db.flush()

    log_application_history(
        db,
        application_id=app.id,
        from_status=None,
        to_status=data.status,
        notes="Added via Opportunities",
    )

    db.commit()
    db.refresh(app)
    return app


def create_manual_application(
    db: Session,
    user: User,
    data: ManualApplicationCreate,
) -> UserApplication:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    applied_at = data.applied_at or (now if data.status == "applied" else None)

    app = UserApplication(
        user_id=user.id,
        job_id=None,
        custom_job_title=data.job_title.strip(),
        custom_company_name=data.company_name.strip(),
        source=data.source or "LinkedIn",
        status=data.status or "applied",
        custom_location=data.location.strip() if data.location else None,
        custom_country=data.country.strip() if data.country else None,
        custom_job_url=data.job_url.strip() if data.job_url else None,
        salary=data.salary.strip() if data.salary else None,
        employment_type=data.employment_type.strip() if data.employment_type else None,
        contact_name=data.contact_name.strip() if data.contact_name else None,
        contact_email=data.contact_email.strip() if data.contact_email else None,
        contact_phone=data.contact_phone.strip() if data.contact_phone else None,
        recruiter=data.recruiter.strip() if data.recruiter else None,
        referral=data.referral.strip() if data.referral else None,
        priority=data.priority or "medium",
        notes=data.notes.strip() if data.notes else None,
        next_follow_up=data.next_follow_up,
        interview_date=data.interview_date,
        applied_at=applied_at,
        created_at=now,
        updated_at=now,
    )
    db.add(app)
    db.flush()

    log_application_history(
        db,
        application_id=app.id,
        from_status=None,
        to_status=app.status,
        notes="Manual application created",
    )

    db.commit()
    db.refresh(app)
    return app


def get_user_applications(
    db: Session,
    user_id: int,
    status: str | None = None,
    source: str | None = None,
    country: str | None = None,
    search: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> list[UserApplication]:
    query = (
        select(UserApplication)
        .outerjoin(Job, UserApplication.job_id == Job.id)
        .outerjoin(Country, Job.country_id == Country.id)
        .outerjoin(Company, Job.company_id == Company.id)
        .where(UserApplication.user_id == user_id)
    )

    if status:
        query = query.where(UserApplication.status == status)
    if source:
        query = query.where(UserApplication.source == source)
    if country:
        query = query.where(
            or_(
                UserApplication.custom_country.ilike(f"%{country}%"),
                Country.name.ilike(f"%{country}%"),
                Country.code.ilike(f"%{country}%"),
            )
        )
    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                UserApplication.custom_job_title.ilike(pattern),
                UserApplication.custom_company_name.ilike(pattern),
                UserApplication.notes.ilike(pattern),
                UserApplication.contact_name.ilike(pattern),
                UserApplication.recruiter.ilike(pattern),
                Job.title.ilike(pattern),
                Company.name.ilike(pattern),
            )
        )
    if start_date:
        query = query.where(
            func.coalesce(UserApplication.applied_at, UserApplication.created_at) >= start_date
        )
    if end_date:
        query = query.where(
            func.coalesce(UserApplication.applied_at, UserApplication.created_at) <= end_date
        )

    query = query.order_by(UserApplication.updated_at.desc())
    return list(db.scalars(query).all())


def get_application(
    db: Session,
    user_id: int,
    application_id: int,
) -> UserApplication | None:
    return db.scalar(
        select(UserApplication).where(
            UserApplication.id == application_id,
            UserApplication.user_id == user_id,
        )
    )


def update_application(
    db: Session,
    user: User,
    application_id: int,
    data: ApplicationUpdate,
) -> UserApplication | None:
    app = get_application(db, user.id, application_id)
    if not app:
        return None

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Check status change
    if data.status is not None and data.status != app.status:
        old_status = app.status
        app.status = data.status
        if data.status == "applied" and not app.applied_at:
            app.applied_at = now

        log_application_history(
            db,
            application_id=app.id,
            from_status=old_status,
            to_status=data.status,
            notes=data.notes,
        )

    if data.notes is not None:
        app.notes = data.notes
    if data.applied_at is not None:
        app.applied_at = data.applied_at
    if data.job_title is not None:
        app.custom_job_title = data.job_title
    if data.company_name is not None:
        app.custom_company_name = data.company_name
    if data.location is not None:
        app.custom_location = data.location
    if data.country is not None:
        app.custom_country = data.country
    if data.job_url is not None:
        app.custom_job_url = data.job_url
    if data.source is not None:
        app.source = data.source
    if data.salary is not None:
        app.salary = data.salary
    if data.employment_type is not None:
        app.employment_type = data.employment_type
    if data.contact_name is not None:
        app.contact_name = data.contact_name
    if data.contact_email is not None:
        app.contact_email = data.contact_email
    if data.contact_phone is not None:
        app.contact_phone = data.contact_phone
    if data.recruiter is not None:
        app.recruiter = data.recruiter
    if data.referral is not None:
        app.referral = data.referral
    if data.priority is not None:
        app.priority = data.priority
    if data.next_follow_up is not None:
        app.next_follow_up = data.next_follow_up
    if data.interview_date is not None:
        app.interview_date = data.interview_date

    app.updated_at = now
    db.commit()
    db.refresh(app)
    return app


def delete_application(db: Session, user: User, application_id: int) -> bool:
    res = db.execute(
        delete(UserApplication).where(
            UserApplication.id == application_id,
            UserApplication.user_id == user.id,
        )
    )
    db.commit()
    return res.rowcount > 0


def delete_application_by_job_id(db: Session, user: User, job_id: int) -> bool:
    res = db.execute(
        delete(UserApplication).where(
            UserApplication.job_id == job_id,
            UserApplication.user_id == user.id,
        )
    )
    db.commit()
    return res.rowcount > 0


def get_application_statistics(
    db: Session,
    user_id: int,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> ApplicationStatsRead:
    apps = get_user_applications(
        db,
        user_id,
        start_date=start_date,
        end_date=end_date,
    )
    total = len(apps)

    status_breakdown: dict[str, int] = {}
    source_breakdown: dict[str, int] = {}

    interview_statuses = {
        "interviewing",
        "1st_interview",
        "2nd_interview",
        "3rd_interview",
        "final_interview",
        "offer",
        "accepted",
    }
    response_statuses = interview_statuses | {"rejected", "withdrawn"}

    active_statuses = {
        "applied",
        "interviewing",
        "1st_interview",
        "2nd_interview",
        "3rd_interview",
        "final_interview",
        "offer",
    }

    interview_count = 0
    response_count = 0
    offer_count = 0
    accepted_count = 0
    rejected_count = 0
    active_count = 0

    interview_days: list[float] = []
    offer_days: list[float] = []

    for app in apps:
        status = app.status or "saved"
        status_breakdown[status] = status_breakdown.get(status, 0) + 1

        source = app.source or "Compust"
        source_breakdown[source] = source_breakdown.get(source, 0) + 1

        if status in active_statuses:
            active_count += 1

        # Check if ever reached interview / offer / response either via current status or history
        histories = app.history or []
        statuses_seen = {status} | {h.to_status for h in histories}

        if any(s in interview_statuses for s in statuses_seen):
            interview_count += 1

        if any(s in response_statuses for s in statuses_seen) and status != "no_answer":
            response_count += 1

        if "offer" in statuses_seen or "accepted" in statuses_seen:
            offer_count += 1

        if "accepted" in statuses_seen:
            accepted_count += 1

        if status == "rejected":
            rejected_count += 1

        # Calculate time metrics if applied_at exists
        app_date = app.applied_at or app.created_at
        if app_date:
            # Find earliest interview transition or interview_date
            first_int_time = app.interview_date
            for h in histories:
                if h.to_status in interview_statuses:
                    if not first_int_time or h.changed_at < first_int_time:
                        first_int_time = h.changed_at
            if first_int_time and first_int_time >= app_date:
                diff = (first_int_time - app_date).total_seconds() / 86400.0
                interview_days.append(diff)

            # Find offer transition
            offer_time = None
            for h in histories:
                if h.to_status in {"offer", "accepted"}:
                    if not offer_time or h.changed_at < offer_time:
                        offer_time = h.changed_at
            if offer_time and offer_time >= app_date:
                diff = (offer_time - app_date).total_seconds() / 86400.0
                offer_days.append(diff)

    applied_base = sum(1 for a in apps if a.status != "saved") or total
    denominator = max(applied_base, 1)

    return ApplicationStatsRead(
        total_applications=total,
        active_applications=active_count,
        status_breakdown=status_breakdown,
        source_breakdown=source_breakdown,
        interview_rate_percent=round((interview_count / denominator) * 100, 1),
        response_rate_percent=round((response_count / denominator) * 100, 1),
        offer_rate_percent=round((offer_count / denominator) * 100, 1),
        acceptance_rate_percent=round((accepted_count / max(offer_count, 1)) * 100, 1)
        if offer_count > 0
        else 0.0,
        rejection_rate_percent=round((rejected_count / denominator) * 100, 1),
        avg_days_to_interview=round(sum(interview_days) / len(interview_days), 1)
        if interview_days
        else None,
        avg_days_to_offer=round(sum(offer_days) / len(offer_days), 1) if offer_days else None,
    )


def get_sankey_pipeline(
    db: Session,
    user_id: int,
    source: str | None = None,
    country: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> SankeyDataRead:
    """Generate dynamic left-to-right Sankey / pipeline funnel based on actual applications and status transitions."""
    apps = get_user_applications(
        db,
        user_id,
        source=source,
        country=country,
        start_date=start_date,
        end_date=end_date,
    )

    if not apps:
        return SankeyDataRead(nodes=[], links=[], total=0)

    # Funnel stages:
    # 0: Sources (Compust, LinkedIn, Indeed, etc.)
    # 1: Applied
    # 2: 1st Round / Screening (or No Answer)
    # 3: Advanced Interviews
    # 4: Offers
    # 5: Final Outcomes (Accepted, Rejected, Withdrawn)

    source_counts: dict[str, int] = {}
    applied_count = 0
    no_answer_count = 0
    screen_count = 0
    screen_rej_count = 0
    advanced_int_count = 0
    advanced_rej_count = 0
    offer_count = 0
    accepted_count = 0
    offer_declined_count = 0
    withdrawn_count = 0

    for app in apps:
        src = app.source or "Compust"
        source_counts[src] = source_counts.get(src, 0) + 1
        applied_count += 1

        history_statuses = [h.to_status for h in (app.history or [])]
        all_statuses = set(history_statuses) | {app.status}

        has_interview = any(
            s in {
                "interviewing",
                "1st_interview",
                "2nd_interview",
                "3rd_interview",
                "final_interview",
                "offer",
                "accepted",
            }
            for s in all_statuses
        )
        has_adv_interview = any(
            s in {"2nd_interview", "3rd_interview", "final_interview", "offer", "accepted"}
            for s in all_statuses
        )
        has_offer = any(s in {"offer", "accepted"} for s in all_statuses)
        is_accepted = app.status == "accepted" or "accepted" in all_statuses

        if app.status == "no_answer":
            no_answer_count += 1
        elif app.status == "withdrawn":
            withdrawn_count += 1
        elif not has_interview:
            if app.status == "rejected":
                screen_rej_count += 1
        else:
            # Reached interview stage
            screen_count += 1
            if has_adv_interview:
                advanced_int_count += 1
                if has_offer:
                    offer_count += 1
                    if is_accepted:
                        accepted_count += 1
                    elif app.status == "rejected":
                        offer_declined_count += 1
                elif app.status == "rejected":
                    advanced_rej_count += 1
            elif app.status == "rejected":
                screen_rej_count += 1

    nodes: list[SankeyNode] = []
    links: list[SankeyLink] = []

    # Stage 0: Sources
    for src_name, count in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
        src_id = f"src_{src_name.lower().replace(' ', '_')}"
        nodes.append(
            SankeyNode(
                id=src_id,
                label=src_name,
                stage_index=0,
                count=count,
                color="#6366f1",
            )
        )
        links.append(SankeyLink(source=src_id, target="stage_applied", value=count))

    # Stage 1: Applied
    nodes.append(
        SankeyNode(
            id="stage_applied",
            label="Applied",
            stage_index=1,
            count=applied_count,
            color="#3b82f6",
        )
    )

    # Links from Applied
    if no_answer_count > 0:
        nodes.append(
            SankeyNode(
                id="stage_no_answer",
                label="No Answer / Ghosted",
                stage_index=2,
                count=no_answer_count,
                color="#64748b",
            )
        )
        links.append(
            SankeyLink(
                source="stage_applied",
                target="stage_no_answer",
                value=no_answer_count,
            )
        )

    direct_rejections = max(0, applied_count - no_answer_count - screen_count - withdrawn_count)
    if direct_rejections > 0:
        nodes.append(
            SankeyNode(
                id="stage_screening_rej",
                label="Initial Screening Rejected",
                stage_index=2,
                count=direct_rejections,
                color="#ef4444",
            )
        )
        links.append(
            SankeyLink(
                source="stage_applied",
                target="stage_screening_rej",
                value=direct_rejections,
            )
        )

    if screen_count > 0:
        nodes.append(
            SankeyNode(
                id="stage_1st_interview",
                label="1st Interview / Screening",
                stage_index=2,
                count=screen_count,
                color="#8b5cf6",
            )
        )
        links.append(
            SankeyLink(
                source="stage_applied",
                target="stage_1st_interview",
                value=screen_count,
            )
        )

        # Stage 3: Advanced Interviews
        stage2_rej = max(0, screen_count - advanced_int_count)
        if stage2_rej > 0:
            nodes.append(
                SankeyNode(
                    id="stage_post_1st_rej",
                    label="Rejected After 1st Round",
                    stage_index=3,
                    count=stage2_rej,
                    color="#f87171",
                )
            )
            links.append(
                SankeyLink(
                    source="stage_1st_interview",
                    target="stage_post_1st_rej",
                    value=stage2_rej,
                )
            )

        if advanced_int_count > 0:
            nodes.append(
                SankeyNode(
                    id="stage_advanced_interview",
                    label="Technical / Final Rounds",
                    stage_index=3,
                    count=advanced_int_count,
                    color="#ec4899",
                )
            )
            links.append(
                SankeyLink(
                    source="stage_1st_interview",
                    target="stage_advanced_interview",
                    value=advanced_int_count,
                )
            )

            # Stage 4: Offers
            adv_rej = max(0, advanced_int_count - offer_count)
            if adv_rej > 0:
                nodes.append(
                    SankeyNode(
                        id="stage_final_rej",
                        label="Rejected After Final",
                        stage_index=4,
                        count=adv_rej,
                        color="#dc2626",
                    )
                )
                links.append(
                    SankeyLink(
                        source="stage_advanced_interview",
                        target="stage_final_rej",
                        value=adv_rej,
                    )
                )

            if offer_count > 0:
                nodes.append(
                    SankeyNode(
                        id="stage_offer",
                        label="Offers Received",
                        stage_index=4,
                        count=offer_count,
                        color="#10b981",
                    )
                )
                links.append(
                    SankeyLink(
                        source="stage_advanced_interview",
                        target="stage_offer",
                        value=offer_count,
                    )
                )

                # Stage 5: Final Outcomes
                if accepted_count > 0:
                    nodes.append(
                        SankeyNode(
                            id="stage_accepted",
                            label="Offer Accepted 🎉",
                            stage_index=5,
                            count=accepted_count,
                            color="#059669",
                        )
                    )
                    links.append(
                        SankeyLink(
                            source="stage_offer",
                            target="stage_accepted",
                            value=accepted_count,
                        )
                    )

                other_offer_outcome = max(0, offer_count - accepted_count)
                if other_offer_outcome > 0:
                    nodes.append(
                        SankeyNode(
                            id="stage_declined",
                            label="Offer Pending / Declined",
                            stage_index=5,
                            count=other_offer_outcome,
                            color="#34d399",
                        )
                    )
                    links.append(
                        SankeyLink(
                            source="stage_offer",
                            target="stage_declined",
                            value=other_offer_outcome,
                        )
                    )

    return SankeyDataRead(nodes=nodes, links=links, total=applied_count)


def export_applications_xlsx(db: Session, user_id: int) -> bytes:
    """Generate professional Excel workbook (.xlsx) of all tracked applications."""
    apps = get_user_applications(db, user_id)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Applications"

    # Header styling
    header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    row_font = Font(name="Calibri", size=10)
    alt_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    thin_border = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0"),
    )

    headers = [
        "ID",
        "Job Title",
        "Company",
        "Source",
        "Status",
        "Applied Date",
        "Location",
        "Country",
        "Salary",
        "Employment Type",
        "Priority",
        "Next Follow-up",
        "Interview Date",
        "Contact Name",
        "Contact Email",
        "Contact Phone",
        "Recruiter",
        "Referral",
        "Notes",
        "Job URL",
    ]

    ws.append(headers)
    ws.row_dimensions[1].height = 28

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = header_alignment
        cell.border = thin_border

    # Format status for readable export
    status_labels = {
        "saved": "Saved",
        "applied": "Applied",
        "no_answer": "No Answer / Ghosted",
        "interviewing": "Interviewing",
        "1st_interview": "1st Interview",
        "2nd_interview": "2nd Interview",
        "3rd_interview": "3rd Interview",
        "final_interview": "Final Interview",
        "offer": "Offer Received",
        "accepted": "Offer Accepted",
        "rejected": "Rejected",
        "withdrawn": "Withdrawn",
    }

    for row_idx, app in enumerate(apps, start=2):
        applied_str = app.applied_at.strftime("%Y-%m-%d") if app.applied_at else ""
        follow_up_str = app.next_follow_up.strftime("%Y-%m-%d") if app.next_follow_up else ""
        interview_str = app.interview_date.strftime("%Y-%m-%d %H:%M") if app.interview_date else ""

        title = app.custom_job_title or (app.job.title if app.job else f"Application #{app.id}")
        company = (
            app.custom_company_name
            or (app.job.company.name if app.job and app.job.company else "Company")
        )
        location = app.custom_location or (app.job.location if app.job else "")
        country = (
            app.custom_country
            or (app.job.country.name if app.job and app.job.country else "")
        )
        url = app.custom_job_url or (app.job.job_url if app.job else "")

        row_values = [
            app.id,
            title,
            company,
            app.source or "Compust",
            status_labels.get(app.status, app.status),
            applied_str,
            location,
            country,
            app.salary or "",
            app.employment_type or "",
            (app.priority or "medium").capitalize(),
            follow_up_str,
            interview_str,
            app.contact_name or "",
            app.contact_email or "",
            app.contact_phone or "",
            app.recruiter or "",
            app.referral or "",
            app.notes or "",
            url,
        ]
        ws.append(row_values)
        ws.row_dimensions[row_idx].height = 20

        is_even = row_idx % 2 == 0
        for col_idx in range(1, len(row_values) + 1):
            cell = ws.cell(row=row_idx, column=col_idx)
            cell.font = row_font
            cell.border = thin_border
            if is_even:
                cell.fill = alt_fill

    # Enable auto filter
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(apps) + 1}"

    # Auto-adjust column widths
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or "")
            if len(val_str) > max_len:
                max_len = len(val_str)
        ws.column_dimensions[col_letter].width = min(max(max_len + 3, 10), 45)

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
