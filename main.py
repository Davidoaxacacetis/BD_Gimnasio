from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, ConnectionFailure
from bson.objectid import ObjectId
from datetime import datetime
from werkzeug.security import check_password_hash 
import urllib.parse 

class GestorGimnasio:
    def __init__(self):
        usuario = "dtntakumi13_db_user"
        password = urllib.parse.quote_plus("Ghostsoldier12*")
        
        uri = f"mongodb+srv://{usuario}:{password}@gimnasio.efxu3ej.mongodb.net/?retryWrites=true&w=majority"
        
        try:
            self.client = MongoClient(uri, serverSelectionTimeoutMS=5000) 
            
            self.client.admin.command('ping')
            
            self.db = self.client['Gimnasio']
            
            self.usuarios_gym = self.db['Usuarios']       
            self.usuarios_app = self.db['usuarios_sistema'] 
            self.membresias = self.db['Membresias']
            self.trabajadores = self.db['Trabajadores']
            self.entrenadores = self.db['Entrenadores']
            self.productos = self.db['Productos']
            
            self._crear_indices()
            print("✅ Conectado exitosamente a MongoDB Atlas (BD Gimnasio)")
            
        except ConnectionFailure as e:
            print(f"❌ Error de conexión: No se pudo conectar a MongoDB. {e}")
            raise
        except Exception as e:
            print(f"❌ Ocurrió un error inesperado al iniciar: {e}")
            raise

    def _crear_indices(self):
        """Crea índices únicos para evitar correos o teléfonos duplicados"""
        self.usuarios_app.create_index("email", unique=True)
        self.usuarios_gym.create_index("telefono", unique=True)

    @property
    def usuarios(self):
        return self.usuarios_app

    def crear_usuario(self, nombre, email, contraseña_encriptada):
        try:
            return self.usuarios_app.insert_one({
                "nombre": nombre, 
                "email": email, 
                "password": contraseña_encriptada, 
                "fecha_registro": datetime.now()
            }).inserted_id
        except DuplicateKeyError:
            print(f"⚠️ El email {email} ya existe.")
            return None

    def validar_credenciales(self, email, contraseña_plana):
        usuario = self.usuarios_app.find_one({"email": email})
        if usuario and check_password_hash(usuario['password'], contraseña_plana):
            return usuario
        return None

    def actualizar_password(self, email, nueva_pass_encriptada):
        try:
            resultado = self.usuarios_app.update_one(
                {"email": email}, 
                {"$set": {"password": nueva_pass_encriptada}}
            )
            return resultado.modified_count > 0
        except Exception as e:
            print(f"Error al actualizar password: {e}")
            return False

    def obtener_usuario(self, uid):
        return self.usuarios_app.find_one({"_id": ObjectId(uid)})

    def actualizar_usuario(self, uid, datos):
        res = self.usuarios_app.update_one({"_id": ObjectId(uid)}, {"$set": datos})
        return res.modified_count > 0

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
        except Exception as e:
            print(f"Error al registrar membresía: {e}")
            return False

    def obtener_todos_los_miembros(self):
        return list(self.usuarios_gym.find())

    def cerrar_conexion(self):
        if self.client:
            self.client.close()
            print("🔌 Conexión cerrada")