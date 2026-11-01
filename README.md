Novel Crawl Web
小说爬虫 Web 应用

项目简介
这是一个基于 Django 框架开发的小说爬虫 Web 应用程序，提供小说抓取、阅读、收藏等功能。

技术栈
后端: Python 3.x + Django
前端: HTML5 + jQuery + Bootstrap 3/4/5
数据库: SQLite (默认)
功能特性
小说来源管理
小说信息抓取与存储
章节内容管理
用户系统
小说收藏
阅读历史记录
用户头像管理
数据模型
SourceSite: 小说来源网站
BookInfo: 小说信息
ChapterInfo: 章节信息
UserInfo: 用户信息
UserCollection: 用户收藏
ReadingHistory: 阅读历史
Avatar: 用户头像
项目结构
novel-crawl-web/
├── app_0/                    # 主应用目录
│   ├── migrations/          # 数据库迁移文件
│   ├── static/              # 静态资源
│   │   ├── images/          # 图片资源
│   │   ├── js/              # JavaScript 文件
│   │   └── plugins/         # 前端插件 (Bootstrap)
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   └── models.py
├── LICENSE
└── README.md
安装部署
克隆项目
git clone https://gitee.com/honghushuo/novel-crawl-web.git
cd novel-crawl-web
创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
安装依赖
pip install django
运行数据库迁移
python manage.py migrate
启动开发服务器
python manage.py runserver
访问 http://127.0.0.1:8000
管理后台
创建超级用户：

python manage.py createsuperuser
访问 http://127.0.0.1:8000/admin 进入管理后台

许可证
MIT License
