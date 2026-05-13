from flask import Flask, render_template, request, redirect, url_for, session, flash
from main import GestorGimnasio
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'Ruby'
gestor = GestorGimnasio()

@app.route('/')
def dashboard():
    if 'usuario_id' not in session:
        return redirect(url_for('login'))
    
    # Ahora obtenemos miembros del gimnasio, no tareas
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

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        if request.form.get("contraseña") != request.form.get("confirmarcontra"):
            flash("Contraseñas no coinciden", "danger")
            return render_template("registro.html")
        if gestor.crear_usuario(request.form.get('nombre'), request.form.get('email'), request.form.get('contraseña')):
            flash('Registro exitoso.', 'success')
            return redirect(url_for('login'))
    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = gestor.validar_credenciales(request.form.get('email'), request.form.get('contraseña'))
        if user:
            session.update({'logueado': True, 'usuario_id': str(user['_id']), 'nombre': user['nombre']})
            return redirect(url_for('dashboard'))
        flash("Credenciales incorrectas", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)