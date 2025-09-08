from django.urls import path
from . import views

app_name = 'students'

urlpatterns = [
    path('', views.student_list, name='list'),
    path('create/', views.student_create, name='create'),
    path('upload/', views.student_upload, name='upload'),
    path('download-template/', views.download_template, name='download_template'),
    path('<int:pk>/edit/', views.student_edit, name='edit'),  # 👈 add this
    path('<int:pk>/delete/', views.student_delete, name='delete'),
]