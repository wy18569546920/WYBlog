#!/usr/bin/python3
# coding=gbk
from django.shortcuts import render
from django.views import View
from home.models import Article, ArticleCategory, Comment
from django.http.response import HttpResponseBadRequest, HttpResponseNotFound
from django.core.paginator import Paginator, EmptyPage
from django.shortcuts import redirect
from django.urls import reverse


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
        cat_id = request.GET.get('cat_id', 1)
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


class DetailView(View):
    def get(self, request):
        """
        :param request:
        :return:
        """
        # 1. ���ܲ���
        id = request.GET.get('id')
        page_size = request.GET.get('page_size', 10)
        page_num = request.GET.get('page_num', 1)
        # 2. ��������id�������ݲ�ѯ
        try:
            article = Article.objects.get(id=id)
        except Article.DoesNotExist:
            return render(request, '404.html')
        else:
            # �����+1
            article.total_view += 1
            article.save()
        # 3. ��ѯ��������
        categories = ArticleCategory.objects.all()

        # ��ѯ�����ǰʮ����������
        hot_articles = Article.objects.order_by('-total_view')[:9]

        # 5. ����������Ϣ��ѯ��������
        comments = Comment.objects.filter(article=article).order_by('-created')
        # ��ȡ��������
        total_count = comments.count()
        # 6. ������ҳ��
        paginator = Paginator(comments, page_size)
        # 7. ���з�ҳ����
        try:
            page_comments = paginator.page(page_num)
        except EmptyPage:
            return HttpResponseNotFound('empty page')
        total_page = paginator.num_pages
        # 8. ��֯ģ������
        context = {
            'categories': categories,
            'category': article.category,
            'article': article,
            'hot_articles': hot_articles,
            'total_count': total_count,
            'total_page': total_page,
            'comments': page_comments,
            'page_size': page_size,
            'page_num': page_num
        }
        return render(request, 'detail.html', context=context)

    def post(self, request):
        """
        :param request:
        :return:
        """
        # 1. �����û���Ϣ
        user = request.user
        # 2. �ж��û��Ƿ��¼
        if user and user.is_authenticated:
            # 3. ��¼�û����Խ���from����
            #     3.1 ������������
            id = request.POST.get('id')
            content = request.POST.get('content')
            #     3.2 ��֤�����Ƿ����
            try:
                article = Article.objects.get(id=id)
            except Article.DoesNotExist:
                return HttpResponseNotFound('û�д�����')
            #     3.3 ��������
            Comment.objects.create(content=content, article=article, user=user)
            #     3.4 �޸����µ�������
            article.comments_count += 1
            article.save()
            # ˢ�µ�ǰҳ��
            path = reverse('home:detail')+'?id={}'.format(article.id)
            return redirect(path)
        else:
            # 4. δ��¼�û���ת����¼ҳ��
            return redirect(reverse('users:login'))
