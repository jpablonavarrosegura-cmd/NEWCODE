from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from werkzeug.security import generate_password_hash, check_password_hash
import os
import re
from datetime import datetime

app = Flask(__name__, 
            template_folder='NEWCODE1/templates',
            static_folder='NEWCODE1/static')

# ==================== CONFIGURACIÓN ====================
basedir = os.path.abspath(os.path.dirname(__file__))

# SECRET_KEY: NUNCA hardcodeada en producción. Lee de env o genera una temporal para dev.
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-temporal-cambiar-en-produccion')

# Base de datos
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'usuarios.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Seguridad de cookies de sesión
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
# app.config['SESSION_COOKIE_SECURE'] = True  # Descomentar en producción con HTTPS

db = SQLAlchemy(app)

# Email del administrador/registrador
ADMIN_EMAIL = 'js_8@gmail.com'


def es_email_administrador(email):
    """Compara emails normalizados para evitar errores por mayúsculas o espacios."""
    if not email:
        return False
    return email.strip().lower() == ADMIN_EMAIL.strip().lower()


# ==================== MODELOS ====================
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    apellido = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    empresa = db.Column(db.String(200))
    telefono = db.Column(db.String(20))
    password = db.Column(db.String(255), nullable=False)
    fecha_registro = db.Column(db.DateTime, default=db.func.now())
    
    def __repr__(self):
        return f'<Usuario {self.email}>'


class MensajeContacto(db.Model):
    __tablename__ = 'mensajes_contacto'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    mensaje = db.Column(db.Text, nullable=False)
    respuesta_admin = db.Column(db.Text, nullable=True)
    estado = db.Column(db.String(20), default='nuevo', nullable=False)
    fecha_registro = db.Column(db.DateTime, default=db.func.now())

    def __repr__(self):
        return f'<MensajeContacto {self.email}>'


# ==================== UTILIDADES ====================
def es_registrador():
    """Verifica si el usuario actual es el administrador/registrador.
    Siempre se valida contra la base de datos para evitar sesiones desactualizadas
    o banderas cacheadas que bloqueen acceso al panel de administración.
    """
    user_id = session.get('user_id')
    if not user_id:
        return False

    usuario_actual = Usuario.query.get(user_id)
    if usuario_actual is None:
        session.pop('is_admin', None)
        return False

    es_admin = es_email_administrador(usuario_actual.email)
    session['is_admin'] = es_admin
    return es_admin


def validar_email(email):
    """Valida formato básico de email."""
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(patron, email) is not None


def validar_password(password):
    """Valida fortaleza mínima de contraseña."""
    if len(password) < 6:
        return "La contraseña debe tener al menos 6 caracteres."
    return None


@app.context_processor
def inject_user():
    user_id = session.get('user_id')
    current_user = Usuario.query.get(user_id) if user_id else None
    return {
        'user_logged_in': user_id is not None,
        'current_user': current_user,
        'puede_gestionar_usuarios': es_registrador(),
        'puede_ver_ayuda': es_registrador()
    }


# ==================== INICIALIZACIÓN BD ====================
with app.app_context():
    db.create_all()
    inspector = inspect(db.engine)
    
    # Verificar y agregar columna respuesta_admin si no existe
    try:
        columnas = [col['name'] for col in inspector.get_columns('mensajes_contacto')]
        if 'respuesta_admin' not in columnas:
            db.session.execute(text("ALTER TABLE mensajes_contacto ADD COLUMN respuesta_admin TEXT"))
            db.session.commit()
    except Exception as e:
        db.session.rollback()
        app.logger.warning(f"Error al verificar/crear columna respuesta_admin: {e}")


# ==================== RUTAS PÚBLICAS ====================
@app.route('/')
def inicio():
    return render_template('index.html')


@app.route('/productos')
def productos():
    return render_template('productos.html')


@app.route('/contactenos', methods=['GET', 'POST'])
def contactenos():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        email = request.form.get('email', '').strip()
        mensaje = request.form.get('mensaje', '').strip()

        if not all([nombre, email, mensaje]):
            flash('Por favor completa todos los campos para enviarnos tu solicitud.', 'danger')
        elif not validar_email(email):
            flash('Por favor ingresa un email válido.', 'danger')
        else:
            try:
                nuevo_mensaje = MensajeContacto(
                    nombre=nombre,
                    email=email,
                    mensaje=mensaje
                )
                db.session.add(nuevo_mensaje)
                db.session.commit()
                flash('Gracias por contactarnos. Hemos recibido tu mensaje y te responderemos pronto.', 'success')
            except Exception as e:
                db.session.rollback()
                flash('Ocurrió un error al guardar tu mensaje. Inténtalo de nuevo.', 'danger')

        return redirect(url_for('contactenos'))

    return render_template('contactenos.html')


@app.route('/nosotros')
def nosotros():
    return render_template('nosotros.html')


@app.route('/mision')
def mision():
    return render_template('mision.html')


@app.route('/vision')
def vision():
    return render_template('vision.html')


# ==================== AUTENTICACIÓN ====================
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        apellido = request.form.get('apellido', '').strip()
        email = request.form.get('email', '').strip().lower()
        empresa = request.form.get('empresa', '').strip()
        telefono = request.form.get('telefono', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validaciones
        if not all([nombre, apellido, email, password]):
            return render_template('registro.html', error='Los campos obligatorios no pueden estar vacíos')
        
        if not validar_email(email):
            return render_template('registro.html', error='El formato del email no es válido')
        
        if password != confirm_password:
            return render_template('registro.html', error='Las contraseñas no coinciden')
        
        error_pass = validar_password(password)
        if error_pass:
            return render_template('registro.html', error=error_pass)
        
        # Verificar si el email ya existe
        usuario_existente = Usuario.query.filter_by(email=email).first()
        if usuario_existente:
            return render_template('registro.html', error='El email ya está registrado')
        
        # Crear nuevo usuario
        try:
            nuevo_usuario = Usuario(
                nombre=nombre,
                apellido=apellido,
                email=email,
                empresa=empresa,
                telefono=telefono,
                password=generate_password_hash(password)
            )
            db.session.add(nuevo_usuario)
            db.session.commit()

            session['user_id'] = nuevo_usuario.id
            session['user_nombre'] = nuevo_usuario.nombre
            session['is_admin'] = es_email_administrador(email)
            
            flash('Registro exitoso. ¡Bienvenido!', 'success')
            return redirect(url_for('inicio'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error en registro: {e}")
            return render_template('registro.html', error='Error al registrar. Por favor inténtalo de nuevo.')
    
    return render_template('registro.html')


@app.route('/iniciar_sesion', methods=['GET', 'POST'])
def iniciar_sesion():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        if not email or not password:
            return render_template('iniciar_sesion.html', error='Email y contraseña son obligatorios')
        
        # Buscar usuario en la base de datos
        usuario = Usuario.query.filter_by(email=email).first()
        
        if usuario and check_password_hash(usuario.password, password):
            session.clear()  # Limpia cualquier sesión previa
            session['user_id'] = usuario.id
            session['user_nombre'] = usuario.nombre
            session['is_admin'] = es_email_administrador(usuario.email)
            
            flash(f'Bienvenido, {usuario.nombre}!', 'success')
            return redirect(url_for('inicio'))
        else:
            # Retraso artificial mínimo para dificultar fuerza bruta
            import time
            time.sleep(0.5)
            return render_template('iniciar_sesion.html', error='Email o contraseña incorrectos')
    
    return render_template('iniciar_sesion.html')


@app.route('/cerrar_sesion')
def cerrar_sesion():
    session.clear()
    flash('Has cerrado sesión correctamente.', 'info')
    return redirect(url_for('inicio'))


# ==================== NOTIFICACIONES ====================
@app.route('/notificaciones')
def notificaciones():
    if not session.get('user_id'):
        flash('Inicia sesión para ver tus notificaciones.', 'warning')
        return redirect(url_for('iniciar_sesion'))

    usuario_actual = Usuario.query.get(session['user_id'])
    if not usuario_actual:
        session.clear()
        flash('Tu sesión ha expirado.', 'warning')
        return redirect(url_for('iniciar_sesion'))

    mensajes = MensajeContacto.query.filter_by(email=usuario_actual.email)\
                                    .order_by(MensajeContacto.fecha_registro.desc())\
                                    .all()
    return render_template('notificaciones.html', mensajes=mensajes)


# ==================== PANEL ADMIN / AYUDA ====================
@app.route('/ayuda')
def ayuda():
    if not es_registrador():
        flash('Solo el administrador puede ver esta sección.', 'danger')
        return redirect(url_for('inicio'))

    mensajes = MensajeContacto.query.order_by(MensajeContacto.fecha_registro.desc()).all()
    return render_template('ayuda.html', mensajes=mensajes)


@app.route('/ayuda/<int:mensaje_id>/atender', methods=['POST'])
def atender_mensaje(mensaje_id):
    if not es_registrador():
        flash('Solo el administrador puede realizar esta acción.', 'danger')
        return redirect(url_for('inicio'))

    mensaje = MensajeContacto.query.get_or_404(mensaje_id)
    mensaje.estado = 'atendido'
    db.session.commit()
    flash('El mensaje ha sido marcado como atendido.', 'success')
    return redirect(url_for('ayuda'))


@app.route('/ayuda/<int:mensaje_id>/responder', methods=['POST'])
def responder_mensaje(mensaje_id):
    if not es_registrador():
        flash('Solo el administrador puede responder mensajes.', 'danger')
        return redirect(url_for('inicio'))

    mensaje = MensajeContacto.query.get_or_404(mensaje_id)
    respuesta = request.form.get('respuesta_admin', '').strip()

    if not respuesta:
        flash('Escribe una respuesta antes de enviar.', 'danger')
        return redirect(url_for('ayuda'))

    try:
        mensaje.respuesta_admin = respuesta
        mensaje.estado = 'respondido'
        db.session.commit()
        flash('La respuesta ha sido enviada correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error al enviar la respuesta.', 'danger')
    
    return redirect(url_for('ayuda'))


@app.route('/admin')
def admin_panel():
    if not es_registrador():
        flash('Solo el registrador puede acceder a este panel.', 'danger')
        return redirect(url_for('inicio'))

    usuarios = Usuario.query.all()
    return render_template('admin.html', usuarios=usuarios)


@app.route('/usuarios')
def ver_usuarios():
    if not es_registrador():
        flash('Solo el registrador puede ver los usuarios registrados.', 'danger')
        return redirect(url_for('inicio'))

    usuarios = Usuario.query.all()
    return render_template('usuarios.html', usuarios=usuarios)


@app.route('/usuarios/<int:usuario_id>/editar', methods=['GET', 'POST'])
def editar_usuario(usuario_id):
    if not es_registrador():
        flash('Solo el registrador puede editar usuarios.', 'danger')
        return redirect(url_for('inicio'))

    usuario = Usuario.query.get_or_404(usuario_id)

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        apellido = request.form.get('apellido', '').strip()
        email = request.form.get('email', '').strip().lower()
        empresa = request.form.get('empresa', '').strip()
        telefono = request.form.get('telefono', '').strip()

        if not all([nombre, apellido, email]):
            flash('Los campos obligatorios no pueden estar vacíos.', 'danger')
            return render_template('editar_usuario.html', usuario=usuario)
        
        if not validar_email(email):
            flash('El formato del email no es válido.', 'danger')
            return render_template('editar_usuario.html', usuario=usuario)

        email_existente = Usuario.query.filter(Usuario.email == email, Usuario.id != usuario_id).first()
        if email_existente:
            flash('El email ya está registrado por otro usuario.', 'danger')
            return render_template('editar_usuario.html', usuario=usuario)

        try:
            usuario.nombre = nombre
            usuario.apellido = apellido
            usuario.email = email
            usuario.empresa = empresa
            usuario.telefono = telefono
            db.session.commit()

            # Si el usuario editado es el actual, actualiza la sesión
            if session.get('user_id') == usuario.id:
                session['user_nombre'] = usuario.nombre
                session['is_admin'] = es_email_administrador(usuario.email)

            flash('Usuario actualizado correctamente.', 'success')
            return redirect(url_for('ver_usuarios'))
        except Exception as e:
            db.session.rollback()
            app.logger.error(f"Error al editar usuario {usuario_id}: {e}")
            flash('Error al actualizar el usuario. Inténtalo de nuevo.', 'danger')
            return render_template('editar_usuario.html', usuario=usuario)

    return render_template('editar_usuario.html', usuario=usuario)


@app.route('/usuarios/<int:usuario_id>/eliminar', methods=['POST'])
def eliminar_usuario(usuario_id):
    if not es_registrador():
        flash('Solo el registrador puede eliminar usuarios.', 'danger')
        return redirect(url_for('inicio'))

    usuario = Usuario.query.get_or_404(usuario_id)
    
    # Protección: evitar que se elimine al único administrador
    if usuario.email == ADMIN_EMAIL:
        flash('No puedes eliminar la cuenta del administrador principal.', 'danger')
        return redirect(url_for('ver_usuarios'))

    try:
        if session.get('user_id') == usuario.id:
            session.clear()
        db.session.delete(usuario)
        db.session.commit()
        flash('Usuario eliminado correctamente.', 'success')
    except Exception as e:
        db.session.rollback()
        app.logger.error(f"Error al eliminar usuario {usuario_id}: {e}")
        flash('Error al eliminar el usuario. Inténtalo de nuevo.', 'danger')

    return redirect(url_for('ver_usuarios'))


# ==================== MANEJO DE ERRORES ====================
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html') if os.path.exists(os.path.join(app.template_folder, '404.html')) else ("Página no encontrada", 404)


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html') if os.path.exists(os.path.join(app.template_folder, '500.html')) else ("Error interno del servidor", 500)


# ==================== EJECUCIÓN ====================
if __name__ == '__main__':
    app.run(debug=True, port=5000)