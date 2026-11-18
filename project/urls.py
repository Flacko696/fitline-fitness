"""
URL configuration for project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import path
from app import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.index, name="index"),
    path("memberships/", views.memberships_list, name="memberships"),
    path("memberships/<int:pk>/buy/", views.buy_membership, name="buy_membership"),
    path("schedule/", views.schedule_list, name="schedule"),
    path("schedule/<int:pk>/", views.schedule_detail, name="schedule_detail"),
    path("schedule/<int:pk>/book/", views.book_workout, name="book_workout"),
    path("trainers/", views.trainers_list, name="trainers"),
    path("reviews/", views.reviews_page, name="reviews"),
    path("contacts/", views.contacts_page, name="contacts"),
    path("search/", views.search_page, name="search"),
    path("account/", views.account_page, name="account"),
    path("account/freeze/<int:pk>/", views.freeze_membership, name="freeze_membership"),
    path("account/cancel/<int:pk>/", views.cancel_booking, name="cancel_booking"),
    path("login/", LoginView.as_view(template_name="login.html"), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
]