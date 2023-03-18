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

logger = logging.getLogger('django')


# 注册视图
class RegisterView(View):

    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        """
        :param request:
        :return:
        """
        # 1. 接收数据
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        smscode = request.POST.get('sms_code')
        # 2. 验证数据
        #     2.1 参数是否齐全
        if not all([mobile, password, password2, smscode]):
            return HttpResponseBadRequest('缺少必要参数')
        #     2.2 手机号格式是否正确
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('手机号不符合规则')
        #     2.3 密码是否符合格式
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return HttpResponseBadRequest('请输入8-20位密码，密码是数字、字母')
        #     2.4 密码和确认密码要一致
        if password != password2:
            return HttpResponseBadRequest('两次密码不一致')
        #     2.5 短信验证码是否和redis中的一致
        redis_conn = get_redis_connection('default')
        redis_sms_code = redis_conn.get('sms: %s' % mobile)
        if redis_sms_code is None:
            return HttpResponseBadRequest('短信验证码已过期')
        if smscode != redis_sms_code.decode():
            print(smscode)
            print(redis_sms_code)
            return HttpResponseBadRequest('短信验证码不一致')
        # 3. 保存数据信息
        #    create_user可以使用系统的方法来对密码加密
        try:
            user = User.objects.create_user(username=mobile, password=password, mobile=mobile)
        except DatabaseError as e:
            logger.error(e)
            return HttpResponseBadRequest('注册失败')

        # 状态保持
        from django.contrib.auth import login
        login(request, user)

        # 4. 返回响应跳转到指定页面
        response = redirect(reverse('home:index'))

        # 设置cookie信息， 以方便首页中用户信息展示的判断和用户信息的展示
        response.set_cookie('is_login', True)  # 登录状态，会话结束自动过期
        response.set_cookie('username', user.username, max_age=7 * 24 * 3600)  # 设置用户名有效期一个月

        return response


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


# 登录视图
class LoginView(View):

    def get(self, request):
        return render(request, 'login.html')

    def post(self, request):
        """
        :param request:
        :return:
        """
        # 1. 接受参数
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        remember = request.POST.get('remember')
        # 2. 参数验证
        #     2.1 验证手机号
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('手机号不符合规则')
        #     2.2 验证密码是否符合
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return HttpResponseBadRequest('请输入8-20位密码，密码是数字、字母')

        # 3. 用户认证登录
        from django.contrib.auth import authenticate  # 系统自带的认证方法
        user = authenticate(mobile=mobile, password=password)  # 默认只对username判断，所以需要到models内自定义一下
        if user is None:
            return HttpResponseBadRequest('用户名或密码错误')

        # 4. 状态保持
        from django.contrib.auth import login
        login(request, user)
        response = redirect(reverse('home:index'))
        # 5. 根据用户选择的是否记住登录状态来进行判断
        # 6. 为了首页显示需要设置一些cookie
        if remember != 'on':
            # 浏览器关闭之后
            request.session.set_expiry(0)
            response.set_cookie('is_login', True)
            response.set_cookie('username', user.username, max_age=14 * 24 * 3600)
        else:
            request.session.set_expiry(None)
            response.set_cookie('is_login', True, max_age=14 * 24 * 3600)
            response.set_cookie('username', user.username, max_age=14 * 24 * 3600)
        # 7. 返回响应
        return response
