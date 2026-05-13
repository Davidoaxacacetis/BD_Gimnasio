from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, ConnectionFailure
from bson.objectid import ObjectId
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import os

class GestorGimnasio    :
    def __init__(self, uri: str = 'mongodb://localhost:27017/'):
        """Inicializar conexión a MongoDB"""
        try:
            self.usuarios_gym = self.db['Usuarios']
            self.membresias = self.db['Membresias']
            self.trabajadores = self.db['Trabajadores']
            self.entrenadores = self.db['Entrenadores']
            self.productos = self.db['Productos']
            self.tareas = self.db['tareas']
            self.usuarios_app = self.db['usuarios_sistema']
            
            self._crear_indices()
            print("✅ Conectado a MongoDB")
        except ConnectionFailure:
            print("❌ Error: No se pudo conectar a MongoDB")
            raise
    
    def _crear_indices(self):
        """Crear índices para mejorar rendimiento"""
        self.usuarios.create_index("email", unique=True)
        self.tareas.create_index([("usuario_id", 1), ("fecha_creacion", -1)])
        self.tareas.create_index("estado")
    
    
    def obtener_usuario(self, usuario_id: str) -> Optional[Dict]:
        """Obtener usuario por ID"""
        try:
            usuario = self.usuarios.find_one({"_id": ObjectId(usuario_id)})
            if usuario:
                usuario['_id'] = str(usuario['_id'])
            return usuario
        except Exception as e:
            print(f"Error al obtener usuario: {e}")
            return None
    
    def crear_usuario(self, nombre: str, email: str, contraseña: str) -> Optional[str]:
        """Crear un nuevo usuario con contraseña"""
        try:
            resultado = self.usuarios.insert_one({
                "nombre": nombre,
                "email": email,
                "password": contraseña,
                "fecha_registro": datetime.now(),
                "activo": True
            })
            return str(resultado.inserted_id)
        except DuplicateKeyError:
            print(f"❌ Error: El email {email} ya está registrado")
            return None

    def actualizar_usuario(self, usuario_id: str, datos_actualizados: Dict) -> bool:
        """
        Actualiza los datos de un usuario existente.
        Permite actualizar nombre, email, password, etc.
        """
        try:
            campos_permitidos = ["nombre", "email", "password", "activo"]
            update_data = {k: v for k, v in datos_actualizados.items() if k in campos_permitidos}
            
            if not update_data:
                return False

            resultado = self.usuarios.update_one(
                {"_id": ObjectId(usuario_id)},
                {"$set": update_data}
            )
            
            return resultado.modified_count > 0
        except DuplicateKeyError:
            print(f"❌ Error: El email ya está registrado por otro usuario")
            return False
        except Exception as e:
            print(f"❌ Error al actualizar usuario: {e}")
            return False

    def validar_credenciales(self, email: str, contraseña: str) -> Optional[Dict]:
        """Validar credenciales para el Login"""
        try:
            usuario = self.usuarios.find_one({"email": email, "password": contraseña})
            if usuario:
                usuario['_id'] = str(usuario['_id'])
            return usuario
        except Exception as e:
            print(f"Error al validar credenciales: {e}")
            return None
    def registrar_membresia_cliente(self, nombre, telefono, tipo_membresia, pago):
        """Almacena la información de los clientes y sus planes[cite: 12, 14]."""
        datos_cliente = {
            "nombre": nombre,
            "telefono": telefono,
            "membresia": tipo_membresia,
            "pago_realizado": float(pago),
            "fecha_inscripcion": datetime.now().strftime("%Y-%m-%d"),
            "estado": "Activo"
        }
        return self.usuarios_gym.update_one(
            {"telefono": telefono}, 
            {"$set": datos_cliente}, 
            upsert=True
        )
    
    def cerrar_conexion(self):
        """Cerrar conexión a MongoDB"""
        if self.cliente:
            self.cliente.close()
            print("🔌 Conexión cerrada")