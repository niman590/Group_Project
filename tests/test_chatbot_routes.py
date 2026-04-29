from conftest import assert_module_functions_present
from conftest import insert_land_record_with_history, insert_user, make_test_connection


def test_chatbot_helpers(route_modules, app):
    chat = route_modules["routes.chatbot_routes"]
    assert chat.normalize_text("  Hello   World ") == "hello world"
    assert chat.extract_deed_number("show D-1001 history") == "D-1001"
    assert chat.extract_deed_number("deed number ABC/10") == "ABC/10"
    with app.test_request_context("/"):
        response = chat.build_response("Hi", action="open_page", target="/x")
        assert response.get_json()["reply"] == "Hi"


def test_chatbot_requires_login(client):
    response = client.post("/chat", json={"message": "hello"})
    assert response.status_code == 401
    assert response.get_json()["action"] == "open_page"


def test_chatbot_dashboard_and_transaction_intents(client, logged_in_user, test_db_path):
    insert_land_record_with_history(test_db_path, deed_number="D-CHAT")
    response = client.post("/chat", json={"message": "open dashboard"})
    assert response.status_code == 200
    assert response.get_json()["type"] == "action"

    response = client.post("/chat", json={"message": "show ownership details for deed D-CHAT"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["type"] in {"answer", "data"}


def test_chatbot_summary_and_faq(client, logged_in_user, test_db_path):
    conn = make_test_connection(test_db_path)
    cur = conn.cursor()
    cur.execute("INSERT INTO planning_applications (user_id, status, workflow_stage, current_step) VALUES (?, 'Submitted', 'Submitted', '1')", (logged_in_user,))
    cur.execute("INSERT INTO property (owner_id, current_value, property_size, property_address) VALUES (?, ?, ?, ?)", (logged_in_user, 1000, 10, "Malabe"))
    prop_id = cur.lastrowid
    cur.execute("INSERT INTO value_prediction (property_id, predicted_value) VALUES (?, ?)", (prop_id, 1000))
    conn.commit()
    conn.close()

    response = client.post("/chat", json={"message": "dashboard summary"})
    assert response.status_code == 200
    assert "reply" in response.get_json()

    response = client.post("/chat", json={"message": "what documents are required"})
    assert response.status_code == 200
    assert "reply" in response.get_json()


def test_chatbot_routes_function_inventory(route_modules):
    expected = ['chatbot_login_required', 'add_chatbot_no_cache_headers', 'get_gemini_client', 'is_logged_in', 'normalize_text', 'extract_deed_number', 'get_user_dashboard_summary', 'get_transaction_history_by_deed', 'build_response', 'handle_navigation_intent', 'handle_live_data_intent', 'handle_faq_intent', 'handle_public_dashboard_faq_intent', 'generate_public_dashboard_fallback', 'generate_gemini_fallback', 'chat']
    assert_module_functions_present(route_modules['routes.chatbot_routes'], expected)
