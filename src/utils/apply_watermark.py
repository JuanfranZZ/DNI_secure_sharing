import cv2
import numpy as np
import ast
import os

def apply_rotated_watermark(img, text, angle=30, opacity=1, color=(255, 255, 255), output_path=None):
    # 1. Load the base image
    h, w = img.shape[:2]

    if img.ndim != 3:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR) # treat the GRAY scale as colored

    # 2. Create a larger canvas to handle rotation without clipping edges
    # We use a canvas larger than the image to ensure tiles cover corners
    diagonal = int(np.sqrt(h**2 + w**2))
    watermark_layer = np.zeros((diagonal, diagonal, 3), dtype=np.uint8)
    #watermark_layer = np.zeros((h, w, 3), dtype=np.uint8)

    # 3. Define text properties
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 1.5
    color = (ast.literal_eval(os.getenv('COLOR_WHITE')) if color is None else color)
    thickness = 2
    
    (text_w, text_h), _ = cv2.getTextSize(text, font, font_scale, thickness)
    
    # 4. Draw repeated text on the larger canvas (straight first)
    # Adjust spacing by changing the +200 and +100 values
    # create a mask for the text over the image
    for y in range(0, diagonal, text_h + 50):
        for x in range(0, diagonal, text_w + 50):
            cv2.putText(watermark_layer, text, org=(x, y), fontFace=font, 
                        fontScale=font_scale, color=(1,1,1), thickness=thickness, lineType=cv2.FILLED)

    # 5. Rotate the entire watermark canvas by 'angle' degrees
    center = (diagonal // 2, diagonal // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated_watermark = cv2.warpAffine(watermark_layer, M, (diagonal, diagonal), flags=cv2.INTER_NEAREST)

    # 6. Crop the rotated canvas back to the original image size
    # We take the center portion to match the original image dimensions
    start_y = (diagonal - h) // 2
    start_x = (diagonal - w) // 2
    cropped_watermark = rotated_watermark[start_y:start_y+h, start_x:start_x+w]

    # 7. Blend with original image
    #if color != (0,0,0): 
    #    output = cv2.addWeighted(img, (1-opacity), cropped_watermark, opacity, 0)
    #else:# black letters case
    #    output = np.multiply(img,cropped_watermark*opacity).astype(np.uint8)
        
    fondo_color = np.ones_like(img, dtype=np.uint8) * np.array(color, dtype=np.uint8)
    output = np.where(cropped_watermark!=0, fondo_color*opacity + (1-opacity)*img, img).astype(np.uint8)

    # Save the final image if an output path is provided
    if output_path:
        cv2.imwrite(output_path, output)
        print(f"Image with rotated text saved to {output_path}")
    
    return output

if __name__=='__main__':
    # Run the function
    result = apply_rotated_watermark('./images/dni_front.jpg', 'CONFIDENTIAL')
    cv2.imwrite('watermarked_result.jpg', result)
    cv2.imshow('30 Degree Tiled Watermark', result)
    cv2.waitKey(0)