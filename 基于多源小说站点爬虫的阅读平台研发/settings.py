from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-cmof-sj6k_^a^m&mb=54z_nm=^36*wajdt0-r+595v4=d76g)q'

DEBUG = True

ALLOWED_HOSTS = []

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    "app_0.apps.App0Config"
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'utils.middle.MiddleItem'
]

ROOT_URLCONF = '基于多源小说站点爬虫的阅读平台研发.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = '基于多源小说站点爬虫的阅读平台研发.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'novel',
        'USER': 'root',
        'PASSWORD': '123456',
        'HOST': 'localhost',
        'PORT': '3306'
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'zh-hans'

TIME_ZONE = 'Asia/Shanghai'  # 北京时间
USE_TZ = True  # 开启时区支持

USE_I18N = True

STATIC_URL = 'static/'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

PERMISSION = {
    'admin': {
        'home', 'count',
        'novel_crawl_page', 'novel_crawl_status',
        'start_novel_crawl', 'retry_failed_novel_crawl',
        'novel_save_config', 'chapter_crawl',
        'chapter_crawl_1', 'chapter_crawl_2',
        'novel_crawl_page_1', 'novel_crawl_status_1',
        'start_novel_crawl_1', 'retry_failed_novel_crawl_1',
        'novel_save_config_1', 'save_site_config',
        'chapter_crawl_status', 'chapter_save_config',
        'chapter_start_crawl', 'chapter_retry_crawl',
        'chapter_crawl_status_1', 'chapter_save_config_1',
        'chapter_start_crawl_1', 'chapter_retry_crawl_1',
        'book_info_import', 'book_chapter_import',
        'category', 'novel', 'avatar',
        'chapter', 'log_history',
        'read_history', 'read_at', 'shift_site',
        'delete_history', 'batch_delete_history',
        'confirm_collection', 'cancel_collection',
        'bookshelf', 'batch_shift_bookshelf',
        'update_page', 'update', 'update_check',
        'update_page_1', 'update_1', 'update_check_1',
        'update_page_2', 'update_2', 'update_check_2',
        'update_chapter', 'update_chapter_1', 'update_chapter_2',
        'novel_crawl_page_2', 'novel_crawl_status_2',
        'start_novel_crawl_2', 'retry_failed_novel_crawl_2',
        'novel_save_config_2', 'chapter_crawl_status_2', 'chapter_save_config_2',
        'chapter_start_crawl_2', 'chapter_retry_crawl_2',
    },
    'normal': {
        'home', 'count',
        'avatar',
        'category', 'novel',
        'chapter', 'log_history',
        'read_history', 'read_at',
        'delete_history', 'batch_delete_history',
        'confirm_collection', 'cancel_collection',
        'bookshelf', 'batch_shift_bookshelf', 'shift_site'
    }
}

MENU = {
    'admin': [
        {'title': '我的书架', 'url': '/bookshelf/'},
        {'title': '分类', 'url': '/read/category/'},
        {'title': '历史记录', 'url': '/read/history/'},
        {'title': '小说信息爬取', 'url': '/info_crawl/'},
        {'title': '小说章节爬取', 'url': '/chapter_crawl/'},
        {'title': '数据更新维护', 'url': '/update/page/'},
    ],

    'normal': [
        {'title': '我的书架', 'url': '/bookshelf/'},
        {'title': '分类', 'url': '/read/category/'},
        {'title': '历史记录', 'url': '/read/history/'},
    ]

}
