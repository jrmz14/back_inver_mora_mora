import os
import uuid
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from integrations.services.services import AIService 

BUCKET_NAME = 'catalog-assets' 

def get_supabase_client():
    """🛡️ INICIALIZACIÓN PEREZOSA: Conecta a Supabase solo cuando se va a usar,
    evitando tronar el servidor en el arranque de Render."""
    try:
        return AIService().supabase if hasattr(AIService(), 'supabase') else None
    except Exception as e:
        print(f"⚠️ No se pudo inicializar Supabase en este momento: {e}")
        return None

def upload_to_supabase(file, folder_name):
    """Sube el archivo a una carpeta específica dentro del nuevo bucket 'catalog-assets'"""
    supabase_client = get_supabase_client() # Llamada segura en demanda
    
    if not supabase_client or not file:
        print("⚠️ Subida cancelada: El cliente de Supabase no está listo o falta el archivo.")
        return ""
    
    ext = file.name.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    supabase_path = f"{folder_name}/{filename}"
    
    try:
        file_bytes = file.read()
        # Sube directo al nuevo bucket dedicado
        supabase_client.storage.from_(BUCKET_NAME).upload(supabase_path, file_bytes)
        public_url = supabase_client.storage.from_(BUCKET_NAME).get_public_url(supabase_path)
        return public_url
    except Exception as e:
        print(f"❌ Error subiendo a Supabase en {folder_name}: {e}")
        return ""

def delete_from_supabase(url):
    """Borra el archivo viejo del nuevo bucket 'catalog-assets'"""
    supabase_client = get_supabase_client() # Llamada segura en demanda
    
    if not supabase_client or not url:
        return
    try:
        parts = url.split(f"{BUCKET_NAME}/")
        if len(parts) > 1:
            supabase_path = parts[1]
            supabase_client.storage.from_(BUCKET_NAME).remove([supabase_path])
    except Exception as e:
        print(f"❌ Error borrando de Supabase: {e}")


# =====================================================================
# MODELOS (Tu estructura original intacta para el APK)
# =====================================================================

class Brand(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nombre de la Marca")
    logo_url = models.URLField(max_length=500, verbose_name="URL del Logo", blank=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name="Activa")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Marca"
        verbose_name_plural = "Marcas"


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="Nombre de la Categoría")
    is_active = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['name']

    def __str__(self):
        return self.name


class Material(models.Model):
    name = models.CharField(max_length=150, verbose_name="Nombre del Material")
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='materials', verbose_name="Marca")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='materials', verbose_name="Categoría")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio por m²")
    catalog_image_url = models.URLField(max_length=500, blank=True, null=True)
    texture_image_url = models.URLField(max_length=500, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.brand.name})"

    class Meta:
        verbose_name = "Material"
        verbose_name_plural = "Materiales"
        ordering = ['-created_at']


# =====================================================================
# SIGNALS PARA ELIMINACIÓN AUTOMÁTICA EN SUPABASE
# =====================================================================

@receiver(post_delete, sender=Brand)
def delete_brand_logo_supabase(sender, instance, **kwargs):
    if instance.logo_url:
        delete_from_supabase(instance.logo_url)

@receiver(post_delete, sender=Material)
def delete_material_images_supabase(sender, instance, **kwargs):
    if instance.catalog_image_url:
        delete_from_supabase(instance.catalog_image_url)
    if instance.texture_image_url:
        delete_from_supabase(instance.texture_image_url)