from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LoginView, LogoutView
from .views import some_view

urlpatterns = [
    path("admin/", admin.site.urls),
    path("sale/", include("sale.urls")),
    path("core/", include("core.urls")),
    path("purchase/", include("purchase.urls")),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(next_page='login'), name="logout"),

    path("", some_view, name="rootview"),
]



admin.site.site_header = 'RESTAURANT-365'