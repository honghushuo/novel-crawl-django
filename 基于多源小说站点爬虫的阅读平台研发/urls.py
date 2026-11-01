from django.urls import path

from app_0.views import log, novel, chapter, count, import_into_database as iid, read, update, novel_1, chapter_1, \
    update_1, novel_2, chapter_2, update_2

urlpatterns = [

    # ======== log ========
    path('login/', log.login, name='login'),
    path('register/', log.register, name='register'),
    path('logout/', log.logout, name='logout'),
    path('save_site_config/', log.save_site_config, name='save_site_config'),

    # ======== count ========
    path('home/', count.home, name='home'),
    path('home/count/', count.count, name='count'),
    path('avatar/count/', count.update_avatar, name='avatar'),

    # ======== novel_info========
    path('info_crawl/', novel.novel_crawl_page, name='novel_crawl_page'),
    path('info_status/', novel.get_crawl_real_time_status, name='novel_crawl_status'),
    path('info_start/', novel.start_novel_crawl, name='start_novel_crawl'),
    path('info_retry/', novel.retry_failed_novel_crawl, name='retry_failed_novel_crawl'),
    path('info_save_config/', novel.save_crawl_config, name='novel_save_config'),

    # ======== novel_info_1========
    path('info_crawl_1/', novel_1.novel_crawl_page, name='novel_crawl_page_1'),
    path('info_status_1/', novel_1.get_crawl_real_time_status, name='novel_crawl_status_1'),
    path('info_start_1/', novel_1.start_novel_crawl, name='start_novel_crawl_1'),
    path('info_retry_1/', novel_1.retry_failed_novel_crawl, name='retry_failed_novel_crawl_1'),
    path('info_save_config_1/', novel_1.save_crawl_config, name='novel_save_config_1'),

    # ======== novel_info_2========
    path('info_crawl_2/', novel_2.novel_crawl_page, name='novel_crawl_page_2'),
    path('info_status_2/', novel_2.get_crawl_real_time_status, name='novel_crawl_status_2'),
    path('info_start_2/', novel_2.start_novel_crawl, name='start_novel_crawl_2'),
    path('info_retry_2/', novel_2.retry_failed_novel_crawl, name='retry_failed_novel_crawl_2'),
    path('info_save_config_2/', novel_2.save_crawl_config, name='novel_save_config_2'),

    # ======== chapter_content ========
    path('chapter_crawl/', chapter.chapter_crawl_page, name='chapter_crawl'),
    path('chapter_status/', chapter.get_real_time_status, name='chapter_crawl_status'),
    path('chapter_save_config/', chapter.save_chapter_config, name='chapter_save_config'),
    path('chapter_start/', chapter.start_chapter_crawl, name='chapter_start_crawl'),
    path('chapter_retry/', chapter.retry_chapter_crawl, name='chapter_retry_crawl'),

    # ======== chapter_content_1 ========
    path('chapter_crawl_1/', chapter_1.chapter_crawl_page, name='chapter_crawl_1'),
    path('chapter_status_1/', chapter_1.get_real_time_status, name='chapter_crawl_status_1'),
    path('chapter_save_config_1/', chapter_1.save_chapter_config, name='chapter_save_config_1'),
    path('chapter_start_1/', chapter_1.start_chapter_crawl, name='chapter_start_crawl_1'),
    path('chapter_retry_1/', chapter_1.retry_chapter_crawl, name='chapter_retry_crawl_1'),

    # ======== chapter_content_2 ========
    path('chapter_crawl_2/', chapter_2.chapter_crawl_page, name='chapter_crawl_2'),
    path('chapter_status_2/', chapter_2.get_real_time_status, name='chapter_crawl_status_2'),
    path('chapter_save_config_2/', chapter_2.save_chapter_config, name='chapter_save_config_2'),
    path('chapter_start_2/', chapter_2.start_chapter_crawl, name='chapter_start_crawl_2'),
    path('chapter_retry_2/', chapter_2.retry_chapter_crawl, name='chapter_retry_crawl_2'),

    # ======== update ========
    path('update/page/', update.update_page, name='update_page'),
    path('update/page_1/', update_1.update_page, name='update_page_1'),
    path('update/page_2/', update_2.update_page, name='update_page_2'),
    path('update/check/', update.update_check, name='update_check'),
    path('update/check_1/', update_1.update_check, name='update_check_1'),
    path('update/check_2/', update_2.update_check, name='update_check_2'),
    path('update/', update.update, name='update'),
    path('update_1/', update_1.update, name='update_1'),
    path('update_2/', update_2.update, name='update_2'),
    path('update/chapter/', chapter.updete_chapter, name='update_chapter'),
    path('update/chapter_1/', chapter_1.updete_chapter, name='update_chapter_1'),
    path('update/chapter_2/', chapter_2.updete_chapter, name='update_chapter_2'),


    # ======== import ========
    path('info_import/', iid.book_info_import, name='book_info_import'),
    path('chapter_import/', iid.book_chapter_import, name='book_chapter_import'),

    # ======== read ========
    path('shift_site/', read.shift_site_now, name='shift_site'),
    path('read/category/', read.category_page, name='category'),
    path('novel/<int:bid>/', read.novel_page, name='novel'),
    path('chapter/<int:nid>/<int:cid>/', read.chapter_page, name='chapter'),
    path('log/history/', read.log_history, name='log_history'),
    path('read/history/', read.read_history, name='read_history'),
    path('read/at/', read.at_read, name='read_at'),
    path('delete/history/', read.delete_history, name='delete_history'),
    path('batch/delete/history/', read.batch_delete_history, name='batch_delete_history'),
    path('confirm/collection/', read.confirm_collection, name='confirm_collection'),
    path('cancel/collection/', read.cancel_collection, name='cancel_collection'),
    path('bookshelf/', read.bookshelf, name='bookshelf'),
    path('bookshelf/delete/', read.batch_shift_bookshelf, name='batch_shift_bookshelf'),

]
