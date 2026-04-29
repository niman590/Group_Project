from conftest import assert_module_functions_present
from io import BytesIO

from conftest import insert_application, insert_user, make_test_connection


class DummyUpload:
    def __init__(self, filename="file.pdf", data=b"data"):
        self.filename = filename
        self.data = data

    def save(self, path):
        with open(path, "wb") as f:
            f.write(self.data)


def test_admin_planning_helper_validation_and_upload(route_modules, app, tmp_path, monkeypatch):
    helpers = route_modules["routes.admin_planning_helpers"]
    assert helpers.allowed_extension("file.pdf")
    assert helpers.allowed_extension("file.docx")
    assert not helpers.allowed_extension("file.exe")
    assert helpers._safe_stage_comment("", "Default") == "Default"

    monkeypatch.setattr(app, "root_path", str(tmp_path), raising=False)
    saved = helpers.save_uploaded_file(DummyUpload("letter.pdf"), "uploads/test_letters")
    assert saved.startswith("static/uploads/test_letters/")
    assert helpers.save_uploaded_file(DummyUpload("bad.exe"), "uploads/test_letters") is None


def test_admin_planning_helper_database_writes(route_modules, test_db_path):
    helpers = route_modules["routes.admin_planning_helpers"]
    user_id = insert_user(test_db_path, email="helper-user@example.com", nic="101010101V")
    app_id = insert_application(test_db_path, user_id=user_id)

    conn = make_test_connection(test_db_path)
    cur = conn.cursor()
    helpers.create_user_notification(cur, user_id, app_id, "Title", "Message", "info")
    helpers.add_workflow_history(cur, app_id, "Submitted", "Created", "OK", user_id)
    assert helpers.get_application_user_id(cur, app_id) == user_id
    helpers.update_application_stage(cur, app_id, "Site Visit", "1")
    conn.commit()

    assert cur.execute("SELECT COUNT(*) AS total FROM user_notifications WHERE user_id=?", (user_id,)).fetchone()["total"] == 1
    assert cur.execute("SELECT workflow_stage FROM planning_applications WHERE application_id=?", (app_id,)).fetchone()["workflow_stage"] == "Site Visit"
    conn.close()


def test_fetch_full_application_bundle(route_modules, test_db_path):
    helpers = route_modules["routes.admin_planning_helpers"]
    user_id = insert_user(test_db_path, email="bundle-user@example.com", nic="202020202V")
    app_id = insert_application(test_db_path, user_id=user_id)
    bundle = helpers.fetch_full_application_bundle(app_id)
    assert bundle is not None
    assert bundle["application"]["application_id"] == app_id
    assert helpers.fetch_full_application_bundle(999999) is None


def test_admin_planning_helpers_function_inventory(route_modules):
    expected = ['ensure_planning_schema', 'allowed_extension', 'save_uploaded_file', '_build_planning_pdf_path', '_safe_stage_comment', 'generate_stage_decision_pdf', 'generate_decision_pdf', 'create_user_notification', 'add_workflow_history', 'get_application_user_id', 'update_application_stage', 'fetch_full_application_bundle']
    assert_module_functions_present(route_modules['routes.admin_planning_helpers'], expected)
