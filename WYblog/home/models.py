from django.db import models
from django.utils import timezone
from users.models import User


# Create your models here.

class ArticleCategory(models.Model):
    """
    文章分类
    """
    # 分类标题
    title = models.CharField(max_length=100, blank=True)
    # 创建时间
    created = models.DateTimeField(default=timezone.now)

    # admin站点显示
    def __str__(self):
        return self.title

    class Meta:
        db_table = 'tb_category'
        verbose_name = '类别管理'
        verbose_name_plural = verbose_name


class Article(models.Model):
    """
    文章内容
    """
    author = models.ForeignKey(User, on_delete=models.CASCADE)  # 作者
    avatar = models.ImageField(upload_to='article/%Y%m%d/', blank=True)  # 标题图
    title = models.CharField(max_length=20, blank=True)  # 标题
    category = models.ForeignKey(ArticleCategory, null=True, blank=True, on_delete=models.CASCADE,
                                 related_name='artilce')  # 分类
    tags = models.CharField(max_length=20, blank=True)  # 标签
    sumary = models.CharField(max_length=200, null=False, blank=False)  # 摘要信息
    content = models.TextField()  # 文章正文
    total_view = models.PositiveIntegerField(default=0)  # 浏览量
    comments_count = models.PositiveIntegerField(default=0)  # 评论量
    created = models.DateTimeField(default=timezone.now)  # 创建时间
    updated = models.DateTimeField(auto_now=True)  # 修改时间

    class Meta:
        db_table = 'tb_article'
        ordering = ('-created',)  # 结果根据创建时间排序
        verbose_name = '文章管理'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title
