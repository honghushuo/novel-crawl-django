import json
import os
import re

from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from app_0 import models

JSON_PATH = 'read_site.json'


@require_POST
def shift_site_now(request):
    localSite = request.POST.get("localSite", "")
    sid = request.POST.get("sourceId", "")

    try:
        sid = int(sid)
    except (ValueError, TypeError):
        sid = 1
        localSite = "笔趣阁"

    site_config = {"localSite": localSite, "sourceId": sid}

    try:
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(site_config, f, ensure_ascii=False, indent=4)

        return JsonResponse({"ok": 1, "msg": f"已切换到：{localSite}"})

    except Exception as e:

        return JsonResponse({"ok": 0, "msg": str(e)})


def get_site():
    if not os.path.exists(JSON_PATH):
        site_config = {"localSite": "笔趣阁", "sourceId": 1}
        with open(JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(site_config, f, ensure_ascii=False, indent=4)
    try:
        with open(JSON_PATH, 'r', encoding='utf-8') as jsonfile:
            data = json.load(jsonfile)
            sname = data.get('localSite', '笔趣阁')
            sid = data.get('sourceId', 1)
            return sname, sid
    except:
        return "笔趣阁", 1


def clean_content(text):
    if not text:
        return "弄丢了"

    text = str(text)

    # 统一标点
    text = text.replace(',', '，').replace('.', '。').replace('?', '？').replace('!', '！')
    text = text.replace(';', '；').replace(':', '：')

    # 过滤网址广告
    text = re.sub(r'https?://\S+|www\.\S+|[a-zA-Z0-9]+.*?(com|cc|org|net|de)', '。', text)
    text = re.sub(r'&emsp；&emsp；', '    ', text)

    # 清空括号
    text = re.sub(r'（）', '', text)
    text = re.sub(r'\(\)', '', text)

    # 多余空行只保留一段
    text = re.sub(r'\n+', '\n', text)

    # 清理首尾空白
    return text.strip()


@require_GET
def category_page(request):
    source_name, source_id = get_site()

    cate = request.GET.get('cate', '')
    keyword = request.GET.get('keyword', '')

    novels = models.BookInfo.objects.filter(source_id=source_id).only(
        'id',
        'source',
        'book_id',
        'status',
        'book_name',
        'author',
        'cover',
        'category',
    )

    # 分类筛选
    if cate == '完本':
        # 完本：单独筛选状态
        novels = novels.filter(status__contains='完').order_by('book_id')
    elif cate == '武侠':
        # 武侠 = 武侠 + 仙侠（合并显示）
        novels = novels.filter(
            Q(category__contains='武侠') | Q(category__contains='仙侠')
        ).order_by('book_id')
    elif cate:
        # 其他正常分类
        novels = novels.filter(category__contains=cate).order_by('book_id')
    else:
        # 全部
        novels = novels.all().order_by('book_id')

    # 关键词搜索
    if keyword:
        novels = models.BookInfo.objects.all()
        novels = novels.filter(
            Q(book_name__icontains=keyword) | Q(author__icontains=keyword)
        )

    count = novels.count()

    return render(request, 'classification.html', {
        'novels': novels,
        'current_category': cate,
        'count': count,
        'keyword': keyword,
        'source_id': source_id,
    })


@require_GET
def novel_page(request, bid):
    user = models.UserInfo.objects.get(username=request.common_username)
    source_id = request.GET.get('source_id')

    if not source_id:
        source_name, source_id = get_site()
    else:
        source_id = int(source_id)  # 确保是数字
    book_id = int(bid)

    # 获取书籍详情
    book_token = get_object_or_404(models.BookInfo, book_id=book_id, source_id=source_id)

    # 章节 必须按 chapter_id 排序
    chapters = models.ChapterInfo.objects.filter(book=book_token).order_by('chapter_id')

    # 是否收藏
    is_collect = models.UserCollection.objects.filter(user=user, book=book_token).exists()

    return render(request, 'novel_detail.html', {
        'novel': book_token,
        'chapters': chapters,
        'is_collect': is_collect
    })


@require_GET
def chapter_page(request, nid, cid):
    source_id = request.GET.get('source_id')

    if not source_id:
        source_name, source_id = get_site()
    else:
        source_id = int(source_id)

    nid = int(nid)
    cid = int(cid)

    book_token = get_object_or_404(models.BookInfo, source_id=source_id, book_id=nid)

    chapters = models.ChapterInfo.objects.filter(book=book_token).order_by('chapter_id')
    chapter = chapters.filter(chapter_id=cid).first()

    if chapter:
        chapter.content = clean_content(chapter.content)

    prev_chapter = chapters.filter(chapter_id__lt=cid).order_by('-chapter_id').first()
    prev_chapter_id = prev_chapter.chapter_id if prev_chapter else None

    next_chapter = chapters.filter(chapter_id__gt=cid).order_by('chapter_id').first()
    next_chapter_id = next_chapter.chapter_id if next_chapter else None

    return render(request, 'chapter_read.html', {
        'chapter': chapter,
        'novel': book_token,
        'prev_chapter_id': prev_chapter_id,
        'next_chapter_id': next_chapter_id
    })


@require_POST
def log_history(request):
    user = models.UserInfo.objects.get(username=request.common_username)
    all_history = models.ReadingHistory.objects.filter(user=user).order_by('-read_time')
    try:
        book_id = int(request.POST.get('book_id'))
        chapter_id = int(request.POST.get('chapter_id'))
        duration = int(request.POST.get('duration', 0))
        source_id = int(request.POST.get('source_id'))
        if not source_id:
            source_name, source_id = get_site()
        else:
            source_id = int(source_id)  # 确保是数字
        if duration < 2:
            return JsonResponse({'ok': 0})

        # 获取书籍
        book = models.BookInfo.objects.get(source_id=source_id, book_id=book_id)

        # 获取这本书的所有章节（按章节ID正序排列）
        all_chapters = models.ChapterInfo.objects.filter(book=book).order_by('chapter_id')

        # 总章节数
        chapter_count = all_chapters.count()

        # 获取当前章节
        chapter_token = get_object_or_404(models.ChapterInfo, book=book, chapter_id=chapter_id)

        try:
            chapter_index = list(all_chapters.values_list('chapter_id', flat=True)).index(chapter_id)
            current_chapter_no = chapter_index + 1  # 第几章
        except ValueError:
            current_chapter_no = 1

        # 阅读进度（当前章 / 总章数）
        try:
            progress = current_chapter_no / chapter_count
        except ZeroDivisionError:
            progress = 0

        title = chapter_token.title

        history = models.ReadingHistory.objects.filter(user=user, book=book).first()

        if history:
            history.read_duration += duration
            history.chapter_id = chapter_id
            history.title = title
            history.read_time = timezone.now()
            history.progress = progress
            history.save()
        else:
            models.ReadingHistory.objects.create(
                user=user, book=book, title=title, chapter_id=chapter_id,
                read_duration=duration, read_time=timezone.now()
            )

        if all_history.count() > 100:
            collected = models.UserCollection.objects.filter(user=user).values_list('book', flat=True)
            all_history[100:].exclude(book__in=collected).delete()

        return JsonResponse({'ok': 1})

    except Exception as e:
        print("记录失败:", str(e))
        return JsonResponse({'ok': 0})


@require_GET
def read_history(request):
    user = get_object_or_404(models.UserInfo, username=request.common_username)
    history = models.ReadingHistory.objects.filter(user=user).order_by('-read_time')
    return render(request, 'read_history.html', {'history': history})


@require_GET
def at_read(request):
    user = get_object_or_404(models.UserInfo, username=request.common_username)
    book_id = request.GET.get('book_id')
    source_id = request.GET.get('source_id')
    book = get_object_or_404(models.BookInfo, book_id=book_id, source_id=source_id)
    history = models.ReadingHistory.objects.filter(user=user, book=book).first()
    if history:
        return JsonResponse({'chapter_id': history.chapter_id})
    else:
        first_chapter = models.ChapterInfo.objects.filter(book=book).order_by('chapter_id').first()
        title = first_chapter.title
        chapter_id = first_chapter.chapter_id
        models.ReadingHistory.objects.create(
            user=user, book=book, title=title, chapter_id=chapter_id, read_duration=0
        )
        return JsonResponse({'chapter_id': chapter_id})


@require_GET
def go_read(request):
    bid = request.GET.get('id')
    chapter_id = request.GET.get('chapterId')
    book_token = get_object_or_404(models.BookInfo, id=bid)
    source_id = book_token.source_id
    return JsonResponse({'chapter_id': chapter_id, 'source_id': source_id})


@require_GET
def delete_history(request):
    user = get_object_or_404(models.UserInfo, username=request.common_username)
    history_id = request.GET.get('history_id')
    try:
        history = models.ReadingHistory.objects.get(user=user, id=history_id)
        is_collected = models.UserCollection.objects.filter(user=user, book=history.book).exists()
        if not is_collected:
            history.delete()
            return JsonResponse({'ok': 1})
        else:
            return JsonResponse({'ok': 0, 'errors': '已收藏，无法删除'})
    except:
        return JsonResponse({'ok': 0, 'errors': '删除失败'})


@require_POST
def batch_delete_history(request):
    user = get_object_or_404(models.UserInfo, username=request.common_username)
    ids = request.POST.get('ids', '')
    if not ids:
        return JsonResponse({'ok': 0, 'errors': '未选择'})
    try:
        id_list = [int(i) for i in ids.split(',')]
        collected = models.UserCollection.objects.filter(user=user).values_list('book', flat=True)
        models.ReadingHistory.objects.filter(id__in=id_list, user=user).exclude(book__in=collected).delete()
        return JsonResponse({'ok': 1})
    except:
        return JsonResponse({'ok': 0})


@require_GET
def confirm_collection(request):
    source_id = request.GET.get('source_id')
    user = get_object_or_404(models.UserInfo, username=request.common_username)
    book_id = request.GET.get('book_id')
    book = get_object_or_404(models.BookInfo, book_id=book_id, source_id=source_id)
    try:
        models.UserCollection.objects.create(user=user, book=book, updated_at=book.last_updated)
        return JsonResponse({'ok': 1})
    except:
        return JsonResponse({'ok': 0})


@require_GET
def cancel_collection(request):
    source_id = request.GET.get('source_id')
    user = get_object_or_404(models.UserInfo, username=request.common_username)
    book_id = request.GET.get('book_id')
    book = get_object_or_404(models.BookInfo, book_id=book_id, source_id=source_id)
    models.UserCollection.objects.filter(user=user, book=book).delete()
    return JsonResponse({'ok': 1})


@require_GET
def bookshelf(request):
    user = get_object_or_404(models.UserInfo, username=request.common_username)
    collections = models.UserCollection.objects.filter(user=user).order_by('-created_at')
    shelf_books = []
    for coll in collections:
        history = models.ReadingHistory.objects.filter(user=user, book=coll.book).order_by('-read_time').first()
        shelf_books.append({'id': coll.id, 'book': coll.book, 'history': history})
    return render(request, 'bookshelf.html', {'shelf_books': shelf_books})


@require_POST
def batch_shift_bookshelf(request):
    user = get_object_or_404(models.UserInfo, username=request.common_username)
    ids = request.POST.get('ids', '')
    if not ids:
        return JsonResponse({'ok': 0})
    id_list = [int(i) for i in ids.split(',')]
    models.UserCollection.objects.filter(id__in=id_list, user=user).delete()
    return JsonResponse({'ok': 1})
