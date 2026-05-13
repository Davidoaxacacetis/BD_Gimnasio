from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, ConnectionFailure
from bson.objectid import ObjectId
from datetime import datetime
from typing import Optional, List, Dict

class GestorGimnasio:
    def __init__(self, uri: str = 'mongodb://localhost:27017/'):
        """Inicializar conexión a MongoDB"""
        try:
            # 1. Establecer el cliente
            self.client = MongoClient(uri)
            
            # 2. Definir la base de datos
            self.db = self.client['Gimnasio']
            
            # 3. Definir las colecciones (Usando nombres consistentes)
            self.usuarios_gym = self.db['Usuarios']       # Miembros del gimnasio
            self.usuarios_app = self.db['usuarios_sistema'] # Usuarios con acceso al dashboard
            self.membresias = self.db['Membresias']
            self.trabajadores = self.db['Trabajadores']
            self.entrenadores = self.db['Entrenadores']
            self.productos = self.db['Productos']
            self.tareas = self.db['tareas']
            
            # Crear índices para optimizar búsquedas
            self._crear_indices()
            
            print("✅ Conectado a MongoDB - Base de Datos: Gimnasio")
        except ConnectionFailure:
            print("❌ Error: No se pudo conectar a MongoDB")
            raise

    def _crear_indices(self):
        """Crear índices para mejorar rendimiento"""
        try:
            # Índice único para los correos de los usuarios del sistema
            self.usuarios_app.create_index("email", unique=True)
            # Índice único para el teléfono de los miembros del gimnasio
            self.usuarios_gym.create_index("telefono", unique=True)
            # Índices para tareas
            self.tareas.create_index([("usuario_id", 1), ("fecha_creacion", -1)])
            self.tareas.create_index("estado")
        except Exception as e:
            print(f"⚠️ Aviso al crear índices: {e}")

    # --- Gestión de Usuarios del Sistema (Login/App) ---
    def obtener_usuario(self, usuario_id: str) -> Optional[Dict]:
        """Obtener usuario del sistema por ID"""
        try:
            usuario = self.usuarios_app.find_one({"_id": ObjectId(usuario_id)})
            if usuario:
                usuario['_id'] = str(usuario['_id'])
            return usuario
        except Exception as e:
            print(f"Error al obtener usuario: {e}")
            return None

    def crear_usuario(self, nombre: str, email: str, contraseña: str) -> Optional[str]:
        """Crear un nuevo usuario del sistema para el dashboard"""
        try:
            resultado = self.usuarios_app.insert_one({
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
        """Actualiza los datos de un usuario del sistema existente"""
        try:
            campos_permitidos = ["nombre", "email", "password", "activo"]
            update_data = {k: v for k, v in datos_actualizados.items() if k in campos_permitidos}
            
            if not update_data:
                return False

            resultado = self.usuarios_app.update_one(
                {"_id": ObjectId(usuario_id)},
                {"$set": update_data}
            )
            return resultado.modified_count > 0
        except Exception as e:
            print(f"❌ Error al actualizar usuario: {e}")
            return False

    def validar_credenciales(self, email: str, contraseña: str) -> Optional[Dict]:
        """Validar credenciales para el Login"""
        try:
            usuario = self.usuarios_app.find_one({"email": email, "password": contraseña})
            if usuario:
                usuario['_id'] = str(usuario['_id'])
            return usuario
        except Exception as e:
            print(f"Error al validar credenciales: {e}")
            return None

    # --- Gestión de Miembros del Gimnasio (Dashboard) ---
    def registrar_membresia_cliente(self, nombre, telefono, tipo_membresia, pago):
        """Registra o actualiza un cliente (miembro) y su plan de membresía"""
        try:
            datos_cliente = {
                "nombre": nombre,
                "telefono": telefono,
                "membresia": tipo_membresia,
                "pago_realizado": float(pago),
                "fecha_inscripcion": datetime.now().strftime("%Y-%m-%d"),
                "estado": "Activo"
            }
            # Se usa el teléfono para identificar al miembro único
            resultado = self.usuarios_gym.update_one(
                {"telefono": telefono}, 
                {"$set": datos_cliente}, 
                upsert=True
            )
            return True
        except Exception as e:
            print(f"❌ Error al registrar membresía: {e}")
            return False

    # --- Gestión de Tareas ---
    def obtener_tareas_usuario(self, usuario_id: str) -> List[Dict]:
        """Obtener todas las tareas de un usuario administrador"""
        try:
            return list(self.tareas.find({"usuario_id": usuario_id}))
        except Exception as e:
            print(f"Error al obtener tareas: {e}")
            return []

    def cerrar_conexion(self):
        """Cerrar conexión a MongoDB"""
        if self.client:
            self.client.close()
            print("🔌 Conexión cerrada")