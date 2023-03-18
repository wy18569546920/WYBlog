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

logger = logging.getLogger('django')


# ע����ͼ
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
            print(smscode)
            print(redis_sms_code)
            return HttpResponseBadRequest('������֤�벻һ��')
        # 3. ����������Ϣ
        #    create_user����ʹ��ϵͳ�ķ��������������
        try:
            user = User.objects.create_user(username=mobile, password=password, mobile=mobile)
        except DatabaseError as e:
            logger.error(e)
            return HttpResponseBadRequest('ע��ʧ��')
        # 4. ������Ӧ��ת��ָ��ҳ��
        #     ��ʱ����һ��ע��ɹ�����Ϣ
        return HttpResponse('ע��ɹ�')


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
