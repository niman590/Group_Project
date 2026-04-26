from locust import HttpUser, task, between
from locust.exception import StopUser
import os
import random
import re
from urllib.parse import urlparse


# ============================================================
# BASIC CONFIGURATION
# ============================================================

TARGET_HOST = os.getenv("TARGET_HOST", "http://127.0.0.1:5000")
LOGIN_PATH = os.getenv("LOGIN_PATH", "/login")

# Citizen/user login
CITIZEN_LOGIN_VALUE = os.getenv("CITIZEN_LOGIN_VALUE", "200503502760")
CITIZEN_PASSWORD = os.getenv("CITIZEN_PASSWORD", "Niman@123")
CITIZEN_PRIMARY_FIELD = os.getenv("CITIZEN_PRIMARY_FIELD", "nic")

# Admin login
ADMIN_LOGIN_VALUE = os.getenv("ADMIN_LOGIN_VALUE", "ADMIN001")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ADMIN001")
ADMIN_PRIMARY_FIELD = os.getenv("ADMIN_PRIMARY_FIELD", "employee_id")

PASSWORD_FIELD = os.getenv("PASSWORD_FIELD", "password")

REDIRECT_STATUS_CODES = {301, 302, 303, 307, 308}


# ============================================================
# ROUTE CANDIDATES
# The script will try these route options and use the first one
# that works. This helps because some projects use:
# /support-documents
# while others use:
# /support_documents
# ============================================================

PUBLIC_PAGE_CANDIDATES = [
    ("PUBLIC: Home", ["/"]),
    ("PUBLIC: Login", ["/login"]),
    ("PUBLIC: Register", ["/register"]),
    ("PUBLIC: Password Reset", ["/password-reset", "/password_reset", "/forgot-password", "/forgot_password"]),
    ("PUBLIC: Land Record Info", ["/land-record-info", "/land_record_info"]),
    ("PUBLIC: Permit Status Info", ["/permit-status-info", "/permit_status_info"]),
]


CITIZEN_PAGE_CANDIDATES = [
    ("USER: Dashboard", ["/dashboard", "/user-dashboard", "/user_dashboard", "/user/dashboard"]),

    ("USER: My Profile", ["/account", "/profile", "/my-profile", "/my_profile", "/user/account"]),

    ("USER: Submit Documents", [
        "/submit-documents",
        "/submit_documents",
        "/plan-approval",
        "/plan_approval",
        "/planning-approval",
        "/planning_approval",
    ]),

    ("USER: My Applications", ["/my-applications", "/my_applications"]),

    ("USER: Transaction History", ["/transaction-history", "/transaction_history"]),

    ("USER: Land Valuation", ["/land-valuation", "/land_valuation"]),

    ("USER: Support Documents", ["/support-documents", "/support_documents"]),

    ("USER: Notifications", ["/all-notifications", "/all_notifications", "/notifications"]),

    ("USER: Change Password", ["/change-password", "/change_password"]),

    # Add ID-based pages manually only if you know a valid ID.
    # Example:
    # ("USER: Planning Approval View", ["/planning-approval-view/1"]),
]


ADMIN_PAGE_CANDIDATES = [
    ("ADMIN: Dashboard", [
        "/admin/dashboard",
        "/admin-dashboard",
        "/admin_dashboard",
    ]),

    ("ADMIN: Planning Applications", [
        "/admin/planning-applications",
        "/admin/planning_applications",
        "/admin-planning-applications",
        "/admin_planning_applications",
    ]),

    ("ADMIN: Transaction Requests", [
        "/admin/transaction-requests",
        "/admin/transaction_requests",
        "/admin/transaction-history-requests",
        "/admin/transaction_history_requests",
        "/admin-transaction-requests",
        "/admin_transaction_requests",
        "/admin_transaction_history_requests",
    ]),

    ("ADMIN: Add New Deed", [
        "/admin/add-deed",
        "/admin/add_deed",
        "/admin-add-deed",
        "/admin_add_deed",
    ]),

    ("ADMIN: Reports", [
        "/admin/reports",
        "/admin-reports",
        "/admin_reports",
    ]),

    ("ADMIN: Suspicious Behavior", [
        "/admin/suspicious-behavior",
        "/admin/suspicious_behavior",
        "/admin-suspicious-behavior",
        "/admin_suspicious_behavior",
        "/security/admin-suspicious-behavior",
        "/security/admin_suspicious_behavior",
    ]),

    ("ADMIN: User Management", [
        "/admin/user-management",
        "/admin/user_management",
        "/admin-user-management",
        "/admin_user_management",
    ]),

    ("ADMIN: My Account", [
        "/account",
        "/admin/account",
        "/admin/my-account",
        "/admin/my_account",
    ]),

    ("ADMIN: Deputy Director Review", [
        "/admin/deputy-director-review",
        "/admin/deputy_director_review",
        "/deputy-director-review",
        "/deputy_director_review",
        "/admin-deputy-director-review",
        "/admin_deputy_director_review",
    ]),

    ("ADMIN: District Project Committee Review", [
        "/admin/district-project-committee-review",
        "/admin/district_project_committee_review",
        "/district-project-committee-review",
        "/district_project_committee_review",
        "/admin-district-project-committee-review",
        "/admin_district_project_committee_review",
    ]),

    ("ADMIN: Planning Office Approval", [
        "/admin/planning-office-approval",
        "/admin/planning_office_approval",
        "/planning-office-approval",
        "/planning_office_approval",
        "/admin-planning-office-approval",
        "/admin_planning_office_approval",
    ]),

    ("ADMIN: Planning Workflow", [
        "/admin/planning-workflow",
        "/admin/planning_workflow",
        "/planning-workflow",
        "/planning_workflow",
        "/admin-planning-workflow",
        "/admin_planning_workflow",
    ]),

    # ID-based detail pages should be added only when you know valid IDs.
    # Example:
    # ("ADMIN: Planning Application Detail", ["/admin/planning-applications/1"]),
]


# ============================================================
# LOGIN FIELD FALLBACKS
# The script first tries the main field names:
# citizen: nic
# admin: employee_id
# Then it tries common alternatives.
# ============================================================

CITIZEN_LOGIN_FIELDS = [
    CITIZEN_PRIMARY_FIELD,
    "nic",
    "nic_no",
    "nic_number",
    "NIC",
    "user_nic",
    "username",
    "identifier",
    "login_id",
    "email",
]

ADMIN_LOGIN_FIELDS = [
    ADMIN_PRIMARY_FIELD,
    "employee_id",
    "admin_id",
    "staff_id",
    "username",
    "identifier",
    "login_id",
    "email",
    "nic",
]


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def unique_items(items):
    result = []
    seen = set()

    for item in items:
        if item not in seen:
            result.append(item)
            seen.add(item)

    return result


def extract_hidden_inputs(html):
    """
    Extract hidden input fields such as CSRF tokens from the login form.
    """
    data = {}

    input_tags = re.findall(r"<input[^>]*>", html, flags=re.IGNORECASE)

    for tag in input_tags:
        is_hidden = re.search(
            r'type=["\']hidden["\']',
            tag,
            flags=re.IGNORECASE
        )

        if not is_hidden:
            continue

        name_match = re.search(
            r'name=["\']([^"\']+)["\']',
            tag,
            flags=re.IGNORECASE
        )

        value_match = re.search(
            r'value=["\']([^"\']*)["\']',
            tag,
            flags=re.IGNORECASE
        )

        if name_match:
            name = name_match.group(1)
            value = value_match.group(1) if value_match else ""
            data[name] = value

    return data


def response_path(response):
    try:
        return urlparse(response.url).path or "/"
    except Exception:
        return "/"


def clean_path(path):
    if not path:
        return "/"

    if not path.startswith("/"):
        return "/" + path

    return path


# ============================================================
# BASE USER CLASS
# ============================================================

class BaseWebsiteUser(HttpUser):
    abstract = True
    host = TARGET_HOST
    wait_time = between(1, 3)

    def is_login_path(self, path):
        login_path = LOGIN_PATH.rstrip("/") or "/"
        current_path = path.rstrip("/") or "/"

        return current_path == login_path

    def login_successful(self, response, success_markers):
        """
        Detect whether login worked.

        Login is considered successful when:
        - final URL is not /login, or
        - page contains strong logged-in markers such as logout/dashboard.
        """
        if response.status_code != 200:
            return False

        final_path = response_path(response)
        body = response.text.lower()

        if not self.is_login_path(final_path):
            return True

        strong_markers = [
            "logout",
            "dashboard",
            "welcome back",
        ]

        for marker in strong_markers:
            if marker in body:
                return True

        for marker in success_markers:
            if marker.lower() in body:
                return True

        return False

    def login_as(self, login_value, password, login_fields, role_name, success_markers):
        """
        Try to log in using the given login value and password.
        """
        login_fields = unique_items(login_fields)

        try:
            login_form_response = self.client.get(
                LOGIN_PATH,
                name=f"{role_name}: GET Login Form",
                allow_redirects=True
            )

            hidden_inputs = extract_hidden_inputs(login_form_response.text)

        except Exception:
            hidden_inputs = {}

        role_name_lower = role_name.lower()

        role_variants = [
            {},
            {"role": role_name_lower},
            {"user_type": role_name_lower},
            {"account_type": role_name_lower},
        ]

        for field_name in login_fields:
            for role_extra in role_variants:
                payload = hidden_inputs.copy()
                payload.update(role_extra)

                payload[field_name] = login_value
                payload[PASSWORD_FIELD] = password

                with self.client.post(
                    LOGIN_PATH,
                    data=payload,
                    name=f"{role_name}: POST Login",
                    allow_redirects=True,
                    catch_response=True
                ) as response:

                    if self.login_successful(response, success_markers):
                        response.success()
                        print(f"[{role_name}] Login successful using field: {field_name}")
                        return

                    response.success()

        with self.client.get(
            LOGIN_PATH,
            name=f"{role_name}: LOGIN FAILED",
            catch_response=True
        ) as response:
            response.failure(
                f"{role_name} login failed. "
                f"Check login route, field names, or credentials."
            )

        raise StopUser()

    def discover_pages(self, page_candidates, group_name):
        """
        Finds the first working route for each page.

        Wrong route options are ignored so your load test focuses on
        actual working pages instead of filling the result table with 404s.
        """
        working_pages = []
        used_paths = set()

        for page_name, candidate_paths in page_candidates:
            selected_page = None

            for candidate_path in candidate_paths:
                candidate_path = clean_path(candidate_path)

                with self.client.get(
                    candidate_path,
                    name=f"DISCOVER {group_name}: {page_name}",
                    allow_redirects=True,
                    catch_response=True
                ) as response:

                    final_path = response_path(response)
                    status_code = response.status_code

                    is_login_page = self.is_login_path(final_path)
                    page_is_actual_login_page = "login" in page_name.lower()

                    if status_code == 200:
                        if page_is_actual_login_page or not is_login_page:
                            selected_page = (final_path, page_name)
                            response.success()
                            break

                    # If the route exists but returns a server/permission error,
                    # keep it so the real load test can show the issue clearly.
                    if status_code in [403, 500]:
                        selected_page = (candidate_path, page_name)
                        response.success()
                        break

                    response.success()

            if selected_page:
                selected_path, selected_name = selected_page

                if selected_path not in used_paths:
                    working_pages.append((selected_path, selected_name))
                    used_paths.add(selected_path)
                    print(f"[{group_name}] Using {selected_name}: {selected_path}")
            else:
                print(f"[{group_name}] No working route found for: {page_name}")

        return working_pages

    def get_checked_page(self, path, name):
        """
        Load a page and mark redirects/errors as failures.

        This is important because a protected page can redirect to /login.
        Without this check, Locust may count that redirect as success.
        """
        with self.client.get(
            path,
            name=name,
            allow_redirects=False,
            catch_response=True
        ) as response:

            if response.status_code == 200:
                response.success()
                return

            if response.status_code in REDIRECT_STATUS_CODES:
                location = response.headers.get("Location", "")
                response.failure(
                    f"Redirected with HTTP {response.status_code} to {location}"
                )
                return

            response.failure(f"HTTP {response.status_code}")


# ============================================================
# PUBLIC VISITOR
# Tests pages that do not require login.
# ============================================================

class PublicVisitor(BaseWebsiteUser):
    weight = 2

    def on_start(self):
        self.pages = self.discover_pages(
            PUBLIC_PAGE_CANDIDATES,
            "PUBLIC"
        )

        if not self.pages:
            print("[PUBLIC] No public pages found.")
            raise StopUser()

    @task
    def visit_public_page(self):
        path, name = random.choice(self.pages)
        self.get_checked_page(path, name)


# ============================================================
# CITIZEN / NORMAL USER
# Logs in using NIC and tests user pages.
# ============================================================

class CitizenPortalUser(BaseWebsiteUser):
    weight = 5

    def on_start(self):
        self.login_as(
            login_value=CITIZEN_LOGIN_VALUE,
            password=CITIZEN_PASSWORD,
            login_fields=CITIZEN_LOGIN_FIELDS,
            role_name="CITIZEN",
            success_markers=[
                "citizen portal",
                "niman",
                "my applications",
                "support documents",
                "land valuation",
            ],
        )

        self.pages = self.discover_pages(
            CITIZEN_PAGE_CANDIDATES,
            "CITIZEN"
        )

        if not self.pages:
            print("[CITIZEN] Login may have failed or no citizen routes were found.")
            raise StopUser()

    @task
    def visit_citizen_page(self):
        path, name = random.choice(self.pages)
        self.get_checked_page(path, name)


# ============================================================
# ADMIN USER
# Logs in using employee ID and tests admin pages.
# ============================================================

class AdminPortalUser(BaseWebsiteUser):
    weight = 2

    def on_start(self):
        self.login_as(
            login_value=ADMIN_LOGIN_VALUE,
            password=ADMIN_PASSWORD,
            login_fields=ADMIN_LOGIN_FIELDS,
            role_name="ADMIN",
            success_markers=[
                "admin portal",
                "system admin",
                "user management",
                "planning applications",
                "suspicious behavior",
            ],
        )

        self.pages = self.discover_pages(
            ADMIN_PAGE_CANDIDATES,
            "ADMIN"
        )

        if not self.pages:
            print("[ADMIN] Login may have failed or no admin routes were found.")
            raise StopUser()

    @task
    def visit_admin_page(self):
        path, name = random.choice(self.pages)
        self.get_checked_page(path, name)