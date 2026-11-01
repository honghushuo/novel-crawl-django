import asyncio
import csv
import json
import os

import aiohttp
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from lxml import etree

from app_0 import models

CSV_FILE_PATH = '看书阁/bookInfo.csv'
UPDATE_LOG = "看书阁/chapterInfo_updated.txt"

JSON_PATH = 'local_site.json'

dirname = '看书阁'
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
                    'source_id': 3,
                })
            except Exception:
                continue

        existing_books = set(
            models.BookInfo.objects.filter(book_id__in=book_ids, source_id=3).values_list('book_id', flat=True))
        json_data = []

        for item in update_list:
            if item['book_id'] in existing_books:
                try:
                    book = models.BookInfo.objects.get(source_id=3, book_id=item['book_id'])
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


async def fetch_book(session, book_id):
    try:
        url = f"https://www.zjuyc.com/files/{book_id}/"
        async with session.get(url, timeout=15) as resp:
            resp.raise_for_status()
            content = await resp.text()

        page = etree.HTML(content)
        chapterList = page.xpath('//td[@class="L"]/a')

        cid_list = []
        for chapter in chapterList:
            try:
                chapter_id = chapter.xpath('./@href')[0].split('/')[-1].split('.')[0]
                cid_list.append(chapter_id)
            except:
                continue
        return cid_list
    except:
        return []


async def run_batch_crawl(book_list):
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_book(session, book_id) for book_id in book_list]
        return await asyncio.gather(*tasks)


@csrf_exempt
@require_POST
def update(request):
    try:
        update_data = json.loads(request.body)
        if not isinstance(update_data, list):
            return JsonResponse({"code": 400, "msg": "数据错误"}, status=400)

        task_list = []
        book_id_map = {}

        for item in update_data:
            try:
                book_id = item.get('book_id')
                start = int(item.get('start', 0))
                book_token = models.BookInfo.objects.get(book_id=book_id, source_id=2)
                count = models.ChapterInfo.objects.filter(book=book_token).count()
                print(book_token, count)

                book_id_map[str(book_id)] = {
                    "start": start,
                    "count": count,
                }
                task_list.append(book_id)
            except:
                continue

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        all_cid_list = loop.run_until_complete(run_batch_crawl(task_list))

        with open(UPDATE_LOG, 'a', encoding='utf-8') as f:
            for i, cid_list in enumerate(all_cid_list):
                book_id = task_list[i]
                info = book_id_map.get(str(book_id))
                if not info:
                    continue

                start = info['start']
                count = info['count']

                start_index = -1
                for idx, cid in enumerate(cid_list):
                    if idx == count:
                        start_index = idx
                        break

                if start_index != -1:
                    update_list = cid_list[start_index:]
                    for num, cid in enumerate(update_list):
                        msg = f"待更新 小说Id: {book_id} - 站点章节: {cid} - 存入ID: {num + count} | （需要更新章节）"
                        f.write(msg + '\n')
                        f.flush()

        return JsonResponse({
            'code': 200,
            'msg': '更新记录完成，请转到章节重爬'
        }, status=200)

    except Exception as e:
        return JsonResponse({"code": 500, "msg": f"错误：{str(e)}"}, status=500)


@require_GET
def update_page(request):
    count = models.BookInfo.objects.filter(source_id=3).count()
    return render(request, 'update_2.html', {'count': count, 'source_name': '看书阁', 'source_id': 3})
