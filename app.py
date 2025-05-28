import csv
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, send_file
from io import BytesIO
from reportlab.pdfgen import canvas
import os

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'

categorias = {
    'Almuerzos': [
        {'nombre': 'Menú día', 'precio': 15000},
        {'nombre': 'Sopa del día', 'precio': 8000},
        {'nombre': 'Arroz con pollo', 'precio': 12000}
    ],
    'Bebidas': [
        {'nombre': 'Jugo natural', 'precio': 5000},
        {'nombre': 'Agua', 'precio': 2000},
        {'nombre': 'Refresco', 'precio': 4000}
    ]
}

usuarios = {
    'admin@example.com': {'password': '1234', 'rol': 'Admin'},
    'domiciliario@example.com': {'password': '1234', 'rol': 'Domiciliario'}
}

# Definimos las mesas y su estado
mesas = ['Mesa 1', 'Mesa 2', 'Mesa 3', 'Mesa 4', 'Mesa 5', 'Mesa 6', 'Mesa 7']
estado_mesas = {mesa: 'libre' for mesa in mesas}  # Todas inicialmente libres

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
    global estado_mesas
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        seleccionados = request.form.getlist('productos')
        mesa = request.form.get('mesa')

        if not mesa or mesa not in mesas:
            return "Debe seleccionar una mesa válida", 400

        if len(seleccionados) == 0:
            return "Debe seleccionar al menos un producto", 400

        # Guardar los productos seleccionados en un archivo CSV
        with open('ventas.csv', mode='a', newline='', encoding='utf-8') as archivo:
            escritor = csv.writer(archivo)
            fecha = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            for producto in seleccionados:
                escritor.writerow([fecha, session.get('usuario'), mesa, producto])

        # Cambiar estado mesa a ocupada
        estado_mesas[mesa] = 'ocupada'

        # Generar PDF con comanda
        buffer = BytesIO()
        p = canvas.Canvas(buffer)
        p.setFont("Helvetica-Bold", 14)
        p.drawString(100, 800, f"Comanda - Restaurante El Punto - Mesa {mesa}")
        p.setFont("Helvetica", 12)
        y = 760
        for producto in seleccionados:
            p.drawString(100, y, f"- {producto}")
            y -= 20
        p.showPage()
        p.save()
        buffer.seek(0)

        return send_file(buffer, as_attachment=True, download_name=f"comanda_mesa_{mesa}.pdf", mimetype='application/pdf')

    # GET: mostrar la página con mesas y productos
    return render_template('ventas.html', categorias=categorias, mesas=mesas, estado_mesas=estado_mesas)

@app.route('/liberar_mesa', methods=['POST'])
def liberar_mesa():
    global estado_mesas
    if 'usuario' not in session:
        return redirect(url_for('login'))

    mesa = request.form.get('mesa')
    if not mesa or mesa not in mesas:
        return "Mesa inválida", 400

    estado_mesas[mesa] = 'libre'
    return redirect(url_for('ventas_en_punto'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
