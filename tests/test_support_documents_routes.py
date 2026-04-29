from conftest import assert_module_functions_present
from pathlib import Path


def test_support_documents_requires_login(client):
    response = client.get("/support-documents")
    assert response.status_code == 302


def test_support_documents_data(route_modules, logged_in_user):
    support = route_modules["routes.support_documents_routes"]
    documents, stats = support.get_support_documents_data()
    assert isinstance(documents, list)
    assert len(documents) >= 1
    assert stats["documents_count"] >= 0


def test_support_documents_page_and_pdf_routes(client, logged_in_user, route_modules, tmp_path, monkeypatch):
    support = route_modules["routes.support_documents_routes"]
    pdf_dir = tmp_path / "support_documents"
    pdf_dir.mkdir()
    for name in [
        "planning_approval_guidelines.pdf",
        "required_documents_checklist.pdf",
        "gazettes_and_rules.pdf",
        "civic_plan_user_manual.pdf",
    ]:
        (pdf_dir / name).write_bytes(b"%PDF-1.4\n%fake")

    monkeypatch.setattr(support, "get_support_documents_folder", lambda: str(pdf_dir))
    assert b"rendered:support_documents.html" in client.get("/support-documents").data
    assert client.get("/support_documents").status_code == 200

    urls = [
        "/support-documents/planning-approval-guidelines/view",
        "/support-documents/planning-approval-guidelines/download",
        "/support-documents/required-documents-checklist/view",
        "/support-documents/required-documents-checklist/download",
        "/support-documents/gazettes-and-rules/view",
        "/support-documents/gazettes-and-rules/download",
        "/support-documents/user-manual/view",
        "/support-documents/user-manual/download",
    ]
    for url in urls:
        assert client.get(url).status_code == 200


def test_ensure_pdf_exists_404(route_modules, app, tmp_path, monkeypatch):
    support = route_modules["routes.support_documents_routes"]
    monkeypatch.setattr(support, "get_support_documents_folder", lambda: str(tmp_path))
    with app.test_request_context("/"):
        try:
            support.ensure_pdf_exists("missing.pdf", "Missing")
        except Exception as exc:
            assert getattr(exc, "code", None) == 404


def test_support_documents_routes_function_inventory(route_modules):
    expected = ['user_login_required', 'add_support_documents_no_cache_headers', 'get_support_documents_folder', 'ensure_pdf_exists', 'get_support_documents_data', 'support_documents_page', 'view_planning_guidelines', 'download_planning_guidelines', 'view_required_documents_checklist', 'download_required_documents_checklist', 'view_gazettes_and_rules', 'download_gazettes_and_rules', 'view_user_manual', 'download_user_manual']
    assert_module_functions_present(route_modules['routes.support_documents_routes'], expected)
