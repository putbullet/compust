import io
from datetime import date, datetime, timedelta, timezone
from typing import Any
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from ..models import Company, Contact, Country, Job, User, UserApplication, UserApplicationHistory
from ..schemas_applications import (
    ActivityTimePoint,
    ApplicationCreate,
    ApplicationEventCreate,
    ApplicationStatsRead,
    ApplicationUpdate,
    FollowUpActionPayload,
    ManualApplicationCreate,
    SankeyDataRead,
    SankeyLink,
    SankeyNode,
    SearchOverview,
    SourceAnalyticsItem,
)
from .contacts import build_contact_read


def log_application_history(
    db: Session,
    application_id: int,
    from_status: str | None,
    to_status: str,
    notes: str | None = None,
    event_type: str = "status_change",
    event_title: str | None = None,
    changed_at: datetime | None = None,
) -> UserApplicationHistory:
    now = changed_at or datetime.now(timezone.utc).replace(tzinfo=None)
    if not event_title:
        if event_type == "status_change":
            stage_name = to_status.replace("_", " ").title()
            event_title = f"Stage changed to {stage_name}"
        elif event_type == "created":
            event_title = "Application created"
        else:
            event_title = event_type.replace("_", " ").title()

    history = UserApplicationHistory(
        application_id=application_id,
        from_status=from_status,
        to_status=to_status,
        changed_at=now,
        notes=notes,
        event_type=event_type,
        event_title=event_title,
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
        if data.resume_suggestions is not None:
            existing.resume_suggestions = data.resume_suggestions
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
                event_type="status_change",
                event_title=f"Stage changed to {data.status.replace('_', ' ').title()}",
            )

        db.commit()
        db.refresh(existing)
        return existing

    applied_at = now if data.status == "applied" else None
    sugg = data.resume_suggestions
    if sugg is None:
        job = db.scalar(select(Job).where(Job.id == job_id))
        if job and job.resume_suggestions:
            sugg = job.resume_suggestions

    app = UserApplication(
        user_id=user.id,
        job_id=job_id,
        status=data.status,
        notes=data.notes,
        source=data.source or "Compust",
        applied_at=applied_at,
        created_at=now,
        updated_at=now,
        resume_suggestions=sugg,
    )
    db.add(app)
    db.flush()

    log_application_history(
        db,
        application_id=app.id,
        from_status=None,
        to_status=data.status,
        notes="Added via Opportunities",
        event_type="created",
        event_title="Application added via Opportunities",
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

    # Smart contact linking
    linked_contact_id = data.contact_id
    c_email = data.contact_email.strip().lower() if data.contact_email else None
    c_name = data.contact_name.strip() if data.contact_name else (data.recruiter.strip() if data.recruiter else None)

    if not linked_contact_id and c_email:
        existing_contact = db.scalar(
            select(Contact).where(
                Contact.user_id == user.id,
                func.lower(Contact.email) == c_email,
            )
        )
        if existing_contact:
            linked_contact_id = existing_contact.id

    if not linked_contact_id and (c_name or c_email):
        # Auto-create contact record for candidate convenience
        new_contact = Contact(
            user_id=user.id,
            name=c_name or c_email or "Contact",
            email=c_email,
            phone=data.contact_phone.strip() if data.contact_phone else None,
            company=data.company_name.strip(),
            role="Recruiter" if data.recruiter else "Hiring Contact",
            created_at=now,
            updated_at=now,
        )
        db.add(new_contact)
        db.flush()
        linked_contact_id = new_contact.id

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
        contact_id=linked_contact_id,
        contact_name=c_name,
        contact_email=c_email,
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
        event_type="created",
        event_title="Application created",
    )

    if data.next_follow_up:
        log_application_history(
            db,
            application_id=app.id,
            from_status=app.status,
            to_status=app.status,
            notes=f"Follow-up scheduled for {data.next_follow_up}",
            event_type="follow_up_scheduled",
            event_title=f"Follow-up scheduled for {data.next_follow_up}",
        )

    if data.interview_date:
        log_application_history(
            db,
            application_id=app.id,
            from_status=app.status,
            to_status=app.status,
            notes=f"Interview scheduled for {data.interview_date}",
            event_type="interview_scheduled",
            event_title=f"Interview scheduled for {data.interview_date.strftime('%b %d, %Y')}",
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
            event_type="status_change",
            event_title=f"Stage changed to {data.status.replace('_', ' ').title()}",
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

    # Contact linking
    if data.contact_id is not None:
        app.contact_id = data.contact_id
        contact = db.scalar(select(Contact).where(Contact.id == data.contact_id, Contact.user_id == user.id))
        if contact:
            app.contact_name = contact.name
            if contact.email:
                app.contact_email = contact.email
            log_application_history(
                db,
                application_id=app.id,
                from_status=app.status,
                to_status=app.status,
                notes=f"Linked to contact: {contact.name}",
                event_type="contact_linked",
                event_title=f"Associated with {contact.name}",
            )
    else:
        if data.contact_name is not None:
            app.contact_name = data.contact_name
        if data.contact_email is not None:
            app.contact_email = data.contact_email
            # Auto-link if exact email matches existing contact
            if not app.contact_id and data.contact_email.strip():
                existing = db.scalar(
                    select(Contact).where(
                        Contact.user_id == user.id,
                        func.lower(Contact.email) == data.contact_email.strip().lower(),
                    )
                )
                if existing:
                    app.contact_id = existing.id

    if data.contact_phone is not None:
        app.contact_phone = data.contact_phone
    if data.recruiter is not None:
        app.recruiter = data.recruiter
    if data.referral is not None:
        app.referral = data.referral
    if data.priority is not None:
        app.priority = data.priority

    # Follow-up changes
    if data.next_follow_up is not None and data.next_follow_up != app.next_follow_up:
        app.next_follow_up = data.next_follow_up
        log_application_history(
            db,
            application_id=app.id,
            from_status=app.status,
            to_status=app.status,
            notes=f"Scheduled for {data.next_follow_up}",
            event_type="follow_up_scheduled",
            event_title=f"Follow-up set to {data.next_follow_up}",
        )
    elif data.next_follow_up is None and "next_follow_up" in data.model_fields_set:
        app.next_follow_up = None

    # Interview date changes
    if data.interview_date is not None and data.interview_date != app.interview_date:
        app.interview_date = data.interview_date
        log_application_history(
            db,
            application_id=app.id,
            from_status=app.status,
            to_status=app.status,
            notes=f"Scheduled for {data.interview_date}",
            event_type="interview_scheduled",
            event_title=f"Interview scheduled for {data.interview_date.strftime('%b %d, %Y')}",
        )

    app.updated_at = now
    db.commit()
    db.refresh(app)
    return app


def execute_follow_up_action(
    db: Session,
    user: User,
    application_id: int,
    payload: FollowUpActionPayload,
) -> UserApplication | None:
    app = get_application(db, user.id, application_id)
    if not app:
        return None

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    action = payload.action

    if action == "complete":
        old_fu = app.next_follow_up
        app.next_follow_up = None
        app.updated_at = now
        log_application_history(
            db,
            application_id=app.id,
            from_status=app.status,
            to_status=app.status,
            notes=payload.notes or f"Follow-up completed (was scheduled for {old_fu})",
            event_type="follow_up_completed",
            event_title="Follow-up completed",
        )
    elif action == "snooze":
        days = payload.days or 2
        today = now.date()
        base_date = app.next_follow_up or today
        if base_date < today:
            base_date = today
        new_date = base_date + timedelta(days=days)
        app.next_follow_up = new_date
        app.updated_at = now
        log_application_history(
            db,
            application_id=app.id,
            from_status=app.status,
            to_status=app.status,
            notes=payload.notes or f"Snoozed by {days} days to {new_date}",
            event_type="follow_up_snoozed",
            event_title=f"Follow-up snoozed to {new_date}",
        )
    elif action == "reschedule":
        new_date = payload.new_date or (now.date() + timedelta(days=7))
        app.next_follow_up = new_date
        app.updated_at = now
        log_application_history(
            db,
            application_id=app.id,
            from_status=app.status,
            to_status=app.status,
            notes=payload.notes or f"Rescheduled to {new_date}",
            event_type="follow_up_rescheduled",
            event_title=f"Follow-up rescheduled to {new_date}",
        )
    elif action == "cancel":
        app.next_follow_up = None
        app.updated_at = now
        log_application_history(
            db,
            application_id=app.id,
            from_status=app.status,
            to_status=app.status,
            notes=payload.notes or "Follow-up cancelled",
            event_type="follow_up_cancelled",
            event_title="Follow-up cancelled",
        )

    db.commit()
    db.refresh(app)
    return app


def add_application_timeline_event(
    db: Session,
    user: User,
    application_id: int,
    data: ApplicationEventCreate,
) -> UserApplicationHistory | None:
    app = get_application(db, user.id, application_id)
    if not app:
        return None

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    event_date = data.event_date or now

    history = log_application_history(
        db,
        application_id=app.id,
        from_status=app.status,
        to_status=app.status,
        notes=data.notes,
        event_type=data.event_type or "note",
        event_title=data.event_title,
        changed_at=event_date,
    )
    app.updated_at = now
    db.commit()
    db.refresh(history)
    return history


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

    # Source-level tracking for Source Analytics
    source_stats: dict[str, dict] = {}

    today = datetime.now(timezone.utc).date()
    one_week_ago = today - timedelta(days=7)
    upcoming_interviews = 0
    upcoming_follow_ups = 0
    overdue_follow_ups = 0
    apps_this_week = 0

    for app in apps:
        status = app.status or "saved"
        status_breakdown[status] = status_breakdown.get(status, 0) + 1

        source = app.source or "Compust"
        source_breakdown[source] = source_breakdown.get(source, 0) + 1

        if source not in source_stats:
            source_stats[source] = {"applications": 0, "responses": 0, "interviews": 0, "offers": 0}
        source_stats[source]["applications"] += 1

        if status in active_statuses:
            active_count += 1

        histories = app.history or []
        statuses_seen = {status} | {h.to_status for h in histories}

        is_interview = any(s in interview_statuses for s in statuses_seen)
        is_response = any(s in response_statuses for s in statuses_seen) and status != "no_answer"
        is_offer = "offer" in statuses_seen or "accepted" in statuses_seen

        if is_interview:
            interview_count += 1
            source_stats[source]["interviews"] += 1

        if is_response:
            response_count += 1
            source_stats[source]["responses"] += 1

        if is_offer:
            offer_count += 1
            source_stats[source]["offers"] += 1

        if "accepted" in statuses_seen:
            accepted_count += 1

        if status == "rejected":
            rejected_count += 1

        # Application date & this week counter
        app_date = app.applied_at or app.created_at
        if app_date:
            if app_date.date() >= one_week_ago:
                apps_this_week += 1

            # Time to interview
            first_int_time = app.interview_date
            for h in histories:
                if h.to_status in interview_statuses:
                    if not first_int_time or h.changed_at < first_int_time:
                        first_int_time = h.changed_at
            if first_int_time and first_int_time >= app_date:
                diff = (first_int_time - app_date).total_seconds() / 86400.0
                interview_days.append(diff)

            # Time to offer
            offer_time = None
            for h in histories:
                if h.to_status in {"offer", "accepted"}:
                    if not offer_time or h.changed_at < offer_time:
                        offer_time = h.changed_at
            if offer_time and offer_time >= app_date:
                diff = (offer_time - app_date).total_seconds() / 86400.0
                offer_days.append(diff)

        # Follow-up and Interview overview metrics
        if app.next_follow_up:
            if app.next_follow_up < today:
                overdue_follow_ups += 1
            elif app.next_follow_up <= today + timedelta(days=7):
                upcoming_follow_ups += 1

        if app.interview_date and app.interview_date.date() >= today:
            upcoming_interviews += 1

    applied_base = sum(1 for a in apps if a.status != "saved") or total
    denominator = max(applied_base, 1)

    # 1. Source Analytics list
    source_analytics: list[SourceAnalyticsItem] = [
        SourceAnalyticsItem(
            source=s_name,
            applications=s_data["applications"],
            responses=s_data["responses"],
            interviews=s_data["interviews"],
            offers=s_data["offers"],
            response_rate_percent=round((s_data["responses"] / max(s_data["applications"], 1)) * 100, 1),
            interview_rate_percent=round((s_data["interviews"] / max(s_data["applications"], 1)) * 100, 1),
        )
        for s_name, s_data in sorted(source_stats.items(), key=lambda x: x[1]["applications"], reverse=True)
    ]

    # 2. Activity Timeline Generator (7d, 30d, 90d, 1y, all)
    def generate_timeline(days: int | None) -> list[ActivityTimePoint]:
        if days:
            start_d = today - timedelta(days=days)
            date_list = [start_d + timedelta(days=i) for i in range(days + 1)]
        else:
            # All time
            earliest = today
            for a in apps:
                ad = (a.applied_at or a.created_at).date()
                if ad < earliest:
                    earliest = ad
            span = max((today - earliest).days, 7)
            date_list = [earliest + timedelta(days=i) for i in range(span + 1)]

        date_map = {
            d.strftime("%Y-%m-%d"): {"applications": 0, "responses": 0, "interviews": 0, "offers": 0}
            for d in date_list
        }

        for a in apps:
            ad_str = (a.applied_at or a.created_at).strftime("%Y-%m-%d")
            if ad_str in date_map:
                date_map[ad_str]["applications"] += 1

            for h in a.history or []:
                hd_str = h.changed_at.strftime("%Y-%m-%d")
                if hd_str in date_map:
                    if h.to_status in interview_statuses:
                        date_map[hd_str]["interviews"] += 1
                    elif h.to_status in response_statuses and h.to_status != "no_answer":
                        date_map[hd_str]["responses"] += 1
                    if h.to_status in {"offer", "accepted"}:
                        date_map[hd_str]["offers"] += 1

        return [
            ActivityTimePoint(
                date=d_str,
                applications=counts["applications"],
                responses=counts["responses"],
                interviews=counts["interviews"],
                offers=counts["offers"],
            )
            for d_str, counts in sorted(date_map.items())
        ]

    activity_timeline = {
        "7d": generate_timeline(7),
        "30d": generate_timeline(30),
        "90d": generate_timeline(90),
        "1y": generate_timeline(365),
        "all": generate_timeline(None),
    }

    # 3. Overview summary
    overview = SearchOverview(
        total_applications=total,
        applications_this_week=apps_this_week,
        total_responses=response_count,
        total_interviews=interview_count,
        total_offers=offer_count,
        avg_response_time_days=round(sum(interview_days) / len(interview_days), 1) if interview_days else None,
        upcoming_interviews=upcoming_interviews,
        upcoming_follow_ups=upcoming_follow_ups,
        overdue_follow_ups=overdue_follow_ups,
    )

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
        source_analytics=source_analytics,
        activity_timeline=activity_timeline,
        overview=overview,
    )


def get_sankey_pipeline(
    db: Session,
    user_id: int,
    source: str | None = None,
    country: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> SankeyDataRead:
    """Generate exact SankeyMATIC-style recruitment funnel based on actual applications and status transitions."""
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

    total_apps = len(apps)

    # Transition tracking per application
    # Stage IDs:
    # 'stage_applications' (Stage 0)
    # 'stage_1st_interview', 'stage_rejected_init', 'stage_no_answer' (Stage 1)
    # 'stage_2nd_interview', 'stage_rejected_1st', 'stage_in_progress_1st' (Stage 2)
    # 'stage_3rd_interview', 'stage_rejected_2nd', 'stage_in_progress_2nd' (Stage 3)
    # 'stage_4th_interview', 'stage_rejected_3rd', 'stage_in_progress_3rd' (Stage 4)
    # 'stage_offers', 'stage_rejected_final', 'stage_in_progress_final' (Stage 5)
    # 'stage_accepted', 'stage_declined', 'stage_pending_offer' (Stage 6)

    link_counts: dict[tuple[str, str], int] = {}

    def add_flow(src: str, tgt: str):
        link_counts[(src, tgt)] = link_counts.get((src, tgt), 0) + 1

    # Stage membership sets — funnel placement is determined exclusively by the
    # application's *current* status.  History entries record when transitions
    # happened (useful for time metrics) but must NOT influence funnel counts:
    # an app that was once "accepted" and is now "rejected" must appear in the
    # rejected bucket, not in the accepted bucket.
    _STAGES_GTE_1ST   = {"interviewing", "1st_interview", "2nd_interview",
                          "3rd_interview", "final_interview", "offer", "accepted"}
    _STAGES_GTE_2ND   = {"2nd_interview", "3rd_interview", "final_interview", "offer", "accepted"}
    _STAGES_GTE_3RD   = {"3rd_interview", "final_interview", "offer", "accepted"}
    _STAGES_GTE_4TH   = {"final_interview", "offer", "accepted"}
    _STAGES_GTE_OFFER = {"offer", "accepted"}

    for app in apps:
        reached_1st      = app.status in _STAGES_GTE_1ST
        reached_2nd      = app.status in _STAGES_GTE_2ND
        reached_3rd      = app.status in _STAGES_GTE_3RD
        reached_4th      = app.status in _STAGES_GTE_4TH
        reached_offer    = app.status in _STAGES_GTE_OFFER
        reached_accepted = app.status == "accepted"

        if not reached_1st:
            if app.status == "no_answer":
                add_flow("stage_applications", "stage_no_answer")
            elif app.status == "rejected":
                add_flow("stage_applications", "stage_rejected_init")
            elif app.status == "withdrawn":
                add_flow("stage_applications", "stage_withdrawn_init")
            else:
                # Still waiting on initial screening
                add_flow("stage_applications", "stage_no_answer")
            continue

        # Reached 1st Interview
        add_flow("stage_applications", "stage_1st_interview")

        if not reached_2nd:
            if reached_offer:
                # Direct jump from 1st to offer
                add_flow("stage_1st_interview", "stage_offers")
                if reached_accepted:
                    add_flow("stage_offers", "stage_accepted")
                elif app.status == "rejected":
                    add_flow("stage_offers", "stage_declined")
                else:
                    add_flow("stage_offers", "stage_pending_offer")
            elif app.status == "rejected":
                add_flow("stage_1st_interview", "stage_rejected_1st")
            elif app.status in ["interviewing", "1st_interview"]:
                add_flow("stage_1st_interview", "stage_in_progress_1st")
            else:
                add_flow("stage_1st_interview", "stage_rejected_1st")
            continue

        # Reached 2nd Interview
        add_flow("stage_1st_interview", "stage_2nd_interview")

        if not reached_3rd:
            if reached_offer:
                # Jump from 2nd to offer
                add_flow("stage_2nd_interview", "stage_offers")
                if reached_accepted:
                    add_flow("stage_offers", "stage_accepted")
                elif app.status == "rejected":
                    add_flow("stage_offers", "stage_declined")
                else:
                    add_flow("stage_offers", "stage_pending_offer")
            elif app.status == "rejected":
                add_flow("stage_2nd_interview", "stage_rejected_2nd")
            elif app.status == "2nd_interview":
                add_flow("stage_2nd_interview", "stage_in_progress_2nd")
            else:
                add_flow("stage_2nd_interview", "stage_rejected_2nd")
            continue

        # Reached 3rd Interview
        add_flow("stage_2nd_interview", "stage_3rd_interview")

        if not reached_4th:
            if reached_offer:
                # Jump from 3rd to offer
                add_flow("stage_3rd_interview", "stage_offers")
                if reached_accepted:
                    add_flow("stage_offers", "stage_accepted")
                elif app.status == "rejected":
                    add_flow("stage_offers", "stage_declined")
                else:
                    add_flow("stage_offers", "stage_pending_offer")
            elif app.status == "rejected":
                add_flow("stage_3rd_interview", "stage_rejected_3rd")
            elif app.status == "3rd_interview":
                add_flow("stage_3rd_interview", "stage_in_progress_3rd")
            else:
                add_flow("stage_3rd_interview", "stage_rejected_3rd")
            continue

        # Reached 4th / Final Interview
        add_flow("stage_3rd_interview", "stage_4th_interview")

        if not reached_offer:
            if app.status == "rejected":
                add_flow("stage_4th_interview", "stage_rejected_final")
            elif app.status == "final_interview":
                add_flow("stage_4th_interview", "stage_in_progress_final")
            else:
                add_flow("stage_4th_interview", "stage_rejected_final")
            continue

        # Reached Offer
        add_flow("stage_4th_interview", "stage_offers")

        if reached_accepted:
            add_flow("stage_offers", "stage_accepted")
        elif app.status == "rejected":
            add_flow("stage_offers", "stage_declined")
        else:
            add_flow("stage_offers", "stage_pending_offer")

    # Node definitions with exact SankeyMATIC colors & stage columns
    node_configs: dict[str, tuple[str, int, str]] = {
        "stage_applications": ("Applications", 0, "#f97316"),  # Orange
        "stage_1st_interview": ("1st Interviews", 1, "#22c55e"),  # Green
        "stage_rejected_init": ("Rejected", 1, "#ef4444"),  # Coral Red
        "stage_no_answer": ("No Answer", 1, "#a855f7"),  # Purple Lavender
        "stage_withdrawn_init": ("Withdrawn", 1, "#64748b"),
        "stage_2nd_interview": ("2nd Interviews", 2, "#d97706"),  # Tan / Brown
        "stage_rejected_1st": ("Rejected", 2, "#f87171"),
        "stage_in_progress_1st": ("1st In Progress", 2, "#60a5fa"),
        "stage_3rd_interview": ("3rd interviews(home assignment)", 3, "#ec4899"),  # Pink
        "stage_rejected_2nd": ("Rejected", 3, "#f87171"),
        "stage_in_progress_2nd": ("2nd In Progress", 3, "#60a5fa"),
        "stage_4th_interview": ("4th interviews", 4, "#06b6d4"),  # Light Cyan
        "stage_rejected_3rd": ("Rejected", 4, "#f87171"),
        "stage_in_progress_3rd": ("3rd In Progress", 4, "#60a5fa"),
        "stage_offers": ("Offers", 5, "#eab308"),  # Yellow / Gold
        "stage_rejected_final": ("rejections", 5, "#14b8a6"),  # Teal
        "stage_in_progress_final": ("Final In Progress", 5, "#60a5fa"),
        "stage_accepted": ("Accepted", 6, "#0284c7"),  # Blue
        "stage_declined": ("Declined", 6, "#94a3b8"),
        "stage_pending_offer": ("Offer Pending", 6, "#38bdf8"),
    }

    # Calculate node totals from in/out links
    node_values: dict[str, int] = {}
    for (src, tgt), count in link_counts.items():
        node_values[src] = max(node_values.get(src, 0), sum(v for (s, _), v in link_counts.items() if s == src))
        node_values[tgt] = max(node_values.get(tgt, 0), sum(v for (_, t), v in link_counts.items() if t == tgt))
    node_values["stage_applications"] = total_apps

    nodes: list[SankeyNode] = []
    for node_id, count in node_values.items():
        if count <= 0:
            continue
        cfg = node_configs.get(node_id, (node_id, 1, "#64748b"))
        nodes.append(
            SankeyNode(
                id=node_id,
                label=cfg[0],
                stage_index=cfg[1],
                count=count,
                color=cfg[2],
            )
        )

    links: list[SankeyLink] = [
        SankeyLink(source=src, target=tgt, value=val)
        for (src, tgt), val in link_counts.items()
        if val > 0
    ]

    return SankeyDataRead(nodes=nodes, links=links, total=total_apps)



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
