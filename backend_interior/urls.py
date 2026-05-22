from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='admin/', permanent=False)),

    path('admin/', admin.site.urls),

    path('api/', include('api.urls')),
]


admin.site.site_header = "Panel de Control"
admin.site.site_title = "Mora Mora Admin"
admin.site.index_title = "Bienvenido al Gestor de Catálogo"