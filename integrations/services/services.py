import os
import requests
import io
import random
import base64
from PIL import Image
from supabase import create_client
from django.conf import settings

class AIService:
    def __init__(self):
        print("--- 🕵️‍♂️ INICIANDO SERVICIO IA Y SUPABASE ---")
        
        # 1. Variables Crudas
        raw_url = getattr(settings, "SUPABASE_URL", os.getenv("SUPABASE_URL"))
        raw_key = getattr(settings, "SUPABASE_KEY", os.getenv("SUPABASE_KEY"))
        
        # 2. Variable Cruda del Bucket (Con valor por defecto)
        raw_bucket = getattr(settings, "SUPABASE_BUCKET_NAME", os.getenv("SUPABASE_BUCKET_NAME", "catalog-assets"))
        
        if not raw_url or not raw_key:
            raise ValueError("🚨 ERROR FATAL: Faltan credenciales de Supabase.")
            
        # 3. La aspiradora
        self.supabase_url = str(raw_url).strip().replace('"', '').replace("'", "")
        self.supabase_key = str(raw_key).strip().replace('"', '').replace("'", "")
        self.bucket_name = str(raw_bucket).strip().replace('"', '').replace("'", "")
        
        # 4. Conexión a Supabase
        self.supabase = create_client(self.supabase_url, self.supabase_key)
        
        # 5. Configuración de Stability AI
        raw_stability = getattr(settings, "STABILITY_KEY", os.getenv("STABILITY_KEY"))
        self.stability_key = str(raw_stability).strip().replace('"', '').replace("'", "") if raw_stability else None
        self.api_host = "https://api.stability.ai"
        self.engine_id = "stable-diffusion-xl-1024-v1-0"
        
        print(f"✅ SERVICIO INICIALIZADO. Bucket: {self.bucket_name}")

    def upload_to_supabase(self, file_data, file_name, bucket_name="remodelaciones"):
        """
        Sube archivos de forma inteligente. Si no le pasas el bucket, 
        asume que es una foto de la app ('remodelaciones').
        """
        if not hasattr(self, 'supabase'):
            raise Exception("🚨 El cliente de Supabase no se pudo inicializar.")
            
        try:
            # Detecta si es PNG o JPEG
            content_type = "image/png" if file_name.lower().endswith(".png") else "image/jpeg"

            self.supabase.storage.from_(bucket_name).upload(
                path=file_name,
                file=file_data,
                file_options={"content-type": content_type}
            )
            return self.supabase.storage.from_(bucket_name).get_public_url(file_name)
            
        except Exception as e:
            print(f"❌ Error en Supabase al subir {file_name} al bucket '{bucket_name}': {e}")
            raise e
        
    def run_remodelacion_logica(self, imagen_url, mask_bytes, room_data):
        try:
            print(f"--- PASO 3: Remodelando con INPAINTING (Máscara de Precisión) ---")
            
            # 1. Bajamos la foto original de Supabase
            response_img = requests.get(imagen_url)
            if response_img.status_code != 200:
                raise Exception("No pude bajar la foto original")

            # 2. Redimensionamos AMBAS imágenes (Original y Máscara)
            img = Image.open(io.BytesIO(response_img.content))
            img_resized = img.resize((768, 1344), Image.LANCZOS)
            
            buffer_img = io.BytesIO()
            img_resized.save(buffer_img, format="PNG") 
            img_final_bytes = buffer_img.getvalue()

            mask_img = Image.open(io.BytesIO(mask_bytes)).convert("L") 
            mask_resized = mask_img.resize((768, 1344), Image.NEAREST) 
            
            buffer_mask = io.BytesIO()
            mask_resized.save(buffer_mask, format="PNG")
            mask_final_bytes = buffer_mask.getvalue()

            # 3. Llamada a Stability AI
            if not self.stability_key:
                raise Exception("Falta la API Key de Stability AI")

            response = requests.post(
                f"{self.api_host}/v1/generation/{self.engine_id}/image-to-image/masking",
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.stability_key}"
                },
                files={
                    "init_image": img_final_bytes,
                    "mask_image": mask_final_bytes 
                },
                data={
                    "mask_source": "MASK_IMAGE_WHITE", 
                    "text_prompts[0][text]": f"Highly detailed {room_data.get('material', 'texture')} applied to the surface, photorealistic, correct perspective, soft architectural lighting",
                    "text_prompts[0][weight]": 1,
                    "text_prompts[1][text]": "bad perspective, deformed, repeating pattern poorly, artifacts",
                    "text_prompts[1][weight]": -1,
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

            # 4. Guardar resultado usando el método unificado
            output_name = f"render_inpaint_{os.urandom(4).hex()}.png"
            return self.upload_to_supabase(image_bytes, output_name)

        except Exception as e:
            print(f"❌ FALLÓ MOTOR STABILITY: {e}")
            seed = random.randint(1, 1000000)
            prompt_p = f"luxury room with {room_data.get('material', 'new')} surface"
            return f"https://image.pollinations.ai/prompt/{prompt_p.replace(' ', '%20')}?seed={seed}"
        
    @staticmethod
    def blend_material_before_ai(original_img_bytes, mask_bytes, material_url):
        resp = requests.get(material_url)
        material_tile = Image.open(io.BytesIO(resp.content))
        
        full_texture = Image.new('RGB', (768, 1344))
        for x in range(0, 768, material_tile.width):
            for y in range(0, 1344, material_tile.height):
                full_texture.paste(material_tile, (x, y))
                
        original = Image.open(io.BytesIO(original_img_bytes))
        mask = Image.open(io.BytesIO(mask_bytes)).convert("L")
        
        blended_img = Image.composite(full_texture, original, mask)
        return blended_img