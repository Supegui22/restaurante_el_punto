from datetime import date
from extensions import db


class Pedido(db.Model):
    __tablename__ = 'pedidos'

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), default='salon')  # 'salon' o 'domicilio'
    ESTADOS = ('activo', 'comanda enviada', 'preparado', 'pagado', 'cancelado')
    estado = db.Column(db.String(50), default='activo')  # 'activo', 'comanda enviada', 'preparado', 'pagado', etc.
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    usuario = db.Column(db.String(100), nullable=False)

    # Solo para tipo 'salon'
    mesa = db.Column(db.String(10), nullable=True)

    # Solo para tipo 'domicilio'
    cliente_nombre = db.Column(db.String(100), nullable=True)
    cliente_telefono = db.Column(db.String(20), nullable=True)
    cliente_direccion = db.Column(db.String(200), nullable=True)

    detalles = db.relationship('DetallePedido', backref='pedido', cascade='all, delete-orphan', lazy=True)

    def __repr__(self):
        if self.tipo == 'salon':
            return f'<Pedido {self.id} - Mesa {self.mesa}>'
        else:
            return f'<Pedido {self.id} - Domicilio {self.cliente_nombre}>'

class DetallePedido(db.Model):
    __tablename__ = 'detalles_pedido'

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedidos.id'), nullable=False)
    producto = db.Column(db.String(100), nullable=False)
    precio = db.Column(db.Float, nullable=False)
    cantidad = db.Column(db.Integer, nullable=False, default=1)

    @property
    def precio_total(self):
        return self.precio * self.cantidad

    def __repr__(self):
        return f'<Detalle {self.id} - Producto {self.producto} x {self.cantidad}>'


class CierreCaja(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, default=date.today)
    total_ventas = db.Column(db.Numeric)
    total_efectivo = db.Column(db.Numeric)
    total_fiado = db.Column(db.Integer)
    pedidos_facturados = db.Column(db.Integer)
    pedidos_pendientes = db.Column(db.Integer)

