from django.contrib import admin
from home.models import ArticleCategory, Article

# Register your models here.
# 注册模型
admin.site.register(ArticleCategory)


class ArticleAdmin(admin.ModelAdmin):
    list_display = 'author', 'title', 'category', 'tags', 'total_view', 'comments_count', 'created'


admin.site.register(Article, ArticleAdmin)
