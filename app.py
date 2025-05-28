import csv
import os
from datetime import datetime
from io import BytesIO
from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
from reportlab.pdfgen import canvas

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'

# Datos fijos para la demo
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

mesas = ['1', '2', '3', '4', '5', '6', '7']


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

    # Inicializar el estado de las mesas si no existe en la sesión
    if 'estado_mesas' not in session:
        session['estado_mesas'] = {mesa: 'libre' for mesa in mesas}

    estado_mesas = session['estado_mesas']

    if request.method == 'POST':
        mesa = request.form.get('mesa')
        seleccionados = request.form.getlist('productos')

        # Marcar mesa como ocupada
        if mesa:
            estado_mesas[mesa] = 'ocupada'
            session.modified = True  # Asegura que se guarde el cambio

        # Guardar los productos en archivo CSV
        with open('ventas.csv', mode='a', newline='', encoding='utf-8') as archivo:
            escritor = csv.writer(archivo)
            fecha = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            for producto in seleccionados:
                escritor.writerow([fecha, session.get('usuario'), mesa, producto])

        # Generar comanda en PDF (opcional)
        buffer = BytesIO()
        p = canvas.Canvas(buffer)
        p.setFont("Helvetica-Bold", 14)
        p.drawString(100, 800, f"Comanda - Mesa {mesa}")
        p.setFont("Helvetica", 12)
        y = 760
        for producto in seleccionados:
            p.drawString(100, y, f"- {producto}")
            y -= 20
        p.showPage()
        p.save()
        buffer.seek(0)

        flash(f'Pedido enviado para la mesa {mesa}')
        return redirect(url_for('ventas_en_punto'))

    return render_template('ventas.html', categorias=categorias, mesas=mesas, estado_mesas=estado_mesas)


@app.route('/liberar_mesa/<mesa>', methods=['POST'])
def liberar_mesa(mesa):
    if 'estado_mesas' in session:
        session['estado_mesas'][mesa] = 'libre'
        session.modified = True
    return redirect(url_for('ventas_en_punto'))


@app.route('/pedidos_activos')
def pedidos_activos():
    pedidos = []
    try:
        with open('ventas.csv', newline='', encoding='utf-8') as archivo:
            lector = csv.reader(archivo)
            pedidos = list(lector)
    except FileNotFoundError:
        pass
    return render_template('pedidos.html', pedidos=pedidos)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
