from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, timedelta
import uuid

app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'

# Simulación base de datos en memoria (para producción cambiar a DB real)
mesas = [1, 2, 3, 4, 5, 6, 7]

# Pedidos almacenados: clave = mesa o domicilio ID, valor = datos del pedido
pedidos_mesas = {}  # {mesa: {'productos': [...], 'estado': 'ocupada'/'libre', 'fecha': datetime}}
pedidos_domicilios = {}  # {pedido_id: {...}}

productos_catalogo = {
    "Bebidas": [
        {"nombre": "Coca-Cola", "precio": 1500, "imagen": "cocacola.png"},
        {"nombre": "Agua", "precio": 1000, "imagen": "agua.png"},
    ],
    "Comidas": [
        {"nombre": "Hamburguesa", "precio": 7000, "imagen": "hamburguesa.png"},
        {"nombre": "Pizza", "precio": 9000, "imagen": "pizza.png"},
    ]
}

def obtener_estado_mesas():
    estado = {}
    for m in mesas:
        estado[m] = pedidos_mesas.get(m, {}).get('estado', 'libre')
    return estado

@app.route('/')
def index():
    return redirect(url_for('salon'))

@app.route('/salon')
def salon():
    estado_mesas = obtener_estado_mesas()
    return render_template('salon.html', mesas=mesas, estado_mesas=estado_mesas)

@app.route('/ventas/<int:mesa>', methods=['GET', 'POST'])
def ventas_en_punto(mesa):
    if mesa not in mesas:
        flash("Mesa inválida", "warning")
        return redirect(url_for('salon'))

    estado_mesas = obtener_estado_mesas()

    if request.method == 'POST':
        productos_enviados = request.form.get('productos', '')
        productos_lista = productos_enviados.split(',') if productos_enviados else []
        # Contar cantidades
        conteo = {}
        for p in productos_lista:
            if p:
                conteo[p] = conteo.get(p, 0) + 1

        # Guardar pedido para esa mesa
        pedido_guardado = []
        for nombre, cantidad in conteo.items():
            # Obtener precio producto
            precio = None
            for cat, prod_list in productos_catalogo.items():
                for prod in prod_list:
                    if prod['nombre'] == nombre:
                        precio = prod['precio']
            if precio is None:
                continue
            pedido_guardado.append({'producto': nombre, 'cantidad': cantidad, 'precio': precio})

        pedidos_mesas[mesa] = {
            'productos': pedido_guardado,
            'estado': 'ocupada' if pedido_guardado else 'libre',
            'fecha': datetime.now()
        }
        flash(f"Pedido para mesa {mesa} guardado.", "success")
        return redirect(url_for('ventas_en_punto', mesa=mesa))

    pedidos_guardados = {mesa: pedidos_mesas.get(mesa, {}).get('productos', [])}
    return render_template('ventas.html',
                           mesa=mesa,
                           mesas=mesas,
                           estado_mesas=estado_mesas,
                           categorias=productos_catalogo,
                           pedidos_guardados=pedidos_guardados)

@app.route('/cocina')
def cocina():
    # Mostrar pedidos activos (mesas ocupadas y domicilios no preparados)
    pedidos_activos_mesas = []
    for m, pedido in pedidos_mesas.items():
        if pedido.get('estado') == 'ocupada':
            pedidos_activos_mesas.append({'mesa': m, **pedido})

    pedidos_activos_domicilios = []
    for pid, pedido in pedidos_domicilios.items():
        if pedido.get('estado') != 'preparado':
            pedidos_activos_domicilios.append({'id': pid, **pedido})

    return render_template('cocina.html',
                           pedidos_mesas=pedidos_activos_mesas,
                           pedidos_domicilios=pedidos_activos_domicilios)

@app.route('/marcar_preparado/<tipo>/<id>', methods=['POST'])
def marcar_preparado(tipo, id):
    if tipo == 'mesa':
        mesa = int(id)
        if mesa in pedidos_mesas:
            pedidos_mesas[mesa]['estado'] = 'preparado'
            flash(f"Pedido mesa {mesa} marcado como preparado.", "success")
    elif tipo == 'domicilio':
        if id in pedidos_domicilios:
            pedidos_domicilios[id]['estado'] = 'preparado'
            flash(f"Pedido domicilio {id} marcado como preparado.", "success")
    else:
        flash("Tipo inválido", "warning")
    return redirect(url_for('cocina'))

@app.route('/domicilios', methods=['GET', 'POST'])
def domicilios():
    if request.method == 'POST':
        cliente = request.form.get('cliente')
        productos_enviados = request.form.get('productos', '')
        productos_lista = productos_enviados.split(',') if productos_enviados else []

        conteo = {}
        for p in productos_lista:
            if p:
                conteo[p] = conteo.get(p, 0) + 1

        pedido_id = str(uuid.uuid4())
        pedido_guardado = []
        for nombre, cantidad in conteo.items():
            precio = None
            for cat, prod_list in productos_catalogo.items():
                for prod in prod_list:
                    if prod['nombre'] == nombre:
                        precio = prod['precio']
            if precio is None:
                continue
            pedido_guardado.append({'producto': nombre, 'cantidad': cantidad, 'precio': precio})

        pedidos_domicilios[pedido_id] = {
            'cliente': cliente,
            'productos': pedido_guardado,
            'estado': 'pendiente',
            'fecha': datetime.now()
        }
        flash(f"Pedido domicilio para {cliente} guardado.", "success")
        return redirect(url_for('domicilios'))

    # Estadísticas
    hoy = datetime.now().date()
    pedidos_hoje = [p for p in pedidos_domicilios.values() if p['fecha'].date() == hoy]
    pendientes = [p for p in pedidos_hoje if p['estado'] == 'pendiente']
    proximo_sabado = hoy + timedelta((5 - hoy.weekday()) % 7)
    # Aquí podrías agregar lógica más avanzada para calcular cobros próximos...

    return render_template('domicilios.html',
                           categorias=productos_catalogo,
                           pedidos=pedidos_domicilios,
                           pendientes=pendientes,
                           proximo_sabado=proximo_sabado)

@app.route('/comanda_pdf/<int:mesa>')
def comanda_pdf(mesa):
    # Aquí deberías implementar PDF real, por ahora devolver un texto simple
    pedido = pedidos_mesas.get(mesa)
    if not pedido:
        flash("No hay pedido para esa mesa.", "warning")
        return redirect(url_for('ventas_en_punto', mesa=mesa))
    texto = f"Comanda mesa {mesa}\n"
    for item in pedido['productos']:
        texto += f"{item['producto']} x{item['cantidad']} - ${item['precio'] * item['cantidad']}\n"
    return f"<pre>{texto}</pre>"

@app.route('/facturar_pedido', methods=['POST'])
def facturar_pedido():
    mesa = int(request.form.get('mesa', 0))
    if mesa in pedidos_mesas:
        pedidos_mesas[mesa]['estado'] = 'facturado'
        flash(f"Pedido mesa {mesa} facturado.", "success")
    else:
        flash("Mesa no encontrada para facturar.", "warning")
    return redirect(url_for('ventas_en_punto', mesa=mesa))

if __name__ == '__main__':
    app.run(debug=True)
