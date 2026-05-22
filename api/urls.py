from django.urls import path
from .views import (
    BrandListView, 
    CategoryListView,  # 💡 La nueva vista que creamos
    MaterialsByBrandView, 
    ProcessImageView, 
    SegmentImageView
)

urlpatterns = [
    # 🗂️ Rutas del Catálogo (Se les sumará el '/api/' de la puerta principal)
    path('catalog/brands/', BrandListView.as_view(), name='brand-list'),
    path('catalog/categories/', CategoryListView.as_view(), name='category-list'), # 🔥 AQUÍ VA EL CAMBIO
    path('catalog/materials/', MaterialsByBrandView.as_view(), name='materials-by-brand'),

    # 🧠 IA y OpenCV
    path('segment/', SegmentImageView.as_view(), name='segment_image'),
    path('process-image/', ProcessImageView.as_view(), name='process_image'),
]