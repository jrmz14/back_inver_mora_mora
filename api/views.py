from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from integrations.services import AIService
import uuid

class ProcessImageView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        image_obj = request.FILES.get('image')
        
        # 1. Recibimos los datos del front (Flutter)
        # Si el compa de Flutter aún no manda 'room_type', ponemos 'bathroom' por defecto
        room_type = request.data.get('room_type', 'bathroom')
        material_piso = request.data.get('material_piso', 'modern tiles')
        material_pared = request.data.get('material_pared', 'white marble')

        if not image_obj:
            return Response({"error": "No se envió ninguna imagen"}, status=400)

        service = AIService()
        
        try:
            # Generar nombre único
            ext = image_obj.name.split('.')[-1]
            file_name = f"{uuid.uuid4()}.{ext}"
            
            # Subir a Supabase
            image_url = service.upload_to_supabase(image_obj.read(), file_name)
            
            # --- LA MACOYA ESTÁ AQUÍ ---
            # Armamos el diccionario que el nuevo servicio espera
            room_data = {
                'tipo': room_type,
                'piso': material_piso,
                'pared': material_pared
            }
            
            # Llamamos al método con el NOMBRE CORRECTO que pusimos en services.py
            # Si en tu services.py le dejaste 'run_replicate_logic', cámbialo aquí también.
            result_url = service.run_remodelacion_logica(image_url, room_data)
            
            return Response({
                "status": "success",
                "original_url": image_url,
                "processed_url": result_url
            })
            
        except Exception as e:
            # Imprime el error real en tu terminal para que lo veas clarito
            print(f"Error detectado: {str(e)}")
            return Response({"status": "error", "message": str(e)}, status=500)