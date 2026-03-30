from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.utils import secure_filename
from datetime import datetime
import os
import sqlite3
import uuid

submit_documents_bp = Blueprint('submit_documents', __name__)

ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "jpg", "jpeg", "png"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db_connection():
    db_path = os.path.join(current_app.root_path, 'database.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_submit_documents_table():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS planning_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id TEXT UNIQUE NOT NULL,
            user_id INTEGER,
            full_name TEXT NOT NULL,
            nic TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL,
            property_id TEXT NOT NULL,
            application_type TEXT NOT NULL,
            district TEXT NOT NULL,
            start_date TEXT,
            project_description TEXT,
            document_names TEXT,
            status TEXT DEFAULT 'Submitted',
            submitted_at TEXT NOT NULL
        )
        """
    )

    conn.commit()
    conn.close()


@submit_documents_bp.before_app_request
def setup_submit_documents_table():
    if not getattr(current_app, '_submit_docs_initialized', False):
        init_submit_documents_table()
        current_app._submit_docs_initialized = True


@submit_documents_bp.route('/submit_documents', methods=['GET', 'POST'])
def submit_documents():
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        nic = request.form.get('nic', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        property_id = request.form.get('property_id', '').strip()
        application_type = request.form.get('application_type', '').strip()
        district = request.form.get('district', '').strip()
        start_date = request.form.get('start_date', '').strip()
        project_description = request.form.get('project_description', '').strip()
        confirm_accuracy = request.form.get('confirm_accuracy')
        review_consent = request.form.get('review_consent')
        uploaded_files = request.files.getlist('planning_documents')

        if not all([full_name, nic, email, phone, address, property_id, application_type, district]):
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('submit_documents.submit_documents'))

        if not confirm_accuracy or not review_consent:
            flash('Please accept both declaration checkboxes.', 'danger')
            return redirect(url_for('submit_documents.submit_documents'))

        upload_folder = os.path.join(current_app.root_path, 'static', 'uploads', 'planning_documents')
        os.makedirs(upload_folder, exist_ok=True)

        saved_files = []

        for file in uploaded_files:
            if file and file.filename:
                if not allowed_file(file.filename):
                    flash(f'Invalid file type: {file.filename}', 'danger')
                    return redirect(url_for('submit_documents.submit_documents'))

                original_name = secure_filename(file.filename)
                unique_name = f"{uuid.uuid4().hex}_{original_name}"
                file_path = os.path.join(upload_folder, unique_name)
                file.save(file_path)
                saved_files.append(unique_name)

        case_id = f"CP-PLN-{datetime.now().year}-{uuid.uuid4().hex[:6].upper()}"
        user_id = session.get('user_id')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO planning_applications (
                case_id, user_id, full_name, nic, email, phone, address,
                property_id, application_type, district, start_date,
                project_description, document_names, submitted_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                case_id,
                user_id,
                full_name,
                nic,
                email,
                phone,
                address,
                property_id,
                application_type,
                district,
                start_date,
                project_description,
                ','.join(saved_files),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
        )
        conn.commit()
        conn.close()

        flash(f'Application submitted successfully. Your case ID is {case_id}.', 'success')
        return redirect(url_for('submit_documents.submit_documents'))

    return render_template('submit_documents.html')


@submit_documents_bp.route('/my_applications')
def my_applications():
    user_id = session.get('user_id')

    conn = get_db_connection()
    cursor = conn.cursor()

    if user_id:
        cursor.execute(
            "SELECT * FROM planning_applications WHERE user_id = ? ORDER BY id DESC",
            (user_id,)
        )
    else:
        cursor.execute(
            "SELECT * FROM planning_applications ORDER BY id DESC"
        )

    applications = cursor.fetchall()
    conn.close()

    return render_template('my_applications.html', applications=applications)
