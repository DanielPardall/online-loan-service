from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from rest_framework import routers
from rest_framework_simplejwt.views import TokenRefreshView

from api.views import (
    CreateUserView,
    CustomTokenObtainPairView,
    UserViewSet,
    GroupViewSet,
    logout
)

router = routers.DefaultRouter()
router.register(r'users', UserViewSet, basename="user")
router.register(r'groups', GroupViewSet, basename="group")

# Função de home básica
def home(request):
    return HttpResponse("API Backend")

# URL Patterns
urlpatterns = [
    path('admin/', admin.site.urls),

    # Endpoints de Autenticação e Tokens
    path('api/user/register/', CreateUserView.as_view(), name="register"),
    path('api/token/', CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'), 
    path('api/logout/', logout),

    path('api/', include('api.urls')),

    path('api-auth/', include('rest_framework.urls')),

    path('', home, name='home'),
]
