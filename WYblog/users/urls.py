from django.urls import path
from users.views import RegisterView, ImageCodeView

urlpatterns = [
    # 注册
    path('register/', RegisterView.as_view(), name='register'),

    # 图片验证码
    path('imagecode/', ImageCodeView.as_view(), name='imagecode'),
]
