import os
import requests
import io
import random
import base64
from PIL import Image
from supabase import create_client

class AIService:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.bucket_name = os.getenv("SUPABASE_BUCKET_NAME", "remodelaciones")
        self.supabase = create_client(self.supabase_url, self.supabase_key)
        
        self.stability_key = os.getenv("STABILITY_KEY")
        self.api_host = "https://api.stability.ai"
        self.engine_id = "stable-diffusion-xl-1024-v1-0"

    def upload_to_supabase(self, file_data, file_name):
        try:
            self.supabase.storage.from_(self.bucket_name).upload(
                path=file_name,
                file=file_data,
                file_options={"content-type": "image/jpeg"}
            )
            return self.supabase.storage.from_(self.bucket_name).get_public_url(file_name)
        except Exception as e:
            print(f"Error en Supabase: {e}")
            raise e

    def run_remodelacion_logica(self, imagen_url, room_data):
        try:
            print(f"--- PASO 3: Remodelando con Redimensionamiento ---")
            
            # 1. Bajamos la foto de Supabase
            response_img = requests.get(imagen_url)
            if response_img.status_code != 200:
                raise Exception("No pude bajar la foto original")

            # --- AQUÍ ESTÁ EL ARREGLO: EL SASTRE ---
            # Abrimos la imagen con Pillow
            img = Image.open(io.BytesIO(response_img.content))
            
            # La forzamos a una medida que SDXL entienda (768x1344 es vertical pro)
            # Usamos LANCZOS para que no pierda nitidez al cambiar de tamaño
            img_resized = img.resize((768, 1344), Image.LANCZOS)
            
            # La volvemos a convertir a bytes para mandarla por la API
            buffer = io.BytesIO()
            img_resized.save(buffer, format="JPEG", quality=95)
            img_final_bytes = buffer.getvalue()
            # ---------------------------------------

            # 2. Llamada a Stability con la imagen ya "entallada"
            response = requests.post(
                f"{self.api_host}/v1/generation/{self.engine_id}/image-to-image",
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.stability_key}"
                },
                files={
                    "init_image": img_final_bytes # Mandamos los bytes redimensionados
                },
                data={
                    "image_strength": 0.40,  # Bájalo de 0.45 a 0.40 para que respete más la foto original
                    "init_image_mode": "IMAGE_STRENGTH",
                    "text_prompts[0][text]": f"Professional interior design of a {room_data['tipo']}, with {room_data['piso']} floors and {room_data['pared']} walls, high quality, photorealistic, architectural lighting",
                    "text_prompts[0][weight]": 1,
                    
                    # --- EL REGAÑO A LA IA (PROMPT NEGATIVO) ---
                    "text_prompts[1][text]": "adding furniture, changing layout, adding objects, new items, modifying room structure, artifacts",
                    "text_prompts[1][weight]": -1, # El -1 significa "NO HAGAS ESTO"
                    # -------------------------------------------
                    
                    "cfg_scale": 7,
                    "samples": 1,
                    "steps": 30,
                }
            )

            if response.status_code != 200:
                raise Exception(f"Error de Stability: {response.text}")

            data = response.json()
            image_base64 = data["artifacts"][0]["base64"]
            image_bytes = base64.b64decode(image_base64)

            # 3. Guardar en Supabase
            output_name = f"render_{os.urandom(4).hex()}.png"
            self.supabase.storage.from_(self.bucket_name).upload(
                path=output_name,
                file=image_bytes,
                file_options={"content-type": "image/png"}
            )
            
            return self.supabase.storage.from_(self.bucket_name).get_public_url(output_name)

        except Exception as e:
            print(f"❌ FALLÓ MOTOR: {e}")
            seed = random.randint(1, 1000000)
            prompt_p = f"luxury {room_data['tipo']} with {room_data['piso']} floor and {room_data['pared']} walls"
            return f"https://image.pollinations.ai/prompt/{prompt_p.replace(' ', '%20')}?seed={seed}"