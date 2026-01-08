import cv2
import json
import os
from pathlib import Path
from dotenv import load_dotenv

import streamlit as st
import plotly.express as px

load_dotenv()

def selector_y_guardado(imagen):
    """
    Muestra la imagen, permite dibujar y tiene un botón para 
    añadir los rectángulos actuales a una lista persistente.
    """
    # 1. Crear el gráfico de Plotly
    fig = px.imshow(imagen)
    fig.update_layout(
        dragmode="drawrect",
        newshape=dict(line_color="lime", fillcolor="rgba(0, 255, 0, 0.1)"),
        margin=dict(l=0, r=0, b=0, t=0),
        height=600
    )

    # 2. Mostrar gráfico (on_select captura los dibujos actuales)
    state = st.plotly_chart(fig, on_select="rerun")

    # 3. Botón para guardar lo que hay en pantalla
    if st.button("Guardar rectángulos actuales"):
        # Inicializar la lista en el estado de sesión si no existe
        if "lista_guardada" not in st.session_state:
            st.session_state.lista_guardada = []

        # Procesar dibujos actuales del estado del gráfico
        if "layout" in state and "shapes" in state["layout"]:
            for shape in state["layout"]["shapes"]:
                if shape["type"] == "rect":
                    x_min, y_min = int(min(shape["x0"], shape["x1"])), int(min(shape["y0"], shape["y1"]))
                    x_max, y_max = int(max(shape["x0"], shape["x1"])), int(max(shape["y0"], shape["y1"]))
                    
                    nuevo_rect = [(x_min, y_min), (x_max, y_max)]
                    
                    # Evitar duplicados si se pulsa el botón varias veces
                    if nuevo_rect not in st.session_state.lista_guardada:
                        st.session_state.lista_guardada.append(nuevo_rect)
            
            st.success(f"¡Guardados! Total en lista: {len(st.session_state.lista_guardada)}")
        else:
            st.warning("No hay ningún rectángulo dibujado para guardar.")

    # Retornar la lista persistente
    return st.session_state.get("lista_guardada", [])

def select_rectangles_on_image(original_img, image_filename=None):
    """
    Allows a user to interactively draw rectangles on an image and returns
    a list of their corner coordinates.

    Args:
        image (numpy array): numpy array from cv2 (BGR)

    Returns:
        list: A list of tuples, where each tuple contains the start and end
              points of a drawn rectangle, e.g., [((x1, y1), (x2, y2)), ...].
    """
    # Global variables for the callback function
    global drawing, start_point, rectangles, img_display
    
    # Reset global variables for a new session
    drawing = False
    start_point = (-1, -1)
    rectangles = []

    try:

        # Create a display copy of the image
        img_display = original_img.copy()

        # Create a window to display the image
        cv2.namedWindow('Image with Rectangles')

        # Set the mouse callback function
        cv2.setMouseCallback('Image with Rectangles', _draw_rectangle_callback)

        print("Instructions:")
        print("  - Click and drag the left mouse button to draw a rectangle.")
        print("  - Press 'q' to quit and return the coordinates.")
        print("  - Press 'c' to clear all drawn rectangles.")

        while True:
            cv2.imshow('Image with Rectangles', img_display)
            key = cv2.waitKey(1) & 0xFF

            # Press 'q' to quit and return the coordinates
            if key == ord('q'):
                break

            # Press 'c' to clear all drawn rectangles
            elif key == ord('c'):
                img_display = original_img.copy()
                rectangles.clear()
                print("All rectangles cleared.")
    
    except FileNotFoundError as e:
        print(e)
        return []
    finally:
        cv2.destroyAllWindows()
    
    if len(rectangles) == 0:
        print("No rectangles selected")
    
    elif 'NUEVO' in image_filename:
        json_string = {"size": list(original_img.shape[:2][::-1]), "rectangles": rectangles}
        print("New template detected")
    
    else:
        json_string = {"size": list(original_img.shape[:2][::-1]), "rectangles": rectangles}
        with open(os.path.join(os.getenv('TEMPLATES_FOLDER'), Path(image_filename).stem + '.json'), 'w') as file:
            json.dump(json_string, file)
    
    return json_string

def _draw_rectangle_callback(event, x, y, flags, param):
    """
    Internal callback function to handle mouse events.
    """
    global drawing, start_point, rectangles, img_display

    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        start_point = [x, y]
    
    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing:
            img_copy = img_display.copy()
            cv2.rectangle(img_copy, start_point, [x, y], (0, 255, 0), 2)
            cv2.imshow('Image with Rectangles', img_copy)

    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False
        end_point = [x, y]
        cv2.rectangle(img_display, start_point, end_point, (0, 255, 0), 2)
        rectangles.append([start_point, end_point])
        cv2.imshow('Image with Rectangles', img_display)
        
def draw_rectangle_on_image(image, corners, color=(128, 128, 128), thickness=-1):
    """
    Draws a rectangle on an image given the coordinates of two opposite corners.

    Args:
        image (numpy array): numpy array from cv2 (BGR)
        corner1 (tuple): The (x, y) coordinates of the first corner.
        corner2 (tuple): The (x, y) coordinates of the opposite corner.
        color (tuple): The BGR color of the rectangle. Default is green.
        thickness (int): The thickness of the rectangle's border. Default is 2.
    
    Returns:
        np.ndarray: The image with the rectangle drawn on it, or None if the image
                    could not be loaded.
    """
    try:        
        for corner1, corner2 in corners:
        
            # Draw the rectangle using the two opposite corners
            cv2.rectangle(image, corner1, corner2, color, thickness)
        
        return image
    
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None
    
def apply_gaussian_blur_to_rectangle(image, corners, kernel_size=(101, 101)):
    """
    Applies a Gaussian blur to a rectangular region of an image.

    Args:
        image_path (str): The path to the image file.
        corner1 (tuple): The (x, y) coordinates of the first corner.
        corner2 (tuple): The (x, y) coordinates of the opposite corner.
        kernel_size (tuple): The size of the Gaussian blur kernel.
                             (e.g., (15, 15)). Must be positive and odd.

    Returns:
        np.ndarray: The image with the blurred rectangle, or None if an error occurs.
    """
    try:
        
        if corners:
        
            for corner1, corner2 in corners:
            
                # Ensure coordinates are in a consistent order (top-left, bottom-right)
                x1, y1 = min(corner1[0], corner2[0]), min(corner1[1], corner2[1])
                x2, y2 = max(corner1[0], corner2[0]), max(corner1[1], corner2[1])

                # Extract the rectangular region of interest (ROI)
                roi = image[y1:y2, x1:x2]
            
                # Apply Gaussian blur to the ROI
                blurred_roi = cv2.GaussianBlur(roi, kernel_size, 0)
            
                # Place the blurred ROI back into the original image
                image[y1:y2, x1:x2] = blurred_roi
                
        else: # not rectangles
            # Extract the rectangular region of interest (ROI)
            roi = image
            
            # Apply Gaussian blur to the ROI
            blurred_roi = cv2.GaussianBlur(roi, kernel_size, 0)
            
            # Place the blurred ROI back into the original image
            image = blurred_roi
            
        
        return image
        
    except FileNotFoundError as e:
        print(e)
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None
        
# Example Usage:
if __name__ == "__main__":

    # Call the function to get the rectangle coordinates
    rect_coords = select_rectangles_on_image("./images/2026-01-02_121317_1.jpg")
    
    print("\nFinal Coordinates of the drawn rectangles:")
    if rect_coords:
        for i, (start, end) in enumerate(rect_coords):
            print(f"  Rectangle {i+1}: Start={start}, End={end}")
    else:
        print("No rectangles were drawn.")