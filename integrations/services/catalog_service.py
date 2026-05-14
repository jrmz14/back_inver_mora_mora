import os
import requests
from requests.auth import HTTPBasicAuth

class CatalogService:
    def __init__(self):
        self.use_mock = os.getenv("USE_WC_MOCK", "True") == "True"
        self.wc_url = os.getenv("WC_URL") # Ejemplo: https://tusitio.com/wp-json/wc/v3
        self.ck = os.getenv("WC_CK")
        self.cs = os.getenv("WC_CS")

    def get_brands(self):
        if self.use_mock:
            return [{"id": 10, "name": "Mock"}]

        print(f"🚀 [Django] Consultando la tabla maestra de marcas (product_brand)...")
        try:
            # 💡 APUNTAMOS AL ENDPOINT DE LA TAXONOMÍA DIRECTAMENTE
            # Usamos /wp-json/wp/v2/product_brand que es el estándar de WP
            params = {
                'consumer_key': self.ck,
                'consumer_secret': self.cs,
                'per_page': 100,
                'hide_empty': False # 👈 Esto trae las marcas aunque no tengan productos aún
            }
            
            # Cambiamos la ruta de /wc/v3/products a /wp/v2/product_brand
            base_url = self.wc_url.split('/wp-json')[0]
            url = f"{base_url}/wp-json/wp/v2/product_brand"
            
            response = requests.get(url, params=params, verify=False)
            
            if response.status_code == 200:
                raw_brands = response.json()
                # WordPress devuelve 'id' y 'name' por defecto en las taxonomías
                brands_list = [{"id": b['id'], "name": b['name']} for b in raw_brands]
                
                print(f"✅ [Django] ¡Coronamos! Se encontraron las {len(brands_list)} marcas reales.")
                return brands_list
            else:
                # 💡 PLAN B: Si el endpoint de arriba falla, probamos con el de WC
                print(f"⚠️ [Django] Endpoint v2 falló, probando con ruta alternativa...")
                url_alt = f"{self.wc_url}/products/brands"
                response = requests.get(url_alt, params=params, verify=False)
                if response.status_code == 200:
                    return [{"id": b['id'], "name": b['name']} for b in response.json()]
                
                return []
        except Exception as e:
            print(f"💥 [Django] Excepción: {e}")
            return []

    def get_materials_by_brand(self, brand_id, category_id=None, page=None):
        print(f"🐍 [Django] Procesando materiales para Marca: {brand_id} | Categoría: {category_id} | Página: {page}")

        if self.use_mock:
            return self._get_mock_materials(brand_id)

        try:
            params = {
                'per_page': 100 if not page else 20, # 100 para traer todo rápido, 20 si usas scroll infinito
                'consumer_key': self.ck,
                'consumer_secret': self.cs,
                'status': 'publish'
            }
            
            # 💡 EL FRANCQTIRADOR: Filtramos en WooCommerce directo si nos pasas el ID
            if category_id:
                params['category'] = category_id

            all_raw_data = []
            
            # 💡 LA BIFURCACIÓN: ¿Traemos todo o solo una página?
            if page:
                # MODO SCROLL INFINITO: Solo traemos la página solicitada
                params['page'] = page
                print(f"🚀 [Django] Pidiendo solo la página {page} a WooCommerce...")
                response = requests.get(f"{self.wc_url}/products", params=params)
                
                if response.status_code == 200:
                    all_raw_data = response.json()
            else:
                # MODO CARGA RÁPIDA (CON FILTRO): Traemos todas las páginas, pero como está 
                # filtrado por categoría, serán poquitas y cargará en segundos.
                params['page'] = 1
                print(f"🚀 [Django] Descargando catálogo completo (optimizado)...")
                while True:
                    response = requests.get(f"{self.wc_url}/products", params=params)
                    if response.status_code == 200:
                        page_data = response.json()
                        if not page_data: break 
                        all_raw_data.extend(page_data)
                        
                        total_pages = int(response.headers.get('X-WP-TotalPages', 1))
                        if params['page'] >= total_pages: break 
                        params['page'] += 1 
                    else:
                        break

            # 💡 FILTRAMOS POR MARCA EN PYTHON
            if brand_id and str(brand_id) != 'all':
                filtered_data = [
                    p for p in all_raw_data 
                    if any(str(b.get('id', '')) == str(brand_id) for b in p.get('brands', []))
                ]
            else:
                filtered_data = all_raw_data
                
            return self._process_wc_products(filtered_data)
            
        except Exception as e:
            print(f"❌ [DJANGO] Error consultando materiales: {e}")
            return {"Pisos": [], "Pared": []}

    def _process_wc_products(self, products):
        """Lógica dinámica: usa las categorías reales de WooCommerce"""
        # 1. Ya no inicializamos con "Pisos" y "Pared", empezamos vacío 💡
        catalog = {}
        
        for p in products:
            try:
                # Extracción de imagen
                img_url = p['images'][0]['src'] if p.get('images') else "https://via.placeholder.com/600x400?text=Sin+Imagen"

                # Extracción de marca
                marca_nombre = "Genérica"
                brands = p.get('brands') or p.get('product_brand') or []
                if brands:
                    marca_nombre = brands[0]['name']

                # 💡 LA MAGIA: Extraer la categoría REAL de WooCommerce
                # Si el producto no tiene categoría, le ponemos "General"
                categorias_wc = p.get('categories', [])
                cat_name = categorias_wc[0]['name'] if categorias_wc else "General"

                # Empacamos el material
                material = {
                    "id": p['id'],
                    "name": p['name'],
                    "prompt": p.get('short_description', '').replace('<p>', '').replace('</p>', '').replace('\n', '').strip() or "modern surface texture",
                    "image_url": img_url,
                    "description": p.get('description', ''),
                    "price": p.get('price', '0.00'),
                    "unit": "m²",
                    "category": cat_name, #  Ahora lleva el nombre real (ej: "Baños")
                    "brand": marca_nombre
                }
                
                #  Agregamos al diccionario dinámicamente
                if cat_name not in catalog:
                    catalog[cat_name] = []
                
                catalog[cat_name].append(material)
                    
            except Exception as e:
                print(f"⏩ [Django] Error en producto {p.get('id')}: {e}")
                continue 
                
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