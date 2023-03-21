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
        # 1. ��ȡ���з�����Ϣ
        categories = ArticleCategory.objects.all()
        # 2. �����û�����ķ���id
        cat_id = request.GET.get('cat_id', 3)
        # 3. ���ݷ���id���з����ѯ
        try:
            category = ArticleCategory.objects.get(id=cat_id)
        except ArticleCategory.DoesNotExist:
            return HttpResponseBadRequest('û�д˷���')
        # 4. ��ȡ��ҳ����
        page_num = request.GET.get('page_num', 1)
        page_size = request.GET.get('page_size', 10)
        # 5. ���ݷ�����Ϣ��ѯ����
        articles = Article.objects.filter(category=category)
        # 6. ������ҳ��
        paginator = Paginator(articles, per_page=page_size)
        # 7. ���з�ҳ����
        try:
            page_articles = paginator.page(page_num)
        except EmptyPage:
            return HttpResponseNotFound('empty page')
        # ��ҳ��
        total_page = paginator.num_pages
        # . �������ݸ�ģ��
        context = {
            'categories': categories,
            'category': category,
            'articles': page_articles,
            'page_size': page_size,
            'total_page': total_page,
            'page_num': page_num
        }
        return render(request, 'index.html', context=context)
