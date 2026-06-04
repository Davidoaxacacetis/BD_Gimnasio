import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from main import GestorGimnasio
from datetime import datetime
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv
from functools import wraps


load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "LlavePorDefectoSiNoHayEnv")

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD") 
app.config['MAIL_DEFAULT_SENDER'] = os.getenv("MAIL_USERNAME", "noreply@gimnasio.com")

mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)
gestor = GestorGimnasio()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash("Por favor, inicia sesión para acceder.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def normalizar_miembros(lista_miembros):
    for m in lista_miembros:
        disc = m.get('disciplinas')
        if not disc:
            m['disciplinas'] = []
        elif isinstance(disc, str):
            m['disciplinas'] = [disc]
    return lista_miembros

@app.route('/')
@login_required
def dashboard():

    todos_los_miembros = gestor.obtener_miembros_con_entrenador()
    mes_seleccionado = request.args.get('mes')

    miembros_activos = []
    miembros_inactivos = []

    for m in todos_los_miembros:
        miembro = m.copy()

        disc = miembro.get('disciplinas')
        if not disc:
            miembro['disciplinas'] = []
        elif isinstance(disc, str):
            miembro['disciplinas'] = [disc]

        if miembro.get('estado') == 'Activo':
            if mes_seleccionado:
                fecha = miembro.get('fecha_vencimiento', '')
                if fecha and len(fecha.split('-')) > 1:
                    if fecha.split('-')[1] == mes_seleccionado:
                        miembros_activos.append(miembro)
            else:
                miembros_activos.append(miembro)
        else:
            miembros_inactivos.append(miembro)

    entrenadores = gestor.obtener_todos_los_entrenadores()

    return render_template(
        'dashboard.html',
        nombre=session.get('nombre'),
        miembros_activos=miembros_activos,
        miembros_inactivos=miembros_inactivos,
        entrenadores=entrenadores,
        mes_seleccionado=mes_seleccionado
    )

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form.get('nombre')
        email = request.form.get('email')
        contraseña = request.form.get("contraseña")
        confirmarcontra = request.form.get("confirmarcontra")

        if contraseña != confirmarcontra:
            flash("Las contraseñas no coinciden", "danger")
            return render_template("registro.html", nombre=nombre, email=email)

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
        usuario = gestor.validar_credenciales(email, contraseña)

        if usuario:
            session['logueado'] = True
            session['usuario_id'] = str(usuario['_id'])
            session['nombre'] = usuario['nombre']
            flash(f"¡Bienvenido de nuevo, {usuario['nombre']}!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Correo o contraseña incorrectos.", "danger")
                
    return render_template('login.html')

@app.route('/recuperar_password', methods=['GET', 'POST'])
def recuperar_password():
    if request.method == 'POST':
        email = request.form.get('email')
        usuario = gestor.usuarios_app.find_one({"email": email}) 
        
        if not usuario:
            flash("El correo electrónico no se encuentra registrado.", "danger")
            return render_template('pedir_email.html')
        
        token = serializer.dumps(email, salt='recuperar-password')
        enlace_recuperacion = url_for('restablecer_token', token=token, _external=True)
        remitente = os.getenv("MAIL_USERNAME") or app.config['MAIL_DEFAULT_SENDER']
        
        msg = Message("Restablecer tu Contraseña - Gimnasio", sender=remitente, recipients=[email])
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
            return render_template('nueva_password.html', token=token)
        
        pass_encriptada = generate_password_hash(nueva_pass)
        
        if gestor.actualizar_password(email, pass_encriptada):
            flash("Contraseña actualizada correctamente.", "success")
            return redirect(url_for('login'))
        else:
            flash("Error al actualizar la contraseña.", "danger")
            
    return render_template('nueva_password.html', token=token)

@app.route('/editar_usuario', methods=['GET', 'POST'])
@login_required
def editar_usuario():
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

@app.route('/agregar_entrenador', methods=['POST'])
@login_required
def agregar_entrenador():

    nombre = request.form.get("nombre")
    especialidad = request.form.get("especialidad")
    telefono = request.form.get("telefono")
    cobro = request.form.get("cobro")

    entrenador_id = gestor.agregar_entrenador(
        nombre,
        especialidad,
        telefono,
        cobro
        )   

    if entrenador_id:
        flash("Entrenador registrado correctamente", "success")
    else:
        flash("Error al registrar entrenador", "danger")

    return redirect(url_for('dashboard'))

@app.route('/cancelar_entrenador/<entrenador_id>', methods=['POST'])
@login_required
def cancelar_entrenador(entrenador_id):

    motivo = request.form.get("motivo")

    gestor.cancelar_entrenador(
        entrenador_id,
        motivo
    )

    flash("Entrenador cancelado correctamente", "warning")

    return redirect(url_for('dashboard'))


@app.route('/reactivar_entrenador/<entrenador_id>')
@login_required
def reactivar_entrenador(entrenador_id):

    if gestor.reactivar_entrenador(entrenador_id):
        flash("Entrenador reactivado correctamente", "success")
    else:
        flash("Error al reactivar entrenador", "danger")

    return redirect(url_for('dashboard'))

@app.route('/editar_entrenador/<entrenador_id>', methods=['POST'])
@login_required
def editar_entrenador(entrenador_id):

    datos = {
        "nombre": request.form.get("nombre"),
        "especialidad": request.form.get("especialidad"),
        "telefono": request.form.get("telefono"),
        "cobro": float(request.form.get("cobro"))
    }

    if gestor.editar_entrenador(entrenador_id, datos):
        flash("Entrenador actualizado", "success")
    else:
        flash("Error al actualizar entrenador", "danger")

    return redirect(url_for("dashboard"))

@app.route('/comprar_membresia', methods=['POST'])
@login_required
def comprar_membresia():
    nombre = request.form.get('nombre_cliente')
    telefono = request.form.get('telefono')
    disciplinas = request.form.getlist('disciplinas') 
    tipo = request.form.get('tipo_membresia')          
    pago = request.form.get('pago')
    entrenador_id = request.form.get('entrenador_id') 

    if gestor.registrar_membresia_cliente(nombre, telefono, disciplinas, tipo, pago, entrenador_id):
        flash(f"Membresía de {nombre} registrada exitosamente.", "success")
    else:
        flash("Error al registrar la membresía.", "danger")
    return redirect(url_for('dashboard'))

@app.route('/agregar_pago/<telefono>', methods=['POST'])
@login_required
def agregar_pago(telefono):
    monto = request.form.get('monto')
    concepto = request.form.get('concepto')
    
    if gestor.agregar_pago_adicional(telefono, monto, concepto):
        flash("Pago anexado al historial con éxito.", "success")
    else:
        flash("No se pudo procesar el pago.", "danger")
    return redirect(url_for('dashboard'))

@app.route('/eliminar_membresia/<telefono>')
@login_required
def borrar_miembro(telefono):
    if gestor.eliminar_membresia(telefono):
        flash("Membresía registrada eliminada correctamente.", "success")
    else:
        flash("No se pudo eliminar la membresía.", "danger")
    return redirect(url_for('dashboard'))

@app.route('/cambiar_estado/<telefono>/<estado>')
@login_required
def cambiar_estado(telefono, estado):
    if gestor.cambiar_estado_membresia(telefono, estado):
        flash(f"Membresía cambiada a {estado} con éxito.", "info")
    else:
        flash("Error al cambiar el estado.", "danger")
    return redirect(url_for('dashboard'))

@app.route('/editar_membresia/<telefono_actual>', methods=['POST'])
@login_required
def editar_membresia_ruta(telefono_actual):

    entrenador_id = request.form.get("entrenador_id")

    datos_actualizados = {
    "nombre": request.form.get("nombre"),
    "telefono": request.form.get("telefono"),
    "disciplinas": request.form.getlist("disciplinas"),
    "membresia_actual": request.form.get("membresia_actual"),
    "entrenador_id": request.form.get("entrenador_id")
}

    pago_str = request.form.get("pago_realizado")

    if pago_str and float(pago_str) > 0:
        datos_actualizados["pago_realizado"] = float(pago_str)

    if gestor.modificar_membresia(telefono_actual, datos_actualizados):
        flash("Membresía modificada correctamente.", "success")
    else:
        flash("No se realizaron cambios o hubo un inconveniente.", "danger")

    return redirect(url_for('dashboard'))

@app.route('/cancelar_membresia/<telefono>', methods=['POST'])
@login_required
def cancelar_membresia(telefono):

    motivo = request.form.get("motivo_cancelacion")

    gestor.membresias.update_one(
        {"telefono_cliente": telefono},
        {
            "$set": {
                "estado": "Inactivo",
                "motivo_cancelacion": motivo
            }
        }
    )

    flash("Membresía cancelada correctamente", "warning")
    return redirect(url_for("dashboard"))

@app.route('/perfil')
@login_required
def perfil():
    usuario = gestor.obtener_usuario(session['usuario_id'])
    return render_template('perfil.html', usuario=usuario)

@app.route('/logout')
def logout():
    session.clear() 
    flash("Has cerrado sesión correctamente", "info")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)