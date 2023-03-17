from django.shortcuts import render
from django.http.response import HttpResponseBadRequest
from django.http import HttpResponse
from libs.captcha.captcha import captcha
from django_redis import get_redis_connection
from django.views import View


# 注册视图
class RegisterView(View):

    def get(self, request):
        return render(request, 'register.html')


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
