from django.urls import path
from .views import BrandListView, MaterialsByBrandView, ProcessImageView, SegmentImageView

urlpatterns = [
    path('catalog/brands/', BrandListView.as_view(), name='brand-list'),
    
    # Endpoint para ver materiales filtrados por marca
    path('catalog/materials/', MaterialsByBrandView.as_view(), name='materials-by-brand'),

    path('process-image/', ProcessImageView.as_view(), name='process_image'),

    path('segment/', SegmentImageView.as_view(), name='segment_image'),

    
]