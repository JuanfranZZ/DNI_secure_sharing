import streamlit as st
from PIL import Image, ImageDraw
from streamlit_image_coordinates import streamlit_image_coordinates
import cv2


def crear_template_page():
 
    st.title("🎯 Marcar Rectángulos")

    if st.session_state['imagen_confirmada'] is None:
        st.warning("⚠️ No hay imagen cargada. Por favor, vuelve al Paso 1.")
    else:
        
        img_cv2_bgr = st.session_state['imagen_confirmada']
        # 1. Definir un ancho máximo de visualización (ej. 800 píxeles)
        WIDTH_DISPLAY = 600
        ratio = img_cv2_bgr.shape[1] / WIDTH_DISPLAY
        new_h = int(img_cv2_bgr.shape[0] / ratio)

        # 2.1 Convertimos a RGB solo para mostrar en Streamlit/Pillow
        # 2.2 Crear una versión pequeña solo para la interfaz de clics
        img_cv2_rgb = cv2.resize(cv2.cvtColor(img_cv2_bgr, cv2.COLOR_BGR2RGB), (WIDTH_DISPLAY, new_h))
        
        img_pil = Image.fromarray(img_cv2_rgb)
        width, height = img_pil.size
        
        st.write(f"Dimensiones: {width}x{height}px. Haz clic para definir p1 y p2.")
        
        # Dibujar rectángulos y puntos temporales en la vista previa
        preview = img_pil.copy()
        draw = ImageDraw.Draw(preview)
        for r in st.session_state.rects:
            draw.rectangle([tuple(r[0]), tuple(r[1])], outline="red", width=5)
        
        if st.session_state.temp_point:
            p = st.session_state.temp_point
            draw.ellipse([p[0]-5, p[1]-5, p[0]+5, p[1]+5], fill="blue")

        # COMPONENTE DE COORDENADAS
        coords = streamlit_image_coordinates(preview, key="pill_clics")

        if coords:
            new_p = [coords["x"], coords["y"]]
            
            # Evitar que el mismo clic se registre varias veces por el rerun
            if "last_clic" not in st.session_state or st.session_state.last_clic != new_p:
                st.session_state.last_clic = new_p
                
                if st.session_state.temp_point is None:
                    st.session_state.temp_point = new_p
                else:
                    p1 = st.session_state.temp_point
                    st.session_state.rects.append([p1, new_p])
                    st.session_state.temp_point = None
                st.rerun()


        st.subheader("Datos del Template")
        st.write(f"Rectángulos: {len(st.session_state.rects)}")
        
        if st.button("Limpiar Puntos"):
            st.session_state.rects = []
            st.session_state.temp_point = None
            st.rerun()

        if st.button("💾 Finalizar y Generar JSON"):
            template = {
                "size": [width, height],
                "rectangles": st.session_state.rects
            }
            st.session_state.nueva_template= template
            st.success("JSON guardado en sesión como plantilla NUEVO.")
            if st.button("Volver al Paso 1 para utilizar la plantilla", on_click=cambiar_crear_template_state):
                st.rerun()
                
def cambiar_crear_template_state():
    st.session_state.crear_template_state = False