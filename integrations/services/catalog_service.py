from catalog.models import Brand, Category, Material

class CatalogService:
    def __init__(self):
        # Ya no necesitamos variables de entorno de WooCommerce ni mocks
        # porque ahora somos dueños de nuestra propia base de datos 😎
        pass

    def get_brands(self):
        print("🚀 [Django] Consultando marcas desde la base de datos local...")
        try:
            # Traemos solo las marcas activas ordenadas alfabéticamente
            brands = Brand.objects.filter(is_active=True).order_by('name')
            
            # Formateamos la lista para que Flutter la entienda igual que antes, 
            # ¡pero ahora incluimos el logo de Supabase!
            brands_list = [
                {
                    "id": b.id, 
                    "name": b.name,
                    "logo_url": b.logo_url or ""
                } 
                for b in brands
            ]
            
            print(f"✅ [Django] Se encontraron {len(brands_list)} marcas reales.")
            return brands_list
        except Exception as e:
            print(f"💥 [Django] Excepción consultando marcas: {e}")
            return []

    def get_categories(self):
        # 💡 Endpoint extra por si Flutter necesita listar las categorías sueltas
        try:
            categories = Category.objects.filter(is_active=True).order_by('name')
            return [{"id": c.id, "name": c.name} for c in categories]
        except Exception as e:
            print(f"💥 [Django] Excepción consultando categorías: {e}")
            return []

    def get_materials_by_brand(self, brand_id, category_id=None, page=None):
        print(f"🐍 [Django] Procesando materiales | Marca: {brand_id} | Categoría: {category_id}")

        try:
            # 1. Base de la consulta: Solo materiales activos e incluimos las relaciones
            # para no saturar la base de datos con consultas repetidas (select_related)
            query = Material.objects.filter(is_active=True).select_related('brand', 'category')

            # 2. Filtramos por marca (Si dice 'all', trae todo)
            if brand_id and str(brand_id) != 'all':
                query = query.filter(brand_id=brand_id)

            # 3. Filtramos por categoría si Flutter la envía
            if category_id:
                query = query.filter(category_id=category_id)

            # 4. Agrupamos y formateamos exactamente como espera la App móvil
            catalog = {}
            
            for material in query:
                cat_name = material.category.name
                
                if cat_name not in catalog:
                    catalog[cat_name] = []
                    
                # 💡 Formato empacado para Flutter
                catalog[cat_name].append({
                    "id": material.id,
                    "name": material.name,
                    "prompt": material.description or f"Textura de {material.name}", # Usamos desc o nombre
                    "image_url": material.catalog_image_url or "https://via.placeholder.com/600x400?text=Sin+Imagen",
                    "texture_url": material.texture_image_url or "", # ¡Nuevo campo para la IA!
                    "description": material.description or "",
                    "price": str(material.price),
                    "unit": "m²",
                    "category": cat_name,
                    "brand": material.brand.name
                })

            return catalog

        except Exception as e:
            print(f"❌ [DJANGO] Error consultando materiales: {e}")
            return {}