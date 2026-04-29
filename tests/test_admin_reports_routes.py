from conftest import assert_module_functions_present

def test_admin_reports_helpers(route_modules):
    reports = route_modules["routes.admin_reports_routes"]
    assert reports.normalize_date_input("2025-01-01") == "2025-01-01"
    assert reports.normalize_date_input("bad") == ""
    assert reports.format_date_for_display("2025-01-02") == "Jan 02, 2025"
    assert reports.build_date_clause("created_at", "2025-01-01", "")[0] == " AND date(created_at) >= date(?)"
    assert reports.fit_text("abcdef", 100) == "abcdef"


def test_admin_reports_page_and_downloads(client, logged_in_admin, route_modules, tmp_path, monkeypatch):
    reports = route_modules["routes.admin_reports_routes"]
    assert b"rendered:admin_reports.html" in client.get("/admin/reports").data

    def write_fake_pdf(*args, **kwargs):
        path = tmp_path / "fake.pdf"
        path.write_bytes(b"%PDF-1.4\n%fake")
        return str(path)

    monkeypatch.setattr(reports, "generate_admin_report_pdf", write_fake_pdf)
    monkeypatch.setattr(reports, "generate_user_registration_pdf", write_fake_pdf)
    monkeypatch.setattr(reports, "generate_application_applicants_pdf", write_fake_pdf)

    assert client.get("/admin/reports/download-pdf").status_code == 200
    assert client.get("/admin/reports/download-users-pdf").status_code == 200
    assert client.get("/admin/reports/download-applicants-pdf").status_code == 200


def test_admin_reports_routes_function_inventory(route_modules):
    expected = ['get_current_user', 'admin_required', 'safe_fetchone_value', 'safe_fetchall', 'normalize_date_input', 'format_date_for_display', 'build_date_clause', 'build_chart_image', 'get_user_registration_chart', 'get_application_status_chart', 'get_recent_users', 'get_recent_applications', 'create_pdf_canvas', 'ensure_pdf_space', 'draw_section_title', 'draw_kv_line', 'decode_chart_image', 'draw_chart_block', 'fit_text', 'wrap_paragraph', 'draw_wrapped_table', 'generate_admin_report_pdf', 'generate_user_registration_pdf', 'generate_application_applicants_pdf', 'admin_reports', 'download_admin_reports_pdf', 'download_user_registration_pdf', 'download_applicants_pdf']
    assert_module_functions_present(route_modules['routes.admin_reports_routes'], expected)
