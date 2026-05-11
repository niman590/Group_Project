import os
import random
import sqlite3
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "land_management_system.db")

SUPPORTED_AREAS = [
    "Ragama",
    "Rajagiriya",
    "Malabe",
    "Ja-Ela",
    "Kelaniya",
    "Kadana",
    "Kadawatha",
    "Kaduwela",
]


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def date_months_ago(months_ago, day_offset=0):
    today = datetime.now()
    target = today - timedelta(days=months_ago * 30)
    target = target + timedelta(days=day_offset)
    return target.strftime("%Y-%m-%d %H:%M:%S")


def random_date_within_2_months():
    today = datetime.now()
    start_date = today - timedelta(days=60)

    return (start_date + timedelta(
        days=random.randint(0, 60),
        hours=random.randint(8, 17),
        minutes=random.randint(0, 59)
    )).strftime("%Y-%m-%d %H:%M:%S")


def clear_old_data(cursor):
    cursor.execute("DELETE FROM value_prediction")
    cursor.execute("DELETE FROM transaction_history")
    cursor.execute("DELETE FROM property")


def seed_users(cursor):
    users = [
        ("Kasun", "Perera", "0711111111", "kasun@example.com", "900111111V", "EMP001", "Ragama"),
        ("Nimal", "Silva", "0722222222", "nimal@example.com", "900222222V", "EMP002", "Rajagiriya"),
        ("Amal", "Fernando", "0733333333", "amal@example.com", "900333333V", "EMP003", "Malabe"),
        ("Sunil", "Bandara", "0744444444", "sunil@example.com", "900444444V", "EMP004", "Ja-Ela"),
        ("Ruwan", "Jayasinghe", "0755555555", "ruwan@example.com", "900555555V", "EMP005", "Kelaniya"),
        ("Chamath", "Perera", "0766666666", "chamath@example.com", "900666666V", "EMP006", "Kadana"),
        ("Dilshan", "Silva", "0777777777", "dilshan@example.com", "900777777V", "EMP007", "Kadawatha"),
        ("Tharindu", "Fernando", "0788888888", "tharindu@example.com", "900888888V", "EMP008", "Kaduwela"),
    ]

    for first, last, phone, email, nic, emp_id, city in users:
        cursor.execute("""
            INSERT OR IGNORE INTO users (
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
                is_active,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            first,
            last,
            phone,
            email,
            generate_password_hash("password123"),
            "1990-01-01",
            f"No. 10, {city} Road",
            city,
            nic,
            emp_id,
            0,
            1,
            random_date_within_2_months()
        ))

        cursor.execute("""
            UPDATE users
            SET first_name = ?,
                last_name = ?,
                phone_number = ?,
                city = ?,
                address = ?,
                employee_id = ?,
                is_admin = 0,
                is_active = 1
            WHERE email = ?
        """, (
            first,
            last,
            phone,
            city,
            f"No. 10, {city} Road",
            emp_id,
            email
        ))


def seed_property(cursor):
    city_values = {
        "Ragama": 14500000,
        "Rajagiriya": 32000000,
        "Malabe": 21000000,
        "Ja-Ela": 16500000,
        "Kelaniya": 18500000,
        "Kadana": 15000000,
        "Kadawatha": 24500000,
        "Kaduwela": 22500000,
    }

    cursor.execute("""
        SELECT user_id, city
        FROM users
        WHERE is_admin = 0
          AND city IN (
            'Ragama',
            'Rajagiriya',
            'Malabe',
            'Ja-Ela',
            'Kelaniya',
            'Kadana',
            'Kadawatha',
            'Kaduwela'
          )
        ORDER BY user_id
    """)
    users = cursor.fetchall()

    for user in users:
        city = user["city"]

        cursor.execute("""
            INSERT INTO property (
                owner_id,
                current_value,
                property_size,
                property_address,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            user["user_id"],
            city_values[city],
            random.randint(20, 100),
            f"No. {random.randint(1, 200)}, {city} Road, {city}",
            random_date_within_2_months()
        ))


def seed_transaction_history(cursor):
    cursor.execute("SELECT property_id, current_value FROM property")
    properties = cursor.fetchall()

    for prop in properties:
        for i in range(6):
            amount = prop["current_value"] + random.randint(-300000, 700000)

            cursor.execute("""
                INSERT INTO transaction_history (
                    property_id,
                    transaction_date,
                    transaction_amount
                )
                VALUES (?, ?, ?)
            """, (
                prop["property_id"],
                date_months_ago(5 - i, random.randint(0, 20)),
                amount
            ))


def seed_value_prediction(cursor):
    city_monthly_growth = {
        "Ragama": 0.012,
        "Rajagiriya": 0.015,
        "Malabe": 0.018,
        "Ja-Ela": 0.011,
        "Kelaniya": 0.013,
        "Kadana": 0.010,
        "Kadawatha": 0.016,
        "Kaduwela": 0.017,
    }

    cursor.execute("""
        SELECT
            p.property_id,
            p.current_value,
            u.city AS geographic_area
        FROM property p
        JOIN users u ON p.owner_id = u.user_id
        WHERE u.city IN (
            'Ragama',
            'Rajagiriya',
            'Malabe',
            'Ja-Ela',
            'Kelaniya',
            'Kadana',
            'Kadawatha',
            'Kaduwela'
        )
        ORDER BY u.city
    """)
    properties = cursor.fetchall()

    for prop in properties:
        area = prop["geographic_area"]
        base_value = float(prop["current_value"])
        monthly_growth = city_monthly_growth.get(area, 0.012)

        for month_index in range(6):
            months_ago = 5 - month_index
            month_base_value = base_value * ((1 + monthly_growth) ** month_index)

            for record_no in range(4):
                noise = random.randint(-80000, 80000)
                predicted_value = round(month_base_value + noise, 2)

                cursor.execute("""
                    INSERT INTO value_prediction (
                        property_id,
                        predicted_value,
                        prediction_date,
                        geographic_area
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    prop["property_id"],
                    predicted_value,
                    date_months_ago(months_ago, record_no * 6),
                    area
                ))


def seed_report(cursor):
    report_titles = [
        "Monthly Land Report",
        "Planning Application Report",
        "Transaction Summary Report",
        "Ownership Transfer Report",
        "Security Event Report",
    ]

    for title in report_titles:
        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM report
            WHERE report_title = ?
        """, (title,))

        if cursor.fetchone()["count"] > 0:
            continue

        approved = random.randint(10, 35)
        rejected = random.randint(1, 8)
        pending = random.randint(5, 20)
        total = approved + rejected + pending

        cursor.execute("""
            INSERT INTO report (
                generated_date,
                total_cases,
                rejected_cases,
                approved_cases,
                pending_cases,
                report_title
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            random_date_within_2_months(),
            total,
            rejected,
            approved,
            pending,
            title
        ))


def seed_land_record(cursor):
    lands = [
        ("D-2001", "No. 100, Ragama Road", "Ragama", "Kasun Perera"),
        ("D-2002", "No. 200, Rajagiriya Road", "Rajagiriya", "Nimal Silva"),
        ("D-2003", "No. 300, Malabe Road", "Malabe", "Amal Fernando"),
        ("D-2004", "No. 400, Ja-Ela Road", "Ja-Ela", "Sunil Bandara"),
        ("D-2005", "No. 500, Kelaniya Road", "Kelaniya", "Ruwan Jayasinghe"),
        ("D-2006", "No. 600, Kadana Road", "Kadana", "Chamath Perera"),
        ("D-2007", "No. 700, Kadawatha Road", "Kadawatha", "Dilshan Silva"),
        ("D-2008", "No. 800, Kaduwela Road", "Kaduwela", "Tharindu Fernando"),
    ]

    for deed, address, location, owner in lands:
        cursor.execute("""
            INSERT OR IGNORE INTO land_record (
                deed_number,
                property_address,
                location,
                current_owner_name,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            deed,
            address,
            location,
            owner,
            random_date_within_2_months()
        ))


def seed_ownership_history(cursor):
    cursor.execute("""
        SELECT land_id, current_owner_name, location
        FROM land_record
        WHERE deed_number LIKE 'D-200%'
    """)
    lands = cursor.fetchall()

    for land in lands:
        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM ownership_history
            WHERE land_id = ?
        """, (land["land_id"],))

        if cursor.fetchone()["count"] > 0:
            continue

        owners = [
            ("Previous Owner A", "801111111V", land["location"], "0710000001", "Original Registration", 1),
            ("Previous Owner B", "802222222V", land["location"], "0710000002", "Sale", 2),
            (land["current_owner_name"], "803333333V", land["location"], "0710000003", "Transfer", 3),
        ]

        for owner_name, nic, address, phone, tx_type, order_no in owners:
            cursor.execute("""
                INSERT INTO ownership_history (
                    land_id,
                    owner_name,
                    owner_nic,
                    owner_address,
                    owner_phone,
                    transfer_date,
                    transaction_type,
                    ownership_order,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                land["land_id"],
                owner_name,
                nic,
                address,
                phone,
                random_date_within_2_months(),
                tx_type,
                order_no,
                random_date_within_2_months()
            ))


def seed_transaction_history_update_request(cursor):
    cursor.execute("SELECT user_id FROM users WHERE is_admin = 0")
    users = cursor.fetchall()

    cursor.execute("SELECT deed_number FROM land_record")
    lands = cursor.fetchall()

    if not users or not lands:
        return

    statuses = ["Pending", "Approved", "Rejected"]

    for i in range(12):
        proposed_nic = f"99{i}123456V"

        cursor.execute("""
            SELECT COUNT(*) AS count
            FROM transaction_history_update_request
            WHERE proposed_owner_nic = ?
        """, (proposed_nic,))

        if cursor.fetchone()["count"] > 0:
            continue

        user = random.choice(users)
        land = random.choice(lands)

        cursor.execute("""
            INSERT INTO transaction_history_update_request (
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
                status,
                submitted_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user["user_id"],
            land["deed_number"],
            f"New Owner {i + 1}",
            proposed_nic,
            "Sample Address",
            f"07700000{i}",
            random_date_within_2_months(),
            random.choice(["Sale", "Gift", "Inheritance", "Transfer"]),
            "Sample update request",
            f"uploads/proof_document_{i + 1}.pdf",
            random.choice(statuses),
            random_date_within_2_months()
        ))


def seed_all_main_tables():
    conn = get_connection()
    cursor = conn.cursor()

    clear_old_data(cursor)

    seed_users(cursor)
    seed_property(cursor)
    seed_transaction_history(cursor)
    seed_value_prediction(cursor)
    seed_report(cursor)
    seed_land_record(cursor)
    seed_ownership_history(cursor)
    seed_transaction_history_update_request(cursor)

    conn.commit()
    conn.close()

    print("Main tables seeded successfully.")
    print("Created 24 valuation records for each supported city.")
    print("Expected total valuation records: 192.")


if __name__ == "__main__":
    seed_all_main_tables()