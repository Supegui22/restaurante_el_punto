from app import db

rol_permisos = db.Table('rol_permisos',
    db.Column('rol_id', db.Integer, db.ForeignKey('rol.id')),
    db.Column('permiso_id', db.Integer, db.ForeignKey('permiso.id'))
)

class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    correo = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    rol_id = db.Column(db.Integer, db.ForeignKey('rol.id'))
    rol = db.relationship('Rol', backref='usuarios')

class Rol(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)
    permisos = db.relationship('Permiso', secondary=rol_permisos, backref='roles')

class Permiso(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    descripcion = db.Column(db.String(100), nullable=False)

class Venta(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    producto = db.Column(db.String(100), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    precio_unitario = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'))
