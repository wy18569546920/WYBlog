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


# 注册视图
class RegisterView(View):

    def get(self, request):
        return render(request, 'register.html')


# 图形验证码
class ImageCodeView(View):

    def get(self, request):
        """
        :param request:
        :return:
        """
        # 1. 接受前端传的uuid
        uuid = request.GET.get('uuid')
        # 2. 判断uuid是否获取到
        if uuid is None:
            return HttpResponseBadRequest('not uuid')
        # 3. 通过调用captcha来生成图片验证码（图片二进制和图片内容）
        text, image = captcha.generate_captcha()
        # 4. 将图片内容保存到redis中
        #     uuid作为一个key,图片内容作为一个value. 同时添加一个过期时间
        redis_conn = get_redis_connection('default')  # 使用redis配置文件中的默认配置
        redis_conn.setex('img: %s' % uuid, 300, text)
        # 5. 返回图片二进制
        return HttpResponse(image, content_type='image/jpeg')


# 短信
class SmsCodeView(View):

    def get(self, request):
        """
        :param request:
        :return:
        """
        # 1. 接受参数
        mobile = request.GET.get('mobile')
        image_code = request.GET.get('image_code')
        uuid = request.GET.get('uuid')
        # 2. 参数验证
        #     a. 验证参数是否齐全

        if not all([mobile, image_code, uuid]):
            return JsonResponse({'code': RETCODE.NECESSARYPARAMERR, 'errmsg': "缺少参数"})
        #     b. 图片验证码的验证
        redis_conn = get_redis_connection('default')
        redis_image_code = redis_conn.get('img: %s' % uuid)
        if redis_image_code is None:
            return JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': u'图片验证码已过期'})
        #     c. 获取到之后，删除redis内的图片验证码缓存
        try:
            redis_conn.delete('img: %s' % uuid)
        except Exception as e:
            logger.error(e)
        #     d. 对比图片验证码  注意：大小写问题   redis的数据时bytes所以需要转换
        if redis_image_code.decode().lower() != image_code.lower():
            return JsonResponse({'code': RETCODE.IMAGECODEERR, 'errmsg': '图片验证码错误'})
        # 3. 生成短信验证码
        sms_code = '%06d' % randint(0, 999999)
        logger.info(sms_code)
        # 4. 保存短信验证码到redis中
        redis_conn.setex('sms: %s' % mobile, 300, sms_code)
        # 5. 发送短信
        send_message(mobile, ['%s' % sms_code, '5'])
        # 6. 返回响应
        return JsonResponse({'code': RETCODE.OK, 'errmsg': '短信发送成功'})
