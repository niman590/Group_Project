from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database.db_connection import get_connection

user_bp = Blueprint("user", __name__)


def get_current_user():
    if "user_id" not in session:
        return None

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT *
        FROM users
        WHERE user_id = ?
        """,
        (session["user_id"],),
    )
    user = cursor.fetchone()
    conn.close()
    return user


def sync_session_user(user):
    session["user_id"] = user["user_id"]
    session["first_name"] = user["first_name"]
    session["last_name"] = user["last_name"]
    session["full_name"] = f"{user['first_name']} {user['last_name']}".strip()
    session["nic"] = user["nic"]
    session["email"] = user["email"]
    session["phone_number"] = user["phone_number"] if user["phone_number"] else ""
    session["address"] = user["address"] if user["address"] else ""
    session["city"] = user["city"] if user["city"] else ""
    session["is_admin"] = user["is_admin"]


@user_bp.route("/user_dashboard")
def user_dashboard():
    if "user_id" not in session:
        flash("Please sign in first.", "error")
        return redirect(url_for("auth.login"))

    user = get_current_user()

    if not user:
        session.clear()
        flash("User not found. Please sign in again.", "error")
        return redirect(url_for("auth.login"))

    return render_template("user_dashboard.html", user=user, active_page="dashboard")


@user_bp.route("/account", methods=["GET", "POST"])
def account():
    if "user_id" not in session:
        flash("Please sign in first.", "error")
        return redirect(url_for("auth.login"))

    user = get_current_user()

    if not user:
        session.clear()
        flash("User not found. Please sign in again.", "error")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        first_name = request.form.get("first_name", "").strip()
        last_name = request.form.get("last_name", "").strip()
        email = request.form.get("email", "").strip()
        phone_number = request.form.get("phone_number", "").strip()
        address = request.form.get("address", "").strip()
        city = request.form.get("city", "").strip()

        if not first_name or not last_name or not email:
            flash("First name, last name, and email are required.", "error")
            return render_template("account.html", user=user, active_page="account")

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT user_id FROM users
            WHERE email = ? AND user_id != ?
            """,
            (email, session["user_id"]),
        )
        existing_email = cursor.fetchone()

        if existing_email:
            conn.close()
            flash("That email address is already being used.", "error")
            return render_template("account.html", user=user, active_page="account")

        cursor.execute(
            """
            UPDATE users
            SET first_name = ?,
                last_name = ?,
                email = ?,
                phone_number = ?,
                address = ?,
                city = ?
            WHERE user_id = ?
            """,
            (
                first_name,
                last_name,
                email,
                phone_number,
                address,
                city,
                session["user_id"],
            ),
        )

        conn.commit()

        cursor.execute(
            """
            SELECT *
            FROM users
            WHERE user_id = ?
            """,
            (session["user_id"],),
        )
        updated_user = cursor.fetchone()
        conn.close()

        sync_session_user(updated_user)
        flash("Your account details were updated successfully.", "success")
        return redirect(url_for("user.account"))

    return render_template("account.html", user=user, active_page="account")


@user_bp.route("/account/delete", methods=["POST"])
def delete_account():
    if "user_id" not in session:
        flash("Please sign in first.", "error")
        return redirect(url_for("auth.login"))

    user_id = session["user_id"]

    conn = get_connection()
    cursor = conn.cursor()

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
            f"""
            DELETE FROM transaction_history
            WHERE property_id IN ({placeholders})
            """,
            property_ids,
        )

        cursor.execute(
            f"""
            DELETE FROM value_prediction
            WHERE property_id IN ({placeholders})
            """,
            property_ids,
        )

        cursor.execute(
            f"""
            DELETE FROM document
            WHERE property_id IN ({placeholders})
            """,
            property_ids,
        )

        cursor.execute(
            f"""
            DELETE FROM property
            WHERE property_id IN ({placeholders})
            """,
            property_ids,
        )

    cursor.execute(
        """
        DELETE FROM plan_case
        WHERE user_id = ?
        """,
        (user_id,),
    )

    cursor.execute(
        """
        DELETE FROM document
        WHERE user_id = ?
        """,
        (user_id,),
    )

    cursor.execute(
        """
        DELETE FROM users
        WHERE user_id = ?
        """,
        (user_id,),
    )

    conn.commit()
    conn.close()

    session.clear()
    flash("Your account has been deleted successfully.", "success")
    return redirect(url_for("main.dashboard"))