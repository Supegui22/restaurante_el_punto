import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, get_flashed_messages
from models import db, Pedido, DetallePedido
from sqlalchemy.exc import SQLAlchemyError

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'

# Configuración de SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ventas.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# Datos fijos para la demo
categorias = {
    'Almuerzos': [
        {'nombre': 'Menú día', 'precio': 15000, 'imagen': 'menu_dia.png'},
        {'nombre': 'Sopa del día', 'precio': 8000, 'imagen': 'sopa_dia.png'},
        {'nombre': 'Arroz con pollo', 'precio': 12000, 'imagen': 'arroz_pollo.png'}
    ],
    'Bebidas': [
        {'nombre': 'Jugo natural', 'precio': 5000, 'imagen': 'jugo_natural.png'},
        {'nombre': 'Agua', 'precio': 2000, 'imagen': 'agua.png'},
        {'nombre': 'Refresco', 'precio': 4000, 'imagen': 'refresco.png'}
    ]
}

usuarios = {
    'admin@example.com': {'password': '1234', 'rol': 'Admin'},
    'domiciliario@example.com': {'password': '1234', 'rol': 'Domiciliario'}
}

mesas = ['1', '2', '3', '4', '5', '6', '7']

@app.before_first_request
def crear_tablas():
    db.create_all()

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        password = request.form['password']
        user = usuarios.get(correo)
        if user and user['password'] == password:
            session['usuario'] = correo
            session['rol'] = user['rol']
            if 'estado_mesas' not in session:
                session['estado_mesas'] = {mesa: 'libre' for mesa in mesas}
            return redirect(url_for('salon'))
        else:
            return "Credenciales inválidas", 401
    return render_template('login.html')

@app.route('/salon')
def salon():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    estado_mesas = session.get('estado_mesas', {mesa: 'libre' for mesa in mesas})
    return render_template('salon.html', mesas=mesas, estado_mesas=estado_mesas)

@app.route('/ventas/<mesa>', methods=['GET', 'POST'])
def ventas_en_punto(mesa):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    if 'estado_mesas' not in session:
        session['estado_mesas'] = {m: 'libre' for m in mesas}
    estado_mesas = session['estado_mesas']

    if request.method == 'POST':
        seleccionados = request.form.getlist('productos')

        if mesa and seleccionados:
            try:
                # Buscar pedido activo para esta mesa
                pedido = Pedido.query.filter_by(mesa=mesa, estado='activo').first()
                if not pedido:
                    pedido = Pedido(mesa=mesa, estado='activo')
                    db.session.add(pedido)
                    db.session.commit()

                # Contar productos seleccionados
                conteo_productos = {}
                for producto in seleccionados:
                    conteo_productos[producto] = conteo_productos.get(producto, 0) + 1

                # Agregar productos al pedido
                for nombre_producto, cantidad in conteo_productos.items():
                    detalle = DetallePedido(
                        pedido_id=pedido.id,
                        producto=nombre_producto,
                        cantidad=cantidad
                    )
                    db.session.add(detalle)

                db.session.commit()
                estado_mesas[mesa] = 'ocupada'
                session.modified = True
                flash(f'Pedido guardado para la mesa {mesa}', 'success')

            except SQLAlchemyError as e:
                db.session.rollback()
                flash('Error al guardar el pedido', 'danger')

        return redirect(url_for('ventas_en_punto', mesa=mesa))

    mensajes = get_flashed_messages()
    return render_template('ventas.html', categorias=categorias, mesa=mesa, mesas=mesas, estado_mesas=estado_mesas, mensajes=mensajes)

@app.route('/liberar_mesa/<mesa>', methods=['POST'])
def liberar_mesa(mesa):
    if 'estado_mesas' in session:
        session['estado_mesas'][mesa] = 'libre'
        session.modified = True
    return redirect(url_for('ventas_en_punto', mesa=mesa))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
