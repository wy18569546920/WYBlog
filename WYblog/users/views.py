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

logger = logging.getLogger('django')


# ע����ͼ
class RegisterView(View):

    def get(self, request):
        return render(request, 'register.html')


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
