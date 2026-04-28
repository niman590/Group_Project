from flask import flash, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

from database.db_connection import get_connection
from routes.admin_routes import (
    admin_bp,
    admin_required,
    is_protected_system_admin,
    is_strong_password,
    is_valid_employee_id,
    is_valid_nic,
    is_valid_phone,
    normalize_employee_id,
    safe_fetchone_value,
)


@admin_bp.route("/admin/users")
def admin_users():
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    search_query = request.args.get("search", "").strip()

    conn = get_connection()
    cursor = conn.cursor()

    total_users = safe_fetchone_value(
        cursor,
        "SELECT COUNT(*) AS total_users FROM users",
        "total_users"
    )

    total_admins = safe_fetchone_value(
        cursor,
        "SELECT COUNT(*) AS total_admins FROM users WHERE is_admin = 1",
        "total_admins"
    )

    active_users = safe_fetchone_value(
        cursor,
        "SELECT COUNT(*) AS active_users FROM users WHERE is_active = 1",
        "active_users"
    )

    inactive_users = safe_fetchone_value(
        cursor,
        "SELECT COUNT(*) AS inactive_users FROM users WHERE is_active = 0",
        "inactive_users"
    )

    if search_query:
        like_term = f"%{search_query}%"

        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE (
                first_name || ' ' || last_name LIKE ?
                OR first_name LIKE ?
                OR last_name LIKE ?
                OR nic LIKE ?
                OR email LIKE ?
                OR employee_id LIKE ?
            )
            ORDER BY user_id ASC
            """,
            (
                like_term,
                like_term,
                like_term,
                like_term,
                like_term,
                like_term,
            ),
        )
    else:
        cursor.execute(
            """
            SELECT *
            FROM users
            ORDER BY user_id ASC
            """
        )

    users = cursor.fetchall()
    conn.close()

    return render_template(
        "admin_user_management.html",
        user=admin_user,
        users=users,
        search_query=search_query,
        total_users=total_users,
        total_admins=total_admins,
        active_users=active_users,
        inactive_users=inactive_users,
        active_page="user_management",
    )


@admin_bp.route("/admin/users/create-admin", methods=["POST"])
def create_admin_user():
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    first_name = request.form.get("first_name", "").strip()
    last_name = request.form.get("last_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    phone_number = request.form.get("phone_number", "").strip()
    address = request.form.get("address", "").strip()
    city = request.form.get("city", "").strip()

    birth_month = request.form.get("birth_month", "").strip()
    birth_day = request.form.get("birth_day", "").strip()
    birth_year = request.form.get("birth_year", "").strip()

    date_of_birth = ""
    if birth_year and birth_month and birth_day:
        date_of_birth = f"{birth_year}-{birth_month}-{birth_day}"

    nic = request.form.get("nic", "").strip().upper()
    employee_id = normalize_employee_id(request.form.get("employee_id"))
    password = request.form.get("password", "").strip()
    confirm_password = request.form.get("confirm_password", "").strip()

    if (
        not first_name
        or not last_name
        or not email
        or not nic
        or not employee_id
        or not password
        or not confirm_password
    ):
        flash("Please fill all required admin fields.", "error")
        return redirect(url_for("admin.admin_users"))

    if not is_valid_nic(nic):
        flash("NIC must be either 9 digits followed by V/X or 12 digits.", "error")
        return redirect(url_for("admin.admin_users"))

    if not is_valid_employee_id(employee_id):
        flash(
            "Employee ID must be 3 to 30 characters and use only letters, numbers, hyphens, underscores, or slashes.",
            "error",
        )
        return redirect(url_for("admin.admin_users"))

    if not is_valid_phone(phone_number):
        flash("Phone number must contain exactly 10 digits.", "error")
        return redirect(url_for("admin.admin_users"))

    if not is_strong_password(password):
        flash(
            "Password must be at least 8 characters and include uppercase, lowercase, number, and symbol.",
            "error",
        )
        return redirect(url_for("admin.admin_users"))

    if password != confirm_password:
        flash("Passwords do not match.", "error")
        return redirect(url_for("admin.admin_users"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT user_id
        FROM users
        WHERE nic = ?
        """,
        (nic,),
    )
    if cursor.fetchone():
        conn.close()
        flash("NIC is already registered.", "error")
        return redirect(url_for("admin.admin_users"))

    cursor.execute(
        """
        SELECT user_id
        FROM users
        WHERE LOWER(email) = LOWER(?)
        """,
        (email,),
    )
    if cursor.fetchone():
        conn.close()
        flash("Email is already registered.", "error")
        return redirect(url_for("admin.admin_users"))

    cursor.execute(
        """
        SELECT user_id
        FROM users
        WHERE employee_id = ?
        """,
        (employee_id,),
    )
    if cursor.fetchone():
        conn.close()
        flash("Employee ID is already in use.", "error")
        return redirect(url_for("admin.admin_users"))

    password_hash = generate_password_hash(password)

    cursor.execute(
        """
        INSERT INTO users (
            first_name,
            last_name,
            phone_number,
            email,
            password_hash,
            date_of_birth,
            address,
            city,
            nic,
            employee_id,
            is_admin,
            is_active
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1)
        """,
        (
            first_name,
            last_name,
            phone_number,
            email,
            password_hash,
            date_of_birth if date_of_birth else None,
            address,
            city,
            nic,
            employee_id,
        ),
    )

    conn.commit()
    conn.close()

    flash("Admin account created successfully.", "success")
    return redirect(url_for("admin.admin_users"))


@admin_bp.route("/admin/users/<int:user_id>/toggle-status", methods=["POST"])
def toggle_user_status(user_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    if admin_user["user_id"] == user_id:
        flash("You cannot deactivate your own admin account.", "error")
        return redirect(url_for("admin.admin_users"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE user_id = ?
        """,
        (user_id,),
    )
    target_user = cursor.fetchone()

    if not target_user:
        conn.close()
        flash("User not found.", "error")
        return redirect(url_for("admin.admin_users"))

    if is_protected_system_admin(target_user):
        conn.close()
        flash("System Admin account cannot be deactivated or changed.", "error")
        return redirect(url_for("admin.admin_users"))

    new_status = 0 if target_user["is_active"] else 1

    cursor.execute(
        """
        UPDATE users
        SET is_active = ?
        WHERE user_id = ?
        """,
        (new_status, user_id),
    )

    conn.commit()
    conn.close()

    flash("User account status updated successfully.", "success")
    return redirect(url_for("admin.admin_users"))


@admin_bp.route("/admin/users/<int:user_id>/make-admin", methods=["POST"])
def make_admin(user_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    employee_id = normalize_employee_id(request.form.get("employee_id"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE user_id = ?
        """,
        (user_id,),
    )
    target_user = cursor.fetchone()

    if not target_user:
        conn.close()
        flash("User not found.", "error")
        return redirect(url_for("admin.admin_users"))

    if is_protected_system_admin(target_user):
        conn.close()
        flash("System Admin account is already protected.", "error")
        return redirect(url_for("admin.admin_users"))

    if target_user["is_admin"]:
        conn.close()
        flash("This user is already an admin.", "info")
        return redirect(url_for("admin.admin_users"))

    if not employee_id:
        conn.close()
        flash("Employee ID is required to promote a user to admin.", "error")
        return redirect(url_for("admin.admin_users"))

    if not is_valid_employee_id(employee_id):
        conn.close()
        flash(
            "Employee ID must be 3 to 30 characters and use only letters, numbers, hyphens, underscores, or slashes.",
            "error",
        )
        return redirect(url_for("admin.admin_users"))

    cursor.execute(
        """
        SELECT user_id
        FROM users
        WHERE employee_id = ?
          AND user_id != ?
        """,
        (employee_id, user_id),
    )
    existing_employee = cursor.fetchone()

    if existing_employee:
        conn.close()
        flash("Employee ID is already assigned to another account.", "error")
        return redirect(url_for("admin.admin_users"))

    cursor.execute(
        """
        UPDATE users
        SET is_admin = 1,
            employee_id = ?
        WHERE user_id = ?
        """,
        (employee_id, user_id),
    )

    conn.commit()
    conn.close()

    flash("User promoted to admin successfully.", "success")
    return redirect(url_for("admin.admin_users"))


@admin_bp.route("/admin/users/<int:user_id>/remove-admin", methods=["POST"])
def remove_admin(user_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    if admin_user["user_id"] == user_id:
        flash("You cannot remove your own admin access.", "error")
        return redirect(url_for("admin.admin_users"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE user_id = ?
        """,
        (user_id,),
    )
    target_user = cursor.fetchone()

    if not target_user:
        conn.close()
        flash("User not found.", "error")
        return redirect(url_for("admin.admin_users"))

    if is_protected_system_admin(target_user):
        conn.close()
        flash("System Admin admin rights cannot be removed.", "error")
        return redirect(url_for("admin.admin_users"))

    if not target_user["is_admin"]:
        conn.close()
        flash("This user is not an admin.", "warning")
        return redirect(url_for("admin.admin_users"))

    cursor.execute(
        """
        UPDATE users
        SET is_admin = 0,
            employee_id = NULL
        WHERE user_id = ?
        """,
        (user_id,),
    )

    conn.commit()
    conn.close()

    flash("Admin access removed successfully.", "success")
    return redirect(url_for("admin.admin_users"))


@admin_bp.route("/admin/users/<int:user_id>/delete", methods=["POST"])
def delete_user(user_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    if admin_user["user_id"] == user_id:
        flash("You cannot delete your own admin account.", "error")
        return redirect(url_for("admin.admin_users"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE user_id = ?
        """,
        (user_id,),
    )
    target_user = cursor.fetchone()

    if not target_user:
        conn.close()
        flash("User not found.", "error")
        return redirect(url_for("admin.admin_users"))

    if is_protected_system_admin(target_user):
        conn.close()
        flash("System Admin account cannot be deleted.", "error")
        return redirect(url_for("admin.admin_users"))

    cursor.execute(
        """
        SELECT property_id
        FROM property
        WHERE owner_id = ?
        """,
        (user_id,),
    )
    property_ids = [row["property_id"] for row in cursor.fetchall()]

    if property_ids:
        placeholders = ",".join("?" for _ in property_ids)

        cursor.execute(
            f"DELETE FROM transaction_history WHERE property_id IN ({placeholders})",
            property_ids,
        )

        cursor.execute(
            f"DELETE FROM value_prediction WHERE property_id IN ({placeholders})",
            property_ids,
        )

        try:
            cursor.execute(
                f"DELETE FROM document WHERE property_id IN ({placeholders})",
                property_ids,
            )
        except Exception:
            pass

        cursor.execute(
            f"DELETE FROM property WHERE property_id IN ({placeholders})",
            property_ids,
        )

    try:
        cursor.execute(
            """
            DELETE FROM plan_case
            WHERE user_id = ?
            """,
            (user_id,),
        )
    except Exception:
        pass

    try:
        cursor.execute(
            """
            DELETE FROM document
            WHERE user_id = ?
            """,
            (user_id,),
        )
    except Exception:
        pass

    cursor.execute(
        """
        DELETE FROM users
        WHERE user_id = ?
        """,
        (user_id,),
    )

    conn.commit()
    conn.close()

    flash("User deleted successfully.", "success")
    return redirect(url_for("admin.admin_users"))