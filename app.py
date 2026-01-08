import streamlit as st
import cv2
import io
import os, time
import numpy as np
from pathlib import Path
import json
import ast

from PIL import Image

from src.editor import procesar_imagen as procesar_imagen
from src.utils.escaneo import ejecutar_escanner_interactivo
from src.utils.crear_template import crear_template_page

from dotenv import load_dotenv

load_dotenv()

# --- 1. CONFIGURACIÓN Y ESTILOS ---
st.set_page_config(
    page_title="Editor DNI",
    page_icon="📸",
    layout="centered"
)

def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    else:
        # Estilos básicos de respaldo si no encuentra el archivo .css
        st.markdown("""
            <style>
            .stButton > button { width: 100%; height: 3em; border-radius: 10px; font-weight: bold; }
            .block-container { padding-top: 2rem; }
            </style>
        """, unsafe_allow_html=True)

local_css("assets/style.css")

# --- PERSISTENCIA DE DATOS EN MEMORIA ---
if "rects" not in st.session_state:
    st.session_state.rects = []
if "temp_point" not in st.session_state:
    st.session_state.temp_point = None
if "final_json" not in st.session_state:
    st.session_state.final_json = None
if "nueva_template" not in st.session_state:
    st.session_state.nueva_template = False
if "imagen_confirmada" not in st.session_state:
    st.session_state.imagen_confirmada = None
if "crear_template_state" not in st.session_state:
    st.session_state.crear_template_state = False
if "imagen_original" not in st.session_state:
    st.session_state.imagen_original = None
if "vista" not in st.session_state:
    st.session_state.vista = 'inicio'  # 'inicio', 'recorte','general' or 'procesado'

# --- 2. BARRA LATERAL (CONTROLES) ---
# ------ Obtener imagen --------------
st.sidebar.button("🏠 Selección de imagen", on_click=lambda: st.session_state.update(vista='inicio', ejecutar_enabled=False, crear_template_state=False))

# ------- Recorte de imagen ----------
st.sidebar.divider()
st.sidebar.button("🔄 Recorte", on_click=lambda: st.session_state.update(vista='recorte', ejecutar_enabled=False, crear_template_state=False), disabled=st.session_state.imagen_original is None)

modo = st.sidebar.radio("Recorte", ['Auto','Manual','Completa'], index=0, disabled=not st.session_state.vista=='recorte', help="Selecciona el modo de recorte de la imagen.")

# ---- procesar --------------------
st.sidebar.divider()
boton_ejecutar = st.sidebar.button("🚀 PROCESAR IMAGEN", disabled=st.session_state.imagen_confirmada is None, on_click=lambda: st.session_state.update(vista='procesado'))

# -------- blanco y negro ------------
check_bnw = st.sidebar.checkbox("Blanco y Negro", value=True, disabled=st.session_state.imagen_confirmada is None or st.session_state.vista != 'procesado')

# -------- desenfoque de datos ---------
name_template = st.sidebar.selectbox(
    "Plantilla",
    ("DNI_FRONTAL", "DNI_TRASERA") if not st.session_state.nueva_template else ("NUEVO", "DNI_FRONTAL", "DNI_TRASERA"),
    help="Selecciona la plantilla que coincide con el tipo de documento que estás editando.",
    index=0,
    disabled=st.session_state.imagen_confirmada is None or st.session_state.vista != 'procesado'
)

crear_template = st.sidebar.toggle("🛠️ Crear/Editar plantilla personalizada", disabled=st.session_state.imagen_confirmada is None or st.session_state.vista != 'procesado', key="crear_template_state")

check_desenfoque = True #st.sidebar.checkbox("Seleccionar zonas", value=False)
st.sidebar.segmented_control("Tipo de desenfoque:", ["Difuminado", "Sólido blanco", "Sólido negro"], key="blur_type", selection_mode="single", default="Difuminado", disabled=st.session_state.vista != 'procesado')

if st.session_state.blur_type == "Difuminado":
    gaussiano = True
    solido_blanco = False
    solido_negro = False
elif st.session_state.blur_type == "Sólido blanco":
    gaussiano = False
    solido_blanco = True
    solido_negro = False
elif st.session_state.blur_type == "Sólido negro":
    gaussiano = False
    solido_blanco = False
    solido_negro = True
else:
    gaussiano = False
    solido_blanco = False
    solido_negro = False


# ----- marca de agua -------------
check_watermark = st.sidebar.checkbox("Marca de agua", value=True, disabled=st.session_state.vista != 'procesado')
marca_de_agua = st.sidebar.text_input("Marca de agua", placeholder="COPIA", value="COPIA", disabled=not check_watermark or st.session_state.vista != 'procesado')
if not check_watermark: marca_de_agua=None

st.sidebar.radio("Color", ["Auto", "Blanco", "Negro", "Rojo"], key="watermark_color", horizontal=True, disabled=not check_watermark or st.session_state.vista != 'procesado')

opacidad_marca_de_agua = st.sidebar.slider(
                            label="Nivel de opacidad",
                            min_value=0.0,
                            max_value=1.0,
                            value=0.5,
                            step=0.1, disabled=not check_watermark or st.session_state.vista != 'procesado'
                        )

if st.session_state.watermark_color=='Auto':
    color_marca_de_agua = None
elif st.session_state.watermark_color=="Blanco":
    color_marca_de_agua = ast.literal_eval(os.getenv('COLOR_WHITE'))
elif st.session_state.watermark_color=="Negro":
    color_marca_de_agua = ast.literal_eval(os.getenv('COLOR_BLACK'))
elif st.session_state.watermark_color=="Rojo":
    color_marca_de_agua = ast.literal_eval(os.getenv('COLOR_RED'))

# --- 3. CUERPO PRINCIPAL (ENTRADA DE DATOS) ---
st.title("📸 DNI editor")
st.write("Sube una foto o usa la cámara.")

# --- 4. LÓGICA DE PROCESAMIENTO ---

# Si el usuario no ha pulsado procesar, mostramos la original
if st.session_state.vista == 'inicio' and not crear_template:
    imagen_original = None
    
    tab1, tab2 = st.tabs(["📸 Cámara", "📁 Archivo/Galería"])

    with tab1:
        foto_camara = st.camera_input("Tomar foto desde cámara", )
        if foto_camara:
            file_bytes = np.asarray(bytearray(foto_camara.read()), dtype=np.uint8)
            st.session_state.imagen_original = cv2.imdecode(file_bytes, 1)

    with tab2:
        foto_archivo = st.file_uploader("Selecciona una imagen", type=["jpg", "jpeg", "png"])
        if foto_archivo:
            file_bytes = np.asarray(bytearray(foto_archivo.read()), dtype=np.uint8)
            st.session_state.imagen_original = cv2.imdecode(file_bytes, 1)
            
    if st.session_state.imagen_original is not None:
        imagen_original = st.session_state.imagen_original
        WIDTH_DISPLAY = 600
        ratio = imagen_original.shape[1] / WIDTH_DISPLAY
        new_h = int(imagen_original.shape[0] / ratio)

        # 2.1 Convertimos a RGB solo para mostrar en Streamlit/Pillow
        # 2.2 Crear una versión pequeña solo para la interfaz de clics
        img_cv2_rgb = cv2.resize(cv2.cvtColor(imagen_original, cv2.COLOR_BGR2RGB), (WIDTH_DISPLAY, new_h))
        st.image(img_cv2_rgb, caption="Imagen seleccionada")
        if st.button("Confirmar imagen"):
            st.success("Imagen confirmada")
            time.sleep(0.5)
            st.rerun()
            
elif st.session_state.vista == 'recorte' and not crear_template:

    if 'imagen_original' in st.session_state and st.session_state.imagen_original is not None:
        st.subheader("Vista previa")
        ejecutar_escanner_interactivo(modo=modo, img_cv2_bgr=st.session_state.imagen_original)

elif crear_template:
   crear_template_page()

elif boton_ejecutar or st.session_state.vista == 'procesado':
    # Procesamiento al pulsar el botón
    with st.spinner("Editando imagen..."):
        if name_template == "NUEVO":
            if st.session_state.nueva_template is None:
                st.error("⚠️ Debes crear y guardar una plantilla personalizada antes de procesar la imagen.")
                boton_ejecutar = False
                crear_template = True
            else:
                template = st.session_state.nueva_template
        else:
            try:
                with open(os.path.join(os.getenv('TEMPLATES_FOLDER'), Path(name_template).stem + '.json'), 'r') as file:
                    template = json.load(file)
            except FileNotFoundError:
                st.error(f"⚠️ No se encontró la plantilla {name_template}. Por favor, crea una plantilla personalizada.")

        # Llamada a tu función
        imagen_final = procesar_imagen(
            st.session_state['imagen_confirmada'], black_n_white=check_bnw,
            development=(os.getenv('MODE') == 'DEVELOPMENT'), gaussian=gaussiano, solid_white=solido_blanco, solid_black=solido_negro, 
            watermark=marca_de_agua, template=template, color=color_marca_de_agua, opacidad=opacidad_marca_de_agua
        )
        
        st.subheader("✨ Resultado")
        st.image(cv2.cvtColor(imagen_final, cv2.COLOR_BGR2RGB), width='content')

    # 3. CONVERSIÓN DE ARRAY A BYTES
    # Convertimos el array de NumPy a un objeto de la librería PIL
    img_pil = Image.fromarray(cv2.cvtColor(imagen_final, cv2.COLOR_BGR2RGB))
    
    buf = io.BytesIO()
    
    # NOMBRE DE FICHERO
    name_file = st.text_input('Nombre del fichero:', value="DNI")

    # 4.1 BOTÓN DE DESCARGA JPG
    img_pil.convert("RGB").save(buf, format="JPEG", quality=90)
    extension = "jpg"
    mimetype = "image/jpeg"
    st.download_button(
        label=f"📥 Descargar como JPEG",
        data=buf.getvalue(),
        file_name=f"{name_file}.{extension}",
        mime=mimetype,
        use_container_width=True
    )
    
    st.slider(label="Calidad de imagen JPEG",                  
                            min_value=0,
                            max_value=100,
                            value=90,
                            step=1)
    
    # 4.2 BOTÓN DE DESCARGA PNG
    img_pil.save(buf, format="PNG")
    extension = "png"
    mimetype = "image/png"
    st.download_button(
        label=f"📥 Descargar como PNG",
        data=buf.getvalue(),
        file_name=f"{name_file}.{extension}",
        mime=mimetype,
        use_container_width=True
    )
    
else:
    st.info("👋 ¡Hola! Selecciona una imagen arriba para empezar a editar.")

# --- 5. PIE DE PÁGINA (TIPO PWA) ---
st.divider()