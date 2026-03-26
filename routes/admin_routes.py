from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from database.db_connection import get_connection

admin_bp = Blueprint("admin", __name__)


def get_current_user():
    if "user_id" not in session:
        return None

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM users
        WHERE user_id = ?
    """, (session["user_id"],))
    user = cursor.fetchone()
    conn.close()
    return user


def admin_required():
    user = get_current_user()
    if not user:
        flash("Please sign in first.", "error")
        return None, redirect(url_for("auth.login"))

    if not user["is_admin"]:
        flash("Admin access only.", "error")
        return None, redirect(url_for("main.dashboard"))

    return user, None


@admin_bp.route("/admin/dashboard")
def admin_dashboard():
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    search_query = request.args.get("search", "").strip()

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS total_users FROM users")
    total_users = cursor.fetchone()["total_users"]

    cursor.execute("SELECT COUNT(*) AS total_admins FROM users WHERE is_admin = 1")
    total_admins = cursor.fetchone()["total_admins"]

    cursor.execute("SELECT COUNT(*) AS active_users FROM users WHERE is_active = 1")
    active_users = cursor.fetchone()["active_users"]

    cursor.execute("SELECT COUNT(*) AS inactive_users FROM users WHERE is_active = 0")
    inactive_users = cursor.fetchone()["inactive_users"]

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
            )
            ORDER BY created_at DESC, user_id DESC
            """,
            (like_term, like_term, like_term, like_term, like_term),
        )
    else:
        cursor.execute(
            """
            SELECT *
            FROM users
            ORDER BY created_at DESC, user_id DESC
            """
        )

    users = cursor.fetchall()
    conn.close()

    return render_template(
        "admin_dashboard.html",
        user=admin_user,
        users=users,
        total_users=total_users,
        total_admins=total_admins,
        active_users=active_users,
        inactive_users=inactive_users,
        search_query=search_query,
    )


@admin_bp.route("/admin/users")
def admin_users():
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/admin/users/<int:user_id>/toggle-status", methods=["POST"])
def toggle_user_status(user_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    if admin_user["user_id"] == user_id:
        flash("You cannot deactivate your own admin account.", "error")
        return redirect(url_for("admin.admin_dashboard"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    target_user = cursor.fetchone()

    if not target_user:
        conn.close()
        flash("User not found.", "error")
        return redirect(url_for("admin.admin_dashboard"))

    new_status = 0 if target_user["is_active"] else 1

    cursor.execute("""
        UPDATE users
        SET is_active = ?
        WHERE user_id = ?
    """, (new_status, user_id))

    conn.commit()
    conn.close()

    if new_status == 1:
        flash("User account activated successfully.", "success")
    else:
        flash("User account deactivated successfully.", "success")

    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/admin/users/<int:user_id>/make-admin", methods=["POST"])
def make_admin(user_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    target_user = cursor.fetchone()

    if not target_user:
        conn.close()
        flash("User not found.", "error")
        return redirect(url_for("admin.admin_dashboard"))

    cursor.execute("""
        UPDATE users
        SET is_admin = 1
        WHERE user_id = ?
    """, (user_id,))

    conn.commit()
    conn.close()

    flash("User promoted to admin successfully.", "success")
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/admin/users/<int:user_id>/remove-admin", methods=["POST"])
def remove_admin(user_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    if admin_user["user_id"] == user_id:
        flash("You cannot remove your own admin access.", "error")
        return redirect(url_for("admin.admin_dashboard"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    target_user = cursor.fetchone()

    if not target_user:
        conn.close()
        flash("User not found.", "error")
        return redirect(url_for("admin.admin_dashboard"))

    cursor.execute("""
        UPDATE users
        SET is_admin = 0
        WHERE user_id = ?
    """, (user_id,))

    conn.commit()
    conn.close()

    flash("Admin access removed successfully.", "success")
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.route("/admin/users/<int:user_id>/delete", methods=["POST"])
def delete_user(user_id):
    admin_user, redirect_response = admin_required()
    if redirect_response:
        return redirect_response

    if admin_user["user_id"] == user_id:
        flash("You cannot delete your own admin account.", "error")
        return redirect(url_for("admin.admin_dashboard"))

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT property_id FROM property WHERE owner_id = ?", (user_id,))
    property_ids = [row["property_id"] for row in cursor.fetchall()]

    if property_ids:
        placeholders = ",".join("?" for _ in property_ids)

        cursor.execute(
            f"DELETE FROM transaction_history WHERE property_id IN ({placeholders})",
            property_ids
        )
        cursor.execute(
            f"DELETE FROM value_prediction WHERE property_id IN ({placeholders})",
            property_ids
        )
        cursor.execute(
            f"DELETE FROM document WHERE property_id IN ({placeholders})",
            property_ids
        )
        cursor.execute(
            f"DELETE FROM property WHERE property_id IN ({placeholders})",
            property_ids
        )

    cursor.execute("DELETE FROM plan_case WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM document WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM users WHERE user_id = ?", (user_id,))

    conn.commit()
    conn.close()

    flash("User deleted successfully.", "success")
    return redirect(url_for("admin.admin_dashboard"))
