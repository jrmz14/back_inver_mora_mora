import cv2
import numpy as np
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from integrations.services.services import AIService
from integrations.services.catalog_service import CatalogService
from integrations.services.segmentation_service import SemanticSegmentationService # El cerebro de IA
import uuid
import io

from integrations.services.inpainting_service import InpaintingService

class SegmentImageView(APIView):
    """
    PASO 1: Recibe la foto, la segmenta y devuelve los links 
    de la original y el mapa de colores.
    """
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        image_obj = request.FILES.get('image')
        if not image_obj:
            return Response({"error": "No se envió ninguna imagen"}, status=400)

        ai_service = AIService()
        seg_service = SemanticSegmentationService()

        try:
            image_bytes = image_obj.read()
            ext = image_obj.name.split('.')[-1]
            original_name = f"orig_{uuid.uuid4()}.{ext}"
            original_url = ai_service.upload_to_supabase(image_bytes, original_name)

            # --- AQUI RECIBIMOS LA MAGIA ---
            map_image, segments_data, img_w, img_h = seg_service.generate_advanced_map(image_bytes)
            
            # Guardamos la máscara por debajo de cuerda en Supabase 
            # (Porque la vamos a usar en el Backend para el recorte final)
            buffer = io.BytesIO()
            map_image.save(buffer, format="PNG")
            map_url = ai_service.upload_to_supabase(buffer.getvalue(), f"map_{uuid.uuid4()}.png")

            # Le respondemos a Flutter con TODO lo que necesita para dibujar
            return Response({
                "status": "success",
                "original_url": original_url,
                "map_url": map_url,
                "image_size": {
                    "width": img_w,
                    "height": img_h
                },
                "segments": segments_data, # <--- La lista de los botoncitos X, Y
                "message": "Espacio analizado con éxito."
            })

        except Exception as e:
            print(f"❌ Error en Segmentación: {str(e)}")
            return Response({"status": "error", "message": str(e)}, status=500)

class ProcessImageView(APIView):
    """
    PASO 2: Recibe la URL de la original, el material y el tipo de superficie 
    para aplicar el empapelado tosco (y próximamente el inpainting final).
    """
    def post(self, request):
        # NOTA: Asegúrate de que Flutter esté mandando 'original_url' y no 'image_url' 
        # según lo que respondimos en el Paso 1.
        image_url = request.data.get('original_url') or request.data.get('image_url')
        material_url = request.data.get('material_url')
        room_type = request.data.get('tipo', 'wall') # 'wall' o 'floor'

        if not image_url or not material_url:
            return Response({"error": "Faltan datos para la remodelación"}, status=400)

        seg_service = SemanticSegmentationService()
        inpaint_service = InpaintingService()
        ai_service = AIService()

        try:
            # 1. Descargar la foto original desde Supabase directamente a la memoria
            print(f"📥 Descargando original de: {image_url}")
            resp = requests.get(image_url)
            image_bytes = resp.content

            # Convertir esos bytes al formato de matrices que usa OpenCV (BGR)
            img_array = np.asarray(bytearray(image_bytes), dtype=np.uint8)
            original_img_cv = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

            # 2. Obtener la máscara binaria exacta (blanco y negro)
            # Como tu modelo local B0 vuela, la generamos on-the-fly para la superficie exacta
            print(f"🧠 Aislado máscara para: {room_type}")
            binary_mask = seg_service.get_binary_mask(image_bytes, room_type)

            # 3. EL PINTOR: Aplicar el Papel Tapiz Tosco
            print("🎨 Aplicando empapelado con la textura del catálogo...")
            rough_img_cv = inpaint_service.apply_rough_wallpaper(
                original_img_cv=original_img_cv, 
                binary_mask=binary_mask, 
                material_url=material_url, 
                tile_size=250 # Ajusta este número si quieres que los azulejos se vean más grandes o pequeños
            )

            # 4. (FUTURO PASO 3) 
            # final_img_cv = inpaint_service.generate_final_render(rough_img_cv, binary_mask, "prompt")

            # Por ahora (MVP), convertimos la imagen tosca de vuelta a bytes para subirla
            _, buffer = cv2.imencode('.jpg', rough_img_cv)
            rough_bytes = buffer.tobytes()
            
            result_name = f"rough_{uuid.uuid4()}.jpg"
            result_url = ai_service.upload_to_supabase(rough_bytes, result_name)

            return Response({
                "status": "success",
                "processed_url": result_url # Flutter mostrará la versión empapelada
            })

        except Exception as e:
            print(f"❌ Error en ProcessImage: {str(e)}")
            return Response({"status": "error", "message": str(e)}, status=500)

# Las vistas de catálogo se mantienen igual, son tu "menú" de materiales
class BrandListView(APIView):
    def get(self, request):
        service = CatalogService()
        return Response(service.get_brands())

class MaterialsByBrandView(APIView):
    def get(self, request):
        brand_id = request.query_params.get('brand_id')
        service = CatalogService()
        return Response(service.get_materials_by_brand(brand_id))