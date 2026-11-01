from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


# ========== 基础配置模型 ==========
class SourceSite(models.Model):
    """爬虫来源站点配置"""
    name = models.CharField(verbose_name="站点名称", max_length=16, unique=True, help_text="如笔趣阁、番茄小说")
    domain = models.CharField(verbose_name="站点域名", max_length=64, unique=True, help_text="如https://www.bqger.cc")

    class Meta:
        db_table = "source_site"
        verbose_name = "来源站点"
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.name}({self.domain})"


# ========== 核心业务模型 ==========
class BookInfo(models.Model):
    """小说基础信息"""

    source = models.ForeignKey(
        SourceSite,
        on_delete=models.CASCADE,
        related_name="books",
        verbose_name="来源站点",
    )

    book_id = models.IntegerField(
        verbose_name="小说ID",
        db_index=True,
    )

    book_name = models.CharField(verbose_name="书名", max_length=32, db_index=True)
    author = models.CharField(verbose_name="作者", max_length=32, db_index=True)
    introduction = models.TextField(verbose_name="简介", blank=True, null=True)

    cover = models.CharField(
        blank=True,
        null=True,
        max_length=64,
        verbose_name="封面图",
        help_text="推荐尺寸：200x300px"
    )

    category = models.CharField(
        verbose_name="小说分类",
        max_length=16,
        db_index=True
    )

    status = models.CharField(
        verbose_name="连载状态",
        max_length=16,
        default="连载中",
        db_index=True
    )

    words = models.CharField(verbose_name="总字数", default="未知", max_length=16)

    score = models.FloatField(
        verbose_name="评分",
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(10.0)],
        db_index=True
    )

    # 更新时间
    last_chapter_name = models.CharField(verbose_name="最新章节名", max_length=128, blank=True)
    last_chapter_id = models.IntegerField(verbose_name="最新章节站点ID", blank=True, null=True, db_index=True)
    last_updated = models.CharField(verbose_name="小说最后更新时间", db_index=True, blank=True, null=True,
                                    max_length=32)

    class Meta:
        db_table = "book_info"
        verbose_name = "小说信息"
        unique_together = [["source", "book_id"]]
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"[{self.source.name}] {self.book_name}"


class ChapterInfo(models.Model):
    """小说章节（目录+内容）"""
    book = models.ForeignKey(
        BookInfo,
        on_delete=models.CASCADE,
        related_name="chapters",
        verbose_name="所属小说"
    )
    chapter_id = models.IntegerField(verbose_name="站点章节ID", db_index=True, blank=True, null=True)
    title = models.CharField(verbose_name="章节标题", max_length=200)
    content = models.TextField(verbose_name="章节内容", blank=True, null=True)
    words = models.CharField(verbose_name="章节字数", default="未知", max_length=16)

    class Meta:
        db_table = "book_chapter"
        verbose_name = "小说章节"
        verbose_name_plural = verbose_name
        # 唯一约束：同一小说的站点章节ID唯一
        unique_together = [("book", "chapter_id")]

    def __str__(self):
        return f"{self.book.book_name} - {self.title}"


class UserInfo(models.Model):
    ROLE_CHOICES = (
        ("admin", "管理员"),
        ("normal", "普通用户"),
    )
    username = models.CharField(verbose_name='用户名', max_length=32, unique=True)
    password = models.CharField(verbose_name="密码", max_length=64)
    role = models.CharField(
        verbose_name="用户角色",
        max_length=12,
        choices=ROLE_CHOICES,
        default="normal"
    )
    phone = models.CharField(
        verbose_name="手机号",
        max_length=11,
        blank=True,
        null=True,
        unique=True
    )
    email = models.CharField(verbose_name='邮箱', max_length=64, blank=True, null=True, unique=True)
    created_at = models.DateTimeField(verbose_name="注册时间", auto_now_add=True)
    address = models.CharField(verbose_name="地址", max_length=64, db_index=True, blank=True, null=True,
                               default="暂住地球...")
    motto = models.CharField(verbose_name="座右铭", max_length=128, db_index=True, blank=True, null=True,
                             default="还没留下什么...")
    occupation = models.CharField(verbose_name="职业", max_length=64, db_index=True, blank=True, null=True,
                                  default="职业未知...")
    hobby = models.CharField(verbose_name="兴趣特长", max_length=128, db_index=True, blank=True, null=True,
                             default="击穿地球...")
    about_me = models.CharField(verbose_name="自述", max_length=256, db_index=True, blank=True, null=True,
                                default="未留下足迹...")
    birthday = models.DateField(
        verbose_name="生日",
        blank=True,
        null=True,
        help_text="格式：YYYY-MM-DD"
    )

    class Meta:
        db_table = "user_info"
        verbose_name = "用户信息"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]

    def __str__(self):
        return self.username


class UserCollection(models.Model):
    """用户收藏"""
    user = models.ForeignKey(
        UserInfo,
        on_delete=models.CASCADE,
        related_name="collections",
        verbose_name="收藏用户"
    )
    book = models.ForeignKey(
        BookInfo,
        on_delete=models.CASCADE,
        related_name="collections",
        verbose_name="收藏小说"
    )
    created_at = models.DateTimeField(verbose_name="收藏时间", db_index=True, auto_now_add=True)
    updated_at = models.DateTimeField(verbose_name="更新时间", auto_now=True)

    class Meta:
        db_table = "user_collection"
        verbose_name = "用户收藏"
        verbose_name_plural = verbose_name
        unique_together = [("user", "book")]  # 一个用户只能收藏一本小说一次


class ReadingHistory(models.Model):
    """用户阅读历史"""
    user = models.ForeignKey(
        UserInfo,
        on_delete=models.CASCADE,
        related_name="reading_history",
        verbose_name="阅读用户"
    )
    book = models.ForeignKey(
        BookInfo,
        on_delete=models.CASCADE,
        related_name="historys",
        verbose_name="所属小说"
    )
    chapter_id = models.IntegerField(
        db_index=True,
        blank=True,
        null=True,
        verbose_name="阅读章节"
    )
    title = models.CharField(verbose_name="章节标题", max_length=200, default='未知')
    progress = models.FloatField(
        verbose_name="阅读进度(0-1)",
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    read_time = models.DateTimeField(verbose_name="阅读时间", db_index=True, auto_now_add=True)
    read_duration = models.IntegerField(verbose_name="阅读时长(秒)", default=0, help_text="统计用户阅读时长")

    class Meta:
        db_table = "user_reading_history"
        verbose_name = "阅读历史"
        verbose_name_plural = verbose_name
        unique_together = [("user", "book")]


class Avatar(models.Model):
    user = models.ForeignKey(
        "UserInfo",
        on_delete=models.CASCADE,
        related_name="user_avatar",
        verbose_name="所属用户",
    )
    avatar = models.ImageField(
        upload_to='app_0/static/images/',
        verbose_name="用户头像",
        blank=True,
        null=True
    )

    class Meta:
        db_table = "user_avatar"
        verbose_name = "头像"
        verbose_name_plural = "头像"

    def __str__(self):
        return f"{self.user} 的头像"
