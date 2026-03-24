from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        print("Login submitted:")
        print("Username:", username)
        print("Password:", password)

        return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        nic = request.form.get('nic')
        phone = request.form.get('phone')
        address = request.form.get('address')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        print("Registration submitted:")
        print("First Name:", first_name)
        print("Last Name:", last_name)
        print("NIC:", nic)
        print("Phone:", phone)
        print("Address:", address)
        print("Email:", email)
        print("Password:", password)
        print("Confirm Password:", confirm_password)

        return redirect(url_for('login'))

    return render_template('register.html')


if __name__ == '__main__':
    app.run(debug=True)