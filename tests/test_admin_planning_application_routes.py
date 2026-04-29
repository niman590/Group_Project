from conftest import assert_module_functions_present
from pathlib import Path

from conftest import flashed_messages, insert_application, insert_user, make_test_connection


def test_admin_planning_internal_helpers(route_modules):
    planning = route_modules["routes.admin_planning_application_routes"]
    assert planning._safe_comment("") == "No additional comments were provided."
    assert planning._safe_comment("Done") == "Done"


def test_admin_planning_list_detail_and_site_visit(client, test_db_path, logged_in_admin, route_modules, monkeypatch):
    planning = route_modules["routes.admin_planning_application_routes"]
    helpers = route_modules["routes.admin_planning_helpers"]
    user_id = insert_user(test_db_path, email="planning-user@example.com", nic="710000000V")
    app_id = insert_application(test_db_path, user_id=user_id, status="Submitted", workflow_stage="Submitted", current_step="1")

    monkeypatch.setattr(planning, "_generate_stage_decision_letter", lambda *a, **k: "static/uploads/planning_stage_letters/fake.pdf")
    monkeypatch.setattr(helpers, "generate_stage_decision_pdf", lambda *a, **k: "static/uploads/planning_stage_letters/fake.pdf", raising=False)
    monkeypatch.setattr(helpers, "generate_decision_pdf", lambda *a, **k: "static/uploads/planning_decisions/fake.pdf", raising=False)
    monkeypatch.setattr(planning, "generate_decision_pdf", lambda *a, **k: "static/uploads/planning_decisions/fake.pdf", raising=False)

    assert b"rendered:admin_planning_applications.html" in client.get("/admin/planning-applications").data
    assert b"rendered:admin_planning_application_detail.html" in client.get(f"/admin/planning-applications/{app_id}").data
    assert client.get("/admin/planning-applications/999999").status_code == 302

    response = client.post(f"/admin/planning-applications/{app_id}/site-visit", data={"visit_status": "Completed", "admin_comment": "Done"})
    assert response.status_code == 302
    conn = make_test_connection(test_db_path)
    row = conn.execute("SELECT workflow_stage, current_step, site_visit_status FROM planning_applications WHERE application_id=?", (app_id,)).fetchone()
    conn.close()
    assert row["workflow_stage"] == "Additional Docs / Clearance"
    assert row["current_step"] == "2"


def test_admin_planning_review_workflow_routes(client, test_db_path, logged_in_admin, route_modules, monkeypatch):
    planning = route_modules["routes.admin_planning_application_routes"]
    monkeypatch.setattr(planning, "_generate_stage_decision_letter", lambda *a, **k: "static/uploads/planning_stage_letters/fake.pdf")
    monkeypatch.setattr(planning, "generate_decision_pdf", lambda *a, **k: "static/uploads/planning_decisions/fake.pdf", raising=False)

    user_id = insert_user(test_db_path, email="workflow-user@example.com", nic="720000000V")
    app_id = insert_application(test_db_path, user_id=user_id, status="Submitted", workflow_stage="Additional Docs / Clearance", current_step="2")

    assert client.post(f"/admin/planning-applications/{app_id}/request-documents", data={"request_title": "Need docs", "request_message": "Upload deed", "document_labels": "Deed\nNIC"}).status_code == 302
    assert client.post(f"/admin/planning-applications/{app_id}/notify-user", data={"title": "Notice", "message": "Check"}).status_code == 302
    assert client.get(f"/admin/planning-applications/{app_id}/planning-office").status_code == 200
    assert client.post(f"/admin/planning-applications/{app_id}/planning-office/submit", data={"decision": "Approved", "comment": "OK"}).status_code == 302
    assert client.post(f"/admin/planning-applications/{app_id}/first-officer-decision", data={"decision": "Approved", "comment": "OK"}).status_code == 302
    assert client.post(f"/admin/planning-applications/{app_id}/deputy-director-decision", data={"decision": "Approved", "comment": "OK"}).status_code == 302
    assert client.post(f"/admin/planning-applications/{app_id}/committee-decision", data={"decision": "Approved", "comment": "OK"}).status_code == 302


def test_admin_planning_download_letters(client, test_db_path, logged_in_admin, tmp_path, monkeypatch, route_modules):
    planning = route_modules["routes.admin_planning_application_routes"]
    fake_pdf = tmp_path / "letter.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4\n%fake")
    monkeypatch.setattr(planning, "_build_absolute_path", lambda relative_path: str(fake_pdf))

    user_id = insert_user(test_db_path, email="download-user@example.com", nic="730000000V")
    app_id = insert_application(test_db_path, user_id=user_id, status="Approved", workflow_stage="Approved", current_step="6")
    conn = make_test_connection(test_db_path)
    conn.execute(
        "UPDATE planning_applications SET decision_pdf_path=?, planning_office_letter_path=?, deputy_director_decision=?, deputy_director_comment=? WHERE application_id=?",
        ("static/uploads/planning_decisions/fake.pdf", "static/uploads/planning_office_letters/first.pdf", "Approved", "Looks fine", app_id),
    )
    conn.commit()
    conn.close()

    assert client.get(f"/admin/planning-applications/{app_id}/decision-pdf").status_code == 200
    assert client.get(f"/admin/planning-applications/{app_id}/first-officer-letter").status_code == 200
    assert client.get(f"/admin/planning-applications/{app_id}/deputy-director-letter").status_code == 200


def test_admin_planning_application_routes_function_inventory(route_modules):
    expected = ['_build_absolute_path', '_safe_comment', '_generate_stage_decision_letter', '_get_application_and_user', 'admin_planning_applications', 'admin_planning_application_detail', 'mark_site_visit', 'request_additional_documents', 'notify_application_user', 'planning_office_approval', 'submit_planning_office_review', 'first_officer_decision', 'deputy_director_decision', 'committee_decision', 'approve_planning_application', 'reject_planning_application', 'download_planning_decision_pdf', 'download_first_officer_letter', 'download_deputy_director_letter']
    assert_module_functions_present(route_modules['routes.admin_planning_application_routes'], expected)
