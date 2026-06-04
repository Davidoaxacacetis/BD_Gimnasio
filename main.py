import os
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError, ConnectionFailure
from bson.objectid import ObjectId
from datetime import datetime, timedelta
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
            self.membresias.create_index("telefono_cliente", unique=True)
        except Exception:
            pass

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

    # --- GESTIÓN DE MEMBRESÍAS DE CLIENTES ---

    def agregar_entrenador(self, nombre, especialidad, telefono, cobro):
        try:
            return self.entrenadores.insert_one({
                "nombre": nombre,
                "especialidad": especialidad,
                "telefono": telefono,
                "cobro": float(cobro),
                "activo": True
            }).inserted_id

        except Exception as e:
            print(f"❌ Error al agregar entrenador: {e}")
            return None

    def obtener_todos_los_entrenadores(self):
        return list(self.entrenadores.find())

    def obtener_entrenador(self, entrenador_id):
        try:
            return self.entrenadores.find_one({
                "_id": ObjectId(entrenador_id)
            })
        except Exception:
            return None

    def cancelar_entrenador(self, entrenador_id, motivo):
        try:
            self.entrenadores.update_one(
                {"_id": ObjectId(entrenador_id)},
                {
                    "$set": {
                        "activo": False,
                        "motivo_cancelacion": motivo
                    }
                }
            )
        
            return True

        except Exception as e:
            print(f"❌ Error al cancelar entrenador: {e}")
            return False

    def editar_entrenador(self, entrenador_id, datos):
        try:

            self.entrenadores.update_one(
                {"_id": ObjectId(entrenador_id)},
                {"$set": datos}
            )

            return True

        except Exception as e:
            print(f"❌ Error al editar entrenador: {e}")
            return False

    def reactivar_entrenador(self, entrenador_id):
        try:
            self.entrenadores.update_one(
            {"_id": ObjectId(entrenador_id)},
            {
                "$set": {
                    "activo": True
                },
                "$unset": {
                    "motivo_cancelacion": ""
                }
            }
        )
            return True
        except Exception as e:
            print(f"❌ Error al reactivar entrenador: {e}")
            return False

    def asignar_entrenador(self, telefono_cliente, entrenador_id):
        try:
            self.membresias.update_one(
            {"telefono_cliente": telefono_cliente},
                {
                    "$set": {
                        "entrenador_id": ObjectId(entrenador_id)
                    }
                }
            )
            return True
        except Exception as e:
            print(f"❌ Error al asignar entrenador: {e}")
            return False

    def registrar_membresia_cliente(self, nombre, telefono, disciplinas, tipo_membresia, pago, entrenador_id=None):
        lista_disciplinas = [disciplinas] if isinstance(disciplinas, str) else disciplinas
        try:
            fecha_inicio = datetime.now()
            dias_duracion = 365 if "anual" in tipo_membresia.lower() else 30
            fecha_fin = fecha_inicio + timedelta(days=dias_duracion)

            datos_membresia = {
                "nombre_cliente": nombre,
                "telefono_cliente": telefono,
                "disciplinas": lista_disciplinas, 
                "tipo": tipo_membresia,
                "pago_realizado": float(pago),
                "historial_pagos": [{"monto": float(pago), "fecha": fecha_inicio.strftime("%Y-%m-%d %H:%M:%S"), "concepto": "Inscripción"}],
                "fecha_inicio": fecha_inicio.strftime("%Y-%m-%d"),
                "fecha_vencimiento": fecha_fin.strftime("%Y-%m-%d"),
                "estado": "Activo",
                "entrenador_id": ObjectId(entrenador_id) if entrenador_id else None # <--- NUEVO
            }

            self.membresias.update_one(
                {"telefono_cliente": telefono}, 
                {"$set": datos_membresia}, 
                upsert=True
            )
            return True
        except Exception as e:
            print(f"❌ Error al registrar la membresía: {e}")
            return False

    def obtener_miembros_con_entrenador(self):
        return list(self.membresias.aggregate([
            {
                "$lookup": {
                    "from": "Entrenadores",
                    "localField": "entrenador_id",
                    "foreignField": "_id",
                    "as": "entrenador_info"
                }
            },
            {"$unwind": {"path": "$entrenador_info", "preserveNullAndEmptyArrays": True}}
        ]))

    def actualizar_disciplinas(self, telefono, nueva_disciplina, operacion="add"):
        """
        operacion: "add" para agregar, "remove" para quitar una disciplina específica.
        """
        try:
            if operacion == "add":
                self.membresias.update_one(
                    {"telefono_cliente": telefono},
                    {"$addToSet": {"disciplinas": nueva_disciplina}}
                )
            elif operacion == "remove":
                self.membresias.update_one(
                    {"telefono_cliente": telefono},
                    {"$pull": {"disciplinas": nueva_disciplina}}
                )
            return True
        except Exception as e:
            print(f"❌ Error al actualizar disciplinas: {e}")
            return False

    def agregar_pago_adicional(self, telefono, monto, concepto):
        try:
            if not concepto:
                concepto = "Abono / Renovación"
                
            nuevo_pago = {
                "monto": float(monto),
                "fecha": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "concepto": concepto
            }
            
            membresia = self.membresias.find_one({"telefono_cliente": telefono})
            updates = {
                "$push": {"historial_pagos": nuevo_pago},
                "$inc": {"pago_realizado": float(monto)}
            }
            
            if membresia:
                fecha_base = datetime.now()
                dias = 365 if "anual" in membresia.get("tipo", "Mensual").lower() else 30
                nueva_fin = fecha_base + timedelta(days=dias)
                
                updates["$set"] = {
                    "estado": "Activo",
                    "fecha_inicio": fecha_base.strftime("%Y-%m-%d"),
                    "fecha_vencimiento": nueva_fin.strftime("%Y-%m-%d")
                }

            self.membresias.update_one({"telefono_cliente": telefono}, updates)
            return True
        except Exception as e:
            print(f"❌ Error al agregar pago al historial: {e}")
            return False

    def obtener_todos_los_miembros(self):
        try:
            fecha_actual_str = datetime.now().strftime("%Y-%m-%d")
            
            self.membresias.update_many(
                {
                    "fecha_vencimiento": {"$lt": fecha_actual_str},
                    "estado": "Activo"
                },
                {"$set": {"estado": "Inactivo"}}
            )
            return list(self.membresias.find())
        except Exception as e:
            print(f"❌ Error al obtener y actualizar estados de miembros: {e}")
            return list(self.membresias.find())

    def eliminar_membresia(self, telefono):
        try:
            res = self.membresias.delete_one({"telefono_cliente": telefono})
            return res.deleted_count > 0
        except Exception as e:
            print(f"❌ Error al eliminar membresía: {e}")
            return False

    def modificar_membresia(self, telefono_actual, nuevos_datos):
        try:
            datos_membresia = {}
            
            if "membresia_actual" in nuevos_datos and nuevos_datos["membresia_actual"]:
                fecha_inicio = datetime.now()
                dias = 365 if "anual" in nuevos_datos["membresia_actual"].lower() else 30
                fecha_fin = fecha_inicio + timedelta(days=dias)
                
                datos_membresia["tipo"] = nuevos_datos["membresia_actual"]
                datos_membresia["fecha_inicio"] = fecha_inicio.strftime("%Y-%m-%d")
                datos_membresia["fecha_vencimiento"] = fecha_fin.strftime("%Y-%m-%d")

            if nuevos_datos.get("nombre"): datos_membresia["nombre_cliente"] = nuevos_datos["nombre"]
            if nuevos_datos.get("telefono"): datos_membresia["telefono_cliente"] = nuevos_datos["telefono"]
            if nuevos_datos.get("disciplinas"):  datos_membresia["disciplinas"] = nuevos_datos["disciplinas"]
            if "entrenador_id" in nuevos_datos:

                entrenador_id = nuevos_datos["entrenador_id"]

                datos_membresia["entrenador_id"] = (
                    ObjectId(entrenador_id)
                if entrenador_id
                else None
                )

            if "pago_realizado" in nuevos_datos: 
                datos_membresia["pago_realizado"] = nuevos_datos["pago_realizado"]

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

            self.membresias.update_one(
                {"telefono_cliente": telefono}, 
                {"$set": {"estado": nuevo_estado}}
            )
            return True
        except Exception as e:
            print(f"❌ Error al cambiar el estado de la membresía: {e}")
            return False

    def cerrar_conexion(self):
        if self.client:
            self.client.close()
            print("🔌 Conexión cerrada")