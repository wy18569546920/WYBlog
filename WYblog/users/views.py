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


# 注册
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


# 登录
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

        # 根据next参数进行页面跳转
        next_page = request.GET.get('next')
        if next_page:
            response = redirect(next_page)
        else:
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


# 退出登录
class LogoutView(View):
    def get(self, request):
        """
        :param request:
        :return:
        """
        # 1. session数据清除
        logout(request)
        # 2. 删除部分cookie数据
        response = redirect(reverse('home:index'))
        response.delete_cookie('is_login')
        # 3. 跳转到首页
        return response


# 忘记密码
class ForgetPasswordView(View):
    def get(self, request):
        return render(request, 'forget_password.html')

    def post(self, request):
        """
        :param request:
        :return:
        """
        # 1. 接受数据
        mobile = request.POST.get('mobile')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        smscode = request.POST.get('sms_code')
        # 2. 验证数据
        #     2.1 判断参数是否齐全
        if not all([mobile, password, password2, smscode]):
            return HttpResponseBadRequest('缺少参数')
        #     2.2 手机号是否符合规则
        if not re.match(r'^1[3-9]\d{9}$', mobile):
            return HttpResponseBadRequest('手机号不符合规则')
        #     2.3 判断密码是否符合规则
        if not re.match(r'^[0-9A-Za-z]{8,20}$', password):
            return HttpResponseBadRequest('请输入8-20位密码，密码是数字、字母')
        #     2.4 判断两次密码是否一致
        if password != password2:
            return HttpResponseBadRequest('两次密码不一致')
        #     2.5 判断短信验证码是否正确
        redis_conn = get_redis_connection('default')
        redis_sms_code = redis_conn.get('sms: %s' % mobile)
        if redis_sms_code is None:
            return HttpResponseBadRequest('短信验证码已过期')
        if smscode != redis_sms_code.decode():
            return HttpResponseBadRequest('短信验证码不一致')
        # 3. 根据手机号进行用户信息查询
        try:
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist:
            # 4. 如果手机号查询出用户信息进行用户密码的修改
            try:
                User.objects.create_user(username=mobile, mobile=mobile, password=password)
            except Exception as e:
                logger.error(e)
                return HttpResponseBadRequest('修改失败，请稍后再试')
        else:
            # 5. 如果手机号没有查询出用户信息，则进行新用户的创建
            user.set_password(password)
            user.save()
        # 6. 进行页面跳转，跳转到登录页面
        response = redirect(reverse('users:login'))
        # 7. 返回响应
        return response


# 个人中心
# 继承LoginRequiredMixin
# 如果用户未登录，则会进行默认的跳转
# 默认跳转链接是/accounts/login/?next=/center/，需要到setting文件添加修改自定义跳转页面url的配置
class UserCenterView(LoginRequiredMixin, View):
    def get(self, request):
        # 获取登录用户的信息
        user = request.user
        # 组织用户信息
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
        # 1. 接受参数
        username = request.POST.get('username', user.username)
        user_desc = request.POST.get('desc', user.user_desc)
        avatar = request.FILES.get('avatar')
        # 2. 将参数保存
        try:
            user.username = username
            user.user_desc = user_desc
            if avatar:
                user.avatar = avatar
            user.save()
        except Exception as e:
            logger.error(e)
            return HttpResponseBadRequest('修改失败，请稍后再试')
        # 3. 更新cookie中的username信息
        # 4. 刷新当前页面（重定向）
        response = redirect(reverse('users:center'))
        response.set_cookie('username', user.username, max_age=14 * 3600 * 24)
        # 5. 返回响应
        return response


# 写博客
class WriteBlogView(LoginRequiredMixin, View):
    def get(self, request):
        # 查询所有分类
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
        # 1. 接受数据
        avatar = request.FILES.get('avatar')
        title = request.POST.get('title')
        category_id = request.POST.get('category')
        tags = request.POST.get('tags')
        sumary = request.POST.get('sumary')
        content = request.POST.get('content')
        user = request.user
        # 2. 验证数据
        if not all([avatar, title, category_id, tags, sumary, content]):
            return HttpResponseBadRequest('缺少参数')
        #   2.1 判断分类id
        try:
            category = ArticleCategory.objects.get(id=category_id)
        except ArticleCategory.DoesNotExist:
            return HttpResponseBadRequest('没有此分类')
        # 3. 数据入库
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
            return HttpResponseBadRequest('发布失败，请稍后再试')
        # 4. 跳转到指定页面
        return redirect(reverse('home:index'))
