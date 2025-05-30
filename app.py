import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, get_flashed_messages, make_response, jsonify
from extensions import db
import models
from models import Pedido, DetallePedido, CierreCaja # Asegúrate que estén definidos
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func
from io import BytesIO
from reportlab.pdfgen import canvas
from markupsafe import Markup
from datetime import datetime
from flask_migrate import Migrate
from datetime import date




#from flask import request, jsonify,redirect, url_for, flash


app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'

# Configuración DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ventas.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar extensiones
db.init_app(app)
migrate = Migrate(app, db)

def escapejs_filter(value):
    _js_escapes = {
        '\\': '\\u005C',
        '\'': '\\u0027',
        '"': '\\u0022',
        '>': '\\u003E',
        '<': '\\u003C',
        '&': '\\u0026',
        '=': '\\u003D',
        '-': '\\u003B',
        u'\u2028': '\\u2028',
        u'\u2029': '\\u2029'
    }
    retval = [_js_escapes.get(letter, letter) for letter in value]
    return Markup("".join(retval))

app.jinja_env.filters['escapejs'] = escapejs_filter

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
            flash("Credenciales inválidas", "danger")
    return render_template('login.html')


@app.route('/salon')
def salon():
    mesas = [1, 2, 3, 4, 5, 6, 7]  # o Mesa.query.all() si usas modelo Mesa
    estado_mesas = {}

    for mesa in mesas:
        pedido_activo = Pedido.query.filter_by(mesa=mesa).filter(Pedido.estado != 'pagado').first()
        if pedido_activo:
            estado_mesas[mesa] = 'ocupada'
        else:
            estado_mesas[mesa] = 'libre'

    return render_template('salon.html', mesas=mesas, estado_mesas=estado_mesas)


@app.route('/ventas')
def ventas_default():
    return redirect(url_for('ventas_en_punto', mesa='1'))

@app.route('/ventas/<mesa>', methods=['GET', 'POST'])
def ventas_en_punto(mesa):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    pedido = Pedido.query.filter_by(mesa=mesa, estado='activo').first()

    if request.method == 'POST':
        productos_str = request.form.get('productos', '')
        seleccionados = productos_str.split(',') if productos_str else []

        if seleccionados:
            try:
                if not pedido:
                    pedido = Pedido(mesa=mesa, usuario=session['usuario'], estado='activo')
                    db.session.add(pedido)
                    db.session.commit()

                # Elimina detalles previos para el pedido activo
                DetallePedido.query.filter_by(pedido_id=pedido.id).delete()

                conteo_productos = {}
                for producto in seleccionados:
                    conteo_productos[producto] = conteo_productos.get(producto, 0) + 1

                for nombre_producto, cantidad in conteo_productos.items():
                    precio = None
                    for cat in categorias.values():
                        for prod in cat:
                            if prod['nombre'] == nombre_producto:
                                precio = prod['precio']
                                break
                        if precio is not None:
                            break
                    if precio is None:
                        precio = 0

                    detalle = DetallePedido(
                        pedido_id=pedido.id,
                        producto=nombre_producto,
                        cantidad=cantidad,
                        precio=precio
                    )
                    db.session.add(detalle)

                db.session.commit()
                flash(f'Pedido guardado para la mesa {mesa}', 'success')

            except SQLAlchemyError:
                db.session.rollback()
                flash('Error al guardar el pedido', 'danger')

        else:
            flash('No hay productos seleccionados para enviar.', 'warning')

        return redirect(url_for('ventas_en_punto', mesa=mesa))

    detalles = DetallePedido.query.filter_by(pedido_id=pedido.id).all() if pedido else []

    mesas_estado = {}
    for m in mesas:
        p_activo = Pedido.query.filter_by(mesa=m, estado='activo').first()
        mesas_estado[m] = 'ocupada' if p_activo else 'libre'

    pedidos_guardados = {}
    for m in mesas:
        p = Pedido.query.filter_by(mesa=m, estado='activo').first()
        if p:
            detalles_m = DetallePedido.query.filter_by(pedido_id=p.id).all()
            pedidos_guardados[m] = detalles_m

    mensajes = get_flashed_messages(with_categories=True)

    return render_template('ventas.html',
                           categorias=categorias,
                           mesa=mesa,
                           mesas=mesas,
                           estado_mesas=mesas_estado,
                           pedido=pedido,
                           detalles=detalles,
                           mensajes=mensajes,
                           pedidos_guardados=pedidos_guardados)


@app.route('/liberar_mesa/<mesa>', methods=['POST'])
def liberar_mesa(mesa):
    pedido = Pedido.query.filter_by(mesa=mesa, estado='activo').first()
    if pedido:
        pedido.estado = 'cerrado'
        db.session.commit()
        flash(f'Mesa {mesa} liberada y pedido cerrado.', 'info')
    else:
        flash(f'Mesa {mesa} ya estaba libre.', 'warning')

    return redirect(url_for('ventas_en_punto', mesa=mesa))
    
@app.route('/facturar', methods=['POST'])
def facturar_pedido():
    mesa = request.form.get('mesa')

    # Aquí asumes que los pedidos están guardados en una base de datos o estructura
    pedido = Pedido.query.filter_by(mesa=mesa, estado='activo').order_by(Pedido.fecha.desc()).first()

    if pedido:
        pedido.estado = 'facturado'
        db.session.commit()
        flash('Pedido facturado correctamente.', 'success')
    else:
        flash('No se encontró un pedido activo para esta mesa.', 'warning')

    return redirect(url_for('ventas_en_punto', mesa=mesa))



@app.route('/cocina')
def cocina():
    pedidos = Pedido.query.filter_by(estado='pendiente').order_by(Pedido.fecha).all()
    return render_template('cocina.html', pedidos=pedidos, current_time=datetime.now())



@app.route('/marcar_preparado/<int:pedido_id>', methods=['POST'])
def marcar_preparado(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    pedido.estado = 'preparado'
    db.session.commit()
    return '', 204


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/enviar_comanda/<mesa>', methods=['POST'])
def enviar_comanda(mesa):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    pedido = Pedido.query.filter_by(mesa=mesa, estado='activo').first()
    if not pedido:
        flash(f"No hay pedido activo para la mesa {mesa}.", "warning")
        return redirect(url_for('ventas_en_punto', mesa=mesa))

    pedido.estado = 'comanda_enviada'
    try:
        db.session.commit()
        flash(f'Comanda enviada a cocina para la mesa {mesa}.', 'success')
    except SQLAlchemyError:
        db.session.rollback()
        flash('Error al enviar la comanda.', 'danger')

    return redirect(url_for('ventas_en_punto', mesa=mesa))


@app.route('/imprimir_comanda/<mesa>')
def imprimir_comanda(mesa):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    pedido = Pedido.query.filter_by(mesa=mesa, estado='activo').first()
    if not pedido:
        flash(f"No hay pedido activo para la mesa {mesa}.", "warning")
        return redirect(url_for('ventas_en_punto', mesa=mesa))

    detalles = DetallePedido.query.filter_by(pedido_id=pedido.id).all()

    return render_template('imprimir_comanda.html', pedido=pedido, detalles=detalles, mesa=mesa)


@app.route('/comanda_pdf/<mesa>')
def comanda_pdf(mesa):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    pedido = Pedido.query.filter_by(mesa=mesa, estado='activo').first()
    if not pedido:
        flash(f"No hay pedido activo para la mesa {mesa}.", "warning")
        return redirect(url_for('ventas_en_punto', mesa=mesa))

    detalles = DetallePedido.query.filter_by(pedido_id=pedido.id).all()

    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.setFont("Helvetica-Bold", 14)
    p.drawString(100, 800, f"🧾 COMANDA - Mesa {mesa}")

    y = 770
    for detalle in detalles:
        p.drawString(100, y, f"{detalle.cantidad} x {detalle.producto}")
        y -= 20

    p.showPage()
    p.save()

    buffer.seek(0)
    return make_response(buffer.getvalue(), 200, {
        'Content-Type': 'application/pdf',
        'Content-Disposition': f'inline; filename=comanda_mesa_{mesa}.pdf'
    })
 
@app.route('/cerrar_caja', methods=['POST'])
def cerrar_caja():
    hoy = date.today()
    pedidos_hoy = Pedido.query.filter(Pedido.fecha == hoy).all()

    total_ventas = sum(p.total for p in pedidos_hoy if p.estado == 'facturado')
    total_fiado = sum(p.total for p in pedidos_hoy if p.estado == 'pendiente')
    total_efectivo = total_ventas  # suponiendo que todo lo facturado fue pagado en efectivo

    cierre = CierreCaja(
        fecha=hoy,
        total_ventas=total_ventas,
        total_efectivo=total_efectivo,
        total_fiado=total_fiado,
        pedidos_facturados=len([p for p in pedidos_hoy if p.estado == 'facturado']),
        pedidos_pendientes=len([p for p in pedidos_hoy if p.estado == 'pendiente'])
    )

    db.session.add(cierre)
    db.session.commit()

    flash("Caja cerrada correctamente", "success")
    return redirect(url_for('ver_cierre_caja', cierre_id=cierre.id))
   
@app.route('/cierre_caja/<int:cierre_id>')
def ver_cierre_caja(cierre_id):
    cierre = CierreCaja.query.get_or_404(cierre_id)
    return render_template('cierre_caja.html', cierre=cierre)



@app.route('/cierre_caja/pdf/<int:cierre_id>')
def descargar_pdf_cierre(cierre_id):
    cierre = CierreCaja.query.get_or_404(cierre_id)
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    
    p.setFont("Helvetica", 14)
    p.drawString(100, 800, f"Cierre de Caja - {cierre.fecha.strftime('%d/%m/%Y')}")
    p.setFont("Helvetica", 12)
    p.drawString(100, 770, f"Total Ventas: ${cierre.total_ventas}")
    p.drawString(100, 750, f"Total Efectivo: ${cierre.total_efectivo}")
    p.drawString(100, 730, f"Total Fiado: ${cierre.total_fiado}")
    p.drawString(100, 710, f"Pedidos Facturados: {cierre.pedidos_facturados}")
    p.drawString(100, 690, f"Pedidos Pendientes: {cierre.pedidos_pendientes}")
    
    p.showPage()
    p.save()

    buffer.seek(0)
    return make_response(buffer.read(), 200, {
        'Content-Type': 'application/pdf',
        'Content-Disposition': f'inline; filename=cierre_caja_{cierre.fecha}.pdf'
    })
 
@app.route('/total_ventas_hoy')
def total_ventas_hoy():
    hoy = date.today()
    pedidos = Pedido.query.filter(Pedido.fecha == hoy, Pedido.estado == 'facturado').all()
    total = sum(p.total for p in pedidos)
    return jsonify({'total': f"{total:,.0f}"})




# --- RUTAS PARA DOMICILIOS ---

@app.route('/domicilios', methods=['GET', 'POST'])
def domicilios():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    pedidos_domicilio = Pedido.query.filter(
    Pedido.tipo == 'domicilio',
    Pedido.estado.in_(['activo', 'comanda_enviada'])
).all()


    if request.method == 'POST':
        cliente = request.form.get('cliente')
        productos_str = request.form.get('productos', '')
        seleccionados = productos_str.split(',') if productos_str else []

        if not cliente:
            flash('Debe ingresar el nombre del cliente.', 'warning')
            return redirect(url_for('domicilios'))

        if not seleccionados:
            flash('Debe seleccionar al menos un producto.', 'warning')
            return redirect(url_for('domicilios'))

        try:
            pedido_dom = Pedido(
                tipo='domicilio',
                cliente_nombre=cliente,
                usuario=session['usuario'],
                estado='activo'
            )
            db.session.add(pedido_dom)
            db.session.commit()

            conteo_productos = {}
            for producto in seleccionados:
                conteo_productos[producto] = conteo_productos.get(producto, 0) + 1

            for nombre_producto, cantidad in conteo_productos.items():
                precio = None
                for cat in categorias.values():
                    for prod in cat:
                        if prod['nombre'] == nombre_producto:
                            precio = prod['precio']
                            break
                    if precio is not None:
                        break
                if precio is None:
                    precio = 0

                detalle_dom = DetallePedido(
                    pedido_id=pedido_dom.id,
                    producto=nombre_producto,
                    cantidad=cantidad,
                    precio=precio
                )
                db.session.add(detalle_dom)

            db.session.commit()
            flash('Pedido a domicilio guardado correctamente.', 'success')
            return redirect(url_for('domicilios'))

        except SQLAlchemyError:
            db.session.rollback()
            flash('Error al guardar el pedido a domicilio.', 'danger')

        return redirect(url_for('domicilios'))

    return render_template('domicilios.html', categorias=categorias, pedidos=pedidos_domicilio, datetime=datetime)



@app.route('/domicilios/enviar_cocina/<int:pedido_id>', methods=['POST'])
def enviar_cocina_domicilio(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    if pedido.tipo != 'domicilio':
        flash('Pedido no corresponde a domicilio.', 'danger')
        return redirect(url_for('domicilios'))

    pedido.estado = 'comanda_enviada'
    try:
        db.session.commit()
        flash('Comanda enviada a cocina para domicilio.', 'success')
    except SQLAlchemyError:
        db.session.rollback()
        flash('Error al enviar la comanda a cocina.', 'danger')
    return redirect(url_for('domicilios'))



@app.route('/domicilios/marcar_preparado/<int:pedido_id>', methods=['POST'])
def marcar_preparado_domicilio(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    if pedido.tipo != 'domicilio':
        return '', 400  # Bad request si no es domicilio

    pedido.estado = 'preparado'
    db.session.commit()
    return '', 204
    
@app.route('/domicilios/marcar_pagado/<int:pedido_id>', methods=['POST'])
def marcar_pagado_domicilio(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)
    if pedido.tipo != 'domicilio':
        flash('Pedido no corresponde a domicilio.', 'danger')
        return redirect(url_for('domicilios'))
    pedido.estado = 'pagado'
    try:
        db.session.commit()
        flash('Pedido marcado como pagado.', 'success')
    except SQLAlchemyError:
        db.session.rollback()
        flash('Error al marcar pedido como pagado.', 'danger')
    return redirect(url_for('domicilios'))

@app.route('/guardar_pedido_finalizado/<mesa>', methods=['POST'])
def guardar_pedido_finalizado(mesa):
    if 'usuario' not in session:
        return jsonify(success=False, mensaje='No autorizado'), 401

    pedido = Pedido.query.filter_by(mesa=mesa, estado='activo').first()
    if not pedido:
        return jsonify(success=False, mensaje='No hay pedido activo para esta mesa.')

    data = request.get_json()
    accion = data.get('accion')

    try:
        # Cambia estado a finalizado, facturado, o similar para guardar en historial
        pedido.estado = 'finalizado'  # o 'facturado' según tu lógica
        db.session.commit()

        url_imprimir = None
        if accion == 'imprimir':
            # Devuelve la url para imprimir el ticket
            url_imprimir = url_for('comanda_pdf', mesa=mesa)

        mensaje = 'Pedido guardado correctamente.'
        if accion == 'imprimir':
            mensaje = 'Pedido guardado y listo para imprimir.'
        elif accion == 'facturar':
            mensaje = 'Pedido guardado como facturado.'

        return jsonify(success=True, mensaje=mensaje, url_imprimir=url_imprimir)

    except Exception as e:
        db.session.rollback()
        return jsonify(success=False, mensaje='Error al guardar el pedido.')



@app.route('/reportes')
def reportes():
    producto_filtro = request.args.get('producto')
    fecha_filtro = request.args.get('fecha')

    # Obtener pedidos facturados
    pedidos = Pedido.query.filter(Pedido.estado == 'pagado').all()
    #pedidos = Pedido.query.filter(Pedido.estado == 'activo').order_by(Pedido.fecha.desc()).all()

    # Lista detallada por producto
    resultados = []
    for pedido in pedidos:
        for detalle in pedido.detalles:
            if producto_filtro and producto_filtro.lower() not in detalle.producto.lower():
                continue
            if fecha_filtro and pedido.fecha.strftime('%Y-%m-%d') != fecha_filtro:
                continue

            resultados.append({
                'pedido_id': pedido.id,
                'fecha': pedido.fecha.strftime('%Y-%m-%d %H:%M'),
                'tipo': pedido.tipo,
                'mesa': pedido.mesa if pedido.tipo == 'salon' else None,
                'cliente': pedido.cliente_nombre if pedido.tipo == 'domicilio' else None,
                'producto': detalle.producto,
                'cantidad': detalle.cantidad,
                'precio': detalle.precio,
                'total': detalle.precio * detalle.cantidad
            })

    return render_template('reportes.html', pedidos=pedidos, resultados=resultados)




if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
