from django import forms
from django.contrib import admin
from django.utils.html import format_html, mark_safe
from .models import Brand, Material, Category,upload_to_supabase, delete_from_supabase

# =====================================================================
# 🏷️ FORMULARIO DE MARCAS (DISEÑO LIMPIO)
# =====================================================================
class BrandAdminForm(forms.ModelForm):
    logo_file = forms.ImageField(
        required=False, 
        label="🖼️ Logotipo de la Marca",
        help_text="Se recomienda subir formatos PNG con fondo transparente para un mejor look en la App móvil."
    )

    class Meta:
        model = Brand
        fields = ['name', 'is_active']

    def save(self, commit=True):
        instance = super().save(commit=False)
        file = self.cleaned_data.get('logo_file')
        if file:
            if instance.logo_url:
                delete_from_supabase(instance.logo_url)
            instance.logo_url = upload_to_supabase(file, 'brands')
        if commit:
            instance.save()
        return instance
    
    

# =====================================================================
# 🏷️ PANEL DE GESTIÓN DE MARCAS
# =====================================================================

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'status_visual', 'acciones_rapidas')
    list_display_links = ('name',)
    actions = None # Quitamos selección masiva

    def status_visual(self, obj):
        if obj.is_active:
            return mark_safe('<span class="badge badge-success" style="padding: 5px 10px; font-size: 11px;">ACTIVA</span>')
        return mark_safe('<span class="badge badge-danger" style="padding: 5px 10px; font-size: 11px;">INACTIVA</span>')
    status_visual.short_description = "Estado"

    def acciones_rapidas(self, obj):
        edit_url = f"/admin/catalog/category/{obj.id}/change/"
        delete_url = f"/admin/catalog/category/{obj.id}/delete/"
        return format_html(
            '<a href="{}" class="btn btn-xs btn-info" style="margin-right: 8px;" title="Editar"><i class="fas fa-pencil-alt"></i></a>'
            '<a href="{}" class="btn btn-xs btn-danger" title="Eliminar"><i class="fas fa-trash"></i></a>',
            edit_url, delete_url
        )
    acciones_rapidas.short_description = "Acciones"


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    form = BrandAdminForm
    
    # 🌟 Agregamos 'acciones_rapidas' al final de la lista
    list_display = ('mostrar_logo', 'name', 'status_visual', 'acciones_rapidas')
    list_display_links = ('name',) # El usuario todavía puede hacer clic en el nombre si quiere
    
    # 🧹 QUITAR EL MENÚ SELECT DE ACCIONES MASIVAS
    actions = None

    # 💉 BOTONES DE EDITAR Y ELIMINAR DIRECTOS
    def acciones_rapidas(self, obj):
        # Generamos las URLs internas de Django Admin para modificar y borrar este ID específico
        edit_url = f"/admin/catalog/brand/{obj.id}/change/"
        delete_url = f"/admin/catalog/brand/{obj.id}/delete/"
        
        return format_html(
            '<a href="{}" class="btn btn-xs btn-info" style="margin-right: 8px;" title="Editar"><i class="fas fa-pencil-alt"></i></a>'
            '<a href="{}" class="btn btn-xs btn-danger" title="Eliminar"><i class="fas fa-trash"></i></a>',
            edit_url, delete_url
        )
    acciones_rapidas.short_description = "Acciones"

    # Miniatura del logo
    def mostrar_logo(self, obj):
        if obj.logo_url:
            return format_html('<img src="{}" style="width: 40px; height: 40px; object-fit: contain; border-radius: 4px; background: #2d3748; padding: 2px;" />', obj.logo_url)
        return mark_safe('<span style="color: #e53e3e; font-weight: bold;">❌ Sin Logo</span>')
    mostrar_logo.short_description = "Logo"

    # Badge de estado
    def status_visual(self, obj):
        if obj.is_active:
            return mark_safe('<span class="badge badge-success" style="padding: 5px 10px; font-size: 11px;">ACTIVA</span>')
        return mark_safe('<span class="badge badge-danger" style="padding: 5px 10px; font-size: 11px;">INACTIVA</span>')
    status_visual.short_description = "Estado"


# =====================================================================
# 🧱 FORMULARIO DE MATERIALES (EL TRABAJO PESADO)
# =====================================================================
class MaterialAdminForm(forms.ModelForm):
    catalog_file = forms.ImageField(
        required=False, 
        label="📸 Foto Comercial / Vitrina",
        help_text="Muestra el piso instalado o en un ambiente real. Es la foto principal que verá el cliente al explorar."
    )
    texture_file = forms.ImageField(
        required=False, 
        label="🎨 Textura de Alta Calidad (Para la IA)",
        help_text="⚠️ ¡CRÍTICO! Sube un recorte perfectamente CUADRADO, limpio, alineado, sin sombras ni marcas de agua. Es el patrón que usará el motor de renderizado IA."
    )

    class Meta:
        model = Material
        fields = ['name', 'brand', 'category', 'description', 'price', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Ej: Porcelanato Negro Rectificado 60x60', 'class': 'form-control-lg'}),
            'price': forms.NumberInput(attrs={'step': '0.01', 'placeholder': '0.00'}),
            'description': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Añade detalles adicionales del material...'}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        cat_file = self.cleaned_data.get('catalog_file')
        tex_file = self.cleaned_data.get('texture_file')
        
        if cat_file:
            if instance.catalog_image_url:
                delete_from_supabase(instance.catalog_image_url)
            instance.catalog_image_url = upload_to_supabase(cat_file, 'materials')
            
        if tex_file:
            if instance.texture_image_url:
                delete_from_supabase(instance.texture_image_url)
            instance.texture_image_url = upload_to_supabase(tex_file, 'textures')
            
        if commit:
            instance.save()
        return instance

@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    form = MaterialAdminForm
    
    # 🌟 Agregamos 'acciones_rapidas' al final de la lista
    list_display = ('mostrar_textura', 'name', 'brand', 'category', 'precio_formateado', 'status_visual', 'acciones_rapidas')
    list_filter = ('brand', 'category', 'is_active')
    search_fields = ('name', 'brand__name')
    
    # 🧹 QUITAR EL MENÚ SELECT DE ACCIONES MASIVAS
    actions = None
    
    # 📑 Pestañas del formulario
    fieldsets = (
        ('📦 Datos Generales', {'fields': ('name', 'brand', 'category', 'price', 'is_active')}),
        ('🖼️ Archivos de Imagen', {'fields': ('catalog_file', 'texture_file')}),
        ('📝 Descripción Comercial', {'fields': ('description',), 'classes': ('collapse',)}),
    )

    # 💉 BOTONES DE EDITAR Y ELIMINAR DIRECTOS
    def acciones_rapidas(self, obj):
        edit_url = f"/admin/catalog/material/{obj.id}/change/"
        delete_url = f"/admin/catalog/material/{obj.id}/delete/"
        
        return format_html(
            '<a href="{}" class="btn btn-xs btn-info" style="margin-right: 8px;" title="Editar"><i class="fas fa-pencil-alt"></i></a>'
            '<a href="{}" class="btn btn-xs btn-danger" title="Eliminar"><i class="fas fa-trash"></i></a>',
            edit_url, delete_url
        )
    acciones_rapidas.short_description = "Acciones"

    def mostrar_textura(self, obj):
        if obj.texture_image_url:
            return format_html('<img src="{}" style="width: 45px; height: 45px; object-fit: cover; border-radius: 6px; border: 1px solid #4a5568;" />', obj.texture_image_url)
        return mark_safe('<span style="color: #a0aec0;">Sin textura</span>')
    mostrar_textura.short_description = "Miniatura"

    def precio_formateado(self, obj):
        return format_html('<strong style="color: #38bdf8;">${} / m²</strong>', obj.price)
    precio_formateado.short_description = "Precio"

    def status_visual(self, obj):
        if obj.is_active:
            return mark_safe('<span class="badge badge-success">Disponible</span>')
        return mark_safe('<span class="badge badge-secondary">Oculto</span>')
    status_visual.short_description = "Visibilidad"