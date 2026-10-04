import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from src.app.models import Contact, ContactInteraction, User
from src.app.schemas_applications import ContactCreate, ContactUpdate
from src.app.repositories.contacts import (
    create_contact,
    update_contact,
    get_user_contacts,
    get_contact_by_id,
    preview_contacts_xlsx,
    export_contacts_xlsx,
)
import openpyxl
import io


@pytest.fixture
def test_user(db_session: Session) -> User:
    user = db_session.query(User).filter(User.email == "crm_test@example.com").first()
    if not user:
        user = User(
            email="crm_test@example.com",
            first_name="CRM",
            last_name="Tester",
            password_hash="fakehashedpassword",
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


def test_create_contact_minimal_not_contacted(db_session: Session, test_user: User):
    """Test contact creation with only basic info without email, phone, or communication."""
    data = ContactCreate(
        first_name="Sarah",
        last_name="Connor",
        name="Sarah Connor",
        company="Skynet",
        role="Recruiter",
    )
    contact = create_contact(db_session, test_user, data)
    assert contact.id is not None
    assert contact.email is None
    assert contact.phone is None

    read = [c for c in get_user_contacts(db_session, test_user.id) if c.id == contact.id][0]
    assert read.communication_status == "not_contacted"
    assert read.has_responded is False
    assert len(read.interactions) == 0


def test_create_contact_with_email_outreach_no_response(db_session: Session, test_user: User):
    """Test contact creation with email interaction, no response yet."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    data = ContactCreate(
        first_name="Alex",
        last_name="Vance",
        name="Alex Vance",
        company="Black Mesa",
        email="alex@blackmesa.org",
        contacted=True,
        contact_method="email",
        contact_date=now,
        email_used="alex@blackmesa.org",
        response_received=False,
    )
    contact = create_contact(db_session, test_user, data)
    read = [c for c in get_user_contacts(db_session, test_user.id) if c.id == contact.id][0]
    assert read.communication_status == "contacted_no_response"
    assert read.has_responded is False
    assert len(read.interactions) == 1
    assert read.interactions[0].type == "email_sent"
    assert "Initial email" in read.interactions[0].summary
    assert "alex@blackmesa.org" in (read.interactions[0].details or "")


def test_create_contact_with_outreach_and_response(db_session: Session, test_user: User):
    """Test contact creation with outreach and received response."""
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    data = ContactCreate(
        first_name="Gordon",
        last_name="Freeman",
        name="Gordon Freeman",
        company="Aperture Science",
        contacted=True,
        contact_method="linkedin",
        contact_date=now,
        response_received=True,
        response_date=now,
        response_notes="Invited for interview next Tuesday",
    )
    contact = create_contact(db_session, test_user, data)
    read = [c for c in get_user_contacts(db_session, test_user.id) if c.id == contact.id][0]
    assert read.communication_status == "responded"
    assert read.has_responded is True
    assert len(read.interactions) == 2
    assert any("response" in i.summary.lower() for i in read.interactions)


def test_update_contact_later_with_response(db_session: Session, test_user: User):
    """Test updating a previously uncontacted contact with communication history."""
    data = ContactCreate(
        first_name="Eli",
        last_name="Vance",
        name="Eli Vance",
        company="Resistance",
    )
    contact = create_contact(db_session, test_user, data)
    read_before = [c for c in get_user_contacts(db_session, test_user.id) if c.id == contact.id][0]
    assert read_before.communication_status == "not_contacted"

    # User later updates Eli to contacted + responded
    update_data = ContactUpdate(
        contacted=True,
        contact_method="phone",
        response_received=True,
        response_notes="Great discussion on phone",
    )
    updated = update_contact(db_session, test_user, contact.id, update_data)
    assert updated is not None

    read_after = [c for c in get_user_contacts(db_session, test_user.id) if c.id == contact.id][0]
    assert read_after.communication_status == "responded"
    assert read_after.has_responded is True
    assert len(read_after.interactions) == 2


def test_german_xlsx_import_headers(db_session: Session, test_user: User):
    """Test that German column headers in Excel spreadsheets are recognized correctly."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Kontakte"
    ws.append(["Vorname", "Nachname", "Firma", "Stelle", "E-Mail-Adresse", "Telefonnummer", "Ort", "Notizen"])
    ws.append(["Hans", "Müller", "Siemens", "Talent Acquisition", "hans.mueller@siemens.de", "+49 89 123456", "München", "Sehr nett"])

    buffer = io.BytesIO()
    wb.save(buffer)
    excel_bytes = buffer.getvalue()

    preview = preview_contacts_xlsx(db_session, test_user.id, excel_bytes)
    assert preview.total_detected == 1
    assert preview.preview_rows[0].first_name == "Hans"
    assert preview.preview_rows[0].last_name == "Müller"
    assert preview.preview_rows[0].company == "Siemens"
    assert preview.preview_rows[0].email == "hans.mueller@siemens.de"
    assert preview.preview_rows[0].location == "München"
