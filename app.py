
import os
import openpyxl
import shutil
import json
import io
import pandas as pd
import pytz
from flask import Flask, render_template, request, redirect, url_for, session, flash, get_flashed_messages, make_response, jsonify, send_file
from extensions import db
import models
from models import Usuario, Rol, RolPermiso, Permiso, Pedido, DetallePedido, CierreCaja, Producto, Categoria, Gasto # Asegúrate que estén definidos
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, and_
from io import BytesIO
from reportlab.pdfgen import canvas
from markupsafe import Markup
from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import date, time
from werkzeug.utils import secure_filename
from functools import wraps
from werkzeug.security import check_password_hash, generate_password_hash  # Solo si usas hashes
from pytz import timezone
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch



app = Flask(__name__)
app.secret_key = 'tu_clave_secreta'

app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'images')

# Configuración de la base de datos
if 'DATABASE_URL' in os.environ:
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ventas.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicializar extensiones
db.init_app(app)
migrate = Migrate(app, db)


def requiere_permiso(nombre_permiso):
    def decorador(func):
        @wraps(func)
        def envoltura(*args, **kwargs):
            usuario_id = session.get('usuario_id')
            if not usuario_id:
                flash("Debes iniciar sesión", "warning")
                return redirect(url_for('login'))

            usuario = Usuario.query.get(usuario_id)
            if not usuario:
                flash("Usuario no encontrado", "danger")
                return redirect(url_for('login'))

            permisos_usuario = [
                rp.permiso.nombre for rp in RolPermiso.query.filter_by(rol_id=usuario.rol_id).all()
            ]

            if nombre_permiso not in permisos_usuario:
                flash(f"No tienes permiso para acceder a esta página ({nombre_permiso})", "danger")
                return redirect(url_for('inicio'))

            return func(*args, **kwargs)
        return envoltura
    return decorador

    

def requiere_permisos(*permisos_requeridos):
    def decorador(func):
        @wraps(func)
        def envoltura(*args, **kwargs):
            usuario_id = session.get('usuario_id')
            if not usuario_id:
                flash("Debes iniciar sesión", "warning")
                return redirect(url_for('login'))

            usuario = Usuario.query.get(usuario_id)
            if not usuario:
                flash("Usuario no encontrado", "danger")
                return redirect(url_for('login'))

            permisos_usuario = [
                rp.permiso.nombre for rp in RolPermiso.query.filter_by(rol_id=usuario.rol_id).all()
            ]

            # Verifica que el usuario tenga al menos uno de los permisos requeridos
            # Verifica que el usuario tenga todos los permisos requeridos
            if not all(p in permisos_usuario for p in permisos_requeridos):
                flash("No tienes permisos para acceder a esta página", "danger")
                return redirect(url_for('inicio'))

            return func(*args, **kwargs)
        return envoltura
    return decorador





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

  

def obtener_categorias_y_productos_desde_bd():
    categorias = {}
    categorias_nombres = {}
    
    categorias_obj = Categoria.query.order_by(Categoria.nombre).all()
    for cat in categorias_obj:
        categorias_nombres[cat.id] = cat.nombre  # Guardamos nombre por ID
        productos_cat = Producto.query.filter_by(categoria_id=cat.id).order_by(Producto.nombre).all()
        categorias[cat.nombre] = [
            {
                'id': prod.id,
                'nombre': prod.nombre,
                'precio': prod.precio,
                'imagen': prod.imagen,
                'stock': prod.stock
            } for prod in productos_cat
        ]
    return categorias, categorias_nombres
    
usuarios = {
    #'admin@example.com': {'password': '1234', 'rol': 'Admin'},
    #'domiciliario@example.com': {'password': '1234', 'rol': 'Domiciliario'}
}

# aquí tus rutas (incluida /ventas/<mesa>)

    #categorias = obtener_categorias_y_productos_desde_bd()
    # resto de la función...

# /*
mesas = ['1', '2', '3', '4', '5', '6', '7']


@app.route('/inicio')
def inicio():
    return render_template('inicio.html')


@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['correo']
        password = request.form['password']

        usuario = Usuario.query.filter_by(correo=correo).first()

        if usuario and check_password_hash(usuario.password, password):
            session['usuario_id'] = usuario.id
            session['usuario'] = usuario.correo
            session['rol'] = usuario.rol.nombre

            # ✅ Guardar permisos del rol en sesión
            permisos = [
                rp.permiso.nombre for rp in RolPermiso.query.filter_by(rol_id=usuario.rol_id).all()
            ]
            session['permisos'] = permisos

            # ✅ Estado de las mesas
            if 'estado_mesas' not in session:
                session['estado_mesas'] = {mesa: 'libre' for mesa in mesas}

            # ✅ Redirigir según el rol
            rol = usuario.rol.nombre.lower()
            if rol == 'administrador':
                return redirect(url_for('inicio'))
            elif rol == 'cocinero':
                return redirect(url_for('cocina'))  # Ajusta el nombre si es distinto
            elif rol == 'cajero':
                return redirect(url_for('inicio'))    
            elif rol == 'domiciliario':
                return redirect(url_for('domicilios'))
            else:
                flash('Este rol no tiene acceso asignado aún.', 'warning')
                return redirect(url_for('login'))
        else:
            flash("Credenciales inválidas", "danger")

    return render_template('login.html')




@app.route('/salon')
@requiere_permiso('ver_salon')
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


#@app.route('/ventas/<int:mesa_id>', endpoint='ventas')
#@requiere_permisos('ver_ventas')
#def ventas_default(mesa_id):
#    return redirect(url_for('ventas_en_punto', mesa='1'))



@app.route('/ventas/<mesa>', methods=['GET', 'POST'])
@requiere_permisos('ver_ventas', 'crear_pedido')
def ventas_en_punto(mesa):
    mesas = [1, 2, 3, 4, 5, 6, 7]
    categorias, categorias_nombres = obtener_categorias_y_productos_desde_bd()

    if 'usuario' not in session:
        return redirect(url_for('login'))

    es_domicilio = False
    mesa_id = None

    if mesa == 'domicilio':
        es_domicilio = True
    else:
        try:
            mesa_id = int(mesa)
            if mesa_id not in mesas:
                flash('Mesa inválida.', 'danger')
                return redirect(url_for('salon'))
        except ValueError:
            flash('Parámetro inválido.', 'danger')
            return redirect(url_for('salon'))

    # ✅ Obtener categoría y página actual desde query params
    categoria_activa = request.args.get('categoria')
    pagina_actual = int(request.args.get('pagina', 1))
    productos_por_pagina = 9
    productos_categoria_paginados = []
    total_paginas = 1

    if categoria_activa and categoria_activa in categorias:
        productos_todos = categorias[categoria_activa]
        total_paginas = (len(productos_todos) + productos_por_pagina - 1) // productos_por_pagina
        inicio = (pagina_actual - 1) * productos_por_pagina
        fin = inicio + productos_por_pagina
        productos_categoria_paginados = productos_todos[inicio:fin]

    if es_domicilio:
        pedido = Pedido.query.filter_by(mesa=None, estado='activo', tipo='domicilio').first()
        if not pedido:
            pedido = Pedido.query.filter_by(mesa=None, tipo='domicilio').order_by(Pedido.fecha.desc()).first()
    else:
        pedido = Pedido.query.filter_by(mesa=mesa_id, estado='activo', tipo='salon').first()
        if not pedido:
            pedido = Pedido.query.filter_by(mesa=mesa_id, tipo='salon').order_by(Pedido.fecha.desc()).first()

    if request.method == 'POST':
        productos_str = request.form.get('productos', '')
        print("📦 Productos recibidos (raw):", productos_str)

        if not productos_str.strip():
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'Faltan productos'}), 400
            flash('No se recibieron productos.', 'warning')
            return redirect(url_for('ventas_en_punto', mesa=mesa))

        try:
            seleccionados = json.loads(productos_str)
        except Exception as e:
            print("❌ Error al parsear JSON:", str(e))
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'JSON inválido'}), 400
            flash('Los datos del pedido no son válidos.', 'danger')
            return redirect(url_for('ventas_en_punto', mesa=mesa))

        if seleccionados:
            try:
                for nombre_producto, info in seleccionados.items():
                    cantidad = info.get('cantidad', 0)
                    if cantidad <= 0:
                        continue
                    producto_bd = Producto.query.filter_by(nombre=nombre_producto).first()
                    if not producto_bd:
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return jsonify({'success': False, 'error': f'Producto {nombre_producto} no encontrado.'}), 400
                        flash(f'Producto {nombre_producto} no encontrado.', 'danger')
                        return redirect(url_for('ventas_en_punto', mesa=mesa))
                    if producto_bd.stock < cantidad:
                        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                            return jsonify({'success': False, 'error': f'Stock insuficiente para {nombre_producto}'}), 400
                        flash(f'Stock insuficiente para el producto {nombre_producto}. Disponible: {producto_bd.stock}', 'warning')
                        return redirect(url_for('ventas_en_punto', mesa=mesa))

                if not pedido or pedido.estado != 'activo':
                    pedido = Pedido(
                        mesa=mesa_id,
                        usuario=session['usuario'],
                        estado='activo',
                        tipo='domicilio' if es_domicilio else 'salon'
                    )
                    db.session.add(pedido)
                    db.session.commit()

                DetallePedido.query.filter_by(pedido_id=pedido.id).delete()

                precios_productos = {
                    prod['nombre']: prod['precio']
                    for cat_productos in categorias.values()
                    for prod in cat_productos
                }

                for nombre_producto, info in seleccionados.items():
                    cantidad = info.get('cantidad', 0)
                    descripcion = info.get('descripcion', '')
                    if cantidad <= 0:
                        continue
                    precio = precios_productos.get(nombre_producto, 0)
                    producto_bd = Producto.query.filter_by(nombre=nombre_producto).first()

                    detalle = DetallePedido(
                        pedido_id=pedido.id,
                        producto_id=producto_bd.id,
                        producto=nombre_producto,
                        cantidad=cantidad,
                        precio=precio,
                        descripcion=descripcion
                    )
                    db.session.add(detalle)
                    producto_bd.stock -= cantidad

                db.session.commit()

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': True})

                flash(f'Pedido guardado para {"domicilio" if es_domicilio else "mesa " + str(mesa_id)}', 'success')

            except SQLAlchemyError:
                db.session.rollback()
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'error': 'Error al guardar el pedido'}), 500
                flash('Error al guardar el pedido.', 'danger')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': 'No hay productos seleccionados'}), 400
            flash('No hay productos seleccionados para enviar.', 'warning')
            return redirect(url_for('ventas_en_punto', mesa=mesa))

    detalles = DetallePedido.query.filter_by(pedido_id=pedido.id).all() if pedido else []

    mesas_estado = {
        m: 'ocupada' if Pedido.query.filter_by(mesa=m, estado='activo', tipo='salon').first() else 'libre'
        for m in mesas
    } if not es_domicilio else None

    pedido_guardado = {
        d.producto: {
            'cantidad': d.cantidad,
            'descripcion': d.descripcion,
            'precio': d.precio
        } for d in detalles
    } if detalles and pedido and pedido.estado == 'activo' else {}

    hay_productos_enviados = bool(pedido_guardado)

    hoy = date.today()
    cierre_existente = CierreCaja.query.filter_by(fecha=hoy, guardado=True).first()
    total_vendido_hoy = 0 if cierre_existente else (
        db.session.query(func.sum(DetallePedido.cantidad * DetallePedido.precio))
        .join(Pedido, Pedido.id == DetallePedido.pedido_id)
        .filter(func.date(Pedido.fecha) == hoy, Pedido.estado == 'facturado')
        .scalar() or 0
    )

    ventas_dia = Pedido.query.filter(
        func.date(Pedido.fecha) == hoy,
        Pedido.estado == 'facturado'
    ).order_by(Pedido.fecha.desc()).all()

    return render_template(
        'ventas.html',
        categorias=categorias,
        categorias_nombres=categorias_nombres,
        mesa=mesa_id,
        mesas=mesas,
        estado_mesas=mesas_estado,
        pedido=pedido,
        detalles=detalles,
        pedido_guardado=pedido_guardado,
        es_domicilio=es_domicilio,
        total_vendido_hoy=total_vendido_hoy,
        hay_productos_enviados=hay_productos_enviados,
        ventas_dia=ventas_dia,
        categoria_activa=categoria_activa,
        pagina_actual=pagina_actual,
        productos_categoria=productos_categoria_paginados,
        total_paginas=total_paginas,
        mensajes=get_flashed_messages(with_categories=True)
    )



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
@requiere_permiso('facturar_pedido')
def facturar_pedido():
    mesa = request.form.get('mesa')
    id_pedido = request.form.get('id_pedido')
    pedido = None

    if mesa:
        pedido = Pedido.query.filter_by(mesa=mesa, estado='activo').order_by(Pedido.fecha.desc()).first()
    elif id_pedido:
        pedido = Pedido.query.filter_by(id=id_pedido, estado='pendiente').first()

    if pedido:
        pedido.estado = 'facturado'

        if pedido.tipo == 'salon':
            pedido.estado_pago = '-'
        elif pedido.tipo == 'domicilio' and not pedido.estado_pago:
            pedido.estado_pago = 'Fiado'

        db.session.commit()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': True})

        flash('Pedido facturado correctamente.', 'success')

        if pedido.mesa:
            return redirect(url_for('ventas_en_punto', mesa=pedido.mesa))
        else:
            return redirect(url_for('domicilios'))
    else:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'error': 'No se encontró un pedido válido'}), 404

        flash('No se encontró un pedido válido para facturar.', 'warning')
        return redirect(url_for('domicilios'))



@app.route('/cocina')
@requiere_permiso('ver_cocina')
def cocina():
    # Pedidos por mesa (tipo salón)
    pedidos_mesas = Pedido.query.filter_by(tipo='salon').filter(
        Pedido.estado.in_(['activo'])
    ).order_by(Pedido.fecha.desc()).all()

    # Pedidos a domicilio
    pedidos_domicilios = Pedido.query.filter_by(tipo='domicilio').filter(
        Pedido.estado_pago.in_(['fiado','pago', ])
    ).order_by(Pedido.fecha.desc()).all()

    # Serialización para adaptar al template
    def serializar(p):
        return {
            'id': p.id,
            'mesa': p.mesa,
            'cliente': p.cliente_nombre,
            'estado': p.estado,
            'fecha': p.fecha,
            'productos': [{'producto': d.producto, 'cantidad': d.cantidad, 'descripcion': d.descripcion or ''} for d in p.detalles]
        }

    pedidos_mesas = [serializar(p) for p in pedidos_mesas]
    pedidos_domicilios = [serializar(p) for p in pedidos_domicilios]

    return render_template('cocina.html',
                           pedidos_mesas=pedidos_mesas,
                           pedidos_domicilios=pedidos_domicilios,
                           current_time=datetime.now())



@app.route('/marcar_preparado/<int:pedido_id>', methods=['POST'])
@requiere_permiso('marcar_pedido_preparado')
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

@app.route('/factura_pdf/<mesa>')
def factura_pdf(mesa):
    if mesa == 'domicilio':
        # Buscar pedido de domicilio que esté activo o fiado (pendiente de pago)
        pedido = Pedido.query.filter(
            Pedido.mesa == None,
            Pedido.tipo == 'domicilio',
            db.or_(
                Pedido.estado == 'activo',
                Pedido.estado_pago == 'fiado'
            )
        ).order_by(Pedido.fecha.desc()).first()
    else:
        try:
            mesa_id = int(mesa)
        except ValueError:
            return "Mesa inválida", 400

        # Buscar pedido de salón activo
        pedido = Pedido.query.filter_by(
            mesa=mesa_id,
            tipo='salon',
            estado='activo'
        ).order_by(Pedido.fecha.desc()).first()

    if not pedido:
        return "No hay pedido activo", 404

    detalles = DetallePedido.query.filter_by(pedido_id=pedido.id).all()
    total = sum(d.precio_total for d in detalles)

    rendered = render_template('factura_pdf.html', pedido=pedido, detalles=detalles, total=total)

    from weasyprint import HTML
    pdf = HTML(string=rendered).write_pdf()

    from flask import Response
    return Response(pdf, mimetype='application/pdf',
                    headers={'Content-Disposition': f'inline; filename=factura_{mesa}.pdf'})

@app.route('/factura_pdf_id/<int:pedido_id>')
def factura_pdf_por_id(pedido_id):
    pedido = Pedido.query.get(pedido_id)

    if not pedido:
        return "Pedido no encontrado", 404

    detalles = DetallePedido.query.filter_by(pedido_id=pedido.id).all()
    total = sum(d.precio_total for d in detalles)

    rendered = render_template('factura_pdf.html', pedido=pedido, detalles=detalles, total=total)

    from weasyprint import HTML
    pdf = HTML(string=rendered).write_pdf()

    from flask import Response
    return Response(pdf, mimetype='application/pdf',
                    headers={'Content-Disposition': f'inline; filename=factura_{pedido_id}.pdf'})


@app.route('/historial_facturas', methods=['GET', 'POST'])
@requiere_permisos('ver_historial_facturas')
def historial_facturas():
    filtro_fecha = request.args.get('fecha')
    filtro_tipo = request.args.get('tipo')

    pedidos = []

    # Filtro de fecha
    fecha = None
    if filtro_fecha:
        try:
            fecha = datetime.strptime(filtro_fecha, '%Y-%m-%d').date()
        except ValueError:
            flash("Formato de fecha inválido", "danger")

    # Filtrado según el tipo
    if filtro_tipo == 'fiado':
        query = Pedido.query.filter_by(tipo='domicilio', estado_pago='fiado')
    else:
        query = Pedido.query.filter_by(estado='facturado')
        if filtro_tipo in ['salon', 'domicilio']:
            query = query.filter_by(tipo=filtro_tipo)

    # Aplicar filtro de fecha si corresponde
    if fecha:
        query = query.filter(db.func.date(Pedido.fecha) == fecha)

    pedidos = query.order_by(Pedido.fecha.desc()).all()

    return render_template('historial_facturas.html', pedidos=pedidos,
                           fecha=filtro_fecha, tipo=filtro_tipo)

@app.route('/cobrar_pedido_fiado/<int:pedido_id>', methods=['POST'])
@requiere_permisos('facturar_pedido')
def cobrar_pedido_fiado(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)

    if pedido.tipo != 'domicilio' or pedido.estado_pago != 'fiado':
        flash('Este pedido no es un pedido fiado válido.', 'warning')
        return redirect(url_for('historial_facturas'))

    pedido.estado_pago = 'pagado'
    pedido.fecha_pago = datetime.utcnow()
    pedido.estado = 'facturado'

    db.session.commit()
    flash('Pedido fiado marcado como pagado y facturado correctamente.', 'success')
    return redirect(url_for('historial_facturas'))



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

    # Todos los pedidos del día
    pedidos_hoy = Pedido.query.filter(func.date(Pedido.fecha) == hoy).all()

    if not pedidos_hoy:
        flash("⚠️ Su cierre no se realizó correctamente. No hay pedidos registrados hoy.", "warning")
        return redirect(url_for('inicio'))

    # Solo validar pendientes en pedidos del salón
    pedidos_pendientes = [
        p for p in pedidos_hoy
        if p.tipo == 'salon' and p.estado != 'facturado'
    ]

    if pedidos_pendientes:
        flash("⚠️ Su cierre no se realizó. Aún hay pedidos del salón no facturados.", "warning")
        return redirect(url_for('inicio'))

    # Calcular totales según tipo y estado
    total_ventas = 0
    total_fiado = 0
    pedidos_facturados = 0
    pedidos_fiados = 0

    for pedido in pedidos_hoy:
        subtotal = sum(d.cantidad * d.precio for d in pedido.detalles)
        if pedido.estado == 'facturado':
            total_ventas += subtotal
            pedidos_facturados += 1
        elif pedido.tipo == 'domicilio' and pedido.estado != 'facturado':
            total_fiado += subtotal
            pedidos_fiados += 1

    cierre = CierreCaja(
        fecha=hoy,
        total_ventas=total_ventas + total_fiado,
        total_efectivo=total_ventas,
        total_fiado=total_fiado,
        pedidos_facturados=pedidos_facturados,
        pedidos_pendientes=pedidos_fiados  # aquí puedes decidir si llamarlo así
    )

    db.session.add(cierre)
    db.session.commit()

    flash("✅ Caja cerrada correctamente", "success")
    return redirect(url_for('ver_cierre_caja', cierre_id=cierre.id))




@app.route('/cierre_caja/<int:cierre_id>')
def ver_cierre_caja(cierre_id):
    cierre = CierreCaja.query.get_or_404(cierre_id)

    # Obtener todos los pedidos con fecha del pedido igual a la del cierre
    pedidos_del_dia = Pedido.query.filter(func.date(Pedido.fecha) == cierre.fecha.date()).all()

    pedidos_facturados_list = []
    pedidos_fiados_list = []

    for p in pedidos_del_dia:
        # Nombre del cliente o mesa
        if p.tipo == 'domicilio':
            p.cliente = p.cliente_nombre if p.cliente_nombre and p.cliente_nombre.strip() else "Sin nombre"
        else:
            p.cliente = f"Mesa {p.mesa}" if p.mesa else "Mesa ?"

        if p.estado == 'facturado':
            pedidos_facturados_list.append(p)
        elif p.tipo == 'domicilio' and p.estado != 'facturado':
            pedidos_fiados_list.append(p)

    # 🔸 Obtener pedidos fiados que fueron pagados hoy (fecha_pago coincide con fecha del cierre)
    pedidos_fiados_cobrados = Pedido.query.filter(
    Pedido.estado_pago == 'pagado',
    Pedido.tipo == 'domicilio',
    func.date(Pedido.fecha_pago) == cierre.fecha.date()
    ).all()


    for p in pedidos_fiados_cobrados:
        p.cliente = p.cliente_nombre or "Sin nombre"

    total_fiados_cobrados = sum(p.total for p in pedidos_fiados_cobrados)

    return render_template(
        'cierre_caja.html',
        cierre=cierre,
        pedidos_facturados_list=pedidos_facturados_list,
        pedidos_fiados_list=pedidos_fiados_list,
        pedidos_fiados_cobrados=pedidos_fiados_cobrados,
        total_fiados_cobrados=total_fiados_cobrados
    )



@app.route('/guardar_cierre/<int:cierre_id>', methods=['POST'])
def guardar_cierre_caja(cierre_id):
    cierre = CierreCaja.query.get_or_404(cierre_id)
    if cierre.guardado:
        flash("Este cierre ya fue guardado en el histórico.", "info")
        return redirect(url_for('ver_cierre_caja', cierre_id=cierre.id))

    # Marcar cierre como guardado
    cierre.guardado = True

    # Obtener pedidos del día actual
    pedidos_del_dia = Pedido.query.filter(
        db.func.date(Pedido.fecha) == cierre.fecha,
        Pedido.estado.in_(['Facturado', 'Fiado'])
    ).all()

    # Marcar pedidos como cerrados o archivados
    for pedido in pedidos_del_dia:
        pedido.estado = 'Cerrado'  # o 'Archivado', o crea un nuevo estado si prefieres

    db.session.commit()
    flash("✅ Cierre guardado y pedidos archivados correctamente.", "success")
    return redirect(url_for('historico_cierres'))


@app.route('/historico_cierres')
@requiere_permisos('historico_cierres')
def historico_cierres():
    cierres = CierreCaja.query.filter_by(guardado=True).order_by(CierreCaja.fecha.desc()).all()
    return render_template('historico_cierres.html', cierres=cierres)



from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from io import BytesIO
from flask import make_response
from sqlalchemy import func

@app.route('/cierre_caja/pdf/<int:cierre_id>')
def descargar_pdf_cierre(cierre_id):
    cierre = CierreCaja.query.get_or_404(cierre_id)

    # 🔹 Recuperar pedidos del día
    pedidos_del_dia = Pedido.query.filter(func.date(Pedido.fecha) == cierre.fecha).all()
    pedidos_facturados = []
    pedidos_fiados = []

    for p in pedidos_del_dia:
        p.total = sum(d.cantidad * d.precio for d in p.detalles)
        if p.tipo == 'domicilio':
            p.cliente = p.cliente_nombre or "Sin nombre"
        else:
            p.cliente = f"Mesa {p.mesa}" if p.mesa else "Mesa ?"

        if p.estado == 'facturado':
            pedidos_facturados.append(p)
        elif p.tipo == 'domicilio' and p.estado != 'facturado':
            pedidos_fiados.append(p)

    # 🔸 Fiados cobrados hoy
    pedidos_fiados_cobrados = Pedido.query.filter(
        Pedido.estado_pago == 'pagado',
        Pedido.tipo == 'domicilio',
        func.date(Pedido.fecha_pago) == cierre.fecha
    ).all()
    for p in pedidos_fiados_cobrados:
        p.total = sum(d.cantidad * d.precio for d in p.detalles)
        p.cliente = p.cliente_nombre or "Sin nombre"

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 50

    def draw_text(text, font_size=10, bold=False):
        nonlocal y
        if y < 100:
            p.showPage()
            y = height - 50
        p.setFont("Helvetica-Bold" if bold else "Helvetica", font_size)
        p.drawString(60, y, text)
        y -= 15

    # 🔹 Encabezado
    draw_text(f"Cierre de Caja - {cierre.fecha.strftime('%d/%m/%Y')}", 12, True)
    draw_text(f"Total Ventas: ${cierre.total_ventas:,.0f}")
    draw_text(f"Total Efectivo: ${cierre.total_efectivo:,.0f}")
    draw_text(f"Total Fiado: ${cierre.total_fiado:,.0f}")
    draw_text(f"Pedidos Facturados: {cierre.pedidos_facturados}")
    draw_text(f"Pedidos Pendientes: {cierre.pedidos_pendientes}")
    draw_text(" ")

    # 📄 Pedidos Facturados
    if pedidos_facturados:
        draw_text("Pedidos Facturados", 11, True)
        for pedido in pedidos_facturados:
            hora = pedido.fecha.strftime("%H:%M")
            draw_text(f"{pedido.cliente} - ${pedido.total:,.0f} - {hora}")

    # 📌 Pedidos Fiados
    if pedidos_fiados:
        draw_text(" ")
        draw_text("Pedidos Fiados", 11, True)
        for pedido in pedidos_fiados:
            hora = pedido.fecha.strftime("%H:%M")
            draw_text(f"{pedido.cliente} - ${pedido.total:,.0f} - {hora}")

    # 💸 Fiados Cobrados
    if pedidos_fiados_cobrados:
        draw_text(" ")
        draw_text("Pedidos Fiados Cobrados", 11, True)
        total_fiados_cobrados = sum(p.total for p in pedidos_fiados_cobrados)
        draw_text(f"Total Cobrados: ${total_fiados_cobrados:,.0f}")
        for pedido in pedidos_fiados_cobrados:
            fiado_el = pedido.fecha.strftime("%d/%m/%Y")
            cobro = pedido.fecha_pago.strftime("%d/%m/%Y")
            draw_text(f"{pedido.cliente} - ${pedido.total:,.0f} - Fiado: {fiado_el} - Cobrado: {cobro}")

    # 🔚 Final
    p.showPage()
    p.save()

    buffer.seek(0)
    return make_response(buffer.read(), 200, {
        'Content-Type': 'application/pdf',
        'Content-Disposition': f'inline; filename=cierre_caja_{cierre.fecha.strftime("%Y%m%d")}.pdf'
    })




 
@app.route('/total_ventas_hoy')
def total_ventas_hoy():
    hoy = date.today()
    inicio_dia = datetime.combine(hoy, time.min)  # hoy 00:00:00
    fin_dia = datetime.combine(hoy, time.max)     # hoy 23:59:59.999999

    pedidos = Pedido.query.filter(
        Pedido.fecha >= inicio_dia,
        Pedido.fecha <= fin_dia,
        Pedido.estado == 'facturado'  # O 'facturado' si ese es el estado correcto, ajusta según tu lógica
    ).all()

    total = 0
    for pedido in pedidos:
        total += sum(detalle.precio_total for detalle in pedido.detalles)

    return jsonify({'total': total})
    
@app.route('/estados_pedidos')
def estados_pedidos():
    estados = db.session.query(Pedido.estado).distinct().all()
    estados_lista = [e[0] for e in estados]
    return jsonify(estados_lista)





# --- RUTAS PARA DOMICILIOS ---

@app.route('/prueba_pedidos')
def prueba_pedidos():
    from sqlalchemy import func
    pedidos = Pedido.query.filter(
        Pedido.tipo == 'domicilio',
        func.lower(Pedido.estado_pago).in_(['fiado', 'pago', 'pagado']),
        func.lower(Pedido.estado).in_(['facturado', 'activo', 'preparado', 'pendiente'])
    ).order_by(Pedido.fecha.desc()).all()

    salida = []
    for p in pedidos:
        salida.append(f"<strong>Pedido ID:</strong> {p.id}, Estado: {p.estado}, Pago: {p.estado_pago}, Fecha: {p.fecha}<br>")
        for d in p.detalles:
            producto = Producto.query.get(d.producto_id)
            if producto:
                salida.append(f"&nbsp;&nbsp;&nbsp;&nbsp;- {producto.nombre}: {d.cantidad} unidades (Stock actual: {producto.stock})<br>")

        salida.append("<hr>")

    return "".join(salida) or "No hay pedidos pendientes"


from flask import request, redirect, url_for, flash
import json

@app.route('/domicilios', methods=['GET', 'POST'])
@requiere_permiso('ver_domicilios')
def domicilios():
    now = datetime.now()
    hoy = now.date()
    fin_hoy = datetime.combine(hoy, datetime.max.time())

    if request.method == 'POST':
        # Leer datos del formulario
        cliente = request.form.get('cliente')
        telefono = request.form.get('telefono')
        direccion = request.form.get('direccion')
        estado_pago = request.form.get('estado_pago', '').lower()
        productos_json = request.form.get('productos')

        if not productos_json:
            flash('Debe seleccionar al menos un producto.', 'danger')
            return redirect(url_for('domicilios'))

        try:
            detalles = json.loads(productos_json)
        except:
            detalles = []

        if len(detalles) == 0:
            flash('Debe seleccionar al menos un producto válido.', 'danger')
            return redirect(url_for('domicilios'))
            
                # --- Validar stock antes de crear pedido ---
        for item in detalles:
            producto_id = item.get('producto_id') or item.get('id')
            cantidad = item.get('cantidad', 1)

            producto_obj = Producto.query.get(producto_id)
            if not producto_obj:
                flash(f'Producto con ID {producto_id} no existe.', 'danger')
                return redirect(url_for('domicilios'))

            if producto_obj.stock < cantidad:
                flash(f'Stock insuficiente para el producto "{producto_obj.nombre}". Disponible: {producto_obj.stock}', 'danger')
                return redirect(url_for('domicilios')) 

        # Crear el pedido sin detalles primero
        nuevo_pedido = Pedido(
            cliente_nombre=cliente,
            cliente_telefono=telefono,
            cliente_direccion=direccion,
            estado_pago=estado_pago,
            tipo='domicilio',
            fecha=now,
            estado='pendiente',
            usuario=session.get('usuario', 'admin')
        )
        db.session.add(nuevo_pedido)
        db.session.commit()

        # Agregar los productos al pedido
        for item in detalles:
            producto_id = item.get('producto_id') or item.get('id')
            cantidad = item.get('cantidad', 1) 
            
            producto_obj = Producto.query.get(producto_id)
            if not producto_obj:
                flash(f'Producto con ID {producto_id} no existe.', 'danger')
                return redirect(url_for('domicilios'))
            
            # Restar stock
            producto_obj.stock -= cantidad
            db.session.add(producto_obj) 
            db.session.flush()
            
            print(f"Descontando stock: {producto_obj.nombre} -> nuevo stock: {producto_obj.stock}")

            

            nombre_producto = producto_obj.nombre if producto_obj else 'Producto desconocido'
           
            print(f'Agregando detalle: producto_id={producto_id}, nombre={nombre_producto}, cantidad={item.get("cantidad", 1)}')

            detalle = DetallePedido(  
                pedido_id=nuevo_pedido.id,
                producto_id=producto_id,
                producto=nombre_producto,
                cantidad=item.get('cantidad', 1),
                precio=item.get('precio', 0),
                descripcion=item.get('descripcion', '')
            )
            db.session.add(detalle)

        db.session.commit()

        flash('Pedido a domicilio guardado correctamente.', 'success')
        return redirect(url_for('domicilios'))

    # Si es GET, mostrar la vista
    pedidos_pendientes = Pedido.query.filter(
        Pedido.tipo == 'domicilio',
        Pedido.estado == 'pendiente',
        Pedido.estado_pago.in_(['fiado', 'pago']),
        db.func.date(Pedido.fecha) <= hoy
    ).order_by(Pedido.fecha.desc()).all()

    dias_hasta_sabado = (5 - now.weekday()) % 7 or 7
    proximo_sabado = now + timedelta(days=dias_hasta_sabado)
    fin_sabado = proximo_sabado.replace(hour=23, minute=59, second=59, microsecond=999999)

    pedidos_fiados_cobrar = Pedido.query.filter(
        Pedido.tipo == 'domicilio',
        Pedido.estado_pago == 'fiado',
        Pedido.fecha <= fin_sabado
    ).order_by(Pedido.fecha.desc()).all()

    categorias = {}
    productos = Producto.query.order_by(Producto.categoria_id, Producto.nombre).all()
    for prod in productos:
        nombre_categoria = prod.categoria.nombre if prod.categoria else 'Sin categoría'
        categorias.setdefault(nombre_categoria, []).append(prod)

    return render_template('domicilios.html',
                           categorias=categorias,
                           pedidos_pendientes=pedidos_pendientes,
                           pedidos_fiados_cobrar=pedidos_fiados_cobrar,
                           now=datetime.now())

@app.route('/actualizar_descripcion', methods=['POST'])
@requiere_permiso('ver_domicilios')
def actualizar_descripcion():
    detalle_id = request.form.get('detalle_id')
    nueva_descripcion = request.form.get('nueva_descripcion', '').strip()

    detalle = DetallePedido.query.get(detalle_id)
    if detalle:
        detalle.descripcion = nueva_descripcion
        db.session.commit()
        flash('Descripción actualizada correctamente.', 'success')
    else:
        flash('No se encontró el detalle del producto.', 'danger')

    return redirect(url_for('domicilios'))





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
    pedido.estado_pago = 'pagado'
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

@app.route('/facturar_domicilio/<int:pedido_id>', methods=['POST'])
def facturar_domicilio(pedido_id):
    pedido = Pedido.query.get_or_404(pedido_id)

    if pedido.tipo != 'domicilio':
        flash('Solo se pueden facturar pedidos a domicilio desde esta ruta.', 'warning')
        return redirect(url_for('domicilios'))

    # Actualizar estado
    pedido.estado = 'facturado'
    pedido.estado_pago = 'pagado'
    db.session.commit()

    flash(f'Pedido a domicilio #{pedido.id} facturado correctamente.', 'success')
    return redirect(url_for('domicilios'))

from datetime import datetime

@app.route('/gastos', methods=['GET', 'POST'])
@requiere_permisos('ver_gastos', 'crear_gasto')
def gastos():
    if request.method == 'POST':
        fecha = datetime.strptime(request.form['fecha'], '%Y-%m-%d').date()
        proveedor = request.form['proveedor']
        descripcion = request.form['descripcion']
        valor = int(request.form['valor'])
        categoria = request.form['categoria']
        estado = request.form['estado']
        
        archivo = request.files.get('archivo')
        nombre_archivo = None
        if archivo and archivo.filename:
            nombre_archivo = secure_filename(archivo.filename)
            archivo.save(os.path.join('static/facturas', nombre_archivo))

        nuevo_gasto = Gasto(
            fecha=fecha,
            proveedor=proveedor,
            descripcion=descripcion,
            valor=valor,
            categoria=categoria,
            estado=estado,
            archivo=nombre_archivo
        )
        db.session.add(nuevo_gasto)
        db.session.commit()
        flash('Gasto registrado con éxito.', 'success')
        return redirect(url_for('gastos'))

    # Filtros
    query = Gasto.query
    desde = request.args.get('desde')
    hasta = request.args.get('hasta')
    categoria = request.args.get('categoria')
    estado = request.args.get('estado')

    if desde:
        query = query.filter(Gasto.fecha >= datetime.strptime(desde, "%Y-%m-%d").date())
    if hasta:
        query = query.filter(Gasto.fecha <= datetime.strptime(hasta, "%Y-%m-%d").date())
    if categoria:
        query = query.filter_by(categoria=categoria)
    if estado:
        query = query.filter_by(estado=estado)

    gastos = query.order_by(Gasto.fecha.desc()).all()
    
    # Resumen de gastos por categoría
    resumen = db.session.query(
        Gasto.categoria,
        func.sum(Gasto.valor)
    ).group_by(Gasto.categoria).all()
    
    labels = [r[0] for r in resumen]
    valores = [r[1] for r in resumen]
    return render_template('gastos.html', gastos=gastos, labels=labels, valores=valores)

@app.route('/gastos/editar/<int:id>', methods=['GET', 'POST'])
@requiere_permisos('ver_gastos', 'crear_gasto')
def editar_gasto(id):
    gasto = Gasto.query.get_or_404(id)
    if request.method == 'POST':
        gasto.fecha = datetime.strptime(request.form['fecha'], '%Y-%m-%d').date()
        gasto.proveedor = request.form['proveedor']
        gasto.descripcion = request.form['descripcion']
        gasto.valor = int(request.form['valor'])
        gasto.categoria = request.form['categoria']
        gasto.estado = request.form['estado']
        
        archivo = request.files.get('archivo')
        if archivo and archivo.filename:
            nombre_archivo = secure_filename(archivo.filename)
            archivo.save(os.path.join('static/facturas', nombre_archivo))
            gasto.archivo = nombre_archivo

        db.session.commit()
        flash('Gasto actualizado correctamente.', 'success')
        return redirect(url_for('gastos'))

    return render_template('editar_gasto.html', gasto=gasto)

@app.route('/gastos/eliminar/<int:id>', methods=['POST'])
@requiere_permisos('ver_gastos', 'crear_gasto')
def eliminar_gasto(id):
    gasto = Gasto.query.get_or_404(id)
    db.session.delete(gasto)
    db.session.commit()
    flash('Gasto eliminado correctamente.', 'success')
    return redirect(url_for('gastos'))



@app.route('/reportes')
@requiere_permiso('ver_reportes')
def reportes():
    producto_filtro = request.args.get('producto')
    fecha_filtro = request.args.get('fecha')
    tipo_filtro = request.args.get('tipo')
    estado_pago_filtro = request.args.get('estado_pago')

    # Base de filtro común
    base_query = Pedido.query.filter(Pedido.estado == 'facturado')

    if fecha_filtro:
        base_query = base_query.filter(func.DATE(Pedido.fecha) == fecha_filtro)

    if tipo_filtro:
        base_query = base_query.filter(Pedido.tipo == tipo_filtro)

    if estado_pago_filtro:
        base_query = base_query.filter(Pedido.estado_pago == estado_pago_filtro)

    if producto_filtro:
        base_query = base_query.join(DetallePedido).filter(
            DetallePedido.producto.ilike(f'%{producto_filtro}%')
        ).distinct()

    pedidos = base_query.options(db.joinedload(Pedido.detalles)).all()

    # Detalle por producto
    resultados = []
    for pedido in pedidos:
        for detalle in pedido.detalles:
            if producto_filtro and producto_filtro.lower() not in detalle.producto.lower():
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

    # Función para aplicar filtros a cualquier consulta
    def aplicar_filtros(query):
        query = query.filter(Pedido.estado == 'facturado')
        if fecha_filtro:
            query = query.filter(func.DATE(Pedido.fecha) == fecha_filtro)
        if tipo_filtro:
            query = query.filter(Pedido.tipo == tipo_filtro)
        if estado_pago_filtro:
            query = query.filter(Pedido.estado_pago == estado_pago_filtro)
        if producto_filtro:
            query = query.filter(DetallePedido.producto.ilike(f'%{producto_filtro}%'))
        return query

    # Resumen por tipo
    resumen_por_tipo = aplicar_filtros(
        db.session.query(
            Pedido.tipo,
            func.count(Pedido.id),
            func.sum(DetallePedido.precio * DetallePedido.cantidad)
        ).join(DetallePedido)
    ).group_by(Pedido.tipo).all()

    # Resumen por estado de pago
    resumen_por_estado = aplicar_filtros(
        db.session.query(
            Pedido.estado_pago,
            func.count(Pedido.id),
            func.sum(DetallePedido.precio * DetallePedido.cantidad)
        ).join(DetallePedido)
    ).group_by(Pedido.estado_pago).all()

    return render_template(
        'reportes.html',
        pedidos=pedidos,
        resultados=resultados,
        resumen_por_tipo=resumen_por_tipo,
        resumen_por_estado=resumen_por_estado
    )


# Ruta para guardar imágenes

@app.route('/categorias')
@requiere_permiso('crear_categoria')
def categorias():
    categorias = Categoria.query.all()
    return render_template('categorias.html', categorias=categorias)

@app.route('/categorias/agregar', methods=['GET', 'POST'])
@requiere_permiso('crear_categoria')
def agregar_categoria():
    categorias = Categoria.query.order_by(Categoria.nombre).all()

    if request.method == 'POST':
        nombre = request.form['nombre'].strip()

        if not nombre:
            flash('El nombre de la categoría es obligatorio.', 'danger')
            return redirect(url_for('agregar_categoria'))

        existente = Categoria.query.filter_by(nombre=nombre).first()
        if existente:
            flash('La categoría ya existe.', 'warning')
            return redirect(url_for('agregar_categoria'))

        nueva = Categoria(nombre=nombre)
        db.session.add(nueva)
        db.session.commit()
        flash('Categoría creada correctamente.', 'success')
        return redirect(url_for('agregar_categoria'))

    return render_template('agregar_categoria.html', categorias=categorias)
    
@app.route('/categorias/editar/<int:categoria_id>', methods=['GET', 'POST'])
def editar_categoria(categoria_id):
    categoria = Categoria.query.get_or_404(categoria_id)

    if request.method == 'POST':
        nombre = request.form['nombre'].strip()

        if not nombre:
            flash('El nombre de la categoría es obligatorio.', 'danger')
            return redirect(url_for('editar_categoria', categoria_id=categoria_id))

        existente = Categoria.query.filter(Categoria.nombre == nombre, Categoria.id != categoria_id).first()
        if existente:
            flash('Ya existe otra categoría con ese nombre.', 'warning')
            return redirect(url_for('editar_categoria', categoria_id=categoria_id))

        categoria.nombre = nombre
        db.session.commit()
        flash('Categoría actualizada correctamente.', 'success')
        return redirect(url_for('agregar_categoria'))

    return render_template('editar_categoria.html', categoria=categoria)


@app.route('/categorias/eliminar/<int:categoria_id>', methods=['POST'])
def eliminar_categoria(categoria_id):
    categoria = Categoria.query.get_or_404(categoria_id)
    db.session.delete(categoria)
    db.session.commit()
    flash('Categoría eliminada correctamente.', 'success')
    return redirect(url_for('agregar_categoria'))




#UPLOAD_FOLDER = os.path.join('static', 'images')
#app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER




@app.route('/agregar_producto', methods=['GET', 'POST'])
@requiere_permiso('crear_producto')
def agregar_producto():
    categorias = Categoria.query.order_by(Categoria.nombre).all()

    if request.method == 'POST':
        # Agregar producto
        nombre = request.form['nombre']
        precio = float(request.form['precio'])
        categoria_id = int(request.form['categoria_id'])
        stock = int(request.form['stock'])
        imagen = request.files.get('imagen')

        filename = None
        if imagen and imagen.filename != '':
            filename = secure_filename(imagen.filename)
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])
            imagen.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        nuevo_producto = Producto(
            nombre=nombre,
            precio=precio,
            categoria_id=categoria_id,
            imagen=filename,
            stock=stock
        )
        db.session.add(nuevo_producto)
        db.session.commit()
        flash('Producto agregado correctamente', 'success')
        return redirect(url_for('agregar_producto'))

    # Filtros GET
    busqueda = request.args.get('busqueda', '').strip()
    categoria_filtro = request.args.get('categoria_filtro')

    query = Producto.query
    if busqueda:
        query = query.filter(Producto.nombre.ilike(f'%{busqueda}%'))
    if categoria_filtro:
        query = query.filter_by(categoria_id=categoria_filtro)

    productos_filtrados = query.order_by(Producto.nombre).all()

    # Organizar por categoría
    categorias_y_productos = {}
    for cat in categorias:
        cat_productos = [p for p in productos_filtrados if p.categoria_id == cat.id]
        if cat_productos:
            categorias_y_productos[cat.nombre] = cat_productos

    return render_template('agregar_producto.html', categorias=categorias, categorias_y_productos=categorias_y_productos)




@app.route('/editar_producto/<int:producto_id>', methods=['GET', 'POST'])
def editar_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)
    categorias = Categoria.query.order_by(Categoria.nombre).all()

    if request.method == 'POST':
        producto.nombre = request.form['nombre']
        producto.precio = float(request.form['precio'])
        producto.categoria_id = int(request.form['categoria_id'])
        producto.stock = int(request.form['stock'])  # <-- actualizar stock

        imagen = request.files.get('imagen')
        if imagen and imagen.filename != '':
            filename = secure_filename(imagen.filename)
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])
            imagen.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            producto.imagen = filename  # Actualiza la imagen solo si subieron una nueva

        db.session.commit()
        flash('Producto actualizado correctamente', 'success')
        return redirect(url_for('agregar_producto'))

    return render_template('editar_producto.html', producto=producto, categorias=categorias)


@app.route('/producto/eliminar/<int:producto_id>', methods=['POST'])
def eliminar_producto(producto_id):
    producto = Producto.query.get_or_404(producto_id)

    # Opcional: borrar imagen física si existe
    if producto.imagen:
        imagen_path = os.path.join(app.config['UPLOAD_FOLDER'], producto.imagen)
        if os.path.exists(imagen_path):
            os.remove(imagen_path)

    db.session.delete(producto)
    db.session.commit()
    flash('Producto eliminado correctamente.', 'success')
    return redirect(url_for('agregar_producto'))


@app.route('/importar_productos_excel', methods=['POST'])
def importar_productos_excel():
    archivo = request.files.get('archivo_excel')
    if not archivo:
        flash('No se seleccionó archivo.', 'danger')
        return redirect(url_for('agregar_producto'))

    try:
        wb = openpyxl.load_workbook(archivo)
        hoja = wb.active

        productos_agregados = 0
        errores = []

        for i, fila in enumerate(hoja.iter_rows(min_row=2), start=2):
            nombre = fila[0].value
            precio = fila[1].value
            categoria_nombre = fila[2].value
            stock_valor = fila[3].value if len(fila) > 3 else 0  # Ahora stock es la 4ta columna
            imagen = fila[4].value if len(fila) > 4 else None     # Imagen la 5ta columna, si existe

            if not nombre or not precio or not categoria_nombre:
                errores.append(f'Fila {i}: datos incompletos.')
                continue

            try:
                precio = float(precio)
            except ValueError:
                errores.append(f'Fila {i}: precio inválido.')
                continue

            try:
                stock = int(stock_valor) if stock_valor is not None else 0
            except (ValueError, TypeError):
                stock = 0

            nombre = str(nombre).strip()
            categoria_nombre = str(categoria_nombre).strip()
            imagen = str(imagen).strip() if imagen else None

            # Buscar o crear categoría automáticamente
            categoria = Categoria.query.filter_by(nombre=categoria_nombre).first()
            if not categoria:
                categoria = Categoria(nombre=categoria_nombre)
                db.session.add(categoria)
                db.session.commit()

            # Verificar si ya existe el producto
            producto_existente = Producto.query.filter_by(nombre=nombre).first()

            if producto_existente:
                producto_existente.precio = precio
                producto_existente.categoria_id = categoria.id
                producto_existente.stock = stock  # Actualizar stock

                imagen_actualizada = False
                if not producto_existente.imagen and imagen:
                    producto_existente.imagen = imagen
                    imagen_actualizada = True

                db.session.commit()
                productos_agregados += 1
            else:
                nuevo_producto = Producto(
                    nombre=nombre,
                    precio=precio,
                    categoria_id=categoria.id,
                    stock=stock,               # Guardar stock
                    imagen=imagen
                )
                db.session.add(nuevo_producto)
                db.session.commit()
                imagen_actualizada = True
                productos_agregados += 1

            # Copiar imagen si es nueva
            if imagen and imagen_actualizada:
                origen_path = os.path.join('uploads_temp', categoria_nombre, imagen)
                destino_path = os.path.join(app.config['UPLOAD_FOLDER'], imagen)

                if os.path.exists(origen_path):
                    shutil.copy(origen_path, destino_path)
                else:
                    errores.append(f'Fila {i}: imagen "{imagen}" no encontrada en carpeta {categoria_nombre}.')

        if errores:
            flash(f'{productos_agregados} productos agregados. {len(errores)} errores: {" | ".join(errores)}', 'warning')
        else:
            flash(f'{productos_agregados} productos importados correctamente.', 'success')

    except Exception as e:
        flash(f'Error procesando el archivo: {str(e)}', 'danger')

    return redirect(url_for('agregar_producto'))

    

@app.route('/listar_estados')
def listar_estados():
    estados_unicos = db.session.query(Pedido.estado).distinct().all()
    # estados_unicos es una lista de tuplas, por ejemplo: [('activo',), ('facturado',), ('pendiente',)]
    estados = [e[0] for e in estados_unicos]
    return "<br>".join(estados)  # Te muestra los estados en el navegador
    
@app.route('/consultar_pedidos')
def consultar_pedidos():
    pedidos = Pedido.query.order_by(Pedido.fecha.desc()).all()
    return render_template('consultar_pedidos.html', pedidos=pedidos)


@app.route('/exportar_excel')
def exportar_excel():
    producto_filtro = request.args.get('producto')
    fecha_filtro = request.args.get('fecha')

    # Obtener todos los pedidos facturados
    pedidos_query = Pedido.query.filter(func.lower(Pedido.estado) == 'facturado')

    if fecha_filtro:
        pedidos_query = pedidos_query.filter(func.DATE(Pedido.fecha) == fecha_filtro)

    pedidos = pedidos_query.order_by(Pedido.fecha.desc()).all()

    # Preparar datos para hojas Salón y Domicilio
    salon_data = []
    domicilio_data = []

    for pedido in pedidos:
        for detalle in pedido.detalles:
            # Aplicar filtro de producto solo al detalle
            if producto_filtro and producto_filtro.lower() not in detalle.producto.lower():
                continue

            fila = {
                'Pedido ID': pedido.id,
                'Fecha': pedido.fecha.strftime('%Y-%m-%d %H:%M'),
                'Tipo': pedido.tipo,
                'Mesa / Cliente': f"Mesa {pedido.mesa}" if pedido.tipo == 'salon' else pedido.cliente_nombre,
                'Producto': detalle.producto,
                'Cantidad': detalle.cantidad,
                'Precio Unitario': detalle.precio,
                'Total': detalle.precio * detalle.cantidad
            }

            if pedido.tipo == 'salon':
                salon_data.append(fila)
            else:
                domicilio_data.append(fila)

    df_salon = pd.DataFrame(salon_data)
    df_domicilio = pd.DataFrame(domicilio_data)

    # -------- Generar resumen por tipo y estado --------
    resumen_tipo_query = db.session.query(
        Pedido.tipo.label('Tipo'),
        func.count(Pedido.id).label('Cantidad de Pedidos'),
        func.sum(DetallePedido.precio * DetallePedido.cantidad).label('Total Ventas')
    ).join(DetallePedido).filter(func.lower(Pedido.estado) == 'facturado')

    resumen_estado_query = db.session.query(
        Pedido.estado.label('Estado'),
        func.count(Pedido.id).label('Cantidad de Pedidos'),
        func.sum(DetallePedido.precio * DetallePedido.cantidad).label('Total Ventas')
    ).join(DetallePedido).filter(func.lower(Pedido.estado) == 'facturado')

    if fecha_filtro:
        resumen_tipo_query = resumen_tipo_query.filter(func.DATE(Pedido.fecha) == fecha_filtro)
        resumen_estado_query = resumen_estado_query.filter(func.DATE(Pedido.fecha) == fecha_filtro)

    if producto_filtro:
        resumen_tipo_query = resumen_tipo_query.filter(DetallePedido.producto.ilike(f'%{producto_filtro}%'))
        resumen_estado_query = resumen_estado_query.filter(DetallePedido.producto.ilike(f'%{producto_filtro}%'))

    resumen_tipo = resumen_tipo_query.group_by(Pedido.tipo).all()
    resumen_estado = resumen_estado_query.group_by(Pedido.estado).all()

    df_resumen_tipo = pd.DataFrame([{
        'Tipo': r[0],
        'Cantidad de Pedidos': r[1],
        'Total Ventas': r[2]
    } for r in resumen_tipo])

    df_resumen_estado = pd.DataFrame([{
        'Estado': r[0],
        'Cantidad de Pedidos': r[1],
        'Total Ventas': r[2]
    } for r in resumen_estado])

    # -------- Generar archivo Excel --------
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_salon.to_excel(writer, sheet_name='Salón', index=False)
        df_domicilio.to_excel(writer, sheet_name='Domicilio', index=False)

        # Hoja resumen
        workbook = writer.book
        sheet = workbook.add_worksheet('Resumen')
        writer.sheets['Resumen'] = sheet

        sheet.write(0, 0, "Resumen por Tipo")
        for i, col in enumerate(df_resumen_tipo.columns):
            sheet.write(1, i, col)
        for row_idx, row in enumerate(df_resumen_tipo.values):
            for col_idx, value in enumerate(row):
                sheet.write(row_idx + 2, col_idx, value)

        start_row = len(df_resumen_tipo) + 4
        sheet.write(start_row, 0, "Resumen por Estado")
        for i, col in enumerate(df_resumen_estado.columns):
            sheet.write(start_row + 1, i, col)
        for row_idx, row in enumerate(df_resumen_estado.values):
            for col_idx, value in enumerate(row):
                sheet.write(start_row + 2 + row_idx, col_idx, value)

    output.seek(0)

    return send_file(output,
                     download_name="reporte_ventas.xlsx",
                     as_attachment=True,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@app.cli.command("crear_datos_iniciales")
def crear_datos_iniciales():
    from models import db, Rol, Permiso, RolPermiso, Usuario

    # Lista base de permisos
    permisos_base = [
        'ver_salon',
        'crear_pedido',
        'crear_pedido_domicilio',
        'ver_cocina',
        'marcar_pedido_preparado',
        'facturar_pedido',
        'ver_reportes',
        'gestionar_permisos',
        'ver_productos',
        'crear_producto',
        'crear_categoria'
    ]

    # Crear permisos si no existen
    for nombre in permisos_base:
        if not Permiso.query.filter_by(nombre=nombre).first():
            db.session.add(Permiso(nombre=nombre))
    db.session.commit()

    # Diccionario de roles y sus permisos
    roles_con_permisos = {
        'Administrador': permisos_base,
        'Domiciliario': ['ver_salon', 'crear_pedido_domicilio', 'ver_cocina'],
        'Cocinero': ['ver_cocina', 'marcar_pedido_preparado'],
        'Cajero': ['ver_salon', 'facturar_pedido', 'ver_reportes'],
        'Mesero': ['ver_salon', 'crear_pedido', 'ver_productos'],
    }

    for rol_nombre, permisos in roles_con_permisos.items():
        rol = Rol.query.filter_by(nombre=rol_nombre).first()
        if not rol:
            rol = Rol(nombre=rol_nombre)
            db.session.add(rol)
            db.session.commit()
        for nombre_permiso in permisos:
            permiso = Permiso.query.filter_by(nombre=nombre_permiso).first()
            if permiso:
                existe = RolPermiso.query.filter_by(rol_id=rol.id, permiso_id=permiso.id).first()
                if not existe:
                    db.session.add(RolPermiso(rol=rol, permiso=permiso))
    db.session.commit()

    # Crear usuarios base
    admin_rol = Rol.query.filter_by(nombre='Administrador').first()
    domi_rol = Rol.query.filter_by(nombre='Domiciliario').first()

    admin_user = Usuario.query.filter_by(correo='admin@example.com').first()
    if not admin_user:
        admin_user = Usuario(correo='admin@example.com', password='1234', rol=admin_rol)
        db.session.add(admin_user)

    dom_user = Usuario.query.filter_by(correo='domiciliario@example.com').first()
    if not dom_user:
        dom_user = Usuario(correo='domiciliario@example.com', password='1234', rol=domi_rol)
        db.session.add(dom_user)

    db.session.commit()

    print("✔ Roles, permisos y usuarios base creados o ya existentes.")



    
@app.route('/permisos', methods=['GET', 'POST'])
@requiere_permiso('gestionar_permisos')
def gestionar_permisos():
    roles = Rol.query.all()
    permisos = Permiso.query.all()
    rol_id = None
    permisos_asignados = []

    if request.method == 'POST':
        rol_id = request.form.get('rol_id')
        permisos_seleccionados = request.form.getlist('permisos')

        rol = Rol.query.get(rol_id)

        if rol and rol.nombre.lower() == 'administrador':
            flash('No se pueden modificar los permisos del rol Administrador.', 'warning')
        else:
            # Actualizar permisos del rol
            RolPermiso.query.filter_by(rol_id=rol_id).delete()
            for permiso_id in permisos_seleccionados:
                db.session.add(RolPermiso(rol_id=rol_id, permiso_id=permiso_id))
            db.session.commit()
            flash(f'Permisos actualizados para el rol {rol.nombre}', 'success')
            return redirect(url_for('gestionar_permisos', rol_id=rol_id))

    # Si hay un rol seleccionado, cargar sus permisos
    if request.method == 'POST' and rol_id:
        permisos_asignados = [
            rp.permiso_id for rp in RolPermiso.query.filter_by(rol_id=rol_id).all()
        ]
    elif request.method == 'GET':
        rol_id = request.args.get('rol_id')
        if rol_id:
            permisos_asignados = [
                rp.permiso_id for rp in RolPermiso.query.filter_by(rol_id=rol_id).all()
            ]

    # Resumen visual
    resumen_permisos = {}
    for rol in roles:
        permisos_rol = db.session.query(Permiso.nombre).join(RolPermiso).filter(RolPermiso.rol_id == rol.id).all()
        resumen_permisos[rol.nombre] = [perm[0] for perm in permisos_rol]

    return render_template(
        'permisos.html',
        roles=roles,
        permisos=permisos,
        rol_id=int(rol_id) if rol_id else None,
        permisos_asignados=permisos_asignados,
        resumen_permisos=resumen_permisos
    )





   
@app.route('/crear_permiso', methods=['POST'])
@requiere_permiso('gestionar_permisos')
def crear_permiso():
    nombre = request.form.get('nombre_permiso')
    if nombre and not Permiso.query.filter_by(nombre=nombre).first():
        nuevo_permiso = Permiso(nombre=nombre)
        db.session.add(nuevo_permiso)
        db.session.commit()

        # Asignar el nuevo permiso al rol Administrador
        rol_admin = Rol.query.filter_by(nombre='Administrador').first()
        if rol_admin:
            rp = RolPermiso(rol_id=rol_admin.id, permiso_id=nuevo_permiso.id)
            db.session.add(rp)
            db.session.commit()
            flash('Permiso creado y asignado automáticamente al Administrador', 'success')
        else:
            flash('Permiso creado, pero no se encontró el rol Administrador', 'warning')
    else:
        flash('El permiso ya existe o el nombre está vacío', 'warning')

    return redirect(url_for('gestionar_permisos'))



@app.route('/crear_rol', methods=['POST'])
@requiere_permiso('gestionar_permisos')
def crear_rol():
    nombre = request.form.get('nombre_rol')
    if nombre and not Rol.query.filter_by(nombre=nombre).first():
        nuevo_rol = Rol(nombre=nombre)
        db.session.add(nuevo_rol)
        db.session.commit()

        # Si el rol es 'Administrador', asignarle todos los permisos disponibles
        if nombre.strip().lower() == 'administrador':
            todos_los_permisos = Permiso.query.all()
            nuevo_rol.permisos = todos_los_permisos
            db.session.commit()

        flash('Rol creado correctamente', 'success')
    else:
        flash('El rol ya existe o el nombre está vacío', 'warning')
    return redirect(url_for('gestionar_permisos'))
    

@app.route('/usuarios')
@requiere_permiso('ver_usuarios')
def lista_usuarios():
    usuarios = Usuario.query.all()
    roles = Rol.query.all()
    return render_template('usuarios.html', usuarios=usuarios, roles=roles)

@app.route('/crear_usuario', methods=['POST'])
@requiere_permiso('ver_usuarios')  # o puedes crear un permiso separado como 'crear_usuario'
def crear_usuario():
    correo = request.form.get('correo')
    password = request.form.get('password')
    rol_id = request.form.get('rol_id')

    # Validaciones básicas
    if not correo or not password or not rol_id:
        flash('Todos los campos son obligatorios.', 'danger')
        return redirect(url_for('lista_usuarios'))

    # Verificar si ya existe ese correo
    if Usuario.query.filter_by(correo=correo).first():
        flash('Ya existe un usuario con ese correo.', 'warning')
        return redirect(url_for('lista_usuarios'))

    # Crear usuario
    nuevo_usuario = Usuario(
        correo=correo,
        password=generate_password_hash(password),
        rol_id=rol_id
    )
    db.session.add(nuevo_usuario)
    db.session.commit()
    flash('Usuario creado exitosamente.', 'success')
    return redirect(url_for('lista_usuarios'))

@app.route('/perfil')
def perfil():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    usuario = Usuario.query.get(session['usuario_id'])
    return render_template('perfil.html', usuario=usuario)

@app.route('/cambiar_contrasena', methods=['GET', 'POST'])
def cambiar_contrasena():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    usuario = Usuario.query.get(session['usuario_id'])

    if request.method == 'POST':
        actual = request.form['actual']
        nueva = request.form['nueva']
        confirmar = request.form['confirmar']

        if usuario.password != actual:
            flash('La contraseña actual es incorrecta.', 'danger')
        elif nueva != confirmar:
            flash('Las contraseñas nuevas no coinciden.', 'warning')
        else:
            usuario.password = nueva  # Usa hash si usas contraseñas cifradas
            db.session.commit()
            flash('Contraseña actualizada con éxito.', 'success')
            return redirect(url_for('perfil'))

    return render_template('cambiar_contrasena.html')




@app.template_filter('hora_local')
def hora_local(fecha):
    if fecha is None:
        return ""
    
    # Si es un objeto date, convertirlo a datetime (agregando hora 00:00)
    if isinstance(fecha, datetime):
        fecha_dt = fecha
    else:
        fecha_dt = datetime.combine(fecha, time())

    bogota = timezone('America/Bogota')
    return fecha_dt.astimezone(bogota).strftime('%d/%m/%Y %H:%M')




@app.route('/restaurar_admin')
def restaurar_admin():
    admin = Rol.query.filter_by(nombre='Admin').first()
    if not admin:
        return "Rol Admin no encontrado", 404

    permisos = Permiso.query.all()
    for permiso in permisos:
        ya_tiene = RolPermiso.query.filter_by(rol_id=admin.id, permiso_id=permiso.id).first()
        if not ya_tiene:
            db.session.add(RolPermiso(rol_id=admin.id, permiso_id=permiso.id))
    db.session.commit()
    return "Permisos restaurados al Admin"

@app.before_first_request
def ejecutar_datos_iniciales_si_no_hay_usuarios():
    from models import Usuario
    if not Usuario.query.first():
        print("⚙ Ejecutando creación de datos iniciales (usuarios, roles, permisos)...")
        crear_datos_iniciales()
 
# Ejecutar automáticamente crear_datos_iniciales en Render si no hay usuarios
with app.app_context():
    from models import Usuario
    if not Usuario.query.filter_by(correo='admin@example.com').first():
        try:
            crear_datos_iniciales()
            print("✔ Usuarios y permisos creados automáticamente en Render")
        except Exception as e:
            print(f"❌ Error creando usuarios iniciales: {e}")
 
 
#@app.route('/crear_permisos_base')
#def crear_permisos_base():
#      'crear_pedido_domicilio',
#        'facturar_pedido',
#        'marcar_pedido_preparado',
#        'eliminar_pedido',
#        'ver_reportes',
#    ]
#    creados = 0
#    for nombre in permisos_nuevos:
#        existe = Permiso.query.filter_by(nombre=nombre).first()
#        if not existe:
#            nuevo_permiso = Permiso(nombre=nombre)
#            db.session.add(nuevo_permiso)
#            creados += 1
#    db.session.commit()
#    return f'Se crearon {creados} permisos nuevos correctamente.'

#if __name__ == '__main__':
#    with app.app_context():
#        db.create_all()
#
#        # Asignar todos los permisos al rol Administrador
#        admin_rol = Rol.query.filter_by(nombre='Administrador').first()
#        if admin_rol:
#            todos_los_permisos = Permiso.query.all()
#            permisos_actuales = {rp.permiso_id for rp in RolPermiso.query.filter_by(rol_id=admin_rol.id).all()}
#            nuevos_permisos = [p for p in todos_los_permisos if p.id not in permisos_actuales]
#            for permiso in nuevos_permisos:
#                db.session.add(RolPermiso(rol_id=admin_rol.id, permiso_id=permiso.id))
#            if nuevos_permisos:
#                db.session.commit()
#                print(f"Permisos actualizados para el rol Administrador")
#    app.run(debug=True)


