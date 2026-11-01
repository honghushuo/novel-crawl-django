import asyncio
import csv
import json
import os
import re
from datetime import datetime

import aiohttp
from aiohttp import ClientTimeout
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from lxml import etree

CONFIG_FILE = "看书阁/chapterInfo_crawl_config.json"
NOVEL_CSV = "看书阁/bookInfo.csv"
CHAPTER_CSV = "看书阁/chapterInfo.csv"
FAIL_LOG = "看书阁/chapterInfo_crawl_log.txt"
PASS_LOG = "看书阁/passed_book.txt"
UPDATE_LOG = "看书阁/chapterInfo_updated.txt"
CSV_HEADERS = ["book_id", "novel_title", "chaptername", "chapterid", "content"]
FAIL_BOOK = "看书阁/faild_book.txt"
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


# 默认配置
DEFAULT_CONFIG = {
    "NOVEL_SEMAPHORE": 5,
    "CHAPTER_SEMAPHORE": 10,
    "RETRY_SEMAPHORE": 5,
    "NOVEL_NUM": 500,
    "BASE_URL": "https://www.zjuyc.com/files/",
    "TIMEOUT": 15
}

# 文件句柄（统一开关）
_csv_file = None
_csv_writer = None
_fail_file = None


def init_config_file():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                json.load(f)
            return
    except:
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=4)


def get_config():
    init_config_file()
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(new_config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(new_config, f, ensure_ascii=False, indent=4)


config = get_config()
init_config_file()

# ===================== 全局爬取状态 =====================
CRAWL_STATUS = {
    "running": False,
    "success_count": 0,
    "fail_count": 0,
    "logs": [],
    "finish": False
}


# ===================== 统一打开 / 关闭文件 =====================
def open_files():
    global _csv_file, _csv_writer, _fail_file
    if not os.path.exists(CHAPTER_CSV):
        _csv_file = open(CHAPTER_CSV, 'w', encoding='utf-8-sig', newline='')
        _csv_writer = csv.writer(_csv_file)
        _csv_writer.writerow(CSV_HEADERS)
    else:
        _csv_file = open(CHAPTER_CSV, 'a', encoding='utf-8', newline='')
        _csv_writer = csv.writer(_csv_file)

    # 失败日志
    _fail_file = open(FAIL_LOG, 'a', encoding='utf-8')


def close_files():
    global _csv_file, _csv_writer, _fail_file
    try:
        if _csv_file:
            _csv_file.close()
        if _fail_file:
            _fail_file.close()
    except:
        pass


# ===================== 工具函数 =====================
def add_log(msg):
    time_msg = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    CRAWL_STATUS["logs"].append(time_msg)
    if len(CRAWL_STATUS["logs"]) > 200:
        CRAWL_STATUS["logs"].pop(0)


def clean_text(text):
    if not text:
        return "空"
    text = re.sub(r'[\n\r\t]', ' ', str(text))
    return text.replace(',', '，').strip() or "空"


def clean_content(text):
    if not text:
        return "弄丢了"
    try:
        if isinstance(text, bytes):
            text = text.decode('utf-8', 'ignore')
    except:
        pass
    text = str(text)
    text = text.replace(',', '，').replace('&nbsp;', ' ').replace(' ', ' ').strip()
    text = re.sub(r'[a-zA-Z0-9]+.*?(com|cc|org|de)', '。', text)
    text = re.sub(r" +", " ", text)
    text = re.sub(r'\n+', '\n', text).strip()
    text = re.sub(r'\(\)', '', text)
    return text


def save_to_csv(data):
    row = [
        clean_text(data.get('book_id')),
        clean_text(data.get('title')),
        clean_text(data.get('chaptername')),
        clean_text(data.get('chapterid')),
        clean_content(data.get('content'))
    ]
    _csv_writer.writerow(row)
    _csv_file.flush()


# ===================== 安全写入已爬小说ID =====================
def write_passed_bid(bid):
    with open(PASS_LOG, 'a', encoding='utf-8') as f:
        f.write(f"{bid}\n")


# ===================== 核心爬取 =====================
async def fetch_chapter(session, book_id, cid, sem, num):
    url = f"{config['BASE_URL']}{book_id}/{cid}.html"
    async with sem:
        try:
            async with session.get(url, timeout=ClientTimeout(total=config['TIMEOUT'])) as resp:
                if resp.status != 200:
                    msg = f"❌ 失败 小说Id: {book_id} - 站点章节: {cid} - 存入ID: {num} | 状态码:{resp.status}"
                    add_log(msg)
                    CRAWL_STATUS["fail_count"] += 1
                    _fail_file.write(msg + '\n')
                    _fail_file.flush()
                    return

                raw_content = await resp.read()
                try:
                    text = raw_content.decode('gbk')
                except:
                    try:
                        text = raw_content.decode('gb2312')
                    except:
                        text = raw_content.decode('utf-8', 'ignore')

                page = etree.HTML(text)

                # 提取 小说名 book_name
                book_name_list = page.xpath('//script[contains(text(),"info.book_name")]/text()')
                book_name = ""
                if book_name_list:
                    script_text = book_name_list[0]
                    if 'info.book_name' in script_text:
                        # 分割提取书名
                        book_name = script_text.split('info.book_name = \'')[1].split('\';')[0].strip()

                # 提取 章节名 chapter_name
                chapter_name_list = page.xpath('//h1/text()')
                chapter_name = chapter_name_list[0].strip() if chapter_name_list else ""

                content_list = page.xpath('//div[@id="htmlContent"]//p/text()')
                content = '\n'.join(content_list)

                data = {
                    "book_id": book_id,
                    "title": book_name,
                    "chaptername": chapter_name,
                    "chapterid": num,
                    "content": content
                }
                save_to_csv(data)
                add_log(f"✅ 成功 {book_id}-{cid}")
                CRAWL_STATUS["success_count"] += 1

        except Exception as e:
            msg = f"❌ 错误 小说Id: {book_id} - 站点章节: {cid} - 存入ID: {num} | {str(e)}"
            add_log(msg)
            CRAWL_STATUS["fail_count"] += 1
            _fail_file.write(msg + '\n')
            _fail_file.flush()


async def crawl_book(session, book_id, novel_sem):
    async with novel_sem:
        try:
            url = f"{config['BASE_URL']}{book_id}" + "/"
            print(url)
            async with session.get(url, timeout=ClientTimeout(total=config['TIMEOUT'])) as resp:
                if resp.status != 200:
                    add_log(f"❌ 获取小说目录失败 {book_id} 状态码:{resp.status}")
                    with open(FAIL_BOOK, 'a', encoding='utf-8') as f:
                        f.write(f"❌ 获取小说目录失败 {book_id} \n")
                    return
                content = await resp.text()
                write_passed_bid(book_id)

            page = etree.HTML(content)
            chapterList = page.xpath('//td[@class="L"]/a')
            cid_list = []
            for chapter in chapterList:
                chapter_id = chapter.xpath('./@href')[0].split('/')[-1].split('.')[0]
                cid_list.append(chapter_id)

            add_log(f"\n🚀 开始爬取 小说{book_id} 共{len(cid_list)}章")
            chapter_sem = asyncio.Semaphore(config["CHAPTER_SEMAPHORE"])

            tasks = [fetch_chapter(session, book_id, cid, chapter_sem, num + 1) for num, cid in enumerate(cid_list)]
            await asyncio.gather(*tasks)

        except Exception as e:
            add_log(f"❌ 爬取小说{book_id}失败")
            with open(FAIL_BOOK, 'a', encoding='utf-8') as f:
                f.write(f"❌ 获取小说目录失败 {book_id} \n")


def open_noveldata():
    if not os.path.exists(PASS_LOG):
        return set()
    with open(PASS_LOG, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    return set(lines)


async def main_chapter_crawl():
    open_files()

    try:
        with open(NOVEL_CSV, 'r', encoding='utf-8') as f:
            novel_list = [r[0] for r in csv.reader(f) if len(r) >= 7][1:]
    except:
        add_log("❌ 未找到 novel_data.csv 文件")
        CRAWL_STATUS["running"] = False
        close_files()
        return

    if not novel_list:
        add_log("❌ 无小说数据可爬取")
        CRAWL_STATUS["running"] = False
        close_files()
        return

    add_log(f"📚 共加载 {len(novel_list)} 本小说")

    novel_sem = asyncio.Semaphore(config["NOVEL_SEMAPHORE"])

    passed = open_noveldata()
    novel_num = 0
    tasks = []

    async with aiohttp.ClientSession() as session:
        for bid in novel_list:
            if bid not in passed:
                novel_num += 1
                summ = novel_num + len(passed)
                if summ > config["NOVEL_NUM"]:
                    break

                tasks.append(crawl_book(session, bid, novel_sem))
        await asyncio.gather(*tasks)

    close_files()
    CRAWL_STATUS["running"] = False
    CRAWL_STATUS["finish"] = True
    add_log(f"\n🏁 全部爬取完成！成功：{CRAWL_STATUS['success_count']} 失败：{CRAWL_STATUS['fail_count']}")


# ===================== 重爬失败 =====================
def get_failed_chapters():
    failed = []
    if not os.path.exists(FAIL_LOG):
        return failed
    with open(FAIL_LOG, 'r', encoding='utf-8') as f:
        for line in f:
            nums = re.findall(r'\d+', line)
            if len(nums) >= 3:
                failed.append({"bid": nums[0], "cid": nums[1], "num": nums[2]})
    return failed


def get_failed_books():
    failed = []
    if not os.path.exists(FAIL_BOOK):
        return failed
    with open(FAIL_BOOK, 'r', encoding='utf-8') as f:
        for line in f:
            nums = re.findall(r'\d+', line)
            if len(nums) >= 1:
                failed.append(nums[0])
    return failed


def get_updated_chapters():
    updated = []
    if not os.path.exists(UPDATE_LOG):
        return updated
    with open(UPDATE_LOG, 'r', encoding='utf-8') as f:
        for line in f:
            nums = re.findall(r'\d+', line)
            if len(nums) >= 3:
                updated.append({"bid": nums[0], "cid": nums[1], "num": nums[2]})
    return updated


async def retry_failed_chapters():
    open_files()

    b_failed = get_failed_books()
    CRAWL_STATUS.update({"running": True, "fail_count": 0, "finish": False})

    open(FAIL_BOOK, 'w').close()
    if b_failed:
        novel_sem = asyncio.Semaphore(config["NOVEL_SEMAPHORE"])
        tasks = []
        async with aiohttp.ClientSession() as session:
            for bid in b_failed:
                tasks.append(crawl_book(session, bid, novel_sem))
            await asyncio.gather(*tasks)

    failed = get_failed_chapters()
    if not failed and not b_failed:
        add_log("🎉 无失败章节，无需重爬")
        return
    add_log(f"🔄 开始重爬 {len(failed)} 个章节")
    open(FAIL_LOG, 'w').close()
    sem = asyncio.Semaphore(config["RETRY_SEMAPHORE"])
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_chapter(session, i['bid'], i['cid'], sem, i['num']) for i in failed]
        await asyncio.gather(*tasks)

    close_files()
    add_log("✅ 重爬完成！")
    CRAWL_STATUS["running"] = False
    CRAWL_STATUS["finish"] = True


async def crawl_updated_chapters():
    updated = get_updated_chapters()
    if not updated:
        add_log("🎉 暂无需要更新的章节")
        return
    CRAWL_STATUS.update({"running": True, "fail_count": 0, "finish": False})
    add_log(f"🔄 开始更新 {len(updated)} 个章节")
    open(UPDATE_LOG, 'w').write('')
    open_files()
    try:
        sem = asyncio.Semaphore(config["RETRY_SEMAPHORE"])
        async with aiohttp.ClientSession() as session:
            tasks = [fetch_chapter(session, i['bid'], i['cid'], sem, i['num']) for i in updated]
            await asyncio.gather(*tasks)
    finally:
        close_files()
    add_log("✅ 更新完成")
    CRAWL_STATUS["running"] = False
    CRAWL_STATUS["finish"] = True


# ===================== Django 接口 =====================
def chapter_crawl_page(request):
    source_name, source_id = get_site()
    return render(request, 'chapter_crawl_2.html', {'source_name': source_name, 'source_id': source_id})


@require_GET
def get_real_time_status(request):
    data = CRAWL_STATUS.copy()
    data["novel_sem"] = config["NOVEL_SEMAPHORE"]
    data["chapter_sem"] = config["CHAPTER_SEMAPHORE"]
    data["retry_sem"] = config["RETRY_SEMAPHORE"]
    data["novel_num"] = config["NOVEL_NUM"]
    return JsonResponse(data)


@require_POST
def save_chapter_config(request):
    if CRAWL_STATUS["running"]:
        return JsonResponse({"status": False, "msg": "爬取中禁止修改配置！"})
    try:
        config["NOVEL_SEMAPHORE"] = int(request.POST.get("novel_sem"))
        config["CHAPTER_SEMAPHORE"] = int(request.POST.get("chapter_sem"))
        config["RETRY_SEMAPHORE"] = int(request.POST.get("retry_sem"))
        config["NOVEL_NUM"] = int(request.POST.get("novel_num"))
        save_config(config)
        add_log("✅ 配置保存成功！")
        return JsonResponse({"status": True, "msg": "保存成功"})
    except:
        return JsonResponse({"status": False, "msg": "保存失败"})


def run_async_task(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(coro)
    finally:
        loop.close()


def start_chapter_crawl(request):
    if CRAWL_STATUS["running"]:
        return JsonResponse({"status": False, "msg": "任务正在运行！"})
    CRAWL_STATUS.update({
        "running": True, "success_count": 0, "fail_count": 0,
        "logs": [], "finish": False
    })
    run_async_task(main_chapter_crawl())
    return JsonResponse({"status": True, "msg": "爬取完成"})


def retry_chapter_crawl(request):
    if CRAWL_STATUS["running"]:
        return JsonResponse({"status": False, "msg": "任务正在运行！"})
    run_async_task(retry_failed_chapters())
    return JsonResponse({"status": True, "msg": "重爬完成"})


def updete_chapter(request):
    if CRAWL_STATUS["running"]:
        return JsonResponse({"status": False, "msg": "任务运行中"})
    run_async_task(crawl_updated_chapters())
    return JsonResponse({"status": True, "msg": "更新完成"})
