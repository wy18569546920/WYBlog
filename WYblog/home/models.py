from django.db import models
from django.utils import timezone
from users.models import User


# Create your models here.

class ArticleCategory(models.Model):
    """
    文章分类
    """
    # 分类标题
    title = models.CharField(max_length=100, blank=True, verbose_name="分类标题")
    # 创建时间
    created = models.DateTimeField(default=timezone.now, verbose_name="创建时间")

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
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="作者")  # 作者
    avatar = models.ImageField(upload_to='article/%Y%m%d/', blank=True, verbose_name="标题图")  # 标题图
    title = models.CharField(max_length=20, blank=True, verbose_name="标题")  # 标题
    category = models.ForeignKey(ArticleCategory, null=True, blank=True, on_delete=models.CASCADE,
                                 related_name='artilce', verbose_name="分类")  # 分类
    tags = models.CharField(max_length=20, blank=True, verbose_name="标签")  # 标签
    sumary = models.CharField(max_length=200, null=False, blank=False, verbose_name="摘要信息")  # 摘要信息
    content = models.TextField(verbose_name="文章正文")  # 文章正文
    total_view = models.PositiveIntegerField(default=0, verbose_name="浏览量")  # 浏览量
    comments_count = models.PositiveIntegerField(default=0, verbose_name="评论量")  # 评论量
    created = models.DateTimeField(default=timezone.now, verbose_name="创建时间")  # 创建时间
    updated = models.DateTimeField(auto_now=True, verbose_name="修改时间")  # 修改时间

    class Meta:
        db_table = 'tb_article'
        ordering = ('-created',)  # 结果根据创建时间排序
        verbose_name = '文章管理'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.title
