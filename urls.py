from django.urls import path
from . import views

urlpatterns = [
    path("scan_product/", views.scan_product, name="scan_product"),
]