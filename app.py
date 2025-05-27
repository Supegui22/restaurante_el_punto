from flask import Flask, render_template, request, redirect, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'clave-secreta'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)

from models import Usuario, Rol, Permiso, Venta

@app.before_first_request
def crear_base():
    db.create_all()
    # Crear permisos iniciales si no existen
    if not Permiso.query.first():
        db.session.add_all([
            Permiso(descripcion='ventas_punto'),
            Permiso(descripcion='ver_reportes'),
            Permiso(descripcion='gestion_usuarios')
        ])
        db.session.commit()

@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        correo = request.form['email']
        password = request.form['password']
        rol = request.form['role']
        user = Usuario.query.filter_by(correo=correo).first()
        if user and check_password_hash(user.password, password) and user.rol.nombre == rol:
            session['usuario_id'] = user.id
            session['rol'] = user.rol.nombre
            return redirect('/ventas')
        return 'Credenciales incorrectas'
    return render_template('login.html')

@app.route('/roles', methods=['GET', 'POST'])
def roles():
    if session.get('rol') != 'Admin':
        return 'Acceso denegado'
    if request.method == 'POST':
        nombre = request.form['role_name']
        permisos = request.form.getlist('permissions')
        nuevo_rol = Rol(nombre=nombre)
        db.session.add(nuevo_rol)
        db.session.commit()
        for descripcion in permisos:
            permiso = Permiso.query.filter_by(descripcion=descripcion).first()
            nuevo_rol.permisos.append(permiso)
        db.session.commit()
        return redirect('/roles')
    permisos = Permiso.query.all()
    return render_template('roles.html', permisos=permisos)

@app.route('/ventas', methods=['GET', 'POST'])
def ventas():
    if session.get('usuario_id') is None:
        return redirect('/login')
    if request.method == 'POST':
        producto = request.form['producto']
        cantidad = int(request.form['cantidad'])
        precio = float(request.form['precio_unitario'])
        total = cantidad * precio
        venta = Venta(producto=producto, cantidad=cantidad, precio_unitario=precio, total=total, usuario_id=session['usuario_id'])
        db.session.add(venta)
        db.session.commit()
        return redirect('/ventas')
    return render_template('ventas.html')

if __name__ == '__main__':
    app.run()
