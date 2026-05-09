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
        # Mantenemos el modelo pro
        self.engine_id = "stable-diffusion-xl-1024-v1-0"

    def upload_to_supabase(self, file_data, file_name):
        try:
            # 💡 EL FIX: Leemos el final del nombre para saber qué etiqueta ponerle
            # Si termina en .png, le decimos a Supabase que es un PNG puro. Si no, va como JPEG.
            content_type = "image/png" if file_name.lower().endswith(".png") else "image/jpeg"

            self.supabase.storage.from_(self.bucket_name).upload(
                path=file_name,
                file=file_data,
                file_options={"content-type": content_type} # 👈 Ahora es dinámico
            )
            return self.supabase.storage.from_(self.bucket_name).get_public_url(file_name)
            
        except Exception as e:
            print(f"❌ Error en Supabase: {e}")
            raise e
        
    # AÑADIMOS EL PARÁMETRO mask_bytes
    def run_remodelacion_logica(self, imagen_url, mask_bytes, room_data):
        try:
            print(f"--- PASO 3: Remodelando con INPAINTING (Máscara de Precisión) ---")
            
            # 1. Bajamos la foto original de Supabase
            response_img = requests.get(imagen_url)
            if response_img.status_code != 200:
                raise Exception("No pude bajar la foto original")

            # 2. Redimensionamos AMBAS imágenes (Original y Máscara) exactamente igual
            img = Image.open(io.BytesIO(response_img.content))
            img_resized = img.resize((768, 1344), Image.LANCZOS)
            
            buffer_img = io.BytesIO()
            img_resized.save(buffer_img, format="PNG") # Stability prefiere PNG para inpainting
            img_final_bytes = buffer_img.getvalue()

            mask_img = Image.open(io.BytesIO(mask_bytes)).convert("L") # "L" asegura que sea Blanco y Negro
            mask_resized = mask_img.resize((768, 1344), Image.NEAREST) # NEAREST para no difuminar los bordes duros
            
            buffer_mask = io.BytesIO()
            mask_resized.save(buffer_mask, format="PNG")
            mask_final_bytes = buffer_mask.getvalue()

            # 3. Llamada a Stability usando el endpoint de MASKING
            # NOTA EL CAMBIO EN LA URL
            response = requests.post(
                f"{self.api_host}/v1/generation/{self.engine_id}/image-to-image/masking",
                headers={
                    "Accept": "application/json",
                    "Authorization": f"Bearer {self.stability_key}"
                },
                files={
                    "init_image": img_final_bytes,
                    "mask_image": mask_final_bytes # Mandamos nuestra máscara sagrada
                },
                data={
                    "mask_source": "MASK_IMAGE_WHITE", # Le decimos que pinte donde la máscara es BLANCA
                    "text_prompts[0][text]": f"Highly detailed {room_data['material']} texture applied to the surface, photorealistic, correct perspective, soft architectural lighting",
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

            # 4. Guardar resultado en Supabase
            output_name = f"render_inpaint_{os.urandom(4).hex()}.png"
            self.supabase.storage.from_(self.bucket_name).upload(
                path=output_name,
                file=image_bytes,
                file_options={"content-type": "image/png"}
            )
            
            return self.supabase.storage.from_(self.bucket_name).get_public_url(output_name)

        except Exception as e:
            print(f"❌ FALLÓ MOTOR STABILITY: {e}")
            # Mantenemos tu rescate con Pollinations por si acaso
            seed = random.randint(1, 1000000)
            prompt_p = f"luxury room with {room_data.get('material', 'new')} surface"
            return f"https://image.pollinations.ai/prompt/{prompt_p.replace(' ', '%20')}?seed={seed}"
        
    def blend_material_before_ai(original_img_bytes, mask_bytes, material_url):
        # 1. Bajamos el material de VTEX
        resp = requests.get(material_url)
        material_tile = Image.open(io.BytesIO(resp.content))
        
        # 2. Creamos una imagen del tamaño de la original llena con el material repetido
        # (Esto es como poner el papel tapiz antes de tomar la foto)
        full_texture = Image.new('RGB', (768, 1344))
        for x in range(0, 768, material_tile.width):
            for y in range(0, 1344, material_tile.height):
                full_texture.paste(material_tile, (x, y))
                
        # 3. Usamos la máscara para pegar el material solo en la pared
        original = Image.open(io.BytesIO(original_img_bytes))
        mask = Image.open(io.BytesIO(mask_bytes)).convert("L")
        
        # Esta es la magia: combina la original con la textura usando la máscara como pegamento
        blended_img = Image.composite(full_texture, original, mask)
        
        return blended_img # Esta es la que le mandamos a Stability