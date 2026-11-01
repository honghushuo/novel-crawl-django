import copy
import json

from django import template
from django.conf import settings

register = template.Library()


# inclusion_tag 是 Django 模板标签的一种，专门用来：把一段 HTML 代码封装成 “可复用组件”，直接在页面调用。
@register.inclusion_tag('menu.html')
def menu(request):
    role = getattr(request, 'common_role', None)
    menu_list = settings.MENU
    if not role or role not in menu_list:
        return {'menu_list': []}

    function_list = copy.deepcopy(menu_list[role])
    with open('local_site.json', "r", encoding="utf-8") as f:
        site_config = json.load(f)
        site = site_config['localSite']
        info = site_config["info_crawl_page"]
        chapter = site_config["chapter_crawl_page"]
        update = site_config["update_page"]

    current_url = request.path_info
    for function in function_list:
        if function['title'] == "小说信息爬取":
            function['url'] = info
        elif function['title'] == "小说章节爬取":
            function['url'] = chapter
        elif function['title'] == "数据更新维护":
            function['url'] = update
        if current_url == function['url'] or current_url.startswith(function['url']):
            function['class'] = 'active'

    return {'menu_list': function_list}
