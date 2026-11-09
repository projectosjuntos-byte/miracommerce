from django.contrib import admin
from django.urls import include, path, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve

from loja.health import live, ready
from loja.metrics_views import metrics

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/live/', live, name='health_live'),
    path('health/ready/', ready, name='health_ready'),
    path('health/metrics/', metrics, name='health_metrics'),
    path('', include('loja.urls')),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
