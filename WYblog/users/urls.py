from django.urls import path
from users.views import RegisterView, ImageCodeView, SmsCodeView, LoginView, LogoutView

urlpatterns = [
    # 注册
    path('register/', RegisterView.as_view(), name='register'),

    # 图片验证码
    path('imagecode/', ImageCodeView.as_view(), name='imagecode'),

    # 短信
    path('smscode/', SmsCodeView.as_view(), name='smscode'),

    # 登录
    path('login/', LoginView.as_view(), name='login'),

    # 退出登录
    path('logout/', LogoutView.as_view(), name='logout'),
]
