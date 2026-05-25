import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from main import GestorGimnasio
from datetime import datetime
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Cargar configuraciones seguras
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "LlavePorDefectoSiNoHayEnv")

# --- CONFIGURACIÓN DE CORREO DESDE EL ENTORNO ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD") 
app.config['MAIL_DEFAULT_SENDER'] = os.getenv("MAIL_USERNAME")

mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)
gestor = GestorGimnasio()

# --- RUTAS ---

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        contraseña = request.form.get("contraseña")
        confirmarcontra = request.form.get("confirmarcontra")

        if contraseña != confirmarcontra:
            flash("Las contraseñas no coinciden", "danger")
            return render_template("registro.html")

        pass_encriptada = generate_password_hash(contraseña)
        usuario_id = gestor.crear_usuario(nombre, email, pass_encriptada)

        if usuario_id:
            flash("Registro exitoso. ¡Ya puedes iniciar sesión!", "success")
            return redirect(url_for('login'))
        else:
            flash('El correo ya está registrado o hubo un error.', 'danger')
            
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        contraseña = request.form.get('contraseña')
        
        usuario = gestor.usuarios.find_one({"email": email})

        if not usuario:
            flash("El usuario no existe. Por favor, regístrate.", "danger")
        else:
            if check_password_hash(usuario['password'], contraseña):
                session['logueado'] = True
                session['usuario_id'] = str(usuario['_id'])
                session['nombre'] = usuario['nombre']
                flash(f"¡Bienvenido de nuevo, {usuario['nombre']}!", "success")
                return redirect(url_for('dashboard'))
            else:
                flash("Contraseña incorrecta.", "danger")
                
    return render_template('login.html')

@app.route('/recuperar_password', methods=['GET', 'POST'])
def recuperar_password():
    if request.method == 'POST':
        email = request.form.get('email')
        usuario = gestor.usuarios.find_one({"email": email}) 
        
        if not usuario:
            flash("El correo electrónico no se encuentra registrado.", "danger")
            return render_template('pedir_email.html')
        
        token = serializer.dumps(email, salt='recuperar-password')
        enlace_recuperacion = url_for('restablecer_token', token=token, _external=True)
        
        msg = Message("Restablecer tu Contraseña - Gimnasio", recipients=[email])
        msg.body = f"Hola {usuario['nombre']}, haz clic aquí para cambiar tu clave: {enlace_recuperacion}"
        
        try:
            mail.send(msg)
            return render_template('confirmacion_envio.html')
        except Exception as e:
            flash(f"Error al enviar el correo: {str(e)}", "danger")
            return render_template('pedir_email.html')
            
    return render_template('pedir_email.html')

@app.route('/restablecer/<token>', methods=['GET', 'POST'])
def restablecer_token(token):
    try:
        email = serializer.loads(token, salt='recuperar-password', max_age=1800)
    except:
        flash("El enlace es inválido o ha expirado.", "danger")
        return redirect(url_for('recuperar_password'))

    if request.method == 'POST':
        nueva_pass = request.form.get('contraseña')
        confirmar_pass = request.form.get('confirmar_contraseña')

        if nueva_pass != confirmar_pass:
            flash("Las contraseñas no coinciden.", "danger")
            return render_template('nueva_password.html')
        
        pass_encriptada = generate_password_hash(nueva_pass)
        
        if gestor.actualizar_password(email, pass_encriptada):
            flash("Contraseña actualizada correctamente.", "success")
            return redirect(url_for('login'))
        else:
            flash("Error al actualizar la contraseña.", "danger")
            
    return render_template('nueva_password.html')

@app.route('/editar_usuario', methods=['GET', 'POST'])
def editar_usuario():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    usuario_id = session['usuario_id']
    if request.method == 'POST':
        datos_nuevos = {
            'nombre': request.form.get('nombre'),
            'email': request.form.get('email')
        }
        datos_nuevos = {k: v for k, v in datos_nuevos.items() if v}

        if gestor.actualizar_usuario(usuario_id, datos_nuevos):
            if 'nombre' in datos_nuevos: session['nombre'] = datos_nuevos['nombre']
            flash('Perfil actualizado correctamente', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('No se realizaron cambios.', 'warning')

    usuario = gestor.obtener_usuario(usuario_id)
    return render_template('editar.html', usuario=usuario)

@app.route('/logout')
def logout():
    session.clear() 
    flash("Has cerrado sesión correctamente", "info")
    return redirect(url_for('login'))

@app.route('/perfil')
def perfil():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    usuario = gestor.obtener_usuario(session['usuario_id'])
    return render_template('perfil.html', usuario=usuario)

@app.route('/')
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    miembros = gestor.obtener_todos_los_miembros()
    return render_template('dashboard.html', 
                            nombre=session['nombre'], 
                            miembros=miembros)

@app.route('/comprar_membresia', methods=['POST'])
def comprar_membresia():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))

    nombre = request.form.get('nombre_cliente')
    telefono = request.form.get('telefono')
    disciplina = request.form.get('plan_disciplina') 
    tipo = request.form.get('tipo_membresia')        
    pago = request.form.get('pago')

    if gestor.registrar_membresia_cliente(nombre, telefono, disciplina, tipo, pago):
        flash(f"Membresía de {nombre} registrada exitosamente.", "success")
    else:
        flash("Error al registrar la membresía.", "danger")
    return redirect(url_for('dashboard'))

@app.route('/eliminar_membresia/<telefono>')
def borrar_miembro(telefono):
    if gestor.eliminar_membresia(telefono):
        flash("Miembro eliminado correctamente.", "success")
    else:
        flash("No se pudo eliminar.", "danger")
    return redirect(url_for('dashboard'))

@app.route('/cambiar_estado/<telefono>/<estado>')
def cambiar_estado(telefono, estado):
    if gestor.cambiar_estado_membresia(telefono, estado):
        flash(f"Membresía cambiada a {estado}.", "info")
    else:
        flash("Error al cambiar el estado.", "danger")
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    app.run(debug=True)