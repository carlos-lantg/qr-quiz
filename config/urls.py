from django.urls import path

from quiz import views

urlpatterns = [
    path("", views.dashboard),
    path("answer/", views.answer),
    path("api/answer/", views.api_answer),
    path("api/stats/", views.api_stats),
    path("api/join/", views.api_join),
    path("api/start/", views.api_start),
    path("api/finish/", views.api_finish),
    path("logo.jpg", views.logo),
    path("admin/", views.admin),
    path("admin/logout/", views.admin_logout),
]
