import csv
import json
import os

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from app_0 import models
from app_0.models import BookInfo

CSV_FILE_PATH = '笔趣阁/bookInfo.csv'
UPDATE_LOG = "笔趣阁/chapterInfo_updated.txt"

JSON_PATH = 'local_site.json'

dirname = '笔趣阁'
os.makedirs(dirname, exist_ok=True)


def get_site():
    with open(JSON_PATH, 'r', encoding='utf-8') as jsonfile:
        data = json.load(jsonfile)
        sname = data.get('localSite', '笔趣阁')
        if sname == '笔趣阁':
            return sname, 1
        elif sname == '悠久小说网':
            return sname, 2
        elif sname == '看书阁':
            return sname, 3


@require_GET
def update_check(request):
    try:
        if not os.path.exists(CSV_FILE_PATH):
            return JsonResponse({'code': 400, 'msg': 'CSV文件不存在', 'data': []})

        try:
            with open(CSV_FILE_PATH, 'r', encoding='utf-8', newline='') as csvfile:
                reader = csv.reader(csvfile)
                next(reader, None)
                rows = [row for row in reader if row and len(row) >= 10]
        except Exception as e:
            return JsonResponse({'code': 500, 'msg': f'CSV读取失败：{str(e)}', 'data': []})

        if not rows:
            return JsonResponse({'code': 200, 'msg': '文件无数据', 'data': []})

        source = get_object_or_404(models.SourceSite, name='笔趣阁')
        book_ids = []
        update_list = []

        for row in rows:
            try:
                book_id = int(str(row[0]).strip())
                last_chapter_id = str(row[6]).strip()
                book_ids.append(book_id)
                update_list.append({
                    'book_id': book_id,
                    'last_chapter_id': last_chapter_id,
                    'source': source.id,
                })
            except Exception:
                continue

        existing_books = set(
            models.BookInfo.objects.filter(book_id__in=book_ids, source=source).values_list('book_id', flat=True))
        json_data = []

        for item in update_list:
            if item['book_id'] in existing_books:
                try:
                    book = models.BookInfo.objects.get(source=source, book_id=item['book_id'])
                    old_cid = str(book.last_chapter_id or 0)
                    new_cid = str(item['last_chapter_id'] or 0)
                    if old_cid != new_cid and new_cid.isdigit():
                        json_data.append({
                            'book_id': item['book_id'],
                            'start': int(old_cid),
                            'end': int(new_cid),
                        })
                except Exception:
                    continue

        if json_data:
            return JsonResponse({'code': 200, 'msg': f'检查完成，共{len(json_data)}本需要更新', 'data': json_data},
                                safe=False)
        else:
            return JsonResponse({'code': 200, 'msg': '暂无需要更新的小说', 'data': []}, safe=False)

    except Exception as e:
        return JsonResponse({'code': 500, 'msg': f'服务器错误：{str(e)}', 'data': []})


@csrf_exempt
@require_POST
def update(request):
    try:
        try:
            update_data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"code": 400, "msg": "JSON格式错误"}, status=400)

        if not isinstance(update_data, list) or len(update_data) == 0:
            return JsonResponse({"code": 400, "msg": "数据为空"}, status=400)

        for item in update_data:
            book_id = item.get('book_id')
            end = int(item.get('end', 0))
            book_token = get_object_or_404(BookInfo, book_id=book_id, source_id=1)
            start = models.ChapterInfo.objects.filter(book=book_token).order_by('chapter_id').last().chapter_id
            for cid in range(start, end + 1):
                msg = f"待更新 {book_id}-{cid} | （需要更新章节）"
                with open(UPDATE_LOG, 'a', encoding='utf-8') as f:
                    f.write(msg + '\n')

        return JsonResponse({
            'code': 200,
            'msg': '更新记录完成，请转到章节重爬'
        }, status=200)

    except Exception as e:
        return JsonResponse({"code": 500, "msg": f"系统异常：{str(e)}"}, status=500)


@require_GET
def update_page(request):
    source_name, source_id = get_site()
    count = models.BookInfo.objects.filter(source_id=1).count()
    return render(request, 'update.html', {'count': count, 'source_name': source_name, 'source_id': source_id})
