from django.urls import path
from . import views

app_name = 'supervisors'

urlpatterns = [
    path('', views.supervisor_list, name='list'),
    path('create/', views.supervisor_create, name='create'),
    path('upload/', views.upload_supervisors, name='upload'),
    path('download-template/', views.download_supervisor_template, name='download_template'),
    path('<int:pk>/edit/', views.supervisor_edit, name='edit'),
    path('<int:pk>/delete/', views.supervisor_delete, name='delete'),
]