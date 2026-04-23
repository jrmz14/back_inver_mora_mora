import os
import requests
import io
from PIL import Image
from supabase import create_client
from huggingface_hub import InferenceClient

class AIService:
    def __init__(self):
        # 1. Configuración de Supabase
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        self.bucket_name = os.getenv("SUPABASE_BUCKET_NAME", "remodelaciones")
        
        # --- LA LÍNEA QUE FALTABA: Sin esto el motor no arranca ---
        self.supabase = create_client(self.supabase_url, self.supabase_key)
        # ---------------------------------------------------------

        # Configuración de respaldo por si acaso (Hugging Face)
        self.hf_client = InferenceClient(api_key=os.getenv("HF_TOKEN"))

    def upload_to_supabase(self, file_data, file_name):
        """Sube la imagen y devuelve la URL pública"""
        try:
            # Ahora self.supabase ya existe, así que esto no fallará
            self.supabase.storage.from_(self.bucket_name).upload(
                path=file_name,
                file=file_data,
                file_options={"content-type": "image/jpeg"}
            )
            url_data = self.supabase.storage.from_(self.bucket_name).get_public_url(file_name)
            return url_data
        except Exception as e:
            print(f"Error en Supabase: {e}")
            raise e

    def run_remodelacion_logica(self, imagen_url, room_data):
        try:
            print(f"--- PASO 3: Remodelando {room_data['tipo']} con SD v1.5 ---")
            
            # 1. Bajamos la foto de Supabase
            response = requests.get(imagen_url)
            if response.status_code != 200:
                raise Exception("No pude bajar la foto de Supabase")
            
            # Convertimos los bytes a un objeto que la IA entienda
            original_img_bytes = response.content

            # 2. El Super Prompt Dinámico
            prompt = (f"A professional interior design of a {room_data['tipo']}, "
                    f"with {room_data['piso']} flooring and {room_data['pared']} walls, "
                    f"highly detailed, realistic, 8k, architectural lighting")

            # 3. Llamada a Hugging Face forzando un modelo compatible
            # Usamos runwayml/stable-diffusion-v1-5 que es el papá del Image-to-Image
            processed_image = self.hf_client.image_to_image(
                image=original_img_bytes,
                prompt=prompt,
                model="runwayml/stable-diffusion-v1-5", 
                strength=0.5, # 0.5 es el equilibrio perfecto para no deformar
                guidance_scale=7.5
            )

            # 4. Guardar el resultado (Este bloque ya lo tienes fino)
            output_name = f"render_{os.urandom(4).hex()}.png"
            img_byte_arr = io.BytesIO()
            processed_image.save(img_byte_arr, format='PNG')
            
            self.supabase.storage.from_(self.bucket_name).upload(
                path=output_name,
                file=img_byte_arr.getvalue(),
                file_options={"content-type": "image/png"}
            )
            
            return self.supabase.storage.from_(self.bucket_name).get_public_url(output_name)

        except Exception as e:
            print(f"--- FALLÓ HF, USANDO POLLINATIONS DE RESPALDO ---")
            print(f"Error real: {e}")
            # El fiel Pollinations que nunca nos deja morir
            prompt_p = f"luxury {room_data['tipo']} with {room_data['piso']} floor and {room_data['pared']} walls, realistic 8k"
            return f"https://image.pollinations.ai/prompt/{prompt_p.replace(' ', '%20')}"