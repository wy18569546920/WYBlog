#!/usr/bin/python3
# coding=gbk
from django.shortcuts import render
from django.views import View
from home.models import Article, ArticleCategory
from django.http.response import HttpResponseBadRequest, HttpResponseNotFound
from django.core.paginator import Paginator, EmptyPage


# Create your views here.

class IndexView(View):

    def get(self, request):
        """
        :param request:
        :return:
        """
        # 1. 获取所有分类信息
        categories = ArticleCategory.objects.all()
        # 2. 接受用户点击的分类id
        cat_id = request.GET.get('cat_id', 3)
        # 3. 根据分类id进行分类查询
        try:
            category = ArticleCategory.objects.get(id=cat_id)
        except ArticleCategory.DoesNotExist:
            return HttpResponseBadRequest('没有此分类')
        # 4. 获取分页参数
        page_num = request.GET.get('page_num', 1)
        page_size = request.GET.get('page_size', 10)
        # 5. 根据分类信息查询文章
        articles = Article.objects.filter(category=category)
        # 6. 创建分页器
        paginator = Paginator(articles, per_page=page_size)
        # 7. 进行分页处理
        try:
            page_articles = paginator.page(page_num)
        except EmptyPage:
            return HttpResponseNotFound('empty page')
        # 总页数
        total_page = paginator.num_pages
        # . 传递数据给模板
        context = {
            'categories': categories,
            'category': category,
            'articles': page_articles,
            'page_size': page_size,
            'total_page': total_page,
            'page_num': page_num
        }
        return render(request, 'index.html', context=context)
