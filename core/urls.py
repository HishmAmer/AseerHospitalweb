from django.contrib import admin
from django.urls import include, path

from employees.views import ThrottledLoginView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', ThrottledLoginView.as_view(), name='login'),
    path('', include('employees.urls')),
]