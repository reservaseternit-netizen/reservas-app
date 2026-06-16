import streamlit as st
import os
import fitz
from streamlit_pdf_viewer import pdf_viewer
import json
import shutil
import time
from datetime import datetime
from zoneinfo import ZoneInfo
# --- NUEVAS LIBRERÍAS PARA GITHUB ---
import requests
import base64

st.set_page_config(page_title="Gestión de Reservas", layout="wide")

# --- ESTILO ---
st.markdown(
    """
<style>
.stApp { background-color: #f5f7fa; }
.stButton>button {
    background-color: #005baa;
    color: white;
    border-radius: 8px;
    height: 45px;
    font-weight: bold;
}
.stButton>button:hover { background-color: #003f7d; }
section[data-testid="stSidebar"] { background-color: #002b5c; }
section[data-testid="stSidebar"] * { color: white !important; }
</style>
""",
    unsafe_allow_html=True,
)

# ================= CONFIGURACIÓN DE GITHUB =================
TOKEN_GITHUB = st.secrets["github"]["access_token"]
USUARIO_GITHUB = "reservaseternit-netizen"       # ⚠️ CAMBIA ESTO POR TU USUARIO REAL DE GITHUB
REPOSITORIO_GITHUB = "reservas-app"       # ⚠️ CAMBIA ESTO POR EL NOMBRE DE TU REPOSITORIO

def subir_a_github(ruta_en_github, contenido_bytes, mensaje_commit="Subida de archivo"):
    """Sube o actualiza un archivo directamente en el repositorio de GitHub"""
    url = f"https://api.github.com/repos/{USUARIO_GITHUB}/{REPOSITORIO_GITHUB}/contents/{ruta_en_github}"
    contenido_base64 = base64.b64encode(contenido_bytes).decode("utf-8")
    headers = {
        "Authorization": f"token {TOKEN_GITHUB}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    # Primero verificamos si el archivo ya existe para obtener su 'sha' (necesario para reemplazar)
    respuesta_get = requests.get(url, headers=headers)
    datos = {
        "message": mensaje_commit,
        "content": contenido_base64
    }
    if respuesta_get.status_code == 200:
        datos["sha"] = respuesta_get.json()["sha"]
        
    respuesta = requests.put(url, headers=headers, json=datos)
    return respuesta.status_code in [200, 201]

def eliminar_de_github(ruta_en_github, mensaje_commit="Eliminación de archivo"):
    """Elimina un archivo del repositorio de GitHub"""
    url = f"https://api.github.com/repos/{USUARIO_GITHUB}/{REPOSITORIO_GITHUB}/contents/{ruta_en_github}"
    headers = {
        "Authorization": f"token {TOKEN_GITHUB}",
        "Accept": "application/vnd.github.v3+json"
    }
    respuesta_get = requests.get(url, headers=headers)
    if respuesta_get.status_code == 200:
        sha = respuesta_get.json()["sha"]
        datos = {
            "message": mensaje_commit,
            "sha": sha
        }
        requests.delete(url, headers=headers, json=datos)
# ===========================================================

# --- HORA COLOMBIA ---
def hora_colombia():
    return datetime.now(ZoneInfo("America/Bogota"))


# --- CARPETAS ---
for carpeta in [
    "reservas/pendientes",
    "reservas/firmadas",
    "reservas/firmas",
    "reservas/archivo",
    "reservas/enviados",
    "reservas/rechazados",
]:
    os.makedirs(carpeta, exist_ok=True)

areas = [
    "Producción",
    "Calidad",
    "Mantenimiento",
    "Logística",
    "Recursos Humanos",
    "Ambiental",
    "Salud Ocupacional",
    "Marketing",
    "Financiera",
    "Almacén",
]

usuarios = {
    "usuario": {"password": "123", "rol": "usuario"},
    "ingeniero": {"password": "999", "rol": "ingeniero"},
    "almacen": {"password": "000", "rol": "almacen"},
}

firmas_contrasena = {
    "Producción": {"archivo": "reservas/firmas/Imagen1.png", "password": "1234"},
    "Logística": {"archivo": "reservas/firmas/LogisticaRojas.png", "password": "5678"},
}


def mostrar_nombre(f):
    return f.split("__", 1)[-1]


if "login" not in st.session_state:
    st.session_state.login = False

# ================= LOGIN =================
if not st.session_state.login:
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:

        if os.path.exists("assets/ETERNITTTTT.png"):
            st.image("assets/ETERNITTTTT.png")

        st.markdown(
            "<h2 style='text-align:center;'>Acceso al Sistema</h2>",
            unsafe_allow_html=True,
        )

        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")

        if st.button("Ingresar", use_container_width=True):

            if u in usuarios and usuarios[u]["password"] == p:

                st.session_state.login = True
                st.session_state.rol = usuarios[u]["rol"]
                st.session_state.user_name = u
                st.session_state.pagina = "principal"

                st.rerun()

            else:
                st.error("Credenciales incorrectas")

# ================= SISTEMA =================
else:

    with st.sidebar:

        if os.path.exists("assets/ETERNITTTTT.png"):
            st.image("assets/ETERNITTTTT.png", width=180)

        st.markdown("### 👤 Usuario")
        st.write(f"**{st.session_state.user_name}**")
        st.write(f"Rol: {st.session_state.rol}")

        st.markdown("---")

        if st.session_state.rol == "usuario":

            if st.button("📤 Enviar"):
                st.session_state.pagina = "principal"
                st.rerun()

            if st.button("📄 Historial"):
                st.session_state.pagina = "historial"
                st.rerun()

        st.markdown("---")

        if st.button("🚪 Cerrar sesión", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    rol = st.session_state.rol

    st.title("📋 Gestión de Reservas")

    # ================= USUARIO =================
    if rol == "usuario":

        if "pagina" not in st.session_state:
            st.session_state.pagina = "principal"

        if "upload_key" not in st.session_state:
            st.session_state.upload_key = 0

        if st.session_state.pagina == "principal":

            st.header("📤 Enviar Nueva Reserva")

            area = st.selectbox("Área", areas)

            archivos = st.file_uploader(
                "Subir PDFs",
                type=["pdf"],
                accept_multiple_files=True,
                key=st.session_state.upload_key,
            )

            if st.button("Enviar"):

                if archivos:

                    os.makedirs(f"reservas/pendientes/{area}", exist_ok=True)
                    os.makedirs(f"reservas/enviados/{area}", exist_ok=True)

                    for arch in archivos:

                        data = arch.getbuffer()
                        timestamp = int(time.time())
                        nombre_unico = f"{timestamp}__{arch.name}"

                        # Guardado temporal en Streamlit local
                        with open(f"reservas/pendientes/{area}/{nombre_unico}", "wb") as f:
                            f.write(data)
                        with open(f"reservas/enviados/{area}/{nombre_unico}", "wb") as f:
                            f.write(data)

                        # ===== MODIFICACIÓN: SUBIR AL GITHUB PERMANENTE =====
                        bytes_puros = arch.getvalue()
                        subir_a_github(f"reservas/pendientes/{area}/{nombre_unico}", bytes_puros, f"Nueva pendiente: {nombre_unico}")
                        subir_a_github(f"reservas/enviados/{area}/{nombre_unico}", bytes_puros, f"Nuevo historial: {nombre_unico}")

                        # ===== METADATA =====
                        metadata = {
                            "archivo": arch.name,
                            "area": area,
                            "fecha_envio": hora_colombia().strftime("%Y-%m-%d %I:%M %p"),
                            "usuario_envio": st.session_state.user_name,
                            "estado": "Pendiente",
                            "firmado_por": "",
                            "fecha_firma": "",
                            "tiempo_aprobacion": "",
                        }

                        # Guardado temporal JSON local
                        with open(f"reservas/enviados/{area}/{nombre_unico}.json", "w") as jf:
                            json.dump(metadata, jf, indent=4)
                        
                        # ===== MODIFICACIÓN: SUBIR METADATA A GITHUB =====
                        json_bytes = json.dumps(metadata, indent=4).encode('utf-8')
                        subir_a_github(f"reservas/enviados/{area}/{nombre_unico}.json", json_bytes, f"Metadata: {nombre_unico}")

                    st.success(f"{len(archivos)} archivos enviados")
                    st.session_state.upload_key += 1
                    st.rerun()

        # ================= HISTORIAL =================
        elif st.session_state.pagina == "historial":

            st.header("📄 Historial")

            col1, col2, col3 = st.columns([3, 3, 1])
            
            with col1:        
                area_sel = st.selectbox("Filtrar por área", ["Todas"] + areas)

            with col2:
                buscador = st.text_input("🔍 Buscar reserva", placeholder="Ej: 2234657")

            with col3:
                st.write("")
                if st.button("🔄"):
                    st.rerun()

            archivos_totales = []

            if area_sel == "Todas":
                for a in areas:
                    ruta = f"reservas/enviados/{a}"
                    if os.path.exists(ruta):
                        for f in os.listdir(ruta):
                            if f.endswith(".pdf"):
                                nombre_visible = mostrar_nombre(f).lower()
                                texto_busqueda = buscador.lower()
                                if texto_busqueda in nombre_visible:
                                    archivos_totales.append((a, f))
            else:
                ruta = f"reservas/enviados/{area_sel}"
                if os.path.exists(ruta):
                    for f in os.listdir(ruta):
                       if f.endswith(".pdf"):
                            nombre_visible = mostrar_nombre(f).lower()
                            texto_busqueda = buscador.lower()
                            if texto_busqueda in nombre_visible:
                                archivos_totales.append((area_sel, f))

            if not archivos_totales:
                st.info("No hay archivos")
            else:
                for i, (a, f) in enumerate(archivos_totales):
                    nombre = mostrar_nombre(f)
                    col1, col2 = st.columns([3, 1])

                    ruta_json = f"reservas/enviados/{a}/{f}.json"
                    metadata = {}
                    
                    if os.path.exists(ruta_json):
                        with open(ruta_json, "r") as jf:
                            metadata = json.load(jf)

                    estado = metadata.get("estado", "Pendiente")

                    if estado == "Firmado":
                        col1.success(f"{nombre} ({a}) - 🟢 Firmado")
                    elif estado == "Archivado":
                        col1.info(f"{nombre} ({a}) - 📦 Entregado")
                    elif "Rechazado" in estado:
                        razon = metadata.get("motivo_rechazo", "Sin motivo")
                        col1.error(f"{nombre} ({a}) - 🚫 {estado} | Motivo: {razon}")
                    else:
                        col1.warning(f"{nombre} ({a}) - 🔴 Pendiente")
                        
                    if metadata:
                        col1.caption(
                            f"📅 Enviado: {metadata.get('fecha_envio','')} | "
                            f"✍️ Firma: {metadata.get('fecha_firma','')} | "
                            f"⏱️ Tiempo: {metadata.get('tiempo_aprobacion','')}"
                        )

                    if col2.button("🗑️", key=f"hist_{a}_{f}_{i}"):
                        # Eliminación local
                        try: os.remove(f"reservas/enviados/{a}/{f}")
                        except: pass
                        try: os.remove(ruta_json)
                        except: pass

                        # ===== MODIFICACIÓN: ELIMINAR DE GITHUB =====
                        eliminar_de_github(f"reservas/enviados/{a}/{f}", f"Borrando PDF historial: {f}")
                        eliminar_de_github(f"reservas/enviados/{a}/{f}.json", f"Borrando JSON historial: {f}")

                        st.rerun()
                        
    # ================= INGENIERO =================
    elif rol == "ingeniero":

        st.header("✍️ Revisión y Firma")
        col1, col2 = st.columns([5, 1])

        with col1:
            area = st.selectbox("Área", ["Todas"] + areas)

        with col2: 
            if st.button("🔄"): 
                st.rerun()
   
        archivos = []

        if area == "Todas":
            for a in areas:
                carpeta = f"reservas/pendientes/{a}"
                if os.path.exists(carpeta):
                    for f in os.listdir(carpeta):
                        archivos.append((a, f))
        else:
            carpeta = f"reservas/pendientes/{area}"
            if os.path.exists(carpeta):
                for f in os.listdir(carpeta):
                    archivos.append((area, f))

        for i, (a, arc) in enumerate(archivos):
            nombre = mostrar_nombre(arc)

            with st.expander(f"{nombre} ({a})"):
                ruta = f"reservas/pendientes/{a}/{arc}"
                pdf_viewer(ruta, key=f"pdf_{a}_{arc}_{i}")
                pw = st.text_input("Contraseña", type="password", key=f"pw_{arc}_{i}")

                if st.button("Firmar", key=f"f_{arc}_{i}"):
                    datos_firma = firmas_contrasena.get(a)

                    if datos_firma and pw == datos_firma.get("password"):
                        ruta_firma = datos_firma["archivo"]

                        if os.path.exists(ruta_firma):
                            doc = fitz.open(ruta)

                            # ===== TU LÓGICA ORIGINAL DE FIRMA =====
                            rect_firma = None
                            pagina_objetivo = None

                            for page in doc:
                                coincidencias = page.search_for("FIRMA 1")
                                if coincidencias:
                                    ref = coincidencias[0]
                                    pagina_objetivo = page
                                    ancho_firma = 120
                                    alto_firma = 50
                                    x_centro = (ref.x0 + ref.x1) / 2

                                    def hay_contenido(page, rect):
                                        texto = page.get_text("text", clip=rect)
                                        if texto.strip(): return True
                                        for d in page.get_drawings():
                                            for item in d["items"]:
                                                if item[0] == "l":
                                                    p1, p2 = item[1], item[2]
                                                    if rect.intersects(fitz.Rect(p1, p2)): return True
                                        return False

                                    y_base_arriba = ref.y0 - 10
                                    for _ in range(8):
                                        rect_intento = fitz.Rect(x_centro - ancho_firma / 2, y_base_arriba - alto_firma, x_centro + ancho_firma / 2, y_base_arriba)
                                        if not hay_contenido(page, rect_intento):
                                            rect_firma = rect_intento
                                            break
                                        y_base_arriba -= 10
                                    else:
                                        y_base_abajo = ref.y1 + 15
                                        for _ in range(12):
                                            rect_intento = fitz.Rect(x_centro - ancho_firma / 2, y_base_abajo, x_centro + ancho_firma / 2, y_base_abajo + alto_firma)
                                            if not hay_contenido(page, rect_intento):
                                                rect_firma = rect_intento
                                                break
                                            y_base_abajo += 12
                                        else:
                                            rect_firma = fitz.Rect(x_centro - ancho_firma / 2, ref.y1 + 40, x_centro + ancho_firma / 2, ref.y1 + 40 + alto_firma)
                                    break

                            if not pagina_objetivo:
                                pagina_objetivo = doc[-1]
                                ancho = pagina_objetivo.rect.width
                                alto = pagina_objetivo.rect.height
                                rect_firma = fitz.Rect(ancho * 0.55, alto * 0.65, ancho * 0.85, alto * 0.85)

                            pagina_objetivo.insert_image(rect_firma, filename=ruta_firma)
                            # ===== FIN LÓGICA ORIGINAL DE FIRMA =====

                            os.makedirs(f"reservas/firmadas/{a}", exist_ok=True)
                            ruta_firmado_local = f"reservas/firmadas/{a}/{arc}"
                            doc.save(ruta_firmado_local)
                            doc.close()

                            # ===== MODIFICACIÓN: SUBIR ARCHIVO FIRMADO A GITHUB Y BORRAR EL PENDIENTE =====
                            with open(ruta_firmado_local, "rb") as f_firmado:
                                bytes_firmados = f_firmado.read()
                            subir_a_github(f"reservas/firmadas/{a}/{arc}", bytes_firmados, f"Documento firmado: {arc}")
                            eliminar_de_github(f"reservas/pendientes/{a}/{arc}", f"Borrando pendiente firmado: {arc}")

                            # ===== ACTUALIZAR METADATA =====
                            ruta_json = f"reservas/enviados/{a}/{arc}.json"
                            if os.path.exists(ruta_json):
                                with open(ruta_json, "r") as jf:
                                    metadata = json.load(jf)

                                fecha_envio = datetime.strptime(metadata["fecha_envio"], "%Y-%m-%d %I:%M %p")
                                ahora = hora_colombia()
                                diferencia = ahora.replace(tzinfo=None) - fecha_envio
                                minutos = int(diferencia.total_seconds() / 60)

                                metadata["estado"] = "Firmado"
                                metadata["firmado_por"] = st.session_state.user_name
                                metadata["fecha_firma"] = ahora.strftime("%Y-%m-%d %I:%M %p")
                                metadata["tiempo_aprobacion"] = f"{minutos} minutos"

                                with open(ruta_json, "w") as jf:
                                    json.dump(metadata, jf, indent=4)
                                
                                # Actualizar metadata en GitHub
                                json_bytes = json.dumps(metadata, indent=4).encode('utf-8')
                                subir_a_github(ruta_json, json_bytes, f"Metadata firmada: {arc}")

                            try: os.remove(ruta)
                            except: pass

                            st.success("✅ Documento firmado correctamente")
                            st.rerun()

                motivo = st.text_input("Motivo", key=f"m_{arc}_{i}")

                if st.button("Rechazar", key=f"r_{arc}_{i}"):
                    if motivo:
                        os.makedirs(f"reservas/rechazados/{a}", exist_ok=True)
                        
                        # Movimiento local
                        shutil.move(ruta, f"reservas/rechazados/{a}/{arc}")

                        # Guardado local de rechazo exclusivo
                        info_rechazo = {
                            "motivo": motivo,
                            "fecha_rechazo": hora_colombia().strftime("%Y-%m-%d %I:%M %p"),
                            "rechazado_por": st.session_state.user_name,
                            "area": a,
                            "archivo": arc,
                        }
                        with open(f"reservas/rechazados/{a}/{arc}.json", "w") as f:
                            json.dump(info_rechazo, f, indent=4)

                        # ===== MODIFICACIÓN: MOVER EN GITHUB (SUBIR A RECHAZADOS Y QUITAR DE PENDIENTES) =====
                        with open(f"reservas/rechazados/{a}/{arc}", "rb") as f_rech:
                            bytes_rech = f_rech.read()
                        subir_a_github(f"reservas/rechazados/{a}/{arc}", bytes_rech, f"Archivo rechazado: {arc}")
                        eliminar_de_github(f"reservas/pendientes/{a}/{arc}", f"Removiendo pendiente por rechazo: {arc}")
                        
                        # Subir JSON específico de rechazo
                        json_rech_bytes = json.dumps(info_rechazo, indent=4).encode('utf-8')
                        subir_a_github(f"reservas/rechazados/{a}/{arc}.json", json_rech_bytes, f"JSON especifico rechazo: {arc}")

                        # ===== ACTUALIZAR METADATA GENERAL =====
                        ruta_json = f"reservas/enviados/{a}/{arc}.json"
                        if os.path.exists(ruta_json):
                            with open(ruta_json, "r") as jf:
                                metadata = json.load(jf)

                            metadata["estado"] = "Rechazado por Ingeniero"
                            metadata["fecha_rechazo"] = hora_colombia().strftime("%Y-%m-%d %I:%M %p")
                            metadata["rechazado_por"] = st.session_state.user_name
                            metadata["motivo_rechazo"] = motivo

                            with open(ruta_json, "w") as jf:
                                json.dump(metadata, jf, indent=4)
                            
                            # Actualizar metadata general en GitHub
                            json_bytes = json.dumps(metadata, indent=4).encode('utf-8')
                            subir_a_github(ruta_json, json_bytes, f"Metadata rechazo ingeniero: {arc}")

                        st.rerun()

    # ================= ALMACÉN =================
    elif rol == "almacen":

        st.header("📦 Gestión de Documentos")
        col1, col2, col3 = st.columns([3, 3, 1])

        with col1:
            area = st.selectbox("Área", ["Todas"] + areas)

        with col2:
            busqueda = st.text_input("🔍 Buscar reserva", placeholder="Ej: 22345678 o nombre PDF")

        with col3:
            st.write("")
            if st.button("🔄", key="refresh_almacen"):
                st.rerun()
                
        vista = st.radio("Vista", ["Firmados", "Archivados", "Rechazados"])
        archivos = []

        if area == "Todas":
            for a in areas:
                if vista == "Firmados": carpeta = f"reservas/firmadas/{a}"
                elif vista == "Archivados": carpeta = f"reservas/archivo/{a}"
                else: carpeta = f"reservas/rechazados/{a}"

                if os.path.exists(carpeta):
                    for f in os.listdir(carpeta):
                        if f.endswith(".pdf"):
                            nombre_visible = mostrar_nombre(f)
                            if (busqueda.strip() == "" or busqueda.lower() in nombre_visible.lower() or busqueda.lower() in f.lower()):
                                 archivos.append((a, f))
        else:
            if vista == "Firmados": carpeta = f"reservas/firmadas/{area}"
            elif vista == "Archivados": carpeta = f"reservas/archivo/{area}"
            else: carpeta = f"reservas/rechazados/{area}"
                
            os.makedirs(carpeta, exist_ok=True)
            for f in os.listdir(carpeta):
                if f.endswith(".pdf"):
                    nombre_visible = mostrar_nombre(f)
                    if (busqueda.strip() == "" or busqueda.lower() in nombre_visible.lower() or busqueda.lower() in f.lower()):
                        archivos.append((area, f))
                    
        # ===== MOSTRAR ARCHIVOS =====
        for i, (a, f) in enumerate(archivos):
            nombre = mostrar_nombre(f)

            if vista == "Firmados": ruta = f"reservas/firmadas/{a}/{f}"
            elif vista == "Archivados": ruta = f"reservas/archivo/{a}/{f}"
            else: ruta = f"reservas/rechazados/{a}/{f}"

            # ================= VISTA FIRMADOS =================
            if vista == "Firmados":
                col1, col2, col3, col4 = st.columns([5, 1, 1, 3], vertical_alignment="center")
                col1.write(f"📄 {nombre} ({a})")

                with open(ruta, "rb") as file:
                    col2.download_button("⬇️", file, file_name=nombre, key=f"down_f_{a}_{f}_{i}")
                        
                # ===== ACCIÓN: ARCHIVAR =====
                if col3.button("📁", key=f"a_{a}_{f}_{i}"):
                    os.makedirs(f"reservas/archivo/{a}", exist_ok=True)
                    shutil.move(ruta, f"reservas/archivo/{a}/{f}")

                    # ===== MODIFICACIÓN: TRANSMITIR CAMBIO A GITHUB =====
                    with open(f"reservas/archivo/{a}/{f}", "rb") as f_arch:
                        bytes_arch = f_arch.read()
                    subir_a_github(f"reservas/archivo/{a}/{f}", bytes_arch, f"Archivado en repositorio: {f}")
                    eliminar_de_github(f"reservas/firmadas/{a}/{f}", f"Removiendo de firmados: {f}")

                    # ===== ACTUALIZAR ESTADO METADATA =====
                    ruta_json = f"reservas/enviados/{a}/{f}.json"
                    if os.path.exists(ruta_json):
                        with open(ruta_json, "r") as jf:
                            metadata = json.load(jf)

                        metadata["estado"] = "Archivado"

                        with open(ruta_json, "w") as jf:
                            json.dump(metadata, jf, indent=4)
                        
                        # Actualizar en GitHub
                        json_bytes = json.dumps(metadata, indent=4).encode('utf-8')
                        subir_a_github(ruta_json, json_bytes, f"Metadata archivada: {f}")

                    st.rerun()

                # ===== ACCIÓN: RECHAZAR DESDE ALMACÉN =====
                with col4:
                    sub1, sub2 = st.columns([3, 1], vertical_alignment="center")
                    with sub1:
                        motivo = st.text_input(" ", key=f"mot_alm_{a}_{f}_{i}", placeholder="Motivo rechazo", label_visibility="collapsed")
                    with sub2:
                        rechazar = st.button("🚫", key=f"rech_alm_{a}_{f}_{i}")

                    if rechazar and motivo:
                         os.makedirs(f"reservas/rechazados/{a}", exist_ok=True)
                         shutil.move(ruta, f"reservas/rechazados/{a}/{f}")

                         # ===== MODIFICACIÓN: SUBIR RECHAZO Y ELIMINAR DE FIRMADOS EN GITHUB =====
                         with open(f"reservas/rechazados/{a}/{f}", "rb") as f_rech_alm:
                             bytes_rech_alm = f_rech_alm.read()
                         subir_a_github(f"reservas/rechazados/{a}/{f}", bytes_rech_alm, f"Rechazado por almacen: {f}")
                         eliminar_de_github(f"reservas/firmadas/{a}/{f}", f"Removiendo de firmados por rechazo: {f}")

                         ruta_json = f"reservas/enviados/{a}/{f}.json"
                         if os.path.exists(ruta_json):
                             with open(ruta_json, "r") as jf:
                                 metadata = json.load(jf)

                             metadata["estado"] = "Rechazado por Almacén"
                             metadata["motivo_rechazo"] = motivo
                             metadata["rechazado_por"] = st.session_state.user_name
                             metadata["fecha_rechazo"] = hora_colombia().strftime("%Y-%m-%d %I:%M %p")

                             with open(ruta_json, "w") as jf:
                                 json.dump(metadata, jf, indent=4)
                             
                             # Actualizar en GitHub
                             json_bytes = json.dumps(metadata, indent=4).encode('utf-8')
                             subir_a_github(ruta_json, json_bytes, f"Metadata rechazo almacen: {f}")

                         st.success("Documento rechazado")
                         st.rerun()

            # ================= VISTA ARCHIVADOS / RECHAZADOS =================
            else:
                col1_a, col2_a, col3_a = st.columns([6, 1, 1], vertical_alignment="center")
                ruta_json = f"reservas/enviados/{a}/{f}.json"
                texto_estado = ""

                if os.path.exists(ruta_json):
                    with open(ruta_json, "r") as jf:
                        metadata = json.load(jf)
                    estado_doc = metadata.get("estado", "")
                    if "Rechazado" in estado_doc:
                        texto_estado = f" | 🚫 {estado_doc}"
                        
                col1_a.write(f"📄 {nombre} ({a}){texto_estado}")

                with open(ruta, "rb") as file:
                    col2_a.download_button("⬇️", file, file_name=nombre, key=f"down_arch_{a}_{f}_{i}")

                if col3_a.button("🗑️", key=f"del_a_{a}_{f}_{i}"):
                    try: os.remove(ruta)
                    except: pass
                    
                    # ===== MODIFICACIÓN: ACCIÓN BORRAR COMPLETO DE GITHUB =====
                    if vista == "Archivados":
                        eliminar_de_github(f"reservas/archivo/{a}/{f}", f"Borrando definitivo archivo: {f}")
                    else:
                        eliminar_de_github(f"reservas/rechazados/{a}/{f}", f"Borrando definitivo rechazado: {f}")
                        try: os.remove(f"reservas/rechazados/{a}/{f}.json")
                        except: pass
                        eliminar_de_github(f"reservas/rechazados/{a}/{f}.json", f"Borrando definitivo JSON rechazo: {f}")
            
                    st.rerun()
