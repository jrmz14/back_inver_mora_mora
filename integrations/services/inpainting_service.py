import os
import cv2
import numpy as np
import urllib.request
import requests
import base64
import io

class InpaintingService:
    def __init__(self):
        self.api_key = os.getenv("STABILITY_KEY")
        
        # 💡 EL MOTOR SAGRADO DE REFINADO (Img2Img con Máscara V1)
        # Usamos SDXL 1.0 para calidad máxima y refinado estricto
        engine_id = "stable-diffusion-xl-1024-v1-0"
        self.api_url = f"https://api.stability.ai/v1/generation/{engine_id}/image-to-image"

    def apply_rough_wallpaper(self, original_img_cv, binary_mask, material_url, tile_size=300):
        """
        PASO 1 (El Tractor): Arma el mosaico matemático tosco con EL MATERIAL REAL.
        Anti-alucinaciones.
        """
        try:
            # 💡 ASEGURAR QUE ESTAMOS USANDO EL MATERIAL REAL DEL CATÁLOGO
            # Si material_url viene de Flutter con tu foto de mosaico real, esto lo descargará.
            print(f"📥 Descargando textura real del catálogo: {material_url}")
            req = urllib.request.urlopen(material_url)
            arr = np.asarray(bytearray(req.read()), dtype=np.uint8)
            texture = cv2.imdecode(arr, cv2.IMREAD_COLOR)

            if texture is None:
                raise Exception("No se pudo decodificar la imagen del material real")

            # Redimensionamos la textura al tamaño del azulejo
            texture = cv2.resize(texture, (tile_size, tile_size))

            # Creamos el lienzo del tamaño de la foto original
            h_img, w_img, _ = original_img_cv.shape
            tiled_canvas = np.zeros((h_img, w_img, 3), dtype=np.uint8)

            # Llenamos el lienzo repitiendo la textura REAL (Tiling)
            for y in range(0, h_img, tile_size):
                for x in range(0, w_img, tile_size):
                    h_tile = min(tile_size, h_img - y)
                    w_tile = min(tile_size, w_img - x)
                    tiled_canvas[y:y+h_tile, x:x+w_tile] = texture[0:h_tile, 0:w_tile]

            # Operación de recorte con la máscara
            if len(binary_mask.shape) == 2:
                mask_3d = cv2.cvtColor(binary_mask, cv2.COLOR_GRAY2BGR)
            else:
                mask_3d = binary_mask

            # LA MEZCLA: Donde la máscara es blanca (255), ponemos EL MOSAICO REAL.
            rough_result = np.where(mask_3d == 255, tiled_canvas, original_img_cv)
            return rough_result

        except Exception as e:
            print(f"❌ Error en mosaico matemático crudo: {e}")
            return original_img_cv

    def apply_ai_refinement(self, rough_img_cv, binary_mask, material_name, room_type="room"):
        print(f"✨ Refinando con la técnica del 35% (IMAGE_STRENGTH)...")
        try:
            # 1. Ajuste de dimensiones para SDXL (768x1344 es el estándar para móviles vertical)
            target_size = (768, 1344)
            rough_resized = cv2.resize(rough_img_cv, target_size, interpolation=cv2.INTER_LANCZOS4)
            mask_resized = cv2.resize(binary_mask, target_size, interpolation=cv2.INTER_NEAREST)

            _, init_buffer = cv2.imencode('.png', rough_resized)
            _, mask_buffer = cv2.imencode('.png', mask_resized)

            prompt = f"Clean photography of {material_name} {room_type}, soft shadows, realistic lighting, architectural detail"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json"
            }

            files = {
                "init_image": init_buffer.tobytes(),
                #"mask_image": mask_buffer.tobytes(),
            }

            # 💡 BASADO EN TU CAPTURA DE LA DOCS:
            data = {
                "init_image_mode": "IMAGE_STRENGTH", # Cambiamos el modo
                "image_strength": "0.85",            # Usamos el valor mágico del 35%
                #"mask_source": "MASK_IMAGE_WHITE",
                "text_prompts[0][text]": prompt,
                "text_prompts[0][weight]": "1",
                "cfg_scale": "7",
                "samples": "1",
                "steps": "30",
                "style_preset": "photographic"
            }

            response = requests.post(self.api_url, headers=headers, files=files, data=data)

            if response.status_code == 200:
                res_json = response.json()
                img_b64 = res_json["artifacts"][0]["base64"]
                img_bytes = base64.b64decode(img_b64)
                
                np_arr = np.frombuffer(img_bytes, np.uint8)
                ai_result_cv = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

                # Re-escalamos de vuelta a la resolución original
                h_orig, w_orig = rough_img_cv.shape[:2]
                final_output = cv2.resize(ai_result_cv, (w_orig, h_orig), interpolation=cv2.INTER_LANCZOS4)
                
                return final_output
            else:
                print(f"⚠️ Error de IA (siguiendo la docs): {response.text}")
                return None

        except Exception as e:
            print(f"❌ Excepción en el refinador: {e}")
            return None