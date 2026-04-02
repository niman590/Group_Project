import os
from flask import Blueprint, render_template, request, jsonify, session, redirect, url_for, flash
from werkzeug.utils import secure_filename
from database.db_connection import get_connection

transaction_history_bp = Blueprint("transaction_history", __name__)

UPLOAD_FOLDER = "static/uploads/history_proofs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@transaction_history_bp.route("/transaction-history", methods=["GET"])
def transaction_history_page():
    return render_template("transaction_history.html", active_page="transaction_history")


@transaction_history_bp.route("/get-transaction-history", methods=["POST"])
def get_transaction_history():
    data = request.get_json()
    deed_number = data.get("deed_number")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT land_id, deed_number, property_address, location, current_owner_name
        FROM land_record
        WHERE deed_number = ?
    """, (deed_number,))
    land = cursor.fetchone()

    if not land:
        conn.close()
        return jsonify({"error": "No land record found for this deed number."})

    land_id = land[0]

    cursor.execute("""
        SELECT owner_name, owner_nic, owner_address, owner_phone, transfer_date, transaction_type, ownership_order
        FROM ownership_history
        WHERE land_id = ?
        ORDER BY ownership_order ASC
    """, (land_id,))
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
            "ownership_order": row[6]
        })

    return jsonify({
        "deed_number": land[1],
        "property_address": land[2],
        "location": land[3],
        "current_owner_name": land[4],
        "history": history
    })


@transaction_history_bp.route("/request-transaction-history-update", methods=["POST"])
def request_transaction_history_update():
    deed_number = request.form.get("deed_number")
    proposed_owner_name = request.form.get("proposed_owner_name")
    proposed_owner_nic = request.form.get("proposed_owner_nic")
    proposed_owner_address = request.form.get("proposed_owner_address")
    proposed_owner_phone = request.form.get("proposed_owner_phone")
    proposed_transfer_date = request.form.get("proposed_transfer_date")
    proposed_transaction_type = request.form.get("proposed_transaction_type")
    notes = request.form.get("notes")

    proof_file = request.files.get("proof_document")

    proof_path = None
    if proof_file and proof_file.filename:
        filename = secure_filename(proof_file.filename)
        proof_path = os.path.join(UPLOAD_FOLDER, filename)
        proof_file.save(proof_path)

    user_id = session.get("user_id", 1)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT land_id FROM land_record WHERE deed_number = ?", (deed_number,))
    land = cursor.fetchone()

    if not land:
        conn.close()
        return jsonify({"error": "Invalid deed number. No matching land found."})

    cursor.execute("""
        INSERT INTO transaction_history_update_request
        (
            user_id, deed_number, proposed_owner_name, proposed_owner_nic,
            proposed_owner_address, proposed_owner_phone, proposed_transfer_date,
            proposed_transaction_type, notes, proof_document_path, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
    """, (
        user_id,
        deed_number,
        proposed_owner_name,
        proposed_owner_nic,
        proposed_owner_address,
        proposed_owner_phone,
        proposed_transfer_date,
        proposed_transaction_type,
        notes,
        proof_path
    ))

    conn.commit()
    conn.close()

    return jsonify({"message": "Update request submitted successfully and is pending admin approval."})


@transaction_history_bp.route("/admin/delete-approved-transaction/<int:request_id>", methods=["POST"])
def delete_approved_transaction(request_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT status
        FROM transaction_history_update_request
        WHERE request_id = ?
    """, (request_id,))
    request_row = cursor.fetchone()

    if not request_row:
        conn.close()
        flash("Transaction request not found.", "error")
        return redirect(url_for("admin.admin_transaction_history_requests"))

    if request_row[0] != "Approved":
        conn.close()
        flash("Only approved transactions can be deleted.", "warning")
        return redirect(url_for("admin.admin_transaction_history_requests"))

    cursor.execute("""
        DELETE FROM transaction_history_update_request
        WHERE request_id = ? AND status = 'Approved'
    """, (request_id,))

    conn.commit()
    conn.close()

    flash("Approved transaction deleted successfully.", "success")
    return redirect(url_for("admin.admin_transaction_history_requests"))