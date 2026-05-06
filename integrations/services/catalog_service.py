# integrations/catalog_service.py
import os
import requests
from requests.auth import HTTPBasicAuth

class CatalogService:
    def __init__(self):
        self.use_mock = os.getenv("USE_WC_MOCK", "True") == "True"
        self.wc_url = os.getenv("WC_URL")
        self.ck = os.getenv("WC_CK")
        self.cs = os.getenv("WC_CS")
        self.auth = HTTPBasicAuth(self.ck, self.cs) if self.ck and self.cs else None

    def get_brands(self):
        if self.use_mock:
            return [
                {"id": 10, "name": "Cerámica Italia"},
                {"id": 11, "name": "Corona"},
                {"id": 12, "name": "Mora Mora"},
                {"id": 13, "name": "Vencerámica"},
            ]
        
        try:
            url = f"{self.wc_url}/products/categories"
            response = requests.get(url, auth=self.auth, params={'hide_empty': False})
            if response.status_code == 200:
                return [{"id": c['id'], "name": c['name']} for c in response.json()]
            return []
        except Exception:
            return []

    def get_materials_by_brand(self, brand_id):
        # 🚩 LOG DE GUERRA
        print(f"🐍 [Django] Procesando materiales para ID: {brand_id}")

        if self.use_mock:
            return self._get_mock_materials(brand_id)

        try:
            # 1. Preparamos los parámetros dinámicos
            params = {'per_page': 50}
            
            # 💡 SI NO ES 'all', filtramos por categoría en WooCommerce
            if brand_id and brand_id != 'all':
                params['category'] = brand_id
                print(f"🎯 [Django] Filtrando API real por categoría: {brand_id}")

            response = requests.get(f"{self.wc_url}/products", auth=self.auth, params=params)
            
            if response.status_code == 200:
                return self._process_wc_products(response.json())
            return {"Pisos": [], "Pared": []}
        except Exception as e:
            print(f"❌ [DJANGO] Error: {e}")
            return {"Pisos": [], "Pared": []}

    def _process_wc_products(self, products):
        """Lógica de clasificación dinámica"""
        catalog = {"Pisos": [], "Pared": []}
        for p in products:
            material = {
                "id": p['id'],
                "name": p['name'],
                "prompt": p.get('short_description', '').replace('<p>', '').replace('</p>', '').strip() or "modern surface",
                "image_url": p['images'][0]['src'] if p['images'] else ""
            }
            
            # Clasificación por tags o nombre
            tags = [t['name'].lower() for t in p.get('tags', [])]
            name_lower = p['name'].lower()
            
            if any(x in tags for x in ["piso", "floor"]) or "piso" in name_lower:
                catalog["Pisos"].append(material)
            else:
                catalog["Pared"].append(material)
        return catalog

    def _get_mock_materials(self, brand_id):
        # 1. Definimos el catálogo maestro por ID de marca
        # Usamos strings porque los query_params de Django llegan como texto
        master_mock = {
            "10": { # Cerámica Italia
                "Pisos": [
                    {"id": 1001, "name": "Porcelanato Ámbar 60x60", "prompt": "polished amber porcelain floor", "image_url": "https://picsum.photos/seed/1001/600/400"},
                    {"id": 1002, "name": "Madera Nórdica Gris", "prompt": "grey scandinavian wood texture", "image_url": "https://picsum.photos/seed/1002/600/400"},
                    {"id": 1003, "name": "Piso Cemento Industrial", "prompt": "raw concrete floor finish", "image_url": "https://picsum.photos/seed/1003/600/400"},
                ],
                "Pared": [
                    {"id": 1004, "name": "Mosaico Hidráulico Azul", "prompt": "blue vintage hydraulic wall tiles", "image_url": "https://picsum.photos/seed/1004/600/400"},
                ]
            },
            "11": { # Corona
                "Pisos": [
                    {"id": 1101, "name": "Piso Mármol Carrara", "prompt": "white carrara marble floor", "image_url": "https://picsum.photos/seed/1101/600/400"},
                    {"id": 1102, "name": "Granito Clásico Sal y Pimienta", "prompt": "salt and pepper granite floor", "image_url": "https://picsum.photos/seed/1102/600/400"},
                ],
                "Pared": [
                    {"id": 1103, "name": "Azulejo Subway Blanco", "prompt": "glossy white subway wall tile", "image_url": "https://picsum.photos/seed/1103/600/400"},
                    {"id": 1104, "name": "Decorado Vintage Cocina", "prompt": "kitchen decorative wall tile floral", "image_url": "https://picsum.photos/seed/1104/600/400"},
                ]
            },
            "12": { # Mora Mora
                "Pisos": [
                    {"id": 1201, "name": "Piedra de Rio Natural", "prompt": "natural river stone floor texture", "image_url": "https://picsum.photos/seed/1201/600/400"},
                    {"id": 1202, "name": "Ladrillo Rústico Terracota", "prompt": "rustic terracotta brick floor", "image_url": "https://picsum.photos/seed/1202/600/400"},
                ],
                "Pared": [
                    {"id": 1203, "name": "Pared de Laja Negra", "prompt": "black slate stone wall", "image_url": "https://picsum.photos/seed/1203/600/400"},
                ]
            },
            "13": { # Vencerámica
                "Pisos": [
                    {"id": 1301, "name": "Porcelanato Negro Galaxia", "prompt": "black galaxy porcelain high gloss", "image_url": "https://picsum.photos/seed/1301/600/400"},
                ],
                "Pared": [
                    {"id": 1302, "name": "Revestimiento Travertino", "prompt": "travertine wall texture beige", "image_url": "https://picsum.photos/seed/1302/600/400"},
                    {"id": 1303, "name": "Cerámica Listelo Oro", "prompt": "gold accent wall tile border", "image_url": "https://picsum.photos/seed/1303/600/400"},
                ]
            }
        }

        # 2. Lógica de filtrado dinámico
        if brand_id == 'all':
            # Mezclamos todo para la opción "Todas"
            all_pisos = []
            all_pared = []
            for brand in master_mock.values():
                all_pisos.extend(brand["Pisos"])
                all_pared.extend(brand["Pared"])
            return {"Pisos": all_pisos, "Pared": all_pared}

        # 3. Devolvemos la marca específica o un mapa vacío si no existe
        return master_mock.get(str(brand_id), {"Pisos": [], "Pared": []})