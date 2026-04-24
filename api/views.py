from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from integrations.services import AIService
import uuid

class ProcessImageView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
       
        image_obj = request.FILES.get('image')
        
        # --- EL ARREGLO: Buscamos las llaves exactas que manda Flutter ---
        # Si no las manda, ponemos valores por defecto en INGLÉS para la IA
        room_type = request.data.get('tipo', 'bathroom') 
        material_piso = request.data.get('piso', 'modern tiles')
        material_pared = request.data.get('pared', 'white marble')

        if not image_obj:
            return Response({"error": "No se envió ninguna imagen"}, status=400)

        service = AIService()
        
        try:
            # Generar nombre único
            ext = image_obj.name.split('.')[-1]
            file_name = f"{uuid.uuid4()}.{ext}"
            
            # Subir a Supabase
            image_url = service.upload_to_supabase(image_obj.read(), file_name)
            
            # Armamos el diccionario que el nuevo servicio espera
            room_data = {
                'tipo': room_type,
                'piso': material_piso,
                'pared': material_pared
            }
            
            print(f"Enviando al motor IA -> Cuarto: {room_type} | Piso: {material_piso} | Pared: {material_pared}")
            
            # Llamamos al método
            result_url = service.run_remodelacion_logica(image_url, room_data)
            
            return Response({
                "status": "success",
                "original_url": image_url,
                "processed_url": result_url
            })
            
        except Exception as e:
            # Imprime el error real en tu terminal para que lo veas clarito
            print(f"❌ Error detectado en la vista: {str(e)}")
            return Response({"status": "error", "message": str(e)}, status=500)