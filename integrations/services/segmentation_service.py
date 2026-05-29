import cv2
import numpy as np
import io
from PIL import Image

class SemanticSegmentationService:
    def __init__(self):
        # 🚀 ADIÓS IA PESADA. Iniciamos el motor 100% matemático.
        # Ya no cargamos modelos de Nvidia, por lo que la RAM de Render queda libre.
        print("Iniciando SemanticSegmentationService (Modo Geométrico Ligero)")

    def _clean_mask(self, mask):
        """
        🧼 Tu limpiador morfológico original intacto.
        """
        mask_uint8 = mask.astype(np.uint8)
        kernel = np.ones((5, 5), np.uint8)
        cleaned = cv2.morphologyEx(mask_uint8, cv2.MORPH_CLOSE, kernel)
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
        return cleaned

    def generate_advanced_map(self, image_path_or_bytes):
        """
        🗺️ Reemplazo del Segformer para producción (Render).
        Calcula las áreas mediante geometría de contornos y devuelve el JSON exacto para tu APK.
        """
        if isinstance(image_path_or_bytes, bytes):
            image = Image.open(io.BytesIO(image_path_or_bytes)).convert("RGB")
        else:
            image = Image.open(image_path_or_bytes).convert("RGB")

        original_img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        h, w = original_img.shape[:2]

        # 1. Suavizamos la imagen para fusionar texturas y dejar bloques de color sólidos
        shifted = cv2.pyrMeanShiftFiltering(original_img, 21, 51)
        gray = cv2.cvtColor(shifted, cv2.COLOR_BGR2GRAY)

        # 2. Buscamos bordes estructurales y los engordamos para separar bien las zonas
        edges = cv2.Canny(gray, 30, 100)
        kernel = np.ones((5, 5), np.uint8)
        edges_dilated = cv2.dilate(edges, kernel, iterations=2)

        # 3. Invertimos: Las paredes/suelo se vuelven bloques blancos limpios
        mask_areas = cv2.bitwise_not(edges_dilated)

        # 4. Encontramos los contornos geométricos de la habitación
        contours, _ = cv2.findContours(mask_areas, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        final_img_rgb = np.zeros((h, w, 3), dtype=np.uint8)
        segments_data = [] # El JSON idéntico para Flutter
        contador_paredes = 1
        
        # Umbral: Filtramos ruido (bloques menores al 5% de la foto)
        min_area = (h * w) * 0.05 

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area > min_area:
                # 5. Calculamos el Centroide con la misma fórmula matemática (Moments)
                M = cv2.moments(cnt)
                if M["m00"] > 0:
                    cX = int(M["m10"] / M["m00"])
                    cY = int(M["m01"] / M["m00"])

                    # 6. Lógica espacial automática: Si está abajo, es piso. Si no, pared.
                    is_floor = cY > (h * 0.75)

                    if is_floor:
                        color = [0, 0, 255] # Tu azul original para el piso
                        seg_id = "floor_1"
                        label = "Piso"
                        segment_type = "floor"
                    else:
                        color = np.random.randint(50, 200, size=3).tolist()
                        seg_id = f"wall_{contador_paredes}"
                        label = f"Pared {contador_paredes}"
                        segment_type = "wall"
                        contador_paredes += 1

                    # Pintamos el mapa de colores de fondo
                    cv2.drawContours(final_img_rgb, [cnt], -1, color, thickness=cv2.FILLED)

                    # 7. ESTRUCTURA SAGRADA PARA EL APK
                    segments_data.append({
                        "id": seg_id,
                        "label": label,
                        "type": segment_type,
                        "x": cX,
                        "y": cY,
                        "color": color
                    })

        # Seguro de vida si la foto es un caos y no detecta formas claras
        if not segments_data:
            segments_data.append({
                "id": "wall_1", "label": "Pared 1", "type": "wall", 
                "x": w//2, "y": h//2, "color": [0, 255, 0]
            })
            cv2.rectangle(final_img_rgb, (0, 0), (w, h), (0, 255, 0), -1)

        return Image.fromarray(final_img_rgb), segments_data, w, h

    def generate_color_map(self, image_path_or_bytes):
        """
        🎨 Dejo tu método de respaldo aquí por si tu views lo llama en algún lado, 
        pero adaptado a modo matemático para que no pida la IA.
        """
        img_map, _, _, _ = self.generate_advanced_map(image_path_or_bytes)
        return img_map

    def get_binary_mask(self, image_bytes, surface_type="wall"):
        """
        ✂️ Genera la máscara blanco/negro que necesita tu InpaintingService de forma matemática.
        """
        if isinstance(image_bytes, bytes):
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        else:
            image = Image.open(image_bytes).convert("RGB")
            
        original_img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        h, w = original_img.shape[:2]

        shifted = cv2.pyrMeanShiftFiltering(original_img, 21, 51)
        gray = cv2.cvtColor(shifted, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 30, 100)
        edges_dilated = cv2.dilate(edges, np.ones((5, 5), np.uint8), iterations=2)
        mask_areas = cv2.bitwise_not(edges_dilated)

        contours, _ = cv2.findContours(mask_areas, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        raw_mask = np.zeros((h, w), dtype=np.uint8)
        min_area = (h * w) * 0.05 

        for cnt in contours:
            if cv2.contourArea(cnt) > min_area:
                M = cv2.moments(cnt)
                if M["m00"] > 0:
                    cY = int(M["m01"] / M["m00"])
                    is_floor = cY > (h * 0.75)

                    if (surface_type == "floor" and is_floor) or (surface_type == "wall" and not is_floor):
                        cv2.drawContours(raw_mask, [cnt], -1, 1, thickness=cv2.FILLED)

        clean_mask = self._clean_mask(raw_mask) 
        return clean_mask * 255