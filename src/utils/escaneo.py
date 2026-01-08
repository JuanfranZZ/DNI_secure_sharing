import streamlit as st
import cv2
import numpy as np
from streamlit_image_coordinates import streamlit_image_coordinates
from PIL import Image, ImageDraw

def ejecutar_escanner_interactivo(modo="Manual", img_cv2_bgr=None):
    """
    Maneja la interfaz de escaneo. 
    Retorna: np.ndarray (BGR) si se confirma el escaneo, de lo contrario None.
    """

    # 1. Definir un ancho máximo de visualización (ej. 800 píxeles)
    WIDTH_DISPLAY = 600
    ratio = img_cv2_bgr.shape[1] / WIDTH_DISPLAY
    new_h = int(img_cv2_bgr.shape[0] / ratio)

    # 2.1 Convertimos a RGB solo para mostrar en Streamlit/Pillow
    # 2.2 Crear una versión pequeña solo para la interfaz de clics
    img_cv2_rgb = cv2.resize(cv2.cvtColor(img_cv2_bgr, cv2.COLOR_BGR2RGB), (WIDTH_DISPLAY, new_h))

    puntos_finales = None

    # --- LÓGICA DE SELECCIÓN ---
    if modo == "Manual":
        
        # --- ESTADO DE SESIÓN ---
        if "puntos_manuales" not in st.session_state:
            st.session_state.puntos_manuales = []

        reset_puntos = st.sidebar.button("Resetear puntos")

        if reset_puntos:
            st.session_state.puntos_manuales = []
            st.rerun()
        
        img_pil = Image.fromarray(img_cv2_rgb)
        draw = ImageDraw.Draw(img_pil)
        
        for i, p in enumerate(st.session_state.puntos_manuales):
            draw.ellipse((p[0]-10, p[1]-10, p[0]+10, p[1]+10), fill="red", outline="white")
            if i > 0:
                draw.line([st.session_state.puntos_manuales[i-1], st.session_state.puntos_manuales[i]], fill="red", width=4)
            if i == 3:
                draw.line([st.session_state.puntos_manuales[3], st.session_state.puntos_manuales[0]], fill="red", width=4)

        st.write("### Selecciona las 4 esquinas del objeto:")
        # Dentro de la función, para que la imagen no sea gigante pero sí visible
        #col_img, _ = st.columns([3, 1])
        #with col_img:
        coords = streamlit_image_coordinates(img_pil, key="coords_manual")

        if coords and len(st.session_state.puntos_manuales) < 4:
            nuevo_punto = (coords["x"], coords["y"])
            if nuevo_punto not in st.session_state.puntos_manuales:
                st.session_state.puntos_manuales.append(nuevo_punto)
                st.rerun()
        
        if len(st.session_state.puntos_manuales) == 4:
            # IMPORTANTE: Escalamos los puntos de vuelta al tamaño original
            puntos_reales = np.array(st.session_state.puntos_manuales, dtype="float32") * ratio
            puntos_finales = puntos_reales
            
    elif modo == "Completa":
        h, w = img_cv2_rgb.shape[:2]
        marco_imagen = np.array([[0, 0], [w-1, 0], [w-1, h-1], [0, h-1]], dtype="float32")
        st.success("Modo completa seleccionado: se usará toda la imagen.")
        img_auto_preview = img_cv2_rgb.copy()
        cv2.rectangle(img_auto_preview, (0,0), (w-1, h-1), (0, 255, 0), 10)
        st.image(img_auto_preview, caption="Detección Automática")
        puntos_finales = marco_imagen * ratio
                
    else: # MODO AUTOMÁTICO
        gray = cv2.cvtColor(img_cv2_rgb, cv2.COLOR_RGB2GRAY)
        #edged = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 200)
        edged = cv2.Canny(gray, 50, 200)
        cnts, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = sorted(cnts, key=cv2.contourArea, reverse=False)[:1]
        
        for c in cnts:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            if len(approx) == 4:
                puntos_finales = approx.reshape(4, 2).astype("float32")
                st.success("¡Objeto detectado!")
                # Dibujar preview del automático
                img_auto_preview = img_cv2_rgb.copy()
                cv2.drawContours(img_auto_preview, [approx], -1, (0, 255, 0), 10)
                st.image(img_auto_preview, caption="Detección Automática")
                # devolvemos los putnos finales escalados
                puntos_finales = puntos_finales * ratio
        
        if puntos_finales is None:
            st.error("No se encontró un contorno claro. Usa el modo manual.")

    # --- PROCESAMIENTO Y RETORNO ---
    if puntos_finales is not None:
        # Ordenar puntos (tl, tr, br, bl)
        rect = np.zeros((4, 2), dtype="float32")
        s = puntos_finales.sum(axis=1)
        rect[0] = puntos_finales[np.argmin(s)]
        rect[2] = puntos_finales[np.argmax(s)]
        diff = np.diff(puntos_finales, axis=1)
        rect[1] = puntos_finales[np.argmin(diff)]
        rect[3] = puntos_finales[np.argmax(diff)]

        (tl, tr, br, bl) = rect
        w = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
        h = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))

        dst = np.float32([[0, 0], [w-1, 0], [w-1, h-1], [0, h-1]])
        M = cv2.getPerspectiveTransform(rect, dst)
        
        # OJO: Aplicamos la transformación sobre la imagen BGR original de OpenCV
        warped_bgr = cv2.warpPerspective(img_cv2_bgr, M, (w, h))
        st.session_state['warped_bgr'] = warped_bgr
        
        # Aplicar ajustes
        #resultado_bgr = cv2.convertScaleAbs(warped_bgr, alpha=contraste, beta=brillo)

        # Mostrar preview del resultado
        st.image(cv2.cvtColor(warped_bgr, cv2.COLOR_BGR2RGB), caption="Vista previa del resultado")

        st.checkbox("Confirmar y usar esta imagen", key="confirm_scan", on_change=activar_ejecutar, value=st.session_state.ejecutar_enabled if "ejecutar_enabled" in st.session_state else False)
            
    return None

def activar_ejecutar():
    if st.session_state.confirm_scan:
        st.session_state.ejecutar_enabled = True
        st.session_state['imagen_confirmada'] = st.session_state['warped_bgr'] # Devolvemos la imagen como la leería cv2
    else:
        st.session_state.ejecutar_enabled = False
        del st.session_state['imagen_confirmada']