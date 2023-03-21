from django.contrib import admin
from home.models import ArticleCategory, Article


# Register your models here.
# 注册模型
class ArticleCategoryAdmin(admin.ModelAdmin):
    list_display = 'title', 'created'
    search_fields = 'title',
    list_per_page = 20


admin.site.register(ArticleCategory, ArticleCategoryAdmin)


class ArticleAdmin(admin.ModelAdmin):
    list_display = 'author', 'title', 'category', 'tags', 'total_view', 'comments_count', 'created', 'updated'
    search_fields = 'title', 'tags',
    list_filter = 'category',
    list_per_page = 20


admin.site.register(Article, ArticleAdmin)
