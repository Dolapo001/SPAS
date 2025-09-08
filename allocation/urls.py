from django.urls import path
from . import views

app_name = 'allocation'

urlpatterns = [
    path('run/', views.run_allocation, name='run'),
    path('results/', views.allocation_results, name='results'),
    path('download-csv/', views.download_csv, name='download_csv'),
    path('download-csv/<int:pk>/', views.download_csv, name='download_csv'),
    path('detail/<int:pk>/', views.allocation_detail, name='detail'),
    path("send-group-email/", views.send_group_email, name="send_group_email"),


]