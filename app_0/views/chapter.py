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

# ===================== 配置 =====================
CONFIG_FILE = "笔趣阁/chapterInfo_crawl_config.json"
NOVEL_CSV = "笔趣阁/bookInfo.csv"
CHAPTER_CSV = "笔趣阁/chapterInfo.csv"
FAIL_LOG = "笔趣阁/chapterInfo_crawl_log.txt"
UPDATE_LOG = "笔趣阁/chapterInfo_updated.txt"
PASS_NOVEL = "笔趣阁/passed_book.txt"
CSV_HEADERS = ["book_id", "novel_title", "chaptername", "chapterid", "content"]
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


DEFAULT_CONFIG = {
    "NOVEL_SEMAPHORE": 3,
    "CHAPTER_SEMAPHORE": 5,
    "RETRY_SEMAPHORE": 5,
    "NOVEL_NUM": 4,
    "BASE_URL": "https://apibi.cc/api/chapter?",
    "TIMEOUT": 10
}

# ===================== 全局文件句柄（统一开关） =====================
_csv_fp = None
_csv_writer = None
_fail_fp = None


# ===================== 配置文件 =====================
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


init_config_file()
config = get_config()
# ===================== 全局状态 =====================
CRAWL_STATUS = {
    "running": False,
    "success_count": 0,
    "fail_count": 0,
    "logs": [],
    "finish": False
}


# ===================== 统一打开 / 关闭文件 =====================
def open_all_files():
    global _csv_fp, _csv_writer, _fail_fp
    # 章节 CSV
    if not os.path.exists(CHAPTER_CSV):
        _csv_fp = open(CHAPTER_CSV, 'w', encoding='utf-8-sig', newline='')
        _csv_writer = csv.writer(_csv_fp)
        _csv_writer.writerow(CSV_HEADERS)
    else:
        _csv_fp = open(CHAPTER_CSV, 'a', encoding='utf-8', newline='')
        _csv_writer = csv.writer(_csv_fp)
    # 失败日志
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


# ===================== 工具 =====================
def add_log(msg):
    time_msg = f"[{datetime.now().strftime('%H:%M:%S')}] {msg}"
    CRAWL_STATUS["logs"].append(time_msg)
    if len(CRAWL_STATUS["logs"]) > 150:
        CRAWL_STATUS["logs"].pop(0)


def clean_text(text):
    # ✅ 修复：0 不会变成空
    if text == 0 or text == "0":
        return "0"
    if not text:
        return "空"
    text = re.sub(r'[\n\r\t]', ' ', str(text))
    return text.replace(',', '，').strip() or "空"


def clean_content(text):
    if not text:
        return "弄丢了"
    text = str(text).replace(',', '，')
    text = re.sub(r'[a-zA-Z0-9]+.*?(com|cc|org|de)', '。', text)
    return re.sub(r'\n+', '\n', text).strip()


def save_to_csv(data):
    row = [
        clean_text(data.get('book_id')),
        clean_text(data.get('title')),
        clean_text(data.get('chaptername')),
        clean_text(data.get('chapterid')),
        clean_content(data.get('txt'))
    ]
    _csv_writer.writerow(row)
    _csv_fp.flush()


# ===================== 核心爬取 =====================
async def fetch_chapter(session, book_id, cid, sem):
    url = f"{config['BASE_URL']}id={book_id}&chapterid={cid}"
    async with sem:
        try:
            async with session.get(url, timeout=ClientTimeout(total=config['TIMEOUT'])) as resp:
                if resp.status != 200:
                    msg = f"❌ 失败 {book_id}-{cid} | 状态码:{resp.status}"
                    add_log(msg)
                    CRAWL_STATUS["fail_count"] += 1
                    _fail_fp.write(msg + '\n')
                    _fail_fp.flush()
                    return

                content = await resp.text()
                data = json.loads(content)
                data["book_id"] = book_id
                save_to_csv(data)
                add_log(f"✅ 成功 {book_id}-{cid}")
                CRAWL_STATUS["success_count"] += 1

        except Exception as e:
            msg = f"❌ 错误 {book_id}-{cid} | {str(e)}"
            add_log(msg)
            CRAWL_STATUS["fail_count"] += 1
            _fail_fp.write(msg + '\n')
            _fail_fp.flush()


async def crawl_book(session, book_id, last_chapter, novel_sem):
    async with novel_sem:
        try:
            max_cid = int(last_chapter)
            if max_cid < 1:
                add_log(f"⚠️ {book_id} 无效章节数")
                return
        except:
            add_log(f"⚠️ {book_id} 章节数错误")
            return

        add_log(f"\n🚀 开始爬取 {book_id} 共{max_cid}章")
        chapter_sem = asyncio.Semaphore(config["CHAPTER_SEMAPHORE"])
        tasks = [fetch_chapter(session, book_id, i, chapter_sem) for i in range(1, max_cid + 1)]
        await asyncio.gather(*tasks)


# ===================== 已爬过列表 =====================
def init_novel_pass():
    if not os.path.exists(PASS_NOVEL):
        with open(PASS_NOVEL, 'w', encoding='utf-8') as f:
            f.write('')


def open_noveldata():
    if not os.path.exists(PASS_NOVEL):
        return set()
    with open(PASS_NOVEL, 'r', encoding='utf-8') as f:
        return {line.strip() for line in f if line.strip()}


def write_pass_novel(bid):
    with open(PASS_NOVEL, 'a', encoding='utf-8') as f:
        f.write(f"{bid}\n")


# ===================== 主任务 =====================
async def main_chapter_crawl():
    try:
        with open(NOVEL_CSV, 'r', encoding='utf-8') as f:
            novel_list = [(r[0], r[6]) for r in csv.reader(f) if len(r) >= 7][1:]
    except:
        add_log("❌ 未找到 novel_data.csv")
        CRAWL_STATUS["running"] = False
        return

    if not novel_list:
        add_log("❌ 无小说可爬")
        CRAWL_STATUS["running"] = False
        return

    add_log(f"📚 共加载 {len(novel_list)} 本")
    novel_sem = asyncio.Semaphore(config["NOVEL_SEMAPHORE"])
    passed = open_noveldata()
    novel_num = 0
    tasks = []
    # ✅ 打开一次文件
    open_all_files()
    try:
        async with aiohttp.ClientSession() as session:
            for bid, lc in novel_list:
                if bid not in passed:
                    novel_num += 1
                    if novel_num > config["NOVEL_NUM"]:
                        break
                    write_pass_novel(bid)
                    tasks.append(crawl_book(session, bid, lc, novel_sem))
            await asyncio.gather(*tasks)
    finally:
        # ✅ 统一关闭
        close_all_files()

    CRAWL_STATUS["running"] = False
    CRAWL_STATUS["finish"] = True
    add_log(f"\n🏁 全部完成！成功：{CRAWL_STATUS['success_count']} 失败：{CRAWL_STATUS['fail_count']}")


# ===================== 重爬失败 =====================
def get_failed_chapters():
    failed = []
    if not os.path.exists(FAIL_LOG):
        return failed
    with open(FAIL_LOG, 'r', encoding='utf-8') as f:
        for line in f:
            nums = re.findall(r'\d+', line)
            if len(nums) >= 2:
                failed.append({"bid": nums[0], "cid": nums[1]})
    return failed


def get_updated_chapters():
    updated = []
    if not os.path.exists(UPDATE_LOG):
        return updated
    with open(UPDATE_LOG, 'r', encoding='utf-8') as f:
        for line in f:
            nums = re.findall(r'\d+', line)
            if len(nums) >= 2:
                updated.append({"bid": nums[0], "cid": nums[1]})
    return updated


async def retry_failed_chapters():
    failed = get_failed_chapters()
    if not failed:
        add_log("🎉 无失败章节, 无需重爬!")
        return

    CRAWL_STATUS.update({"running": True, "fail_count": 0, "finish": False})
    add_log(f"🔄 开始重新爬取 {len(failed)} 个章节")
    open(FAIL_LOG, 'w').write('')

    # ✅ 打开一次
    open_all_files()

    try:
        sem = asyncio.Semaphore(config["RETRY_SEMAPHORE"])
        async with aiohttp.ClientSession() as session:
            tasks = [fetch_chapter(session, i['bid'], i['cid'], sem) for i in failed]
            await asyncio.gather(*tasks)
    finally:
        # ✅ 关闭一次
        close_all_files()

    add_log("✅ 爬取完成")
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
    open_all_files()
    try:
        sem = asyncio.Semaphore(config["RETRY_SEMAPHORE"])
        async with aiohttp.ClientSession() as session:
            tasks = [fetch_chapter(session, i['bid'], i['cid'], sem) for i in updated]
            await asyncio.gather(*tasks)
    finally:
        close_all_files()
    add_log("✅ 更新完成")
    CRAWL_STATUS["running"] = False
    CRAWL_STATUS["finish"] = True


# ===================== Django 视图 =====================
def chapter_crawl_page(request):
    source_name, source_id = get_site()
    return render(request, 'chapter_crawl.html', {'source_name': source_name, 'source_id': source_id})


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
        return JsonResponse({"status": False, "msg": "运行中禁止修改"})
    try:
        config["NOVEL_SEMAPHORE"] = int(request.POST.get("novel_sem"))
        config["CHAPTER_SEMAPHORE"] = int(request.POST.get("chapter_sem"))
        config["RETRY_SEMAPHORE"] = int(request.POST.get("retry_sem"))
        config["NOVEL_NUM"] = int(request.POST.get("novel_num"))
        save_config(config)
        add_log("✅ 配置保存成功")
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
        return JsonResponse({"status": False, "msg": "任务运行中"})

    CRAWL_STATUS.update({
        "running": True, "success_count": 0, "fail_count": 0,
        "logs": [], "finish": False
    })
    if os.path.exists(FAIL_LOG):
        os.remove(FAIL_LOG)
    init_novel_pass()
    run_async_task(main_chapter_crawl())
    return JsonResponse({"status": True, "msg": "爬取完成"})


def retry_chapter_crawl(request):
    if CRAWL_STATUS["running"]:
        return JsonResponse({"status": False, "msg": "任务运行中"})
    run_async_task(retry_failed_chapters())
    return JsonResponse({"status": True, "msg": "重爬完成"})


def updete_chapter(request):
    if CRAWL_STATUS["running"]:
        return JsonResponse({"status": False, "msg": "任务运行中"})
    run_async_task(crawl_updated_chapters())
    return JsonResponse({"status": True, "msg": "更新完成"})
