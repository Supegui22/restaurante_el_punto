from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        return redirect(url_for('ventas'))
    return render_template('login.html')

@app.route('/roles')
def roles():
    return render_template('roles.html')

@app.route('/ventas')
def ventas():
    return render_template('ventas.html')

if __name__ == '__main__':
    app.run(debug=True)