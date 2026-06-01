import os
import io
import time
import base64
import requests
import cv2
import numpy as np
from PIL import Image
from django.conf import settings

class SemanticSegmentationService:
    def __init__(self):
        print("--- 🧠 INICIANDO CEREBRO DE IA (HUGGING FACE API) ---")
        raw_token = getattr(settings, "HF_TOKEN", os.getenv("HF_TOKEN"))
        
        if not raw_token:
            raise ValueError("🚨 ERROR: Falta el HF_TOKEN en el entorno.")
            
        self.hf_token = str(raw_token).strip().replace('"', '').replace("'", "")
        
        # El modelo Segformer B0 que usabas localmente, pero ahora en la nube
        self.api_url = "https://api-inference.huggingface.co/models/nvidia/segformer-b0-finetuned-ade-512-512"
        self.headers = {"Authorization": f"Bearer {self.hf_token}"}

    def _call_hf_api(self, image_bytes):
        """
        Llama a la API de Hugging Face. 
        Maneja el "Cold Start" (cuando el modelo está dormido y tarda en cargar).
        """
        max_retries = 5
        for attempt in range(max_retries):
            print(f"📡 Llamando a Hugging Face (Intento {attempt + 1})...")
            response = requests.post(self.api_url, headers=self.headers, data=image_bytes)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 503:
                # El modelo está cargando. Esperamos 5 segundos y reintentamos.
                print("⏳ El modelo de IA está despertando. Esperando 5 segundos...")
                time.sleep(5)
            else:
                raise Exception(f"Fallo en Hugging Face API: {response.status_code} - {response.text}")
                
        raise Exception("Tiempo de espera agotado cargando el modelo de Hugging Face.")

    def generate_advanced_map(self, image_path_or_bytes):
        """
        Obtiene la segmentación de la IA y extrae los pines (centroides) para Flutter.
        """
        if isinstance(image_path_or_bytes, bytes):
            image_bytes = image_path_or_bytes
            image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        else:
            with open(image_path_or_bytes, "rb") as f:
                image_bytes = f.read()
            image = Image.open(image_path_or_bytes).convert("RGB")

        original_img = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        h, w = original_img.shape[:2]

        # 1. Llamamos a la API
        hf_result = self._call_hf_api(image_bytes)
        
        final_img_rgb = np.zeros((h, w, 3), dtype=np.uint8)
        segments_data = []
        contador_paredes = 1

        # 2. Procesamos la respuesta de la IA
        for item in hf_result:
            label = item.get("label", "").lower()
            
            # Solo nos interesan paredes o pisos
            if label in ["wall", "floor"]:
                # Decodificamos la máscara base64 que nos dio la IA
                mask_b64 = item.get("mask")
                mask_data = base64.b64decode(mask_b64)
                mask_img = Image.open(io.BytesIO(mask_data)).convert("L")
                
                # Redimensionamos la máscara al tamaño de la foto original por seguridad
                mask_resized = mask_img.resize((w, h), Image.NEAREST)
                mask_cv = np.array(mask_resized)
                
                # Pintamos el fondo para depuración (Opcional, se puede quitar)
                color = [0, 0, 255] if label == "floor" else np.random.randint(50, 200, size=3).tolist()
                final_img_rgb[mask_cv > 128] = color

                # Extraemos los contornos de esta máscara perfecta para buscar el Centro
                contours, _ = cv2.findContours(mask_cv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                for cnt in contours:
                    # Filtramos basuritas muy pequeñas
                    if cv2.contourArea(cnt) > (h * w) * 0.02:
                        M = cv2.moments(cnt)
                        if M["m00"] > 0:
                            cX = int(M["m10"] / M["m00"])
                            cY = int(M["m01"] / M["m00"])
                            
                            seg_id = "floor_1" if label == "floor" else f"wall_{contador_paredes}"
                            ui_label = "Piso" if label == "floor" else f"Pared {contador_paredes}"
                            
                            segments_data.append({
                                "id": seg_id,
                                "label": ui_label,
                                "type": label,
                                "x": cX,
                                "y": cY,
                                "color": color
                            })
                            
                            if label == "wall":
                                contador_paredes += 1

        # Seguro de vida por si la foto no tiene paredes claras
        if not segments_data:
            segments_data.append({
                "id": "wall_1", "label": "Pared 1", "type": "wall", 
                "x": w//2, "y": h//2, "color": [255, 0, 0]
            })

        return Image.fromarray(final_img_rgb), segments_data, w, h

    def get_binary_mask(self, image_bytes, surface_type="wall"):
        """
        ✂️ Genera la máscara blanco/negro perfecta para el motor de Inpainting.
        """
        hf_result = self._call_hf_api(image_bytes)
        
        # Leemos el tamaño original para devolver la máscara exacta
        image = Image.open(io.BytesIO(image_bytes))
        w, h = image.size
        
        # Creamos un lienzo negro por defecto
        final_mask = np.zeros((h, w), dtype=np.uint8)
        
        target_label = "floor" if surface_type == "floor" else "wall"
        
        for item in hf_result:
            if item.get("label", "").lower() == target_label:
                mask_data = base64.b64decode(item.get("mask"))
                mask_img = Image.open(io.BytesIO(mask_data)).convert("L")
                mask_resized = mask_img.resize((w, h), Image.NEAREST)
                mask_cv = np.array(mask_resized)
                
                # Combinamos (por si Hugging Face devuelve la pared dividida en dos objetos)
                final_mask = cv2.bitwise_or(final_mask, mask_cv)

        # Retornamos la máscara perfecta (donde > 128 es blanco 255)
        _, binary_ready = cv2.threshold(final_mask, 128, 255, cv2.THRESH_BINARY)
        
        return binary_ready