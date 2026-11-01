import csv
import json
import os

from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_GET

from app_0 import models


def getFileName():
    with open('local_site.json', 'r', encoding='utf-8') as jsonfile:
        data = json.load(jsonfile)
        source_name = data['localSite']
        source = get_object_or_404(models.SourceSite, name=source_name)
        if source_name == '笔趣阁':
            nf = '笔趣阁/bookInfo.csv'
            cf = '笔趣阁/chapterInfo.csv'
        elif source_name == '悠久小说网':
            nf = '悠久小说网/bookInfo.csv'
            cf = '悠久小说网/chapterInfo.csv'
        elif source_name == '看书阁':
            nf = '看书阁/bookInfo.csv'
            cf = '看书阁/chapterInfo.csv'
        return nf, cf, source


@require_GET
def book_info_import(request):
    NOVEL_FILE, CHAPTER_FILE, source = getFileName()
    success_count = 0
    error_count = 0
    error_list = []

    try:
        with open(NOVEL_FILE, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)  # 跳过表头
            rows = list(reader)

        if not rows:
            return JsonResponse({'code': 200, 'msg': '文件无数据'})

        book_ids = []
        create_list = []
        update_list = []

        for idx, row in enumerate(rows):
            try:
                if not row or len(row) < 10:
                    continue

                book_id = row[0].strip()
                author = row[1].strip()
                book_name = row[2].strip()
                introduction = row[3].strip()
                status = row[4].strip()
                last_chapter_name = row[5].strip()
                last_chapter_id = row[6].strip()
                last_updated = row[7].strip()
                category = row[8].strip()
                cover = row[9].strip()

                book = models.BookInfo(
                    book_id=int(book_id),
                    source=source,
                    author=author,
                    book_name=book_name,
                    introduction=introduction,
                    status=status,
                    category=category,
                    cover=cover,
                    last_updated=last_updated,
                    last_chapter_id=int(last_chapter_id),
                    last_chapter_name=last_chapter_name,
                )

                book_ids.append(book_id)
                update_list.append(book)

            except Exception as e:
                error_count += 1
                error_list.append(f"第{idx + 2}行失败：{str(e)}")

        # 批量操作：原子事务，要么全成功，要么全回滚
        with transaction.atomic():
            # 批量查询已存在的 book_id
            existing_books = set(
                models.BookInfo.objects.filter(book_id__in=book_ids, source=source).values_list('book_id', flat=True)
            )

            for book in update_list:
                if book.book_id in existing_books:

                    models.BookInfo.objects.filter(book_id=book.book_id, source=source).update(
                        source=book.source,
                        author=book.author,
                        book_name=book.book_name,
                        introduction=book.introduction,
                        status=book.status,
                        category=book.category,
                        cover=book.cover,
                        last_updated=book.last_updated,
                        last_chapter_id=book.last_chapter_id,
                        last_chapter_name=book.last_chapter_name,
                    )
                    success_count += 1
                else:
                    create_list.append(book)

            if create_list:
                models.BookInfo.objects.bulk_create(create_list, batch_size=500)
                success_count += len(create_list)

        # 返回结果
        return JsonResponse({
            'code': 200,
            'msg': '批量导入完成',
            '成功': success_count,
            '失败': error_count,
            '错误': error_list[:10]
        })

    except FileNotFoundError:
        return JsonResponse({'code': 200, 'msg': '未找到数据文件'})
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'msg': f'批量导入失败：{str(e)}',
            '成功': success_count,
            '失败': error_count
        })


@require_GET
def book_chapter_import(request):
    NOVEL_FILE, CHAPTER_FILE, source = getFileName()
    success_count = 0
    error_count = 0
    batch_size = 500
    chapter_batch = []

    if not os.path.exists(CHAPTER_FILE):
        return JsonResponse({"code": 200, "msg": "没有数据需要导入"}, status=200)

    try:
        with open(CHAPTER_FILE, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            next(reader)
            rows = list(reader)

        book_ids = {row[0].strip() for row in rows if row and row[0].strip()}

        book_map = {
            str(book.book_id): book
            for book in models.BookInfo.objects.filter(book_id__in=book_ids, source=source)
        }

        existing_keys = set()

        if book_map:
            book_db_ids = [book.id for book in book_map.values()]

            existing_keys = set(models.ChapterInfo.objects.filter(
                book_id__in=book_db_ids
            ).values_list('book_id', 'chapter_id'))

        # 开始正式导入
        for row_num, row in enumerate(rows, start=2):
            try:
                # 行数据为空直接跳过
                if not row:
                    print(f"[导入失败] 第{row_num}行：数据行为空")
                    error_count += 1
                    continue

                # 列数不足
                if len(row) < 5:
                    print(f"[导入失败] 第{row_num}行：CSV列数不足，至少需要5列")
                    error_count += 1
                    continue

                book_id = row[0].strip()
                chapter_name = row[2].strip()
                chapter_id = row[3].strip()
                content = row[4]

                # 字段缺失
                if not all([book_id, chapter_name, chapter_id, content]):
                    print(f"[导入失败] 第{row_num}行：字段不完整（book_id、章节名、章节ID、内容不能为空）")
                    error_count += 1
                    continue

                # 找不到对应书籍
                book = book_map.get(book_id)
                if not book:
                    print(f"[导入失败] 第{row_num}行：book_id={book_id} 在数据库中不存在或来源不匹配")
                    error_count += 1
                    continue

                try:
                    int(chapter_id)
                except:
                    print(f"[导入失败] 第{row_num}行：chapter_id={chapter_id} 不是有效数字")
                    error_count += 1
                    continue

                unique_key = (book.id, chapter_id)
                if unique_key in existing_keys:
                    continue

                chapter_batch.append(
                    models.ChapterInfo(
                        book=book,
                        title=chapter_name,
                        content=content,
                        chapter_id=int(chapter_id),
                    )
                )

                if len(chapter_batch) >= batch_size:
                    models.ChapterInfo.objects.bulk_create(chapter_batch, ignore_conflicts=True)
                    success_count += len(chapter_batch)
                    chapter_batch = []

            except Exception as e:
                # 捕获未知异常
                print(f"[导入失败] 第{row_num}行：未知错误 => {str(e)}")
                error_count += 1
                continue

        if chapter_batch:
            models.ChapterInfo.objects.bulk_create(chapter_batch, ignore_conflicts=True)
            success_count += len(chapter_batch)

        if os.path.exists(CHAPTER_FILE):
            os.remove(CHAPTER_FILE)

        return JsonResponse({
            "code": 200,
            "msg": "章节批量导入完成",
            "成功条数": success_count,
            "失败条数": error_count
        })

    except Exception as e:
        print(f"[导入异常] 整体导入失败：{str(e)}")
        return JsonResponse({
            "code": 500,
            "msg": f"导入异常，已自动回滚：{str(e)}"
        }, status=500)
