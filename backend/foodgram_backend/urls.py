from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    path('recipes/', include('recipes.urls')),
    path('users/', include('users.urls')),
]
