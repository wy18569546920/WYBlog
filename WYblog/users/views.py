#!/usr/bin/python3
# coding=gbk
from django.shortcuts import render
from django.http.response import HttpResponseBadRequest, JsonResponse
from django.http import HttpResponse
from libs.captcha.captcha import captcha
from django_redis import get_redis_connection
from django.views import View
from utils.response_code import RETCODE
from random import randint
from libs.ronglian_sms_sdk.SendMessage import send_message
import logging
import re
from users.models import User
from django.db import DatabaseError
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from home.models import ArticleCategory, Article

logger = logging.getLogger('django')


# ע��
class RegisterView(View):

    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        """
        :param request:
        :return:
        """
        # 1. ��������
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        smscode = request.POST.get('sms_code')
        # 2. ��֤����
        #     2.1 �����Ƿ���ȫ
        if not all([mobile, password, password2, smscode]):
            return HttpResponseBadRequest('ȱ�ٱ�Ҫ����')
        #     2.2 �ֻ��Ÿ�ʽ�Ƿ���ȷ
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('�ֻ��Ų����Ϲ���')
        #     2.3 �����Ƿ���ϸ�ʽ
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return HttpResponseBadRequest('������8-20λ���룬���������֡���ĸ')
        #     2.4 �����ȷ������Ҫһ��
        if password != password2:
            return HttpResponseBadRequest('�������벻һ��')
        #     2.5 ������֤���Ƿ��redis�е�һ��
        redis_conn = get_redis_connection('default')
        redis_sms_code = redis_conn.get('sms: %s' % mobile)
        if redis_sms_code is None:
            return HttpResponseBadRequest('������֤���ѹ���')
        if smscode != redis_sms_code.decode():
            return HttpResponseBadRequest('������֤�벻һ��')
        # 3. ����������Ϣ
        #    create_user����ʹ��ϵͳ�ķ��������������
        try:
            user = User.objects.create_user(username=mobile, password=password, mobile=mobile)
        except DatabaseError as e:
            logger.error(e)
            return HttpResponseBadRequest('ע��ʧ��')

        # ״̬����
        from django.contrib.auth import login
        login(request, user)

        # 4. ������Ӧ��ת��ָ��ҳ��
        response = redirect(reverse('home:index'))

        # ����cookie��Ϣ�� �Է�����ҳ���û���Ϣչʾ���жϺ��û���Ϣ��չʾ
        response.set_cookie('is_login', True)  # ��¼״̬���Ự�����Զ�����
        response.set_cookie('username', user.username, max_age=7 * 24 * 3600)  # �����û�����Ч��һ����

        return response


# ͼ����֤��
class ImageCodeView(View):

    def get(self, request):
        """
        :param request:
        :return:
        """
        # 1. ����ǰ�˴���uuid
        uuid = request.GET.get('uuid')
        # 2. �ж�uuid�Ƿ��ȡ��
        if uuid is None:
            return HttpResponseBadRequest('not uuid')
        # 3. ͨ������captcha������ͼƬ��֤�루ͼƬ�����ƺ�ͼƬ���ݣ�
        text, image = captcha.generate_captcha()
        # 4. ��ͼƬ���ݱ��浽redis��
        #     uuid��Ϊһ��key,ͼƬ������Ϊһ��value. ͬʱ���һ������ʱ��
        redis_conn = get_redis_connection('default')  # ʹ��redis�����ļ��е�Ĭ������
        redis_conn.setex('img: %s' % uuid, 300, text)
        # 5. ����ͼƬ������
        return HttpResponse(image, content_type='image/jpeg')


# ����
class SmsCodeView(View):

    def get(self, request):
        """
        :param request:
        :return:
        """
        # 1. ���ܲ���
        mobile = request.GET.get('mobile')
        image_code = request.GET.get('image_code')
        uuid = request.GET.get('uuid')
        # 2. ������֤
        #     a. ��֤�����Ƿ���ȫ

        if not all([mobile, image_code, uuid]):
            return JsonResponse({'code': RETCODE.NECESSARYPARAMERR, 'errmsg': "ȱ�ٲ���"})
        #     b. ͼƬ��֤�����֤
        redis_conn = get_redis_connection('default')
        redis_image_code = redis_conn.get('img: %s' % uuid)
        if redis_image_code is None:
            return JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': u'ͼƬ��֤���ѹ���'})
        #     c. ��ȡ��֮��ɾ��redis�ڵ�ͼƬ��֤�뻺��
        try:
            redis_conn.delete('img: %s' % uuid)
        except Exception as e:
            logger.error(e)
        #     d. �Ա�ͼƬ��֤��  ע�⣺��Сд����   redis������ʱbytes������Ҫת��
        if redis_image_code.decode().lower() != image_code.lower():
            return JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': 'ͼƬ��֤�����'})
        # 3. ���ɶ�����֤��
        sms_code = '%06d' % randint(0, 999999)
        logger.info(sms_code)
        # 4. ���������֤�뵽redis��
        redis_conn.setex('sms: %s' % mobile, 300, sms_code)
        # 5. ���Ͷ���
        send_message(mobile, ['%s' % sms_code, '5'])
        # 6. ������Ӧ
        return JsonResponse({'code': RETCODE.OK, 'errmsg': '���ŷ��ͳɹ�'})


# ��¼
class LoginView(View):

    def get(self, request):
        return render(request, 'login.html')

    def post(self, request):
        """
        :param request:
        :return:
        """
        # 1. ���ܲ���
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        remember = request.POST.get('remember')
        # 2. ������֤
        #     2.1 ��֤�ֻ���
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('�ֻ��Ų����Ϲ���')
        #     2.2 ��֤�����Ƿ����
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return HttpResponseBadRequest('������8-20λ���룬���������֡���ĸ')

        # 3. �û���֤��¼
        from django.contrib.auth import authenticate  # ϵͳ�Դ�����֤����
        user = authenticate(mobile=mobile, password=password)  # Ĭ��ֻ��username�жϣ�������Ҫ��models���Զ���һ��
        if user is None:
            return HttpResponseBadRequest('�û������������')

        # 4. ״̬����
        from django.contrib.auth import login
        login(request, user)

        # ����next��������ҳ����ת
        next_page = request.GET.get('next')
        if next_page:
            response = redirect(next_page)
        else:
            response = redirect(reverse('home:index'))

        # 5. �����û�ѡ����Ƿ��ס��¼״̬�������ж�
        # 6. Ϊ����ҳ��ʾ��Ҫ����һЩcookie
        if remember != 'on':
            # ������ر�֮��
            request.session.set_expiry(0)
            response.set_cookie('is_login', True)
            response.set_cookie('username', user.username, max_age=14 * 24 * 3600)
        else:
            request.session.set_expiry(None)
            response.set_cookie('is_login', True, max_age=14 * 24 * 3600)
            response.set_cookie('username', user.username, max_age=14 * 24 * 3600)
        # 7. ������Ӧ
        return response


# �˳���¼
class LogoutView(View):
    def get(self, request):
        """
        :param request:
        :return:
        """
        # 1. session�������
        logout(request)
        # 2. ɾ������cookie����
        response = redirect(reverse('home:index'))
        response.delete_cookie('is_login')
        # 3. ��ת����ҳ
        return response


# ��������
class ForgetPasswordView(View):
    def get(self, request):
        return render(request, 'forget_password.html')

    def post(self, request):
        """
        :param request:
        :return:
        """
        # 1. ��������
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        smscode = request.POST.get('sms_code')
        # 2. ��֤����
        #     2.1 �жϲ����Ƿ���ȫ
        if not all([mobile, password, password2, smscode]):
            return HttpResponseBadRequest('ȱ�ٲ���')
        #     2.2 �ֻ����Ƿ���Ϲ���
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('�ֻ��Ų����Ϲ���')
        #     2.3 �ж������Ƿ���Ϲ���
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return HttpResponseBadRequest('������8-20λ���룬���������֡���ĸ')
        #     2.4 �ж����������Ƿ�һ��
        if password != password2:
            return HttpResponseBadRequest('�������벻һ��')
        #     2.5 �ж϶�����֤���Ƿ���ȷ
        redis_conn = get_redis_connection('default')
        redis_sms_code = redis_conn.get('sms: %s' % mobile)
        if redis_sms_code is None:
            return HttpResponseBadRequest('������֤���ѹ���')
        if smscode != redis_sms_code.decode():
            return HttpResponseBadRequest('������֤�벻һ��')
        # 3. �����ֻ��Ž����û���Ϣ��ѯ
        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            # 4. ����ֻ��Ų�ѯ���û���Ϣ�����û�������޸�
            try:
                User.objects.create_user(username=mobile, mobile=mobile, password=password)
            except Exception as e:
                logger.error(e)
                return HttpResponseBadRequest('�޸�ʧ�ܣ����Ժ�����')
        else:
            # 5. ����ֻ���û�в�ѯ���û���Ϣ����������û��Ĵ���
            user.set_password(password)
            user.save()
        # 6. ����ҳ����ת����ת����¼ҳ��
        response = redirect(reverse('users:login'))
        # 7. ������Ӧ
        return response


# ��������
# �̳�LoginRequiredMixin
# ����û�δ��¼��������Ĭ�ϵ���ת
# Ĭ����ת������/accounts/login/?next=/center/����Ҫ��setting�ļ�����޸��Զ�����תҳ��url������
class UserCenterView(LoginRequiredMixin, View):
    def get(self, request):
        # ��ȡ��¼�û�����Ϣ
        user = request.user
        # ��֯�û���Ϣ
        context = {
            'username': user.username,
            'mobile': user.mobile,
            'avatar': user.avatar.url if user.avatar else None,
            'user_desc': user.user_desc
        }
        return render(request, 'center.html', context=context)

    def post(self, request):
        """
        :param request:
        :return:
        """
        user = request.user
        # 1. ���ܲ���
        username = request.POST.get('username', user.username)
        user_desc = request.POST.get('desc', user.user_desc)
        avatar = request.FILES.get('avatar')
        # 2. ����������
        try:
            user.username = username
            user.user_desc = user_desc
            if avatar:
                user.avatar = avatar
            user.save()
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest('�޸�ʧ�ܣ����Ժ�����')
        # 3. ����cookie�е�username��Ϣ
        # 4. ˢ�µ�ǰҳ�棨�ض���
        response = redirect(reverse('users:center'))
        response.set_cookie('username', user.username, max_age=14 * 3600 * 24)
        # 5. ������Ӧ
        return response


# д����
class WriteBlogView(LoginRequiredMixin, View):
    def get(self, request):
        # ��ѯ���з���
        categories = ArticleCategory.objects.all()
        context = {
            'categories': categories
        }
        return render(request, 'write_blog.html', context=context)

    def post(self, request):
        """
        :param request:
        :return:
        """
        # 1. ��������
        avatar = request.FILES.get('avatar')
        title = request.POST.get('title')
        category_id = request.POST.get('category')
        tags = request.POST.get('tags')
        sumary = request.POST.get('sumary')
        content = request.POST.get('content')
        user = request.user
        # 2. ��֤����
        if not all([avatar, title, category_id, tags, sumary, content]):
            return HttpResponseBadRequest('ȱ�ٲ���')
        #   2.1 �жϷ���id
        try:
            category = ArticleCategory.objects.get(id=category_id)
        except ArticleCategory.DoesNotExist:
            return HttpResponseBadRequest('û�д˷���')
        # 3. �������
        try:
            Article.objects.create(
                author=user,
                title=title,
                avatar=avatar,
                category=category,
                tags=tags,
                sumary=sumary,
                content=content
            )
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest('����ʧ�ܣ����Ժ�����')
        # 4. ��ת��ָ��ҳ��
        return redirect(reverse('home:index'))
