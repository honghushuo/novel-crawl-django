import asyncio
import csv
import json
import os
import re
from datetime import datetime

import aiohttp
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST
from lxml import etree

CONFIG_FILE = "悠久小说网/bookInfo_crawl_config.json"
CSV_FILE = "悠久小说网/bookInfo.csv"
FAIL_LOG = "悠久小说网/bookInfo_crawl_log.txt"
CSV_HEADERS = ["book_id", "author", "title", "intro", "status",
               "lastchapter", "lastchapterid", "lastupdate", "sortname", "cover_url"]
JSON_PATH = 'local_site.json'

dirname = '悠久小说网'
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


# ===================== 全局文件句柄 =====================
_csv_fp = None
_csv_writer = None
_fail_fp = None


# 初始化配置文件
def init_config_file():
    if not os.path.exists(CONFIG_FILE):
        default_config = {
            "general_url": 'http://wap.ujxsw.org/book/',
            'book_id': 1,
            "MAX_CONCURRENT": 50,
            "AGAIN_SEMAPHORE": 4,
            "MAX_NOT_EXIST": 20,
            "MAX_CRAWL_NUM": 500
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_config, f, ensure_ascii=False, indent=4)


def get_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(new_config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(new_config, f, ensure_ascii=False, indent=4)


init_config_file()

# ===================== 全局爬取状态 =====================
CRAWL_STATUS = {
    "running": False,
    "current_id": 1,
    "success_count": 0,
    "fail_count": 0,
    "logs": [],
    "finish": False
}


# ===================== 统一打开 / 关闭文件 =====================
def open_all_files():
    global _csv_fp, _csv_writer, _fail_fp
    # 打开 CSV
    _csv_fp = open(CSV_FILE, 'a', encoding='utf-8-sig', newline='')
    _csv_writer = csv.writer(_csv_fp)

    # 打开失败日志
    _fail_fp = open(FAIL_LOG, 'a', encoding='utf-8')


def close_all_files():
    global _csv_fp, _csv_writer, _fail_fp
    try:
        if _csv_fp:
            _csv_fp.close()
        if _fail_fp:
            _fail_fp.close()
    except:
        pass


# ===================== 工具函数 =====================
def init_csv_header():
    if os.path.exists(CSV_FILE):
        os.remove(CSV_FILE)
    with open(CSV_FILE, 'w', encoding='utf-8-sig', newline='') as f:
        csv.writer(f).writerow(CSV_HEADERS)
    add_log("✅ CSV文件已创建并写入表头")


def clean_text(text):
    if text is None or text == '':
        return '空'
    cleaned = re.sub(r'[\n\r\t]', '', str(text))
    cleaned = re.sub(r'&nbsp;', '', cleaned)
    cleaned = cleaned.replace(',', '，')
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned if cleaned else '空'


def add_log(msg):
    time_msg = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    CRAWL_STATUS["logs"].append(time_msg)
    if len(CRAWL_STATUS["logs"]) > 100:
        CRAWL_STATUS["logs"].pop(0)


# ===================== 核心爬取函数（修复信号量，标准异步） =====================
async def get_single_intro(url, semaphore, session):
    book_id = url.split('/')[-1]
    async with semaphore:
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    pre_data = await response.text()
                    page = etree.HTML(pre_data)

                    title = page.xpath("//h1[@id='52mb_h1']//text()")[0]
                    author = \
                        page.xpath("//div[@class='cover']/div[@class='block']//p[contains(text(),'作者')]/a/text()")[
                            0].strip()
                    cover_url = \
                        page.xpath("//div[@class='cover']/div[@class='block']//div[@class='block_img2']/img/@src")[
                            0].strip()
                    sortname = \
                        page.xpath("//div[@class='cover']/div[@class='block']//p[contains(text(),'分类')]/a/text()")[
                            0].strip()
                    status = \
                        page.xpath("//div[@class='cover']/div[@class='block']//p[contains(text(),'状态')]/text()")[
                            0].split(
                            '：')[-1].strip()
                    lastupdate = \
                        page.xpath("//div[@class='cover']/div[@class='block']//p[contains(text(),'更新时间')]/text()")[
                            0].split('：')[-1].strip()
                    lastchapter = \
                        page.xpath(
                            "//div[@class='cover']/div[@class='block']//p[contains(text(),'最新章节')]/a/text()")[
                            0].strip()
                    lastchapterid = \
                        page.xpath("//div[@class='cover']/div[@class='block']//p[contains(text(),'最新章节')]/a/@href")[
                            0].split('/')[-1].split('.')[0]
                    intro = page.xpath('//div[@class="bk-intro-bd"]//text()')[1]
                    intro = clean_text(intro)

                    csv_row = [book_id, author, title, intro, status,
                               lastchapter, lastchapterid, lastupdate, sortname, cover_url]

                    # 直接写入，不再打开关闭
                    _csv_writer.writerow(csv_row)
                    _csv_fp.flush()

                    CRAWL_STATUS["success_count"] += 1
                    add_log(f"✅ 爬取成功 | ID={book_id} | {title}")
                    return [0, 1]

                else:
                    add_log(f"❌ 小说不存在 | ID={book_id}")
                    return [1, 1]

        except asyncio.TimeoutError:
            CRAWL_STATUS["fail_count"] += 1
            msg = f"⏰ 请求超时 | ID={book_id}"
            add_log(msg)
            _fail_fp.write(f"{book_id}请求超时，跳过爬取\n")
            _fail_fp.flush()
            return [0, 1]

        except Exception as e:
            add_log(f"❌ 错误 | ID={book_id} | {str(e)}")
            return [0, 0]


# ===================== 主爬取逻辑 =====================
async def get_intro():
    config = get_config()
    book_id = config['book_id']
    total_not_exist = 0
    total_num = 0
    has_more = True
    semaphore = asyncio.Semaphore(config["MAX_CONCURRENT"])
    pending_tasks = set()

    if os.path.exists(FAIL_LOG):
        os.remove(FAIL_LOG)
    open_all_files()

    try:
        async with aiohttp.ClientSession() as session:
            while has_more or pending_tasks:
                while has_more and len(pending_tasks) < config["MAX_CONCURRENT"]:
                    url = config['general_url'] + str(book_id)
                    task = asyncio.create_task(get_single_intro(url, semaphore, session))
                    task.book_id = book_id
                    pending_tasks.add(task)
                    CRAWL_STATUS["current_id"] = book_id
                    book_id += 1
                    total_num += 1

                    if total_num >= config["MAX_CRAWL_NUM"]:
                        has_more = False

                if pending_tasks:
                    done_tasks, pending_tasks = await asyncio.wait(
                        pending_tasks, return_when=asyncio.FIRST_COMPLETED
                    )

                    for task in done_tasks:
                        st = await task
                        task_flag, task_status = st[0], st[1]

                        if task_flag == 0:
                            total_not_exist = 0
                        else:
                            total_not_exist += 1

                        if task_status == 0 or total_not_exist >= config["MAX_NOT_EXIST"]:
                            has_more = False
                            add_log(f"⚠️ 停止爬取：连续不存在{total_not_exist}本")

            if pending_tasks:
                await asyncio.gather(*pending_tasks)

    finally:
        close_all_files()

    CRAWL_STATUS["running"] = False
    CRAWL_STATUS["finish"] = True
    add_log(f"🏁 爬取完成！总计：{CRAWL_STATUS['success_count']}本成功")


# ===================== 失败ID解析 =====================
def parse_failed_novel_ids():
    if not os.path.exists(FAIL_LOG):
        return []
    failed_ids = []
    pattern = re.compile(r'\d+')
    with open(FAIL_LOG, 'r', encoding='utf-8') as f:
        for line in f:
            match = pattern.search(line.strip())
            if match:
                failed_ids.append(match.group())
    return list(set(failed_ids))


# ===================== 重爬逻辑 =====================
async def revisit(target_list):
    config = get_config()
    open(FAIL_LOG, 'w', encoding='utf-8').close()

    CRAWL_STATUS["fail_count"] = 0
    CRAWL_STATUS["running"] = True

    open_all_files()

    try:
        sem = asyncio.Semaphore(config["AGAIN_SEMAPHORE"])
        async with aiohttp.ClientSession() as session:
            tasks = [get_single_intro(config['general_url'] + f'{tid}', sem, session) for tid in target_list]
            await asyncio.gather(*tasks)
    finally:
        close_all_files()

    CRAWL_STATUS["running"] = False
    CRAWL_STATUS["finish"] = True
    add_log(f"✅ 重爬完成！失败ID：{len(target_list)}个")


# ===================== Django 视图 =====================
def novel_crawl_page(request):
    source_name, source_id = get_site()
    return render(request, 'info_crawl_1.html', {'source_name': source_name, 'source_id': source_id})


@require_GET
def get_crawl_real_time_status(request):
    config = get_config()
    data = CRAWL_STATUS.copy()
    data["max_concurrent"] = config["MAX_CONCURRENT"]
    data["again_sem"] = config["AGAIN_SEMAPHORE"]
    data["max_crawl_num"] = config["MAX_CRAWL_NUM"]
    return JsonResponse(data)


@require_POST
def save_crawl_config(request):
    if CRAWL_STATUS["running"]:
        return JsonResponse({"status": False, "msg": "爬取中禁止修改配置"})
    try:
        config = get_config()
        config["MAX_CONCURRENT"] = int(request.POST.get("max_concurrent", 50))
        config["AGAIN_SEMAPHORE"] = int(request.POST.get("again_sem", 4))
        config["MAX_CRAWL_NUM"] = int(request.POST.get("max_crawl_num", 500))
        save_config(config)
        add_log("✅ 配置保存成功！")
        return JsonResponse({"status": True, "msg": "配置保存成功"})
    except:
        return JsonResponse({"status": False, "msg": "配置保存失败"})


def start_novel_crawl(request):
    if CRAWL_STATUS["running"]:
        return JsonResponse({"status": False, "msg": "任务正在运行"})
    CRAWL_STATUS.update({
        "running": True, "current_id": 1, "success_count": 0,
        "fail_count": 0, "logs": [], "finish": False
    })
    init_csv_header()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(get_intro())

    return JsonResponse({"status": True, "msg": "爬取完成"})


def retry_failed_novel_crawl(request):
    if CRAWL_STATUS["running"]:
        return JsonResponse({"status": False, "msg": "任务正在运行"})
    failed_ids = parse_failed_novel_ids()
    if not failed_ids:
        return JsonResponse({"status": True, "msg": "无失败数据"})

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(revisit(failed_ids))

    return JsonResponse({"status": True, "msg": "重爬完成"})
