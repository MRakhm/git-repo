from django.urls import path
from useradmin import views

app_name = "useradmin"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("products/", views.dashboard_products, name="dashboard-products"),
    path("add-products/", views.dashboard_add_product, name="dashboard-add-products"),
    path("edit-products/<pid>/", views.dashboard_edit_product, name="dashboard-edit-products"),
    path("delete-products/<pid>/", views.dashboard_delete_product, name="dashboard-delete-products"),
    path('send-otp/', views.send_otp_view, name='send_otp'),
    path('dashboard_statistics/', views.dashboard_statistics_superuser, name='dashboard_statistics'),
    path('add_multiple_products/', views.add_multiple_products, name='add-multiple-products'),
]
