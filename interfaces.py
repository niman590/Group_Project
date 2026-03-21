from flask import Flask, render_template_string, request, redirect, url_for, flash, session

app = Flask(__name__)
app.secret_key = "dev-secret-key-change-later"


LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Civic Plan | Login</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
        }

        body {
            min-height: 100vh;
            background: linear-gradient(135deg, #163f73, #2f63b3);
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }

        .container {
            width: 100%;
            max-width: 1050px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            background: #ffffff;
            overflow: hidden;
            box-shadow: 0 15px 40px rgba(0,0,0,0.22);
            border: 1px solid rgba(0,0,0,0.2);
        }

        .left-panel {
            background:
                linear-gradient(rgba(9, 35, 79, 0.84), rgba(9, 35, 79, 0.84)),
                url('https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1200&q=80') center/cover;
            color: white;
            padding: 55px 35px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .left-panel h1 {
            font-size: 2.9rem;
            line-height: 1.25;
            font-weight: 800;
            margin-bottom: 28px;
            max-width: 420px;
        }

        .left-panel p {
            font-size: 1rem;
            line-height: 1.8;
            color: #e5eefb;
            max-width: 430px;
        }

        .right-panel {
            background: #f4f4f4;
            padding: 28px 22px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .top-brand {
            display: flex;
            justify-content: center;
            align-items: flex-start;
            position: relative;
            margin-bottom: 18px;
        }

        .logo-box {
            position: absolute;
            right: 0;
            top: 0;
            font-size: 10px;
            color: #1f4f94;
            text-align: center;
            font-weight: bold;
            border: 1px solid #d3dbe8;
            padding: 6px 8px;
            background: white;
            line-height: 1.2;
        }

        .brand-text {
            text-align: center;
        }

        .brand-text h2 {
            color: #27559c;
            font-size: 2rem;
            font-weight: 800;
            letter-spacing: 1px;
        }

        .brand-text p {
            color: #a0a4aa;
            font-size: 1.2rem;
            margin-top: 4px;
        }

        .tab-buttons {
            display: flex;
            gap: 18px;
            margin: 22px 0 20px 0;
        }

        .tab-buttons button {
            flex: 1;
            border: none;
            padding: 12px;
            border-radius: 10px;
            font-weight: 700;
            font-size: 1rem;
            cursor: pointer;
            transition: 0.3s ease;
        }

        .tab-buttons .inactive {
            background: #b7c7df;
            color: #1b1b1b;
        }

        .tab-buttons .active {
            background: #2f63b3;
            color: white;
        }

        .form-section {
            display: none;
        }

        .form-section.active {
            display: block;
        }

        .input-group {
            margin-bottom: 14px;
        }

        .input-group label {
            display: block;
            font-size: 0.95rem;
            font-weight: 700;
            color: #2f63b3;
            margin-bottom: 7px;
        }

        .input-group input {
            width: 100%;
            padding: 13px 14px;
            border: 1px solid #c4cedd;
            border-radius: 10px;
            background: #eceff3;
            font-size: 0.98rem;
            outline: none;
            color: #444;
        }

        .input-group input:focus {
            border-color: #2f63b3;
            background: #ffffff;
        }

        .row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            margin: 8px 0 18px 0;
            flex-wrap: wrap;
        }

        .remember {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.92rem;
            color: #4c5f7a;
        }

        .row a {
            text-decoration: none;
            color: #4b74b9;
            font-size: 0.92rem;
        }

        .btn-login {
            width: 100%;
            padding: 14px;
            border: none;
            border-radius: 8px;
            background: #143f7a;
            color: white;
            font-size: 1.1rem;
            font-weight: 700;
            cursor: pointer;
            transition: 0.3s ease;
        }

        .btn-login:hover {
            background: #0f3568;
        }

        .footer-text {
            margin-top: 14px;
            text-align: center;
            color: #777;
            font-size: 0.98rem;
        }

        .footer-text a {
            color: #4b74b9;
            font-weight: 700;
            text-decoration: none;
        }

        .flash {
            background: #e8f1ff;
            border: 1px solid #b8cdf2;
            color: #1f4f94;
            padding: 10px 12px;
            border-radius: 8px;
            margin-bottom: 14px;
            font-size: 0.95rem;
        }

        @media (max-width: 900px) {
            .container {
                grid-template-columns: 1fr;
            }

            .left-panel {
                padding: 40px 25px;
            }

            .left-panel h1 {
                font-size: 2.2rem;
            }

            .right-panel {
                padding: 24px 18px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="left-panel">
            <h1>Smart Digital Land Management and Planning Approval System</h1>
            <p>
                Secure access portal for citizens and administrators to manage land records,
                planning approvals, and related digital services.
            </p>
        </div>

        <div class="right-panel">
            <div class="top-brand">
                <div class="brand-text">
                    <h2>CIVIC PLAN</h2>
                    <p>Land Management Portal</p>
                </div>
                <div class="logo-box">CIVIC<br>PLAN</div>
            </div>

            {% with messages = get_flashed_messages() %}
                {% if messages %}
                    {% for message in messages %}
                        <div class="flash">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}

            <div class="tab-buttons">
                <button id="citizenTab" class="active" onclick="showTab('citizen')">Citizen Login</button>
                <button id="adminTab" class="inactive" onclick="showTab('admin')">Admin Login</button>
            </div>

            <div id="citizenForm" class="form-section active">
                <form method="POST" action="{{ url_for('login_citizen') }}">
                    <div class="input-group">
                        <label for="citizen_nic">NIC Number</label>
                        <input type="text" id="citizen_nic" name="nic" placeholder="Enter NIC number" required>
                    </div>

                    <div class="input-group">
                        <label for="citizen_password">Password</label>
                        <input type="password" id="citizen_password" name="password" placeholder="Enter password" required>
                    </div>

                    <div class="row">
                        <label class="remember">
                            <input type="checkbox" name="remember">
                            Remember me
                        </label>
                        <a href="{{ url_for('forgot_password') }}">Forgot Password?</a>
                    </div>

                    <button type="submit" class="btn-login">Login as Citizen</button>
                </form>

                <div class="footer-text">
                    Don’t have an account? <a href="{{ url_for('register_citizen') }}">Register here</a>
                </div>
            </div>

            <div id="adminForm" class="form-section">
                <form method="POST" action="{{ url_for('login_admin') }}">
                    <div class="input-group">
                        <label for="admin_name">Admin Full Name</label>
                        <input type="text" id="admin_name" name="full_name" placeholder="Enter full name" required>
                    </div>

                    <div class="input-group">
                        <label for="employee_id">Employee ID / Password</label>
                        <input type="password" id="employee_id" name="employee_id" placeholder="Enter employee ID" required>
                    </div>

                    <div class="row">
                        <label class="remember">
                            <input type="checkbox" name="remember">
                            Remember me
                        </label>
                        <a href="{{ url_for('forgot_password') }}">Forgot Password?</a>
                    </div>

                    <button type="submit" class="btn-login">Login as Admin</button>
                </form>

                <div class="footer-text">
                    Need admin access? <a href="{{ url_for('register_admin') }}">Register here</a>
                </div>
            </div>
        </div>
    </div>

    <script>
        function showTab(role) {
            const citizenTab = document.getElementById("citizenTab");
            const adminTab = document.getElementById("adminTab");
            const citizenForm = document.getElementById("citizenForm");
            const adminForm = document.getElementById("adminForm");

            if (role === "citizen") {
                citizenTab.classList.remove("inactive");
                citizenTab.classList.add("active");
                adminTab.classList.remove("active");
                adminTab.classList.add("inactive");
                citizenForm.classList.add("active");
                adminForm.classList.remove("active");
            } else {
                adminTab.classList.remove("inactive");
                adminTab.classList.add("active");
                citizenTab.classList.remove("active");
                citizenTab.classList.add("inactive");
                adminForm.classList.add("active");
                citizenForm.classList.remove("active");
            }
        }
    </script>
</body>
</html>
"""


REGISTER_CITIZEN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Civic Plan | Citizen Registration</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
        }

        body {
            min-height: 100vh;
            background: linear-gradient(135deg, #163f73, #2f63b3);
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }

        .container {
            width: 100%;
            max-width: 1050px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            background: #ffffff;
            overflow: hidden;
            box-shadow: 0 15px 40px rgba(0,0,0,0.20);
            border: 1px solid rgba(0,0,0,0.2);
        }

        .left-panel {
            background:
                linear-gradient(rgba(8, 37, 82, 0.82), rgba(8, 37, 82, 0.82)),
                url('https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1200&q=80') center/cover;
            color: white;
            padding: 70px 35px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .left-panel h1 {
            font-size: 3rem;
            line-height: 1.25;
            font-weight: 800;
            margin-bottom: 28px;
        }

        .left-panel p {
            font-size: 1rem;
            line-height: 1.8;
            color: #e6eefb;
            max-width: 420px;
        }

        .right-panel {
            background: #f7f7f7;
            padding: 28px 22px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .top-brand {
            display: flex;
            justify-content: center;
            align-items: flex-start;
            position: relative;
            margin-bottom: 18px;
        }

        .logo-box {
            position: absolute;
            right: 0;
            top: 0;
            font-size: 10px;
            color: #1f4f94;
            text-align: center;
            font-weight: bold;
            border: 1px solid #d3dbe8;
            padding: 6px 8px;
            background: white;
            line-height: 1.2;
        }

        .brand-text {
            text-align: center;
        }

        .brand-text h2 {
            color: #27559c;
            font-size: 2rem;
            font-weight: 800;
            letter-spacing: 1px;
        }

        .brand-text p {
            color: #a0a4aa;
            font-size: 1.2rem;
            margin-top: 4px;
        }

        .tab-buttons {
            display: flex;
            gap: 18px;
            margin: 22px 0 20px 0;
        }

        .tab-buttons a {
            flex: 1;
            text-align: center;
            text-decoration: none;
            padding: 12px;
            border-radius: 10px;
            font-weight: 700;
            font-size: 1rem;
        }

        .active-tab {
            background: #2f63b3;
            color: white;
        }

        .inactive-tab {
            background: #b7c7df;
            color: #1b1b1b;
        }

        .form-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 14px;
        }

        .input-group {
            margin-bottom: 12px;
        }

        .input-group.full {
            grid-column: 1 / -1;
        }

        .input-group label {
            display: block;
            font-size: 0.95rem;
            font-weight: 700;
            color: #2f63b3;
            margin-bottom: 7px;
        }

        .input-group input,
        .input-group textarea {
            width: 100%;
            padding: 13px 14px;
            border: 1px solid #c4cedd;
            border-radius: 10px;
            background: #eceff3;
            font-size: 0.98rem;
            outline: none;
            color: #444;
        }

        .input-group textarea {
            min-height: 85px;
            resize: vertical;
        }

        .input-group input:focus,
        .input-group textarea:focus {
            border-color: #2f63b3;
            background: #ffffff;
        }

        .row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            margin: 8px 0 18px 0;
            flex-wrap: wrap;
        }

        .remember {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.92rem;
            color: #4c5f7a;
        }

        .row a {
            text-decoration: none;
            color: #4b74b9;
            font-size: 0.92rem;
        }

        .btn-register {
            width: 100%;
            padding: 14px;
            border: none;
            border-radius: 8px;
            background: #143f7a;
            color: white;
            font-size: 1.1rem;
            font-weight: 700;
            cursor: pointer;
        }

        .footer-text {
            margin-top: 14px;
            text-align: center;
            color: #777;
            font-size: 0.98rem;
        }

        .footer-text a {
            color: #4b74b9;
            font-weight: 700;
            text-decoration: none;
        }

        .flash {
            background: #e8f1ff;
            border: 1px solid #b8cdf2;
            color: #1f4f94;
            padding: 10px 12px;
            border-radius: 8px;
            margin-bottom: 14px;
            font-size: 0.95rem;
        }

        @media (max-width: 900px) {
            .container {
                grid-template-columns: 1fr;
            }

            .left-panel {
                padding: 40px 25px;
            }

            .left-panel h1 {
                font-size: 2.2rem;
            }

            .right-panel {
                padding: 24px 18px;
            }

            .form-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="left-panel">
            <h1>Smart Digital Land Management and Planning Approval System</h1>
            <p>
                Secure citizen registration portal for accessing land records,
                planning approvals, and related digital services.
            </p>
        </div>

        <div class="right-panel">
            <div class="top-brand">
                <div class="brand-text">
                    <h2>CIVIC PLAN</h2>
                    <p>Land Management Portal</p>
                </div>
                <div class="logo-box">CIVIC<br>PLAN</div>
            </div>

            <div class="tab-buttons">
                <a href="{{ url_for('register_citizen') }}" class="active-tab">Citizen Register</a>
                <a href="{{ url_for('register_admin') }}" class="inactive-tab">Admin Register</a>
            </div>

            {% with messages = get_flashed_messages() %}
                {% if messages %}
                    {% for message in messages %}
                        <div class="flash">{{ message }}</div>
                    {% endfor %}
                {% endif %}
            {% endwith %}

            <form method="POST" action="{{ url_for('register_citizen') }}">
                <div class="form-grid">
                    <div class="input-group">
                        <label for="full_name">Full Name</label>
                        <input type="text" id="full_name" name="full_name" placeholder="Enter full name" required>
                    </div>

                    <div class="input-group">
                        <label for="nic">NIC Number</label>
                        <input type="text" id="nic" name="nic" placeholder="Enter NIC number" required>
                    </div>

                    <div class="input-group full">
                        <label for="address">Address</label>
                        <textarea id="address" name="address" placeholder="Enter address" required></textarea>
                    </div>

                    <div class="input-group">
                        <label for="email">Email Address</label>
                        <input type="email" id="email" name="email" placeholder="Enter email address" required>
                    </div>

                    <div class="input-group">
                        <label for="phone">Phone Number</label>
                        <input type="text" id="phone" name="phone" placeholder="Enter phone number" required>
                    </div>

                    <div class="input-group">
                        <label for="password">Password</label>
                        <input type="password" id="password" name="password" placeholder="Enter password" required>
                    </div>

                    <div class="input-group">
                        <label for="confirm_password">Confirm Password</label>
                        <input type="password" id="confirm_password" name="confirm_password" placeholder="Confirm password" required>
                    </div>
                </div>

                <div class="row">
                    <label class="remember">
                        <input type="checkbox" required>
                        I agree to the terms and conditions
                    </label>
                    <a href="{{ url_for('home') }}">Back to Login</a>
                </div>

                <button type="submit" class="btn-register">Register as Citizen</button>
            </form>

            <div class="footer-text">
                Already have an account? <a href="{{ url_for('home') }}">Login here</a>
            </div>
        </div>
    </div>
</body>
</html>
"""


REGISTER_ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Civic Plan | Admin Registration</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
        }

        body {
            min-height: 100vh;
            background: linear-gradient(135deg, #163f73, #2f63b3);
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }

        .container {
            width: 100%;
            max-width: 1050px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            background: #ffffff;
            overflow: hidden;
            box-shadow: 0 15px 40px rgba(0,0,0,0.20);
            border: 1px solid rgba(0,0,0,0.2);
        }

        .left-panel {
            background:
                linear-gradient(rgba(8, 37, 82, 0.82), rgba(8, 37, 82, 0.82)),
                url('https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?auto=format&fit=crop&w=1200&q=80') center/cover;
            color: white;
            padding: 70px 35px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .left-panel h1 {
            font-size: 3rem;
            line-height: 1.25;
            font-weight: 800;
            margin-bottom: 28px;
        }

        .left-panel p {
            font-size: 1rem;
            line-height: 1.8;
            color: #e6eefb;
            max-width: 420px;
        }

        .right-panel {
            background: #f7f7f7;
            padding: 28px 22px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .top-brand {
            display: flex;
            justify-content: center;
            align-items: flex-start;
            position: relative;
            margin-bottom: 18px;
        }

        .logo-box {
            position: absolute;
            right: 0;
            top: 0;
            font-size: 10px;
            color: #1f4f94;
            text-align: center;
            font-weight: bold;
            border: 1px solid #d3dbe8;
            padding: 6px 8px;
            background: white;
            line-height: 1.2;
        }

        .brand-text {
            text-align: center;
        }

        .brand-text h2 {
            color: #27559c;
            font-size: 2rem;
            font-weight: 800;
            letter-spacing: 1px;
        }

        .brand-text p {
            color: #a0a4aa;
            font-size: 1.2rem;
            margin-top: 4px;
        }

        .tab-buttons {
            display: flex;
            gap: 18px;
            margin: 22px 0 20px 0;
        }

        .tab-buttons a {
            flex: 1;
            text-align: center;
            text-decoration: none;
            padding: 12px;
            border-radius: 10px;
            font-weight: 700;
            font-size: 1rem;
        }

        .active-tab {
            background: #2f63b3;
            color: white;
        }

        .inactive-tab {
            background: #b7c7df;
            color: #1b1b1b;
        }

        .note-box {
            background: #eaf2ff;
            border: 1px solid #bfd3f7;
            color: #1f4f94;
            padding: 12px 14px;
            border-radius: 8px;
            font-size: 0.95rem;
            margin-bottom: 16px;
            line-height: 1.5;
        }

        .form-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 14px;
        }

        .input-group {
            margin-bottom: 12px;
        }

        .input-group.full {
            grid-column: 1 / -1;
        }

        .input-group label {
            display: block;
            font-size: 0.95rem;
            font-weight: 700;
            color: #2f63b3;
            margin-bottom: 7px;
        }

        .input-group input,
        .input-group select {
            width: 100%;
            padding: 13px 14px;
            border: 1px solid #c4cedd;
            border-radius: 10px;
            background: #eceff3;
            font-size: 0.98rem;
            outline: none;
            color: #444;
        }

        .btn-register {
            width: 100%;
            padding: 14px;
            border: none;
            border-radius: 8px;
            background: #143f7a;
            color: white;
            font-size: 1.1rem;
            font-weight: 700;
            cursor: pointer;
            margin-top: 10px;
        }

        .footer-text {
            margin-top: 14px;
            text-align: center;
            color: #777;
            font-size: 0.98rem;
        }

        .footer-text a {
            color: #4b74b9;
            font-weight: 700;
            text-decoration: none;
        }

        @media (max-width: 900px) {
            .container {
                grid-template-columns: 1fr;
            }

            .left-panel {
                padding: 40px 25px;
            }

            .left-panel h1 {
                font-size: 2.2rem;
            }

            .right-panel {
                padding: 24px 18px;
            }

            .form-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="left-panel">
            <h1>Smart Digital Land Management and Planning Approval System</h1>
            <p>
                Secure administrator onboarding portal for authorized government officers
                handling land management and planning approval services.
            </p>
        </div>

        <div class="right-panel">
            <div class="top-brand">
                <div class="brand-text">
                    <h2>CIVIC PLAN</h2>
                    <p>Land Management Portal</p>
                </div>
                <div class="logo-box">CIVIC<br>PLAN</div>
            </div>

            <div class="tab-buttons">
                <a href="{{ url_for('register_citizen') }}" class="inactive-tab">Citizen Register</a>
                <a href="{{ url_for('register_admin') }}" class="active-tab">Admin Register</a>
            </div>

            <div class="note-box">
                Admin registration is restricted. Submitted details must be reviewed and approved
                before access is granted.
            </div>

            <form method="POST" action="{{ url_for('register_admin') }}">
                <div class="form-grid">
                    <div class="input-group">
                        <label for="admin_name">Full Name</label>
                        <input type="text" id="admin_name" name="admin_name" placeholder="Enter full name" required>
                    </div>

                    <div class="input-group">
                        <label for="employee_id">Employee ID</label>
                        <input type="text" id="employee_id" name="employee_id" placeholder="Enter employee ID" required>
                    </div>

                    <div class="input-group">
                        <label for="department">Department</label>
                        <input type="text" id="department" name="department" placeholder="Enter department" required>
                    </div>

                    <div class="input-group">
                        <label for="official_email">Official Email</label>
                        <input type="email" id="official_email" name="official_email" placeholder="Enter official email" required>
                    </div>

                    <div class="input-group full">
                        <label for="admin_password">Password</label>
                        <input type="password" id="admin_password" name="admin_password" placeholder="Enter password" required>
                    </div>
                </div>

                <button type="submit" class="btn-register">Submit Admin Registration</button>
            </form>

            <div class="footer-text">
                Back to <a href="{{ url_for('home') }}">Login</a>
            </div>
        </div>
    </div>
</body>
</html>
"""


SUCCESS_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #163f73, #2f63b3);
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
        }

        .box {
            background: white;
            max-width: 650px;
            width: 100%;
            padding: 35px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0,0,0,0.18);
        }

        h1 {
            color: #1f4f94;
            margin-bottom: 14px;
        }

        p {
            color: #4d5d72;
            line-height: 1.7;
            font-size: 1rem;
        }

        a {
            display: inline-block;
            margin-top: 20px;
            padding: 12px 18px;
            background: #143f7a;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="box">
        <h1>{{ title }}</h1>
        <p>{{ message }}</p>
        <a href="{{ button_link }}">{{ button_text }}</a>
    </div>
</body>
</html>
"""


FORGOT_PASSWORD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Forgot Password</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #163f73, #2f63b3);
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
        }

        .box {
            background: white;
            width: 100%;
            max-width: 650px;
            padding: 35px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.18);
        }

        h1 {
            color: #1f4f94;
            margin-bottom: 12px;
        }

        p {
            color: #55677c;
            line-height: 1.7;
            margin-bottom: 18px;
        }

        .input-group {
            margin-bottom: 14px;
        }

        label {
            display: block;
            color: #2f63b3;
            font-weight: bold;
            margin-bottom: 6px;
        }

        input {
            width: 100%;
            padding: 12px;
            border: 1px solid #c4cedd;
            border-radius: 8px;
            background: #f0f3f7;
        }

        button, a {
            display: inline-block;
            margin-top: 10px;
            padding: 12px 18px;
            border: none;
            background: #143f7a;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: bold;
            cursor: pointer;
        }

        .back-link {
            background: #6f86a7;
            margin-left: 8px;
        }
    </style>
</head>
<body>
    <div class="box">
        <h1>Forgot Password</h1>
        <p>This is a frontend-only placeholder page. Later you can connect this to email or SMS password recovery.</p>
        <form>
            <div class="input-group">
                <label for="email">Email or NIC</label>
                <input type="text" id="email" placeholder="Enter email or NIC">
            </div>
            <button type="button">Send Reset Link</button>
            <a class="back-link" href="{{ url_for('home') }}">Back to Login</a>
        </form>
    </div>
</body>
</html>
"""


CITIZEN_DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Civic Plan | Citizen Dashboard</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: Arial, sans-serif;
        }

        body {
            background: #eef3f9;
            color: #22364d;
        }

        .navbar {
            background: #143f7a;
            color: white;
            padding: 18px 28px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 14px;
        }

        .brand h1 {
            font-size: 1.6rem;
            margin-bottom: 4px;
        }

        .brand p {
            font-size: 0.92rem;
            color: #d5e4ff;
        }

        .nav-actions a {
            text-decoration: none;
            color: white;
            background: rgba(255,255,255,0.14);
            padding: 10px 14px;
            border-radius: 8px;
            margin-left: 8px;
            display: inline-block;
        }

        .hero {
            background: linear-gradient(135deg, #1b4d93, #2f63b3);
            color: white;
            padding: 32px 28px;
        }

        .hero h2 {
            font-size: 2rem;
            margin-bottom: 10px;
        }

        .hero p {
            max-width: 700px;
            line-height: 1.7;
            color: #ebf3ff;
        }

        .wrapper {
            padding: 28px;
        }

        .cards {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 18px;
            margin-bottom: 28px;
        }

        .card {
            background: white;
            padding: 22px;
            border-radius: 14px;
            box-shadow: 0 8px 22px rgba(0,0,0,0.08);
        }

        .card h3 {
            color: #1f4f94;
            margin-bottom: 10px;
            font-size: 1.05rem;
        }

        .card p {
            color: #5c6f85;
            line-height: 1.6;
            margin-bottom: 16px;
            font-size: 0.95rem;
        }

        .card a {
            text-decoration: none;
            color: white;
            background: #143f7a;
            padding: 10px 14px;
            border-radius: 8px;
            display: inline-block;
            font-weight: bold;
        }

        .grid-2 {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 18px;
        }

        .panel {
            background: white;
            padding: 24px;
            border-radius: 14px;
            box-shadow: 0 8px 22px rgba(0,0,0,0.08);
        }

        .panel h3 {
            color: #1f4f94;
            margin-bottom: 16px;
        }

        .status-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 14px 0;
            border-bottom: 1px solid #e5ebf3;
            gap: 10px;
        }

        .status-item:last-child {
            border-bottom: none;
        }

        .status-title {
            font-weight: bold;
            margin-bottom: 4px;
        }

        .status-sub {
            color: #6a7c90;
            font-size: 0.92rem;
        }

        .badge {
            padding: 8px 12px;
            border-radius: 999px;
            font-size: 0.85rem;
            font-weight: bold;
            white-space: nowrap;
        }

        .submitted {
            background: #e8f1ff;
            color: #1f4f94;
        }

        .review {
            background: #fff3da;
            color: #946200;
        }

        .approved {
            background: #e3f8e8;
            color: #1f7a3d;
        }

        ul.notice-list {
            padding-left: 18px;
            color: #5c6f85;
            line-height: 1.8;
        }

        @media (max-width: 1000px) {
            .cards {
                grid-template-columns: repeat(2, 1fr);
            }

            .grid-2 {
                grid-template-columns: 1fr;
            }
        }

        @media (max-width: 650px) {
            .cards {
                grid-template-columns: 1fr;
            }

            .hero h2 {
                font-size: 1.6rem;
            }

            .navbar {
                padding: 16px;
            }

            .wrapper {
                padding: 16px;
            }

            .hero {
                padding: 24px 16px;
            }
        }
    </style>
</head>
<body>
    <div class="navbar">
        <div class="brand">
            <h1>CIVIC PLAN</h1>
            <p>Citizen Dashboard</p>
        </div>
        <div class="nav-actions">
            <a href="{{ url_for('profile') }}">My Profile</a>
            <a href="{{ url_for('logout') }}">Logout</a>
        </div>
    </div>

    <div class="hero">
        <h2>Welcome, {{ citizen_name }}</h2>
        <p>
            Manage your land applications, track planning approval status,
            view notifications, and access digital records from one secure portal.
        </p>
    </div>

    <div class="wrapper">
        <div class="cards">
            <div class="card">
                <h3>Submit New Application</h3>
                <p>Create a new land or planning approval request through the online portal.</p>
                <a href="{{ url_for('submit_application') }}">Apply Now</a>
            </div>

            <div class="card">
                <h3>Track Application Status</h3>
                <p>Check whether your application is submitted, under review, approved, or rejected.</p>
                <a href="{{ url_for('track_status') }}">Track Status</a>
            </div>

            <div class="card">
                <h3>My Land Records</h3>
                <p>Access citizen-facing digital records and previously submitted land-related details.</p>
                <a href="{{ url_for('land_records') }}">View Records</a>
            </div>

            <div class="card">
                <h3>Notifications</h3>
                <p>See recent updates, messages, and important alerts about your submitted requests.</p>
                <a href="{{ url_for('notifications') }}">View Alerts</a>
            </div>
        </div>

        <div class="grid-2">
            <div class="panel">
                <h3>Recent Application Updates</h3>

                <div class="status-item">
                    <div>
                        <div class="status-title">Planning Approval Request #PLN-1001</div>
                        <div class="status-sub">Submitted on 12 March 2026</div>
                    </div>
                    <span class="badge submitted">Submitted</span>
                </div>

                <div class="status-item">
                    <div>
                        <div class="status-title">Land Ownership Verification #LND-2023</div>
                        <div class="status-sub">Updated on 15 March 2026</div>
                    </div>
                    <span class="badge review">Under Review</span>
                </div>

                <div class="status-item">
                    <div>
                        <div class="status-title">Survey Clearance #SUR-3045</div>
                        <div class="status-sub">Completed on 09 March 2026</div>
                    </div>
                    <span class="badge approved">Approved</span>
                </div>
            </div>

            <div class="panel">
                <h3>Important Notices</h3>
                <ul class="notice-list">
                    <li>Please ensure all supporting documents are clear and valid.</li>
                    <li>Use your NIC number consistently for all submissions.</li>
                    <li>Approval timelines may vary based on application type.</li>
                    <li>Contact your local authority office for urgent verification matters.</li>
                </ul>
            </div>
        </div>
    </div>
</body>
</html>
"""


ADMIN_DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Civic Plan | Admin Dashboard</title>
    <style>
        body {
            margin: 0;
            font-family: Arial, sans-serif;
            background: #eef3f9;
            color: #22364d;
        }

        .navbar {
            background: #143f7a;
            color: white;
            padding: 18px 28px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .navbar a {
            text-decoration: none;
            color: white;
            background: rgba(255,255,255,0.14);
            padding: 10px 14px;
            border-radius: 8px;
        }

        .hero {
            background: linear-gradient(135deg, #1b4d93, #2f63b3);
            color: white;
            padding: 32px 28px;
        }

        .hero h2 {
            margin-bottom: 10px;
        }

        .wrapper {
            padding: 28px;
        }

        .grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 18px;
            margin-bottom: 20px;
        }

        .card, .panel {
            background: white;
            padding: 22px;
            border-radius: 14px;
            box-shadow: 0 8px 22px rgba(0,0,0,0.08);
        }

        .card h3, .panel h3 {
            color: #1f4f94;
            margin-bottom: 10px;
        }

        .card p, .panel p {
            color: #5c6f85;
            line-height: 1.6;
        }

        .panel-row {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 18px;
        }

        .task {
            padding: 14px 0;
            border-bottom: 1px solid #e5ebf3;
        }

        .task:last-child {
            border-bottom: none;
        }

        @media (max-width: 1000px) {
            .grid, .panel-row {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="navbar">
        <div>
            <strong>CIVIC PLAN</strong><br>
            <small>Administrator Dashboard</small>
        </div>
        <a href="{{ url_for('logout') }}">Logout</a>
    </div>

    <div class="hero">
        <h2>Welcome, {{ admin_name }}</h2>
        <p>Review pending applications, monitor workflow, and manage administrative approvals.</p>
    </div>

    <div class="wrapper">
        <div class="grid">
            <div class="card">
                <h3>Pending Applications</h3>
                <p>24 applications awaiting review.</p>
            </div>
            <div class="card">
                <h3>Approved Today</h3>
                <p>08 applications approved successfully.</p>
            </div>
            <div class="card">
                <h3>Rejected Cases</h3>
                <p>03 applications rejected with comments.</p>
            </div>
            <div class="card">
                <h3>Registered Citizens</h3>
                <p>1,248 portal users currently registered.</p>
            </div>
        </div>

        <div class="panel-row">
            <div class="panel">
                <h3>Recent Review Queue</h3>
                <div class="task"><strong>PLN-1042</strong> - Planning approval awaiting zoning review.</div>
                <div class="task"><strong>LND-2018</strong> - Ownership verification requires document validation.</div>
                <div class="task"><strong>SUR-3099</strong> - Survey clearance pending final officer approval.</div>
            </div>

            <div class="panel">
                <h3>Admin Notes</h3>
                <p>Use this placeholder panel later for reports, notifications, and officer coordination.</p>
            </div>
        </div>
    </div>
</body>
</html>
"""


PLACEHOLDER_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #163f73, #2f63b3);
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
        }

        .box {
            background: white;
            width: 100%;
            max-width: 700px;
            padding: 35px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.18);
        }

        h1 {
            color: #1f4f94;
            margin-bottom: 12px;
        }

        p {
            color: #55677c;
            line-height: 1.8;
        }

        a {
            display: inline-block;
            margin-top: 20px;
            padding: 12px 18px;
            background: #143f7a;
            color: white;
            text-decoration: none;
            border-radius: 8px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="box">
        <h1>{{ title }}</h1>
        <p>{{ message }}</p>
        <a href="{{ back_link }}">{{ back_text }}</a>
    </div>
</body>
</html>
"""


@app.route("/")
def home():
    return render_template_string(LOGIN_TEMPLATE)


@app.route("/login/citizen", methods=["POST"])
def login_citizen():
    nic = request.form.get("nic", "").strip()
    password = request.form.get("password", "").strip()

    if not nic or not password:
        flash("Please enter NIC number and password.")
        return redirect(url_for("home"))

    session["user_role"] = "citizen"
    session["citizen_name"] = "Citizen User"
    session["citizen_nic"] = nic
    return redirect(url_for("citizen_dashboard"))


@app.route("/login/admin", methods=["POST"])
def login_admin():
    full_name = request.form.get("full_name", "").strip()
    employee_id = request.form.get("employee_id", "").strip()

    if not full_name or not employee_id:
        flash("Please enter admin full name and employee ID.")
        return redirect(url_for("home"))

    session["user_role"] = "admin"
    session["admin_name"] = full_name
    return redirect(url_for("admin_dashboard"))


@app.route("/register/citizen", methods=["GET", "POST"])
def register_citizen():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        nic = request.form.get("nic", "").strip()
        address = request.form.get("address", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if not all([full_name, nic, address, email, phone, password, confirm_password]):
            flash("Please fill in all required fields.")
            return redirect(url_for("register_citizen"))

        if password != confirm_password:
            flash("Password and Confirm Password do not match.")
            return redirect(url_for("register_citizen"))

        return render_template_string(
            SUCCESS_TEMPLATE,
            title="Citizen Registration Successful",
            message="Your citizen registration form has been submitted successfully. You can connect this form to the database later.",
            button_link=url_for("home"),
            button_text="Go to Login"
        )

    return render_template_string(REGISTER_CITIZEN_TEMPLATE)


@app.route("/register/admin", methods=["GET", "POST"])
def register_admin():
    if request.method == "POST":
        admin_name = request.form.get("admin_name", "").strip()
        employee_id = request.form.get("employee_id", "").strip()
        department = request.form.get("department", "").strip()
        official_email = request.form.get("official_email", "").strip()
        admin_password = request.form.get("admin_password", "").strip()

        if not all([admin_name, employee_id, department, official_email, admin_password]):
            flash("Please fill in all required admin fields.")
            return redirect(url_for("register_admin"))

        return render_template_string(
            SUCCESS_TEMPLATE,
            title="Admin Registration Submitted",
            message="Your admin registration request has been submitted for approval.",
            button_link=url_for("home"),
            button_text="Go to Login"
        )

    return render_template_string(REGISTER_ADMIN_TEMPLATE)


@app.route("/forgot-password")
def forgot_password():
    return render_template_string(FORGOT_PASSWORD_TEMPLATE)


@app.route("/citizen-dashboard")
def citizen_dashboard():
    if session.get("user_role") != "citizen":
        flash("Please login as a citizen first.")
        return redirect(url_for("home"))

    citizen_name = session.get("citizen_name", "Citizen User")
    return render_template_string(CITIZEN_DASHBOARD_TEMPLATE, citizen_name=citizen_name)


@app.route("/admin-dashboard")
def admin_dashboard():
    if session.get("user_role") != "admin":
        flash("Please login as an admin first.")
        return redirect(url_for("home"))

    admin_name = session.get("admin_name", "Administrator")
    return render_template_string(ADMIN_DASHBOARD_TEMPLATE, admin_name=admin_name)


@app.route("/submit-application")
def submit_application():
    if session.get("user_role") != "citizen":
        flash("Please login as a citizen first.")
        return redirect(url_for("home"))

    return render_template_string(
        PLACEHOLDER_TEMPLATE,
        title="Submit New Application",
        message="This is a frontend placeholder for the land or planning approval submission form. Later you can add fields, document uploads, and map integration here.",
        back_link=url_for("citizen_dashboard"),
        back_text="Back to Dashboard"
    )


@app.route("/track-status")
def track_status():
    if session.get("user_role") != "citizen":
        flash("Please login as a citizen first.")
        return redirect(url_for("home"))

    return render_template_string(
        PLACEHOLDER_TEMPLATE,
        title="Track Application Status",
        message="This page can later show your application timeline, review progress, officer comments, and approval results.",
        back_link=url_for("citizen_dashboard"),
        back_text="Back to Dashboard"
    )


@app.route("/land-records")
def land_records():
    if session.get("user_role") != "citizen":
        flash("Please login as a citizen first.")
        return redirect(url_for("home"))

    return render_template_string(
        PLACEHOLDER_TEMPLATE,
        title="My Land Records",
        message="This is a placeholder for digital land record viewing. You can later show verified records, ownership details, and downloadable documents here.",
        back_link=url_for("citizen_dashboard"),
        back_text="Back to Dashboard"
    )


@app.route("/notifications")
def notifications():
    if session.get("user_role") != "citizen":
        flash("Please login as a citizen first.")
        return redirect(url_for("home"))

    return render_template_string(
        PLACEHOLDER_TEMPLATE,
        title="Notifications",
        message="This page can later display status changes, reminders, approval notices, and system alerts for the citizen.",
        back_link=url_for("citizen_dashboard"),
        back_text="Back to Dashboard"
    )


@app.route("/profile")
def profile():
    if session.get("user_role") != "citizen":
        flash("Please login as a citizen first.")
        return redirect(url_for("home"))

    return render_template_string(
        PLACEHOLDER_TEMPLATE,
        title="My Profile",
        message="This is a placeholder for the citizen profile page. Later you can show name, NIC, contact details, password change, and account settings here.",
        back_link=url_for("citizen_dashboard"),
        back_text="Back to Dashboard"
    )


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out successfully.")
    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)