
"""
import cv2
import numpy as np

def ordenar_puntos(pts):
    rect = np.zeros((4, 2), dtype="float32")
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect

def aplicar_perspectiva(img_rgb, pts_origen):
    pts_rect = ordenar_puntos(pts_origen)
    (tl, tr, br, bl) = pts_rect
    
    # Calcular dimensiones reales
    w = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
    h = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))
    
    pts_destino = np.float32([[0, 0], [w, 0], [w, h], [0, h]])
    M = cv2.getPerspectiveTransform(pts_rect, pts_destino)
    return cv2.warpPerspective(img_rgb, M, (w, h))

def detectar_automatico(img_rgb):
    # Pre-procesamiento
    gray = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    edged = cv2.Canny(gray, 150, 200)
    
    cnts, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[0:5]
    
    for c in cnts:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) == 4:
            return approx.reshape(4, 2)
    return None

"""
import os
from dotenv import load_dotenv

load_dotenv()

def get_nombre_plantillas():
    template_dir = os.getenv('TEMPLATES_FOLDER')
    if not os.path.exists(template_dir):
        return []
    return [f[:-5] for f in os.listdir(template_dir) if f.endswith('.json')]