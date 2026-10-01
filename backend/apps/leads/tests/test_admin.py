import csv
import io
from typing import Any

import pytest
from auditlog.models import LogEntry
from django.test import Client
from django.urls import reverse_lazy

from apps.leads.models import Lead
from apps.users.models import User

CHANGELIST = reverse_lazy("admin:leads_lead_changelist")


@pytest.fixture
def manager(db: Any) -> User:
    return User.objects.create_superuser(phone="+998900000009", password="Str0ng-pass")


@pytest.fixture
def staff_client(manager: User) -> Client:
    client = Client()
    client.force_login(manager)
    return client


def action_data(action: str, *leads: Lead) -> dict[str, Any]:
    return {"action": action, "_selected_action": [lead.pk for lead in leads]}


def test_mark_contacted_is_audited(staff_client: Client, manager: User) -> None:
    lead = Lead.objects.create(name="Ali", phone="+998901112233")
    done = Lead.objects.create(name="Vali", phone="+998901112234", status=Lead.Status.CONVERTED)

    response = staff_client.post(CHANGELIST, action_data("mark_contacted", lead, done))

    assert response.status_code == 302
    lead.refresh_from_db()
    done.refresh_from_db()
    assert lead.status == Lead.Status.CONTACTED
    assert done.status == Lead.Status.CONVERTED
    entry = LogEntry.objects.get_for_object(lead).get(action=LogEntry.Action.UPDATE)
    assert entry.actor == manager
    assert "status" in entry.changes_dict


def test_export_csv_neutralises_formulas(staff_client: Client) -> None:
    payload = '=HYPERLINK("http://example.com","bosing")'
    lead = Lead.objects.create(name=payload, phone="+998901112233", comment="@SUM(1)")

    response = staff_client.post(CHANGELIST, action_data("export_csv", lead))

    rows = list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))
    name, phone, comment = rows[1][1], rows[1][2], rows[1][5]
    assert name == "'" + payload
    assert phone == "'+998901112233"
    assert comment == "'@SUM(1)"
