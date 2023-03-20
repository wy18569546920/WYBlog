from django.db import models
from django.contrib.auth.models import AbstractUser


# Create your models here.

# 继承django的User类,添加自定义的字段
class User(AbstractUser):
    mobile = models.CharField(max_length=11, unique=True, blank=False)  # 手机号
    avatar = models.ImageField(upload_to='avatar/%Y%m%d/', blank=True)  # 头像
    user_desc = models.CharField(max_length=500, blank=True)

    # 修改认证字段为mobile
    USERNAME_FIELD = 'mobile'

    # 创建超级管理员必须输入的字段（不包括 手机号和密码）
    REQUIRED_FIELDS = ['username', 'email']

    class Meta:
        db_table = 'tb_users'  # 修改表名称
        verbose_name = '用户管理'  # admin 后台显示
        verbose_name_plural = verbose_name  # admin 后台显示

    def __str__(self):
        return self.mobile
