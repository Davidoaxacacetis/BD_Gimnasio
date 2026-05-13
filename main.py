from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, ConnectionFailure
from bson.objectid import ObjectId
from datetime import datetime
from typing import Optional, List, Dict

class GestorGimnasio:
    def __init__(self, uri: str = 'mongodb://localhost:27017/'):
        try:
            self.client = MongoClient(uri)
            self.db = self.client['Gimnasio']
            
            # Colecciones según el documento
            self.usuarios_gym = self.db['Usuarios']       # Los miembros
            self.usuarios_app = self.db['usuarios_sistema'] # Tú (admin)
            self.membresias = self.db['Membresias']
            self.trabajadores = self.db['Trabajadores']
            self.entrenadores = self.db['Entrenadores']
            self.productos = self.db['Productos']
            
            self._crear_indices()
            print("✅ Conectado a BD Gimnasio")
        except ConnectionFailure:
            print("❌ Error de conexión")
            raise

    def _crear_indices(self):
        self.usuarios_app.create_index("email", unique=True)
        self.usuarios_gym.create_index("telefono", unique=True)

    # Lógica de Clientes y Membresías
    def registrar_membresia_cliente(self, nombre, telefono, tipo_membresia, pago):
        try:
            datos = {
                "nombre": nombre,
                "telefono": telefono,
                "membresia": tipo_membresia,
                "pago_realizado": float(pago),
                "fecha_inscripcion": datetime.now().strftime("%Y-%m-%d"),
                "estado": "Activo"
            }
            self.usuarios_gym.update_one({"telefono": telefono}, {"$set": datos}, upsert=True)
            return True
        except Exception:
            return False

    def obtener_todos_los_miembros(self):
        return list(self.usuarios_gym.find())

    # Lógica de Acceso al Sistema
    def crear_usuario(self, nombre, email, contraseña):
        try:
            return self.usuarios_app.insert_one({
                "nombre": nombre, "email": email, "password": contraseña
            }).inserted_id
        except DuplicateKeyError:
            return None

    def validar_credenciales(self, email, contraseña):
        return self.usuarios_app.find_one({"email": email, "password": contraseña})

    def obtener_usuario(self, uid):
        return self.usuarios_app.find_one({"_id": ObjectId(uid)})

    def actualizar_usuario(self, uid, datos):
        res = self.usuarios_app.update_one({"_id": ObjectId(uid)}, {"$set": datos})
        return res.modified_count > 0