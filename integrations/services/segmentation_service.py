from transformers import SegformerImageProcessor, SegformerForSemanticSegmentation
from PIL import Image
import torch
import numpy as np
import io
import cv2

class SemanticSegmentationService:
    def __init__(self):
        # Motor B0: Ligero y rápido
        model_name = "nvidia/segformer-b0-finetuned-ade-512-512"
        self.processor = SegformerImageProcessor.from_pretrained(model_name)
        self.model = SegformerForSemanticSegmentation.from_pretrained(model_name)


    def _clean_mask(self, mask):
        """
        Aplica filtros morfológicos para cerrar huecos en las paredes.
        """
        # Convertimos a formato que OpenCV entienda (uint8)
        mask_uint8 = mask.astype(np.uint8)
        
        # Kernel: es como el tamaño de la brocha que limpia. 
        # Si ves que aún quedan huecos, súbelo a (7,7)
        kernel = np.ones((5,5), np.uint8)
        
        # MORPH_CLOSE: Rellena los huequitos negros dentro de la pared
        cleaned = cv2.morphologyEx(mask_uint8, cv2.MORPH_CLOSE, kernel)
        
        # MORPH_OPEN: Quita puntitos blancos que sobran fuera de la pared
        cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel)
        
        return cleaned

    def generate_advanced_map(self, image_path_or_bytes):
       # 1. Cargar la imagen (Acepta bytes o ruta de archivo)
        if isinstance(image_path_or_bytes, bytes):
            image = Image.open(io.BytesIO(image_path_or_bytes)).convert("RGB")
        else:
            image = Image.open(image_path_or_bytes).convert("RGB")

        # Convertimos la imagen de PIL a un array de Numpy en formato BGR (que es el que usa OpenCV)
        original_img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        # 2. Pasar por SegFormer para saber dónde están las paredes en general
        inputs = self.processor(images=image, return_tensors="pt")
        with torch.no_grad():
            outputs = self.model(**inputs)

        logits = outputs.logits
        logits_resized = torch.nn.functional.interpolate(
            logits,
            size=image.size[::-1],
            mode="bilinear",
            align_corners=False,
        )
        segmentation_map = logits_resized.argmax(dim=1)[0].cpu().numpy()

        # --- LA CIRUGÍA ANTI-ALUCINACIONES EMPIEZA AQUÍ ---
        
        # 💡 Identificamos los estorbos comunes (Obstáculos)
        # IDs de ADE20K: 7(cama), 12(persona), 14(puerta), 15(mesa), 19(gabinete), 31(silla), 32(sofá)
        obstaculos_ids = [7, 12, 14, 15, 19, 31, 32]
        raw_obstacle_mask = np.isin(segmentation_map, obstaculos_ids).astype(np.uint8)
        
        # Engordamos un poquito la máscara de los obstáculos para tener un "margen de seguridad"
        kernel_seguridad = np.ones((15, 15), np.uint8)
        safe_obstacle_mask = cv2.dilate(raw_obstacle_mask, kernel_seguridad, iterations=1)

        # A. Extraemos y LIMPIAMOS la máscara de la Pared (ID 0)
        raw_wall_mask = (segmentation_map == 0).astype(np.uint8)
        clean_wall_mask = self._clean_mask(raw_wall_mask)
        
        # 🔨 EL CORTAFRÍO: Le restamos los obstáculos a la pared limpia
        clean_wall_mask = cv2.subtract(clean_wall_mask, safe_obstacle_mask)
        
        # B. Extraemos y LIMPIAMOS la máscara del Piso (ID 3)
        raw_floor_mask = (segmentation_map == 3).astype(np.uint8)
        clean_floor_mask = self._clean_mask(raw_floor_mask)

        # 🔨 EL CORTAFRÍO: Le restamos los obstáculos al piso también
        clean_floor_mask = cv2.subtract(clean_floor_mask, safe_obstacle_mask)

        # Multiplicamos por 255 para que OpenCV la entienda en los pasos siguientes
        wall_mask = clean_wall_mask * 255

        # --- FIN DE LA CIRUGÍA, SEGUIMOS CON WATERSHED ---

        # 3. Detección de Bordes (Canny) sobre la foto original para buscar esquinas
        gray = cv2.cvtColor(original_img, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)

        # 4. Limpiar bordes: Solo nos interesan los bordes que Caen DENTRO de la pared limpia (ya sin obstáculos)
        wall_edges = cv2.bitwise_and(edges, edges, mask=wall_mask)

        # 5. Dilatamos los bordes para crear "muros de contención" gruesos entre paredes
        kernel = np.ones((3,3), np.uint8)
        boundary_lines = cv2.dilate(wall_edges, kernel, iterations=1)

        # 6. Marcadores para Watershed
        unknown = cv2.subtract(wall_mask, boundary_lines)
        ret, markers = cv2.connectedComponents(unknown)

        markers = markers + 1
        markers[boundary_lines == 255] = 0

        # 7. Algoritmo Watershed (Inunda hasta chocar con las esquinas)
        markers = cv2.watershed(original_img, markers)

        # 8. Pintar cada instancia y CALCULAR CENTROIDES
        final_img_rgb = np.zeros((original_img.shape[0], original_img.shape[1], 3), dtype=np.uint8)
        
        segments_data = [] # ¡Aquí guardaremos los datos para Flutter!

        # Analizamos las paredes detectadas (Watershed empieza desde el ID 2)
        contador_paredes = 1
        for i in range(2, np.max(markers) + 1):
            wall_instance_mask = (markers == i).astype(np.uint8)
            
            # Calculamos el "Centro de Masa" (Centroide) con OpenCV
            M = cv2.moments(wall_instance_mask)
            
            # Evitamos división por cero si la máscara está vacía
            if M["m00"] > 0:
                cX = int(M["m10"] / M["m00"])
                cY = int(M["m01"] / M["m00"])
                
                # OJO: Filtramos manchas muy pequeñas (ruido). 
                area = cv2.countNonZero(wall_instance_mask)
                if area > 10000: # Puedes ajustar este número si descarta paredes buenas
                    color = np.random.randint(0, 255, size=3).tolist()
                    final_img_rgb[wall_instance_mask == 1] = color
                    
                    segments_data.append({
                        "id": f"wall_{i}",
                        "label": f"Pared {contador_paredes}",
                        "type": "wall",
                        "x": cX,
                        "y": cY,
                        "color": color
                    })
                    contador_paredes += 1

        # Analizamos el Piso (Máscara limpia y SIN obstáculos que guardamos arriba)
        floor_mask_binary = clean_floor_mask.astype(np.uint8)
        M_floor = cv2.moments(floor_mask_binary)
        if M_floor["m00"] > 0:
            cX_floor = int(M_floor["m10"] / M_floor["m00"])
            cY_floor = int(M_floor["m01"] / M_floor["m00"])
            
            area_floor = cv2.countNonZero(floor_mask_binary)
            if area_floor > 10000:
                final_img_rgb[floor_mask_binary == 1] = [0, 0, 255] # Azul
                segments_data.append({
                    "id": "floor_1",
                    "label": "Piso",
                    "type": "floor",
                    "x": cX_floor,
                    "y": cY_floor,
                    "color": [0, 0, 255]
                })

        # Devolvemos la imagen generada Y la data de los botones,
        # además del tamaño original de la foto para que Flutter calcule las proporciones.
        return Image.fromarray(final_img_rgb), segments_data, image.width, image.height

    # Dejo el método anterior intacto por si quieres usar el básico después
    def generate_color_map(self, image_path_or_bytes):
        if isinstance(image_path_or_bytes, bytes):
            image = Image.open(io.BytesIO(image_path_or_bytes)).convert("RGB")
        else:
            image = Image.open(image_path_or_bytes).convert("RGB")

        inputs = self.processor(images=image, return_tensors="pt")
        with torch.no_grad():
            outputs = self.model(**inputs)

        logits = outputs.logits
        logits_resized = torch.nn.functional.interpolate(
            logits, size=image.size[::-1], mode="bilinear", align_corners=False
        )
        segmentation_map = logits_resized.argmax(dim=1)[0].cpu().numpy()

        color_map = np.zeros((segmentation_map.shape[0], segmentation_map.shape[1], 3), dtype=np.uint8)
        color_map[segmentation_map == 0] = [255, 0, 0] 
        color_map[segmentation_map == 3] = [0, 0, 255]
        color_map[segmentation_map == 5] = [0, 255, 0]

        return Image.fromarray(color_map)
    

    def get_binary_mask(self, image_bytes, surface_type="wall"):
        """
        Función auxiliar rápida que solo devuelve una máscara matemática en blanco y negro 
        (255 = área a pintar, 0 = no pintar) para el recorte del inpainting en OpenCV.
        """
        if isinstance(image_bytes, bytes):
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        else:
            image = Image.open(image_bytes).convert("RGB")
            
        inputs = self.processor(images=image, return_tensors="pt")
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            
        logits = outputs.logits
        logits_resized = torch.nn.functional.interpolate(
            logits, size=image.size[::-1], mode="bilinear", align_corners=False
        )
        segmentation_map = logits_resized.argmax(dim=1)[0].cpu().numpy()
        
        # ID 0 es Pared, ID 3 es Piso
        target_id = 0 if surface_type == "wall" else 3
        
        raw_mask = (segmentation_map == target_id).astype(np.uint8)
        
        # Usamos tu mismo método de limpieza para que los bordes no queden mordidos
        clean_mask = self._clean_mask(raw_mask) 
        
        return clean_mask * 255