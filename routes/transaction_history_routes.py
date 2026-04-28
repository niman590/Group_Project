import os
from functools import wraps

from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    session,
    redirect,
    url_for,
    flash,
)

from werkzeug.utils import secure_filename
from database.db_connection import get_connection
from database.security_utils import track_api_request_burst, log_suspicious_event


transaction_history_bp = Blueprint("transaction_history", __name__)

UPLOAD_FOLDER = "static/uploads/history_proofs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def user_login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            if request.is_json or request.path.startswith("/api/"):
                return jsonify({
                    "success": False,
                    "message": "Please log in first."
                }), 401

            flash("Please log in first.", "error")
            return redirect(url_for("auth.login"))

        return view_func(*args, **kwargs)

    return wrapper


def admin_login_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in first.", "error")
            return redirect(url_for("auth.login"))

        if not session.get("is_admin"):
            flash("You are not allowed to access this action.", "error")
            return redirect(url_for("user.user_dashboard"))

        return view_func(*args, **kwargs)

    return wrapper


@transaction_history_bp.after_request
def add_transaction_history_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@transaction_history_bp.route("/transaction-history", methods=["GET"])
@user_login_required
def transaction_history_page():
    return render_template("transaction_history.html", active_page="transaction_history")


@transaction_history_bp.route("/get-transaction-history", methods=["POST"])
@user_login_required
def get_transaction_history():
    track_api_request_burst(limit=10, minutes=1)

    data = request.get_json() or {}
    deed_number = data.get("deed_number")

    if not deed_number:
        return jsonify({"error": "Please enter a deed number."}), 400

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT land_id, deed_number, property_address, location, current_owner_name
        FROM land_record
        WHERE deed_number = ?
        """,
        (deed_number,),
    )
    land = cursor.fetchone()

    if not land:
        conn.close()

        log_suspicious_event(
            user_id=session.get("user_id"),
            rule_name="INVALID_TRANSACTION_LOOKUP",
            severity="low",
            event_type="transaction",
            route=request.path,
            ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
            user_agent=request.headers.get("User-Agent"),
            description=f"Transaction history lookup attempted with invalid deed number: {deed_number}",
        )

        return jsonify({"error": "No land record found for this deed number."}), 404

    land_id = land[0]

    cursor.execute(
        """
        SELECT owner_name, owner_nic, owner_address, owner_phone, transfer_date, transaction_type, ownership_order
        FROM ownership_history
        WHERE land_id = ?
        ORDER BY ownership_order ASC
        """,
        (land_id,),
    )
    history_rows = cursor.fetchall()

    conn.close()

    history = []
    for row in history_rows:
        history.append({
            "owner_name": row[0],
            "owner_nic": row[1],
            "owner_address": row[2],
            "owner_phone": row[3],
            "transfer_date": row[4],
            "transaction_type": row[5],
            "ownership_order": row[6],
        })

    return jsonify({
        "deed_number": land[1],
        "property_address": land[2],
        "location": land[3],
        "current_owner_name": land[4],
        "history": history,
    })


@transaction_history_bp.route("/request-transaction-history-update", methods=["POST"])
@user_login_required
def request_transaction_history_update():
    track_api_request_burst(limit=5, minutes=1)

    deed_number = request.form.get("deed_number")
    proposed_owner_name = request.form.get("proposed_owner_name")
    proposed_owner_nic = request.form.get("proposed_owner_nic")
    proposed_owner_address = request.form.get("proposed_owner_address")
    proposed_owner_phone = request.form.get("proposed_owner_phone")
    proposed_transfer_date = request.form.get("proposed_transfer_date")
    proposed_transaction_type = request.form.get("proposed_transaction_type")
    notes = request.form.get("notes")

    proof_file = request.files.get("proof_document")

    if not deed_number or not proposed_owner_name or not proposed_transfer_date or not proposed_transaction_type:
        return jsonify({"error": "Please fill all required fields."}), 400

    proof_path = None

    if proof_file and proof_file.filename:
        filename = secure_filename(proof_file.filename)

        if not filename.lower().endswith(".pdf"):
            return jsonify({"error": "Only PDF proof documents are allowed."}), 400

        timestamped_filename = f"{session.get('user_id')}_{filename}"
        proof_path = os.path.join(UPLOAD_FOLDER, timestamped_filename)
        proof_file.save(proof_path)

    user_id = session.get("user_id")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT land_id
        FROM land_record
        WHERE deed_number = ?
        """,
        (deed_number,),
    )
    land = cursor.fetchone()

    if land:
        request_type = "EXISTING_DEED_UPDATE"
        request_note = notes
        response_message = "Update request submitted successfully and is pending admin approval."
    else:
        request_type = "NEW_DEED_REQUEST"
        request_note = f"[NEW DEED NUMBER REQUEST] This deed number is not currently in the system.\n\n{notes or ''}"
        response_message = "New deed number request submitted successfully and is pending admin approval."

    cursor.execute(
        """
        INSERT INTO transaction_history_update_request
        (
            user_id,
            deed_number,
            proposed_owner_name,
            proposed_owner_nic,
            proposed_owner_address,
            proposed_owner_phone,
            proposed_transfer_date,
            proposed_transaction_type,
            notes,
            proof_document_path,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
        """,
        (
            user_id,
            deed_number,
            proposed_owner_name,
            proposed_owner_nic,
            proposed_owner_address,
            proposed_owner_phone,
            proposed_transfer_date,
            proposed_transaction_type,
            request_note,
            proof_path,
        ),
    )

    conn.commit()
    conn.close()

    if request_type == "NEW_DEED_REQUEST":
        log_suspicious_event(
            user_id=session.get("user_id"),
            rule_name="NEW_DEED_NUMBER_REQUEST",
            severity="low",
            event_type="transaction",
            route=request.path,
            ip_address=request.headers.get("X-Forwarded-For", request.remote_addr),
            user_agent=request.headers.get("User-Agent"),
            description=f"User requested transaction update for deed number not yet in system: {deed_number}",
        )

    return jsonify({"message": response_message})


@transaction_history_bp.route("/admin/delete-approved-transaction/<int:request_id>", methods=["POST"])
@admin_login_required
def delete_approved_transaction(request_id):
    track_api_request_burst(limit=5, minutes=1)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT status
        FROM transaction_history_update_request
        WHERE request_id = ?
        """,
        (request_id,),
    )
    request_row = cursor.fetchone()

    if not request_row:
        conn.close()
        flash("Transaction request not found.", "error")
        return redirect(url_for("admin.admin_transaction_history_requests"))

    if request_row["status"] != "Approved":
        conn.close()
        flash("Only approved transactions can be deleted.", "warning")
        return redirect(url_for("admin.admin_transaction_history_requests"))

    cursor.execute(
        """
        DELETE FROM transaction_history_update_request
        WHERE request_id = ? AND status = 'Approved'
        """,
        (request_id,),
    )

    conn.commit()
    conn.close()

    flash("Approved transaction deleted successfully.", "success")
    return redirect(url_for("admin.admin_transaction_history_requests"))