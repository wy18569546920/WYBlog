from django.urls import path
from users.views import RegisterView, ImageCodeView, SmsCodeView

urlpatterns = [
    # 注册
    path('register/', RegisterView.as_view(), name='register'),

    # 图片验证码
    path('imagecode/', ImageCodeView.as_view(), name='imagecode'),

    # 短信
    path('smscode/', SmsCodeView.as_view(), name='smscode'),
]
