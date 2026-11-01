import os

from django import forms
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from app_0 import models


class userInfo(forms.ModelForm):
    class Meta:
        model = models.UserInfo
        fields = ['phone', 'email', 'address', 'motto', 'occupation', 'hobby', 'about_me', 'birthday']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for name, field in self.fields.items():

            field.widget.attrs['class'] = 'form-control'
            field.widget.attrs['placeholder'] = '请输入{}'.format(field.label)
            if name == 'birthday':
                field.widget.attrs['placeholder'] = '请输入{}(格式：2026-01-01)'.format(field.label)


@require_GET
def home(request):
    user_info = models.UserInfo.objects.filter(username=request.common_username).first()
    avatar_obj = models.Avatar.objects.filter(user=user_info).first()
    if avatar_obj:
        image_path = avatar_obj.avatar.name if (avatar_obj and avatar_obj.avatar) else None
        image_path = str(image_path).split('app_0/static/')[-1]
    else:
        image_path = None
    info = {
        "id": user_info.id,
        "username": user_info.username,
        "role": user_info.role,
        "phone": user_info.phone,
        "email": user_info.email,
        "address": user_info.address,
        "motto": user_info.motto,
        "about_me": user_info.about_me,
        "occupation": user_info.occupation,
        "hobby": user_info.hobby,
        "birthday": user_info.birthday,
        "avatar": image_path,

    }
    if request.method == 'GET':
        name = request.common_username
        obj = models.UserInfo.objects.filter(username=name)
        form = userInfo(instance=obj.first())
        return render(request, 'home.html', {'info': info, 'form': form})


@require_POST
def count(request):
    name = request.common_username
    obj = models.UserInfo.objects.filter(username=name)
    form = userInfo(request.POST, instance=obj.first())

    if form.is_valid():
        form.save()
        return JsonResponse({'status': True})

    return JsonResponse({'status': False, 'errors': form.errors})


@require_POST
def update_avatar(request):
    user = models.UserInfo.objects.filter(username=request.common_username).first()
    image_file = request.FILES.get('image')
    if not image_file:
        return JsonResponse({'ok': 0, 'error': '没有拿到图片'})

    ext = os.path.splitext(image_file.name)[-1].lower()  # 自动拿真实后缀
    new_name = f"{user.username}_头像{ext}"
    image_file.name = new_name

    try:
        # 先删除旧头像记录 + 旧文件
        old_avatar = models.Avatar.objects.filter(user=user).first()
        if old_avatar and old_avatar.avatar:
            # 从硬盘删除旧文件
            if old_avatar.avatar.path:
                if os.path.exists(old_avatar.avatar.path):
                    os.remove(old_avatar.avatar.path)
        # 删除数据库记录
        models.Avatar.objects.filter(user=user).delete()

        # 保存新头像
        new_avatar = models.Avatar.objects.create(
            user=user,
            avatar=image_file
        )

        return JsonResponse({'ok': 1})

    except Exception as e:
        return JsonResponse({'ok': 0, 'error': str(e)})
