# integrations/catalog_service.py
import os
import requests

class CatalogService:
    def __init__(self):
        # Switch para desarrollo/producción
        self.use_mock = os.getenv("USE_WC_MOCK", "True") == "True"

    def get_brands(self):
        if self.use_mock:
            return [
                {
                    "id": 1, 
                    "nombre": "Cerámica Italia", 
                    "slug": "ceramica-italia", 
                    "conteo": 24,
                    "logo": "https://ceramicaitalia.com/wp-content/uploads/2021/05/logo-ceramica-italia.png",
                    "imagen_banner": "https://ceramicaitalia.vtexassets.com/arquivos/ids/166675-1200-auto?v=638363403328500000&width=1200&height=auto&aspect=true",
                    "descripcion": "Líderes en porcelanatos y revestimientos con tecnología digital."
                },
                {
                    "id": 2, 
                    "nombre": "Corona", 
                    "slug": "corona", 
                    "conteo": 18,
                    "logo": "https://corona.co/medias/logo-corona.png?context=bWFzdGVyfHJvb3R8MzM0NnxpbWFnZS9wbmd8aGNlL2g0Ny84OTk1ODk0MjY1ODg2LnBuZ3wzMGRkOGU2Zjc1YjA5YzQ4ZjE1ZTRmZjUwMzgxZDMwNDQxZDg1ZmZiYmZjNGQyOTZlODVlYmU0YzEwYjA0YTI0",
                    "imagen_banner": "https://corona.co/medias/inspiracion-cocina-moderna.jpg?context=bWFzdGVyfHJvb3R8MTM0MjE2fGltYWdlL2pwZWd8aDUyL2hmMC85MDIxNDU1NTI3OTY2LmpwZ3w1OWRkOTFkZjkxYzQ4NDY5NmYwYmExZWU0ZGNmMTNlZDM1ZGEzZDIwNjg4ZDUxY2M5ZDIyYjE1ZDE1ZDI5YzE2",
                    "descripcion": "Innovación y calidad para transformar tus espacios."
                },
                {
                    "id": 3, 
                    "nombre": "Mora Mora Exclusive", 
                    "slug": "mora-mora-exclusive", 
                    "conteo": 10,
                    "logo": "https://placehold.co/400x400/1a1a1a/ffffff?text=MM",
                    "imagen_banner": "https://images.unsplash.com/photo-1618221195710-dd6b41faaea6?q=80&w=1200",
                    "descripcion": "Selección premium de mármoles y piedras naturales."
                }
            ]
        return []

    def get_materials_by_brand(self, brand_id):
        if self.use_mock:
            # Aquí usamos los links directos de VTEX y Corona Assets
            return [
                {
                    "id": 201,
                    "nombre": "Mármol Statuario Calacatta",
                    "formato": "60x120 cm",
                    "precio": "34.90",
                    "moneda": "USD",
                    "imagen": "https://ceramicaitalia.vtexassets.com/arquivos/ids/167277-1200-auto?v=638941695460670000&width=1200&height=auto&aspect=true",
                    "slug": "calacatta-white-marble",
                    "tags": ["brillante", "lujo", "pared"],
                    "descripcion": "Base blanca pura con vetas grises profundas. El clásico del lujo italiano."
                },
                {
                    "id": 202,
                    "nombre": "Madera Amazonas Canelo",
                    "formato": "20x120 cm",
                    "precio": "28.50",
                    "moneda": "USD",
                    "imagen": "https://ceramicaitalia.vtexassets.com/arquivos/ids/167274-1200-auto?v=638941693890830000&width=1200&height=auto&aspect=true",
                    "slug": "canelo-wood-plank",
                    "tags": ["mate", "textura", "piso"],
                    "descripcion": "Réplica exacta de madera natural con relieve al tacto."
                },
                {
                    "id": 203,
                    "nombre": "Pizarra Negra Ardesia",
                    "formato": "60x60 cm",
                    "precio": "22.00",
                    "moneda": "USD",
                    "imagen": "https://ceramicaitalia.vtexassets.com/arquivos/ids/166680-1200-auto?v=638363421558200000&width=1200&height=auto&aspect=true",
                    "slug": "black-slate-stone",
                    "tags": ["mate", "exterior", "antideslizante"],
                    "descripcion": "Piedra tecnológica de alta resistencia en tonos grafito oscuro."
                },
                {
                    "id": 204,
                    "nombre": "Hidráulico Provenza Azul",
                    "formato": "33x33 cm",
                    "precio": "19.80",
                    "moneda": "USD",
                    "imagen": "https://ceramicaitalia.vtexassets.com/arquivos/ids/156320-1200-auto?v=637205161474270000&width=1200&height=auto&aspect=true",
                    "slug": "blue-provenza-tile",
                    "tags": ["decorado", "vintage", "cocina"],
                    "descripcion": "Patrones tradicionales inspirados en la arquitectura europea."
                }
            ]
        return []