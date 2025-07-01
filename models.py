from datetime import datetime, date
from extensions import db



class Categoria(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(80), unique=True, nullable=False)
    productos = db.relationship('Producto', backref='categoria', lazy=True)

class Producto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    precio = db.Column(db.Float, nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categoria.id'), nullable=False)
    imagen = db.Column(db.String(100))  # nombre del archivo imagen
    stock = db.Column(db.Integer, default=0)  # cantidad actual en inventario



class Pedido(db.Model):
    __tablename__ = 'pedidos'

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(20), default='salon')  # 'salon' o 'domicilio'

    ESTADOS = ('activo', 'comanda_enviada', 'preparado', 'pagado', 'cancelado')
    estado = db.Column(db.String(50), default='activo')  # Estado general del pedido

    estado_pago = db.Column(db.String(20), nullable=True)  # 'fiado' o 'pagado' (solo para domicilios)

    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_pago = db.Column(db.DateTime, nullable=True)  # ← NUEVO CAMPO: fecha cuando se cobra el fiado

    usuario = db.Column(db.String(100), nullable=False)

    # Solo para tipo 'salon'
    mesa = db.Column(db.String(10), nullable=True)

    # Solo para tipo 'domicilio'
    cliente_nombre = db.Column(db.String(100), nullable=True)
    cliente_telefono = db.Column(db.String(20), nullable=True)
    cliente_direccion = db.Column(db.String(200), nullable=True)

    # Relación con DetallePedido
    detalles = db.relationship('DetallePedido', backref='pedido', cascade='all, delete-orphan', lazy=True)

    def __repr__(self):
        if self.tipo == 'salon':
            return f'<Pedido {self.id} - Mesa {self.mesa}>'
        else:
            return f'<Pedido {self.id} - Domicilio {self.cliente_nombre}>'
    
    @property
    def total(self):
        return sum(det.precio_total for det in self.detalles)





class DetallePedido(db.Model):
    __tablename__ = 'detalles_pedido'

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedidos.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('producto.id'), nullable=False)
    producto = db.Column(db.String(100), nullable=False)
    precio = db.Column(db.Float, nullable=False)
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    descripcion = db.Column(db.String(255), nullable=True)  # <-- Nuevo campo

    @property
    def precio_total(self):
        return self.precio * self.cantidad

    def __repr__(self):
        return f'<Detalle {self.id} - Producto {self.producto} x {self.cantidad}>'




class CierreCaja(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.DateTime, default=datetime.now)
    total_ventas = db.Column(db.Numeric(10, 2))
    total_efectivo = db.Column(db.Numeric(10, 2))
    total_fiado = db.Column(db.Integer)
    pedidos_facturados = db.Column(db.Integer)
    pedidos_pendientes = db.Column(db.Integer)
    guardado = db.Column(db.Boolean, default=False)  # Nuevo campo
    
class Rol(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    usuarios = db.relationship('Usuario', back_populates='rol', lazy=True)

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    correo = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    
    rol_id = db.Column(db.Integer, db.ForeignKey('rol.id'), nullable=False)
    rol = db.relationship('Rol', back_populates='usuarios')

class Permiso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)  # ej: 'ver_ventas', 'ver_cocina'

class RolPermiso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rol_id = db.Column(db.Integer, db.ForeignKey('rol.id'), nullable=False)
    permiso_id = db.Column(db.Integer, db.ForeignKey('permiso.id'), nullable=False)

    rol = db.relationship('Rol', backref=db.backref('permisos_asignados', lazy=True))
    permiso = db.relationship('Permiso', backref=db.backref('roles_asociados', lazy=True))
    
class Gasto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, nullable=False)
    proveedor = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.String(255), nullable=False)
    valor = db.Column(db.Integer, nullable=False)
    categoria = db.Column(db.String(50), nullable=False)  # Ej: 'Insumos', 'Servicios'
    estado = db.Column(db.String(20), nullable=False, default='pendiente')  # pagado o pendiente
    archivo = db.Column(db.String(120))  # Nombre del archivo PDF si se sube

    



