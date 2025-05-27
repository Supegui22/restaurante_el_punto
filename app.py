import csv
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, send_file
from io import BytesIO
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'

categorias = {
    'Almuerzos': ['Menú día', 'Sopa del día', 'Arroz con pollo'],
    'Bebidas': ['Jugo natural', 'Agua', 'Refresco']
}

usuarios = {
    'admin@example.com': {'password': '1234', 'rol': 'Admin'},
    'domiciliario@example.com': {'password': '1234', 'rol': 'Domiciliario'}
}

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        password = request.form['password']
        user = usuarios.get(correo)
        if user and user['password'] == password:
            session['usuario'] = correo
            session['rol'] = user['rol']
            return redirect(url_for('ventas_en_punto'))
        else:
            return "Credenciales inválidas", 401
    return render_template('login.html')

@app.route('/ventas', methods=['GET', 'POST'])
def ventas_en_punto():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        seleccionados = request.form.getlist('productos')
    # Guardar los productos seleccionados en un archivo CSV
    with open('ventas.csv', mode='a', newline='', encoding='utf-8') as archivo:
        escritor = csv.writer(archivo)
        fecha = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        for producto in seleccionados:
            escritor.writerow([fecha, session.get('usuario'), producto])

        # Generar PDF con comanda
        buffer = BytesIO()
        p = canvas.Canvas(buffer)
        p.setFont("Helvetica-Bold", 14)
        p.drawString(100, 800, "Comanda - Restaurante El Punto")
        p.setFont("Helvetica", 12)
        y = 760
        for producto in seleccionados:
            p.drawString(100, y, f"- {producto}")
            y -= 20
        p.showPage()
        p.save()
        buffer.seek(0)
        return send_file(buffer, as_attachment=True, download_name="comanda.pdf", mimetype='application/pdf')

    return render_template('ventas.html', categorias=categorias)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
