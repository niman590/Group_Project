from conftest import assert_module_functions_present
from io import BytesIO

from conftest import insert_application, make_test_connection


def test_submit_documents_helpers(route_modules):
    submit = route_modules["routes.submit_documents_routes"]
    assert submit.get_status_badge_class("Approved") == "badge-success"
    assert submit.get_status_badge_class("Rejected") == "badge-danger"
    assert submit.get_status_badge_class("Draft") == "badge-warning"
    assert submit.get_status_badge_class("Under Review") == "badge-info"
    app = {"status": "Draft", "workflow_stage": "Submitted", "current_step": "1", "committee_decision": None, "deputy_director_decision": None, "first_officer_decision": None, "site_visit_status": "Pending", "additional_docs_required": 0}
    assert submit.get_status_label(app) == "Draft"
    app["status"] = "Approved"
    assert submit.get_status_label(app) == "Approved"


def test_submit_documents_login_and_page(client):
    response = client.get("/submit-documents")
    assert response.status_code == 302
    response = client.get("/gis-search-location?q=Malabe")
    assert response.status_code == 401


def test_gis_search_and_reverse_geocode(client, logged_in_user, route_modules, monkeypatch):
    submit = route_modules["routes.submit_documents_routes"]

    class FakeSearchResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return [{"lat": "7.1", "lon": "80.1", "display_name": "Malabe"}]

    class FakeReverseResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"display_name": "Malabe, Sri Lanka"}

    def fake_get(url, *args, **kwargs):
        if "reverse" in url:
            return FakeReverseResponse()
        return FakeSearchResponse()

    monkeypatch.setattr(submit.requests, "get", fake_get)
    response = client.get("/gis-search-location?q=Malabe")
    assert response.status_code == 200
    assert response.get_json()["success"] is True

    response = client.get("/gis-reverse-geocode?lat=7.1&lon=80.1")
    assert response.status_code == 200
    assert client.get("/gis-search-location").status_code == 400
    assert client.get("/gis-reverse-geocode").status_code == 400


def test_save_planning_draft_steps_and_fetch(client, logged_in_user):
    assert b"rendered:plan_approval.html" in client.get("/submit-documents").data
    step_payloads = [
        (1, {"development_work_type": "New", "proposed_use": ["Residential"], "assessment_no": "A1"}),
        (2, {"applicants": [{"name": "A", "nic": "123456789V", "telephone": "0771234567", "email": "a@example.com", "address": "A"}]}),
        (3, {"architect_town_planner_name": "Arch", "engineer_name": "Eng", "applicant_owns_land": "yes"}),
        (4, {"owner_name": "Owner", "owner_nic": "123456789V"}),
        (5, {"rate_clearance_ref": "R1"}),
        (6, {"existing_use": "Bare", "proposed_use_text": "House", "site_extent": 10}),
        (7, {"distance_street_boundary": 1, "no_of_floors": 2}),
        (8, {"plot_coverage": 50, "floor_area_ratio": 1.2}),
        (9, {"existing_units": 0, "proposed_units": 1}),
        (10, {"submitted_plans": ["Site plan", "Floor plan"]}),
    ]
    for step, data in step_payloads:
        response = client.post("/save-planning-draft-step", json={"step": step, "data": data})
        assert response.status_code == 200
        assert response.get_json()["success"] is True

    response = client.get("/get-planning-draft")
    assert response.status_code == 200
    assert response.get_json()["success"] is True


def test_save_planning_files_submit_and_my_applications(client, logged_in_user, test_db_path, route_modules, monkeypatch, tmp_path):
    submit = route_modules["routes.submit_documents_routes"]
    monkeypatch.setattr(submit, "UPLOAD_FOLDER", str(tmp_path))
    app_id = insert_application(test_db_path, user_id=logged_in_user, status="Draft")

    response = client.post("/save-planning-draft-files", data={"files[site_plan]": (BytesIO(b"%PDF"), "site.pdf")}, content_type="multipart/form-data")
    assert response.status_code == 200

    response = client.post("/submit-planning-application", json={})
    assert response.status_code == 200
    assert response.get_json()["success"] is True
    assert b"rendered:my_applications.html" in client.get("/my-applications").data

    response = client.post(f"/my-applications/{app_id}/delete-draft")
    assert response.status_code == 302


def test_submit_requested_document_notifications_edit_download_and_planning_view(client, logged_in_user, test_db_path, tmp_path, route_modules, monkeypatch):
    submit = route_modules["routes.submit_documents_routes"]
    monkeypatch.setattr(submit, "REQUESTED_DOCS_FOLDER", str(tmp_path))
    app_id = insert_application(test_db_path, user_id=logged_in_user, status="Submitted")

    conn = make_test_connection(test_db_path)
    cur = conn.cursor()
    cur.execute("INSERT INTO planning_application_requests (application_id, requested_by, request_type, request_title, request_message, status) VALUES (?, ?, 'Additional Documents', 'Need doc', 'Upload', 'Open')", (app_id, logged_in_user))
    request_id = cur.lastrowid
    cur.execute("INSERT INTO planning_application_requested_documents (request_id, application_id, document_label, status) VALUES (?, ?, 'NIC', 'Pending')", (request_id, app_id))
    doc_id = cur.lastrowid
    cur.execute("INSERT INTO user_notifications (user_id, application_id, title, message, notification_type) VALUES (?, ?, 'Hello', 'Message', 'info')", (logged_in_user, app_id))
    cur.execute("UPDATE planning_applications SET decision_pdf_path='static/uploads/planning_decisions/fake.pdf' WHERE application_id=?", (app_id,))
    conn.commit()
    conn.close()

    response = client.post(f"/upload-requested-document/{doc_id}", data={"requested_document": (BytesIO(b"%PDF"), "nic.pdf")}, content_type="multipart/form-data")
    assert response.status_code == 302

    assert client.get("/notifications").status_code == 200
    assert client.get(f"/edit-planning-draft/{app_id}").status_code in {200, 302}
    assert client.get(f"/planning-approval/{app_id}").status_code == 200


def test_submit_documents_routes_function_inventory(route_modules):
    expected = ['user_login_required', 'add_submit_documents_no_cache_headers', 'send_planning_submission_email', 'get_or_create_draft_application', 'create_user_notification', 'get_status_label', 'get_status_badge_class', 'gis_search_location', 'gis_reverse_geocode', 'submit_documents', 'save_planning_draft_step', 'save_planning_draft_files', 'get_planning_draft', 'submit_planning_application', 'my_applications', 'delete_draft_application', 'upload_requested_document', 'user_notifications', 'edit_planning_draft', 'download_decision_pdf', 'planning_approval']
    assert_module_functions_present(route_modules['routes.submit_documents_routes'], expected)
