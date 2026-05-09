from integrations.services.segmentation_service import SemanticSegmentationService

print("Cargando el cerebro de IA...")
service = SemanticSegmentationService()

print("Analizando la foto...")
# Pon aquí el nombre de una foto que tengas guardada
resultado = service.generate_advanced_map("mifoto.jpg")

print("¡Listo! Guardando el mapa de colores...")
resultado.save("mapa_resultado.jpg")