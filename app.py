from flask import Flask, render_template, request, redirect, url_for, session, flash
from main import GestorGimnasio
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'Ruby'
gestor = GestorGimnasio()


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

        usuario_id = gestor.crear_usuario(nombre, email, contraseña)
        if usuario_id:
            usuario_id = str(usuario_id) 
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
            flash("Correo o contraseña incorrectos", "danger")
            
    return render_template('login.html')

@app.route('/recuperar_password', methods=['GET', 'POST'])
def recuperar_password():
    return render_template('recuperar.html')


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
            if 'email' in datos_nuevos: session['email'] = datos_nuevos['email']
            
            flash('Perfil actualizado correctamente', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('No se realizaron cambios o el email ya existe', 'warning')

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
    tipo = request.form.get('tipo_membresia')
    pago = request.form.get('pago')

    if gestor.registrar_membresia_cliente(nombre, telefono, tipo, pago):
        flash(f"Membresía de {nombre} registrada.", "success")
    else:
        flash("Error al registrar.", "danger")
    return redirect(url_for('dashboard'))


if __name__ == '__main__':
    app.run(debug=True)