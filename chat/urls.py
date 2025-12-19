from django.urls import path
from chat.views import index

urlpatterns = [
    path('<str:group_name>/', index),
]