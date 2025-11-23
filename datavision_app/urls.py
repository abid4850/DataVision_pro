from django.urls import path
from . import views

app_name = "datavision"

urlpatterns = [
    path("", views.home, name="home"),
    path("analyze/", views.analyze, name="analyze"),
    path("blog/", views.blog, name="blog"),
    path("blog/<slug:slug>/", views.blog_post, name="blog_post"),
    path("contact/", views.contact, name="contact"),
    path("result/<str:filename>/", views.result, name="result"),
]
