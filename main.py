import os
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, ConnectionFailure
from bson.objectid import ObjectId
from datetime import datetime
from werkzeug.security import check_password_hash 
from dotenv import load_dotenv

load_dotenv()

class GestorGimnasio:
    def __init__(self, uri=None):
        if not uri:
            uri = os.getenv("MONGO_URI")
        
        try:
            self.client = MongoClient(uri, serverSelectionTimeoutMS=5000) 
            self.client.admin.command('ping')
            
            try:
                self.db = self.client.get_default_database()
            except:
                self.db = self.client['Gimnasio']
            
            # Mapeo de colecciones
            self.usuarios_gym = self.db['Usuarios']       
            self.usuarios_app = self.db['usuarios_sistema'] 
            self.membresias = self.db['Membresias']
            self.trabajadores = self.db['Trabajadores']
            self.entrenadores = self.db['Entrenadores']
            self.productos = self.db['Productos']
            
            self._crear_indices()
            print(f"✅ Conectado exitosamente a MongoDB Atlas (BD: {self.db.name})")
            
        except ConnectionFailure as e:
            print(f"❌ Error de conexión: No se pudo conectar a MongoDB. {e}")
            raise
        except Exception as e:
            print(f"❌ Ocurrió un error inesperado al iniciar: {e}")
            raise

    def _crear_indices(self):
        self.usuarios_app.create_index("email", unique=True)
        try:
            self.usuarios_gym.create_index("telefono", unique=True)
        except Exception:
            pass

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
        try:
            return self.usuarios_app.find_one({"_id": ObjectId(uid)})
        except Exception:
            return None

    def actualizar_usuario(self, uid, datos):
        try:
            res = self.usuarios_app.update_one({"_id": ObjectId(uid)}, {"$set": datos})
            return res.modified_count > 0
        except Exception:
            return False

    def registrar_membresia_cliente(self, nombre, telefono, disciplina, tipo_membresia, pago):
        try:
            fecha_inicio = datetime.now()
            
            if "anual" in tipo_membresia.lower():
                dias_duracion = 365
            else:
                dias_duracion = 30
                
            from datetime import timedelta
            fecha_fin = fecha_inicio + timedelta(days=dias_duracion)

            datos_membresia = {
                "nombre_cliente": nombre,
                "telefono_cliente": telefono,
                "disciplina": disciplina, 
                "tipo": tipo_membresia,
                "pago_realizado": float(pago),
                "fecha_inicio": fecha_inicio.strftime("%Y-%m-%d"),
                "fecha_vencimiento": fecha_fin.strftime("%Y-%m-%d"),
                "estado": "Activo"
            }

            self.membresias.update_one(
                {"telefono_cliente": telefono}, 
                {"$set": datos_membresia}, 
                upsert=True
            )

            datos_cliente = {
                "nombre": nombre,
                "telefono": telefono,
                "disciplina": disciplina, 
                "membresia_actual": tipo_membresia,
                "pago_realizado": float(pago),
                "fecha_inscripcion": fecha_inicio.strftime("%Y-%m-%d"), 
                "vence": fecha_fin.strftime("%Y-%m-%d"),
                "estado": "Activo",
                "ultima_actualizacion": datetime.now()
            }
            self.usuarios_gym.update_one(
                {"telefono": telefono}, 
                {"$set": datos_cliente}, 
                upsert=True
            )

            print(f"✅ Membresía registrada con éxito. Vence el: {fecha_fin.strftime('%Y-%m-%d')}")
            return True

        except Exception as e:
            print(f"❌ Error al registrar la membresía en las colecciones: {e}")
            return False

    def eliminar_membresia(self, telefono):
        """
        Borra por completo los registros del miembro en ambas colecciones.
        """
        try:
            # Elimina de la lista de miembros del gimnasio
            res_gym = self.usuarios_gym.delete_one({"telefono": telefono})
            # Elimina de la colección de membresías histórico/pagos
            res_memb = self.membresias.delete_one({"telefono_cliente": telefono})
            
            return res_gym.deleted_count > 0 or res_memb.deleted_count > 0
        except Exception as e:
            print(f"❌ Error al eliminar membresía: {e}")
            return False

    def modificar_membresia(self, telefono_actual, nuevos_datos):
        try:
            if "membresia_actual" in nuevos_datos:
                fecha_inicio = datetime.now()
                dias = 365 if "anual" in nuevos_datos["membresia_actual"].lower() else 30
                from datetime import timedelta
                fecha_fin = fecha_inicio + timedelta(days=dias)
                
                nuevos_datos["fecha_inscripcion"] = fecha_inicio.strftime("%Y-%m-%d")
                nuevos_datos["vence"] = fecha_fin.strftime("%Y-%m-%d")

            self.usuarios_gym.update_one({"telefono": telefono_actual}, {"$set": nuevos_datos})
            
            datos_membresia = {}
            if "nombre" in nuevos_datos: datos_membresia["nombre_cliente"] = nuevos_datos["nombre"]
            if "telefono" in nuevos_datos: datos_membresia["telefono_cliente"] = nuevos_datos["telefono"]
            if "disciplina" in nuevos_datos: datos_membresia["disciplina"] = nuevos_datos["disciplina"]
            if "membresia_actual" in nuevos_datos: 
                datos_membresia["tipo"] = nuevos_datos["membresia_actual"]
                datos_membresia["fecha_inicio"] = nuevos_datos["fecha_inscripcion"]
                datos_membresia["fecha_vencimiento"] = nuevos_datos["vence"]
            if "pago_realizado" in nuevos_datos: datos_membresia["pago_realizado"] = nuevos_datos["pago_realizado"]
            if "estado" in nuevos_datos: datos_membresia["estado"] = nuevos_datos["estado"]

            if datos_membresia:
                self.membresias.update_one({"telefono_cliente": telefono_actual}, {"$set": datos_membresia})

            return True
        except Exception as e:
            print(f"❌ Error al modificar membresía: {e}")
            return False

    def cambiar_estado_membresia(self, telefono, nuevo_estado):
        try:
            if nuevo_estado not in ["Activo", "Inactivo"]:
                return False

            self.usuarios_gym.update_one(
                {"telefono": telefono}, 
                {"$set": {"estado": nuevo_estado, "ultima_actualizacion": datetime.now()}}
            )
            self.membresias.update_one(
                {"telefono_cliente": telefono}, 
                {"$set": {"estado": nuevo_estado}}
            )
            
            print(f"🔄 Membresía asociada al teléfono {telefono} ahora está: {nuevo_estado}")
            return True
        except Exception as e:
            print(f"❌ Error al cambiar el estado de la membresía: {e}")
            return False

    def obtener_todos_los_miembros(self):
        return list(self.usuarios_gym.find())

    def cerrar_conexion(self):
        if self.client:
            self.client.close()
            print("🔌 Conexión cerrada")