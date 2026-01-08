from src.utils.rectangles import select_rectangles_on_image, draw_rectangle_on_image, apply_gaussian_blur_to_rectangle
from src.utils.apply_watermark import apply_rotated_watermark
import os
from dotenv import load_dotenv
import cv2

load_dotenv()

def procesar_imagen(image, development=None, black_n_white=True, solid_white=False, solid_black=False, gaussian=False, watermark=None, color=(125, 125, 125), opacidad=0.5, template='image'):
    
    image_file = f'{template}.jpg'
    
    if black_n_white:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    get_size = template['size']
    image = cv2.resize(image, tuple(get_size)) 

    if development:
        # get rectangles
        aux = select_rectangles_on_image(image, image_filename=image_file, save_template=True)
        get_rectangles = aux['rectangles']

        print("\nFinal Coordinates of the drawn rectangles:")
        if get_rectangles:
            for i, (start, end) in enumerate(get_rectangles):
                print(f"  Rectangle {i+1}: Start={start}, End={end}")
        else:
            print("No rectangles were drawn.")
            
    if solid_white or solid_black:
        # load template rectangles
        get_rectangles = template['rectangles']
        # image with solid rectangles
        image = draw_rectangle_on_image(image, get_rectangles, color=((255,255,255) if solid_white else (0,0,0)), thickness=-1)
        
    elif gaussian:
        # load template rectangles
        get_rectangles = template['rectangles']
        # image with gaussian blur on rectangles
        image = apply_gaussian_blur_to_rectangle(image, get_rectangles)
    
    if watermark:
        if color is None: # Auto
            if solid_white:
                color = (0,0,0) # letters in black
            elif solid_black:
                color = (255,255,255) # letters in white
        else:
            color = color
        # image with watermark
        image = apply_rotated_watermark(image, watermark, 35, color=color, opacity=opacidad)
    
    #cv2.imwrite(template + '_result.jpg', image)

    return image

if __name__=='__main__':
    
    # front ---------------------------------------------------------
    image_path = os.path.join(os.getenv('IMAGES_FOLDER'), 'dni_front_2.jpg')
    procesar_imagen(image_path, autocrop=True)
    
    # back -------------------------------------------------------
    image_path = os.path.join(os.getenv('IMAGES_FOLDER'), 'dni_back_2.jpg')
    procesar_imagen(image_path, autocrop=False)