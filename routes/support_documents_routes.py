from functools import wraps
import os

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    session,
    flash,
    send_from_directory,
    abort,
    current_app,
    request,
    jsonify,
)

from database.db_connection import get_connection


support_documents_bp = Blueprint("support_documents", __name__)


def user_login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({
                    "success": False,
                    "message": "Please sign in first."
                }), 401

            flash("Please sign in first.", "error")
            return redirect(url_for("auth.login"))

        return view_func(*args, **kwargs)

    return wrapper


@support_documents_bp.after_request
def add_support_documents_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


def get_support_documents_folder():
    return os.path.join(current_app.root_path, "static", "support_documents")


def ensure_pdf_exists(filename, friendly_name):
    pdf_directory = get_support_documents_folder()
    pdf_path = os.path.join(pdf_directory, filename)

    if not os.path.exists(pdf_path):
        abort(404, description=f"{friendly_name} not found.")

    return pdf_directory


def get_support_documents_data():
    """
    Uses the existing project database only.
    No new database or table is created here.
    """

    conn = get_connection()
    cursor = conn.cursor()

    stats = {
        "documents_count": 0,
        "properties_count": 0,
        "transactions_count": 0,
        "cases_count": 0,
    }

    try:
        cursor.execute("SELECT COUNT(*) AS total FROM document")
        row = cursor.fetchone()
        stats["documents_count"] = row["total"] if row else 0
    except Exception:
        stats["documents_count"] = 0

    try:
        cursor.execute("SELECT COUNT(*) AS total FROM property")
        row = cursor.fetchone()
        stats["properties_count"] = row["total"] if row else 0
    except Exception:
        stats["properties_count"] = 0

    try:
        cursor.execute("SELECT COUNT(*) AS total FROM transaction_history")
        row = cursor.fetchone()
        stats["transactions_count"] = row["total"] if row else 0
    except Exception:
        stats["transactions_count"] = 0

    try:
        cursor.execute("SELECT COUNT(*) AS total FROM plan_case")
        row = cursor.fetchone()
        stats["cases_count"] = row["total"] if row else 0
    except Exception:
        stats["cases_count"] = 0

    conn.close()

    documents = [
        {
            "title": "Planning Approval Guidelines",
            "category": "Planning",
            "icon": "fa-file-lines",
            "description": "Guidance for citizens on how to prepare and submit planning approval applications correctly.",
            "audience": "Citizens",
            "status": "Available",
            "view_url": url_for("support_documents.view_planning_guidelines"),
            "download_url": url_for("support_documents.download_planning_guidelines"),
        },
        {
            "title": "Required Documents Checklist",
            "category": "Planning",
            "icon": "fa-list-check",
            "description": "Checklist of files and information needed before submitting planning approval requests.",
            "audience": "Citizens",
            "status": "Available",
            "view_url": url_for("support_documents.view_required_documents_checklist"),
            "download_url": url_for("support_documents.download_required_documents_checklist"),
        },
        {
            "title": "Gazettes, Rules and Policies",
            "category": "Policy",
            "icon": "fa-scale-balanced",
            "description": "Planning rules, approval policies, and official guidance relevant to land management.",
            "audience": "Citizens / Admin",
            "status": "Available",
            "view_url": url_for("support_documents.view_gazettes_and_rules"),
            "download_url": url_for("support_documents.download_gazettes_and_rules"),
        },
        {
            "title": "User Guide",
            "category": "Help",
            "icon": "fa-book-open",
            "description": "Guide for using dashboard modules such as profile, applications, valuation, and transaction history.",
            "audience": "Citizens",
            "status": "Project Deliverable",
            "view_url": url_for("support_documents.view_user_manual"),
            "download_url": url_for("support_documents.download_user_manual"),
        },
        {
            "title": "Administrator Guide",
            "category": "Admin",
            "icon": "fa-user-shield",
            "description": "Guide for approval workflows, record checks, monitoring, and document review tasks.",
            "audience": "Admin",
            "status": "Project Deliverable",
            "view_url": "",
            "download_url": "",
        },
        {
            "title": "Developer Manual",
            "category": "Technical",
            "icon": "fa-code",
            "description": "Technical documentation for code structure, modules, database usage, and maintenance.",
            "audience": "Developers",
            "status": "Project Deliverable",
            "view_url": "",
            "download_url": "",
        },
        {
            "title": "Transaction History Guide",
            "category": "Records",
            "icon": "fa-clock-rotate-left",
            "description": "Explains how ownership history and land transaction records are viewed and updated.",
            "audience": "Citizens",
            "status": "Available",
            "view_url": "",
            "download_url": "",
        },
        {
            "title": "Land Valuation Help Guide",
            "category": "Valuation",
            "icon": "fa-chart-line",
            "description": "Support document for understanding valuation inputs, outputs, and result interpretation.",
            "audience": "Citizens",
            "status": "Available",
            "view_url": "",
            "download_url": "",
        },
    ]

    return documents, stats


@support_documents_bp.route("/support_documents")
@support_documents_bp.route("/support-documents")
@user_login_required
def support_documents_page():
    documents, stats = get_support_documents_data()

    documents = [
        doc for doc in documents
        if doc.get("audience") not in ["Admin", "Developers"]
    ]

    return render_template(
        "support_documents.html",
        documents=documents,
        stats=stats,
        active_page="support_documents",
    )


@support_documents_bp.route("/support-documents/planning-approval-guidelines/view")
@user_login_required
def view_planning_guidelines():
    filename = "planning_approval_guidelines.pdf"
    directory = ensure_pdf_exists(filename, "Planning Approval Guidelines")

    return send_from_directory(directory, filename, as_attachment=False)


@support_documents_bp.route("/support-documents/planning-approval-guidelines/download")
@user_login_required
def download_planning_guidelines():
    filename = "planning_approval_guidelines.pdf"
    directory = ensure_pdf_exists(filename, "Planning Approval Guidelines")

    return send_from_directory(
        directory,
        filename,
        as_attachment=True,
        download_name="planning_approval_guidelines.pdf",
    )


@support_documents_bp.route("/support-documents/required-documents-checklist/view")
@user_login_required
def view_required_documents_checklist():
    filename = "required_documents_checklist.pdf"
    directory = ensure_pdf_exists(filename, "Required Documents Checklist")

    return send_from_directory(directory, filename, as_attachment=False)


@support_documents_bp.route("/support-documents/required-documents-checklist/download")
@user_login_required
def download_required_documents_checklist():
    filename = "required_documents_checklist.pdf"
    directory = ensure_pdf_exists(filename, "Required Documents Checklist")

    return send_from_directory(
        directory,
        filename,
        as_attachment=True,
        download_name="required_documents_checklist.pdf",
    )


@support_documents_bp.route("/support-documents/gazettes-and-rules/view")
@user_login_required
def view_gazettes_and_rules():
    filename = "gazettes_and_rules.pdf"
    directory = ensure_pdf_exists(filename, "Gazettes and Rules")

    return send_from_directory(directory, filename, as_attachment=False)


@support_documents_bp.route("/support-documents/gazettes-and-rules/download")
@user_login_required
def download_gazettes_and_rules():
    filename = "gazettes_and_rules.pdf"
    directory = ensure_pdf_exists(filename, "Gazettes and Rules")

    return send_from_directory(
        directory,
        filename,
        as_attachment=True,
        download_name="gazettes_and_rules.pdf",
    )


@support_documents_bp.route("/support-documents/user-manual/view")
@user_login_required
def view_user_manual():
    manual_filename = "civic_plan_user_manual.pdf"
    manual_directory = get_support_documents_folder()
    manual_path = os.path.join(manual_directory, manual_filename)

    if not os.path.exists(manual_path):
        abort(404, description="Civic Plan User Manual not found.")

    return send_from_directory(
        manual_directory,
        manual_filename,
        as_attachment=False,
    )


@support_documents_bp.route("/support-documents/user-manual/download")
@user_login_required
def download_user_manual():
    manual_filename = "civic_plan_user_manual.pdf"
    manual_directory = get_support_documents_folder()
    manual_path = os.path.join(manual_directory, manual_filename)

    if not os.path.exists(manual_path):
        abort(404, description="Civic Plan User Manual not found.")

    return send_from_directory(
        manual_directory,
        manual_filename,
        as_attachment=True,
        download_name="civic_plan_user_manual.pdf",
    )