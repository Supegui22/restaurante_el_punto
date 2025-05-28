from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# Este archivo asume que SQLAlchemy se inicializó en app.py como `db = SQLAlchemy()`
from app import db

class Pedido(db.Model):
    __tablename__ = 'pedidos'

    id = db.Column(db.Integer, primary_key=True)
    mesa = db.Column(db.String(10), nullable=False)
    usuario = db.Column(db.String(100), nullable=False)
    estado = db.Column(db.String(20), default='activo')  # activo, enviado, cerrado, etc.
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    detalles = db.relationship('DetallePedido', backref='pedido', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Pedido {self.id} - Mesa {self.mesa}>'

class DetallePedido(db.Model):
    __tablename__ = 'detalles_pedido'

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedidos.id'), nullable=False)
    producto = db.Column(db.String(100), nullable=False)
    precio = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<Detalle {self.id} - Producto {self.producto}>'
