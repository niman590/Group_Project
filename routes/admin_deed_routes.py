from datetime import datetime

from flask import flash, redirect, render_template, request, url_for

from database.db_connection import get_connection
from database.security_utils import track_api_request_burst
from routes.admin_routes import admin_bp, admin_required


NEW_DEED_NOTE_MARKERS = [
    "[NEW_DEED_REQUEST]",
    "[NEW DEED REQUEST]",
    "[NEW DEED NUMBER REQUEST]",
    "This deed number is not currently in the system.",
    "not currently in the system",
]


def clean_request_note(raw_note):
    note = (raw_note or "").strip()

    replacements = [
        "[NEW_DEED_REQUEST]",
        "[NEW DEED REQUEST]",
        "[NEW DEED NUMBER REQUEST]",
        "This deed number is not currently in the system.",
    ]

    for text in replacements:
        note = note.replace(text, "")

    return note.strip()


def is_new_deed_number_request(req):
    status = (req["status"] or "").strip()
    notes = (req["notes"] or "").strip()

    if status == "Pending New Deed Review":
        return True

    lowered_notes = notes.lower()

    for marker in NEW_DEED_NOTE_MARKERS:
        if marker.lower() in lowered_notes:
            return True

    return False


def get_next_ownership_order(cursor, land_id):
    cursor.execute(
        """
        SELECT COALESCE(MAX(ownership_order), 0) AS max_order
        FROM ownership_history
        WHERE land_id = ?
        """,
        (land_id,),
    )

    row = cursor.fetchone()

    if not row:
        return 1

    return int(row["max_order"] or 0) + 1


def insert_ownership_history(
    cursor,
    land_id,
    owner_name,
    owner_nic,
    owner_address,
    owner_phone,
    transfer_date,
    transaction_type,
    ownership_order,
):
    cursor.execute(
        """
        INSERT INTO ownership_history (
            land_id,
            owner_name,
            owner_nic,
            owner_address,
            owner_phone,
            transfer_date,
            transaction_type,
            ownership_order
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            land_id,
            owner_name,
            owner_nic,
            owner_address,
            owner_phone,
            transfer_date,
            transaction_type,
            ownership_order,
        ),
    )


def create_new_land_record_from_request(cursor, req):
    deed_number = (req["deed_number"] or "").strip()
    proposed_owner_name = (req["proposed_owner_name"] or "").strip()
    proposed_owner_address = (req["proposed_owner_address"] or "").strip()

    property_address = proposed_owner_address or "Address to be verified"
    location = proposed_owner_address or "Location to be verified"

    cursor.execute(
        """
        INSERT INTO land_record (
            deed_number,
            property_address,
            location,
            current_owner_name
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            deed_number,
            property_address,
            location,
            proposed_owner_name,
        ),
    )

    return cursor.lastrowid


@admin_bp.route("/admin/transaction-history-requests")
def admin_transaction_history_requests():
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM transaction_history_update_request
        ORDER BY submitted_at DESC
        """
    )

    requests = cursor.fetchall()
    conn.close()

    return render_template(
        "admin_transaction_history_requests.html",
        user=admin_user,
        requests=requests,
        active_page="transaction_requests",
    )


@admin_bp.route("/admin/transaction-history-request/<int:request_id>/approve", methods=["POST"])
def approve_transaction_history_request(request_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM transaction_history_update_request
        WHERE request_id = ?
          AND status IN ('Pending', 'Pending New Deed Review')
        """,
        (request_id,),
    )

    req = cursor.fetchone()

    if not req:
        conn.close()
        flash("Request not found or already processed.", "error")
        return redirect(url_for("admin.admin_transaction_history_requests"))

    deed_number = (req["deed_number"] or "").strip()
    proposed_owner_name = (req["proposed_owner_name"] or "").strip()
    proposed_owner_nic = (req["proposed_owner_nic"] or "").strip()
    proposed_owner_address = (req["proposed_owner_address"] or "").strip()
    proposed_owner_phone = (req["proposed_owner_phone"] or "").strip()
    proposed_transfer_date = (req["proposed_transfer_date"] or "").strip()
    proposed_transaction_type = (req["proposed_transaction_type"] or "").strip() or "Transfer"

    if not deed_number:
        conn.close()
        flash("Cannot approve request because deed number is missing.", "error")
        return redirect(url_for("admin.admin_transaction_history_requests"))

    if not proposed_owner_name:
        conn.close()
        flash("Cannot approve request because proposed owner name is missing.", "error")
        return redirect(url_for("admin.admin_transaction_history_requests"))

    if not proposed_transfer_date:
        conn.close()
        flash("Cannot approve request because transfer date is missing.", "error")
        return redirect(url_for("admin.admin_transaction_history_requests"))

    reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        """
        SELECT land_id
        FROM land_record
        WHERE deed_number = ?
        """,
        (deed_number,),
    )

    existing_land = cursor.fetchone()
    new_deed_request = is_new_deed_number_request(req)

    try:
        if existing_land:
            land_id = existing_land["land_id"]
            ownership_order = get_next_ownership_order(cursor, land_id)

            insert_ownership_history(
                cursor=cursor,
                land_id=land_id,
                owner_name=proposed_owner_name,
                owner_nic=proposed_owner_nic,
                owner_address=proposed_owner_address,
                owner_phone=proposed_owner_phone,
                transfer_date=proposed_transfer_date,
                transaction_type=proposed_transaction_type,
                ownership_order=ownership_order,
            )

            cursor.execute(
                """
                UPDATE land_record
                SET current_owner_name = ?
                WHERE land_id = ?
                """,
                (proposed_owner_name, land_id),
            )

            success_message = "Current deed transaction request approved successfully."

        else:
            if not new_deed_request:
                conn.close()
                flash(
                    "No matching deed number was found. This request was not marked as a new deed number request.",
                    "error",
                )
                return redirect(url_for("admin.admin_transaction_history_requests"))

            land_id = create_new_land_record_from_request(cursor, req)

            final_transaction_type = proposed_transaction_type
            if not final_transaction_type or final_transaction_type == "Transfer":
                final_transaction_type = "New Registration"

            insert_ownership_history(
                cursor=cursor,
                land_id=land_id,
                owner_name=proposed_owner_name,
                owner_nic=proposed_owner_nic,
                owner_address=proposed_owner_address,
                owner_phone=proposed_owner_phone,
                transfer_date=proposed_transfer_date,
                transaction_type=final_transaction_type,
                ownership_order=1,
            )

            success_message = (
                "New deed number approved successfully. "
                "A new deed record was created and added to ownership history."
            )

        cursor.execute(
            """
            UPDATE transaction_history_update_request
            SET status = 'Approved',
                reviewed_by = ?,
                reviewed_at = ?,
                admin_comment = ?
            WHERE request_id = ?
            """,
            (
                admin_user["user_id"],
                reviewed_at,
                "Approved by admin",
                request_id,
            ),
        )

        conn.commit()
        flash(success_message, "success")

    except Exception as e:
        conn.rollback()
        flash(f"Failed to approve request: {str(e)}", "error")

    finally:
        conn.close()

    return redirect(url_for("admin.admin_transaction_history_requests"))


@admin_bp.route("/admin/transaction-history-request/<int:request_id>/reject", methods=["POST"])
def reject_transaction_history_request(request_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    admin_comment = (request.form.get("admin_comment") or "").strip()

    if not admin_comment:
        flash("Please enter a reason for rejection.", "error")
        return redirect(url_for("admin.admin_transaction_history_requests"))

    conn = get_connection()
    cursor = conn.cursor()
    reviewed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute(
        """
        UPDATE transaction_history_update_request
        SET status = 'Rejected',
            reviewed_by = ?,
            reviewed_at = ?,
            admin_comment = ?
        WHERE request_id = ?
          AND status IN ('Pending', 'Pending New Deed Review')
        """,
        (
            admin_user["user_id"],
            reviewed_at,
            admin_comment,
            request_id,
        ),
    )

    if cursor.rowcount == 0:
        conn.rollback()
        conn.close()
        flash("Request not found or already processed.", "error")
        return redirect(url_for("admin.admin_transaction_history_requests"))

    conn.commit()
    conn.close()

    flash("Transaction history request rejected.", "warning")
    return redirect(url_for("admin.admin_transaction_history_requests"))


@admin_bp.route("/admin/add-deed", methods=["GET"])
def admin_add_deed_page():
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    return render_template(
        "admin_add_deed.html",
        user=admin_user,
        active_page="add_deed",
    )


@admin_bp.route("/admin/add-deed", methods=["POST"])
def admin_add_deed():
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    track_api_request_burst(limit=10, minutes=1)

    deed_number = (request.form.get("deed_number") or "").strip()
    property_address = (request.form.get("property_address") or "").strip()
    location = (request.form.get("location") or "").strip()

    owner_names = [v.strip() for v in request.form.getlist("owner_name[]")]
    owner_nics = [v.strip() for v in request.form.getlist("owner_nic[]")]
    owner_addresses = [v.strip() for v in request.form.getlist("owner_address[]")]
    owner_phones = [v.strip() for v in request.form.getlist("owner_phone[]")]
    transfer_dates = [v.strip() for v in request.form.getlist("transfer_date[]")]
    transaction_types = [v.strip() for v in request.form.getlist("transaction_type[]")]

    if not deed_number:
        flash("Deed number is required.", "error")
        return redirect(url_for("admin.admin_add_deed_page"))

    if not property_address:
        flash("Property address is required.", "error")
        return redirect(url_for("admin.admin_add_deed_page"))

    if not location:
        flash("Location is required.", "error")
        return redirect(url_for("admin.admin_add_deed_page"))

    if not owner_names or all(not name for name in owner_names):
        flash("At least one owner is required.", "error")
        return redirect(url_for("admin.admin_add_deed_page"))

    total_rows = len(owner_names)

    if not (
        len(owner_nics) == total_rows
        and len(owner_addresses) == total_rows
        and len(owner_phones) == total_rows
        and len(transfer_dates) == total_rows
        and len(transaction_types) == total_rows
    ):
        flash("Owner rows are incomplete. Please check all transaction rows.", "error")
        return redirect(url_for("admin.admin_add_deed_page"))

    cleaned_history = []

    for index in range(total_rows):
        if not owner_names[index]:
            flash(f"Owner name is required for row {index + 1}.", "error")
            return redirect(url_for("admin.admin_add_deed_page"))

        if not transfer_dates[index]:
            flash(f"Transfer date is required for row {index + 1}.", "error")
            return redirect(url_for("admin.admin_add_deed_page"))

        transaction_type = transaction_types[index]
        if not transaction_type:
            transaction_type = "Original Registration" if index == 0 else "Transfer"

        cleaned_history.append(
            {
                "owner_name": owner_names[index],
                "owner_nic": owner_nics[index],
                "owner_address": owner_addresses[index],
                "owner_phone": owner_phones[index],
                "transfer_date": transfer_dates[index],
                "transaction_type": transaction_type,
                "ownership_order": index + 1,
            }
        )

    current_owner_name = cleaned_history[-1]["owner_name"]

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

    existing_land = cursor.fetchone()

    if existing_land:
        conn.close()
        flash("This deed number already exists in the system.", "error")
        return redirect(url_for("admin.admin_add_deed_page"))

    try:
        cursor.execute(
            """
            INSERT INTO land_record (
                deed_number,
                property_address,
                location,
                current_owner_name
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                deed_number,
                property_address,
                location,
                current_owner_name,
            ),
        )

        land_id = cursor.lastrowid

        for row in cleaned_history:
            insert_ownership_history(
                cursor=cursor,
                land_id=land_id,
                owner_name=row["owner_name"],
                owner_nic=row["owner_nic"],
                owner_address=row["owner_address"],
                owner_phone=row["owner_phone"],
                transfer_date=row["transfer_date"],
                transaction_type=row["transaction_type"],
                ownership_order=row["ownership_order"],
            )

        conn.commit()
        flash("New deed with ownership history added successfully.", "success")

    except Exception as e:
        conn.rollback()
        flash(f"Failed to add deed: {str(e)}", "error")

    finally:
        conn.close()

    return redirect(url_for("admin.admin_add_deed_page"))
