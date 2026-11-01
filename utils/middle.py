from django.conf import settings
from django.shortcuts import redirect, HttpResponse
from django.urls.exceptions import Resolver404
from django.utils.deprecation import MiddlewareMixin


class MiddleItem(MiddlewareMixin):
    @staticmethod
    def process_request(request):
        whitelist = ('/login/', '/register/')
        if request.path_info in whitelist:
            return

        user_obj = request.session.get('user_info')
        if user_obj:
            request.common_userid = user_obj['id']
            request.common_username = user_obj['username']
            request.common_role = user_obj['role']
            if request.path_info == '/':
                return redirect('/home/')
            return
        else:
            return redirect('/login/')

    @staticmethod
    def process_response(request, response):
        return response

    @staticmethod
    def process_view(request, view_func, view_args, view_kwargs):
        whitelist = ('/login/', '/register/', '/logout/')
        if request.path_info in whitelist:
            return

        try:
            url_name = request.resolver_match.url_name
        except (AttributeError, Resolver404):
            return HttpResponse('抱歉，你的页面被外星人偷走了~')

        role = getattr(request, 'common_role', None)
        if not role:
            return HttpResponse('抱歉，你的页面被外星人偷走了~')

        role_permission_set = settings.PERMISSION.get(role, set())
        if url_name in role_permission_set:
            return

        return HttpResponse('抱歉，你的页面被外星人偷走了~')