import hashlib
import json
import re

from django import forms
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import render, redirect

from app_0 import models


def get_md5(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    md5_hash = hashlib.md5()
    md5_hash.update(pwd_bytes)
    md5_digest = md5_hash.hexdigest()
    return md5_digest


class Loginform(forms.Form):
    username_error = {'required': '用户名不能为空', 'max-length': '用户名不能超过32个字符'}
    password_error = {'required': '密码不能为空', 'max-length': '用户名不能超过128个字符'}

    username = forms.CharField(label='姓名', required=True, widget=forms.TextInput, error_messages=username_error)
    password = forms.CharField(label='密码', required=True, widget=forms.PasswordInput(render_value=True),
                               error_messages=password_error)

    def __init__(self, *args, **kwargs):  # 自己的构造函数，继承了父类，但又重写了一部分
        super().__init__(*args, **kwargs)  # 调用父类的构造函数自定义字段的属性

        for name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            field.widget.attrs['placeholder'] = '请输入{}'.format(field.label)


def login(request):
    if request.method == 'GET':
        form = Loginform()
        return render(request, 'login.html', {'form': form})
    form = Loginform(data=request.POST)

    if not form.is_valid():
        return render(request, 'login.html', {'form': form})
    # 当表单通过 is_valid() 方法验证后，可以通过 cleaned_data 获取处理过的数据：
    # 访问前必须验证：在访问 cleaned_data 前必须调用 is_valid()，否则会抛出 AttributeError
    if form.cleaned_data['username'] != '谢晓弟':
        form.cleaned_data['password'] = get_md5(form.cleaned_data['password'])
    obj = models.UserInfo.objects.filter(**form.cleaned_data).first()
    if not obj:
        return render(request, 'login.html', {'form': form, 'error': '用户名或密码错误，请重新输入！'})
    request.session['user_info'] = {'id': obj.id, 'username': obj.username, 'role': obj.role}
    return redirect('/home/')


class RegisterForm(forms.Form):
    username_error = {'required': '用户名不能为空', 'max-length': '用户名不能超过32个字符'}
    password_error = {'required': '密码不能为空', 'max-length': '用户名不能超过64个字符'}
    again_password_error = {'required': '密码不能为空', 'max-length': '用户名不能超过64个字符'}

    username = forms.CharField(label='姓名', required=True, widget=forms.TextInput, error_messages=username_error)
    password = forms.CharField(label='密码', required=True, widget=forms.PasswordInput(render_value=True),
                               error_messages=password_error)
    again_password = forms.CharField(label='密码', required=True, widget=forms.PasswordInput(render_value=True),
                                     error_messages=again_password_error)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['again_password'].widget.attrs['placeholder'] = "请再次输入密码"

        for name, field in self.fields.items():
            if name != "again_password":
                field.widget.attrs['placeholder'] = '请输入{}'.format(field.label)
            field.widget.attrs['class'] = 'form-control'

    def clean_username(self):
        value = self.cleaned_data['username']
        obj = models.UserInfo.objects.filter(username=value).first()
        if obj:
            raise ValidationError("该用户已存在，请重新输入")
        return value

    def clean_password(self):
        value = get_md5(self.cleaned_data['password'])
        if re.findall(r'\W+', value):
            raise ValidationError('请输入合适的密码(数字 字母)')
        return value

    def clean_again_password(self):
        value = get_md5(self.cleaned_data['again_password'])
        pre_value = self.cleaned_data['password']
        if value != pre_value:
            raise ValidationError('密码输入不一致，请重新输入')
        return value


def register(request):
    if request.method == 'GET':
        form = RegisterForm()
        return render(request, 'register.html', {'form': form})

    form = RegisterForm(request.POST)
    if not form.is_valid():
        return render(request, 'register.html', {'form': form})

    username = form.cleaned_data['username']
    password = form.cleaned_data['password']
    models.UserInfo.objects.create(username=username, password=password)

    return redirect('/login/')


def logout(request):
    request.session.clear()
    return JsonResponse({'status': True})


def save_site_config(request):
    # 直接获取前端传的字段
    localSite = request.POST.get("localSite", "")
    info_crawl_page = request.POST.get("info_crawl_page", "")
    chapter_crawl_page = request.POST.get("chapter_crawl_page", "")
    update_page = request.POST.get("update_page", "")

    # 构建要保存的字典
    site_config = {
        "localSite": localSite,
        "info_crawl_page": info_crawl_page,
        "chapter_crawl_page": chapter_crawl_page,
        "update_page": update_page
    }

    # 保存到项目根目录
    json_path = "local_site.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(site_config, f, ensure_ascii=False, indent=4)

    return JsonResponse({
        "ok": 1,
        "msg": f"已切换到：{localSite}",
        "site": localSite
    })


