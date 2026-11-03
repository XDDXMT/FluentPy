"""Presentation metadata for the website's icon browser.

Families use whole name prefixes: FOLDER_ARROW remains a file icon, while an
ARROW icon belongs to navigation. Search synonyms may match modifier words.
The SVGs and FluentIcon public names are never changed by this classification.
"""

from pathlib import PurePosixPath

CATEGORIES = (
    (
        "interface",
        "界面与操作",
        "APPS",
        "app apps window panel pane layout tab menu grid list checkbox checkmark button toggle form select task multiselect reorder accessibility dismiss add subtract remove delete search filter more settings control options collapse expand navigation_unread",
    ),
    (
        "navigation",
        "箭头与导航",
        "ARROW_RIGHT",
        "arrow chevron home navigation compass sign direction route",
    ),
    (
        "files",
        "文件与文档",
        "FOLDER",
        "document folder archive clipboard copy cut paste note notepad save attach attachment pin print scan storage collections tray drawer bundle",
    ),
    (
        "text",
        "文字与排版",
        "TEXT_FONT",
        "text textbox font align indent padding spacebar symbol number math pi comma ampersand asterisk bracket parentheses quote subscript superscript letter",
    ),
    (
        "media",
        "音视频",
        "SPEAKER_2",
        "speaker desktop_speaker phone_speaker tablet_speaker dual_screen_speaker options_speaker mic music midi headphones headset record sound volume play pause replay skip rewind fast_forward video filmstrip tv stream radio movies",
    ),
    (
        "images",
        "图片与设计",
        "IMAGE",
        "image camera picture photo edit draw pen paint color crop shapes shape square circle triangle rectangle line oval polygon bezier vector ink scribble ruler eyedropper design highlight eraser cube resize position border zoom 3d cutout flip rotate lasso wand",
    ),
    (
        "communication",
        "消息与通话",
        "CHAT",
        "chat comment mail send call phone megaphone channel voicemail alert notification mention message communication important",
    ),
    (
        "people",
        "人物与组织",
        "PEOPLE",
        "person people guest contact organization org presence bot agent handshake hand meet conference team group_person",
    ),
    (
        "devices",
        "设备与硬件",
        "DESKTOP",
        "desktop laptop tablet keyboard mouse cursor touchpad touch device dual_screen hard_drive usb port battery power memory ram cpu chip sim sd_card surface smartwatch game_console xbox haptic connected flash lightbulb connector board",
    ),
    (
        "network",
        "网络与连接",
        "WIFI_1",
        "wifi bluetooth network cloud globe earth cellular router antenna connection plug link share transmission cast broadcast remote tether network_check",
    ),
    (
        "data",
        "表格与数据",
        "TABLE",
        "table data database chart poll diagram gantt pivot flow funnel cube_tree organization_chart pulse analytics cube_multiple cube_sync",
    ),
    (
        "time",
        "日期与时间",
        "CALENDAR_LTR",
        "calendar clock timer hourglass alarm snooze history shifts time watch stopwatch",
    ),
    (
        "security",
        "安全与隐私",
        "SHIELD",
        "shield lock key eye password fingerprint incognito prohibited block warning certificate signature safety protect passkey shield_keyhole",
    ),
    (
        "commerce",
        "购物与金融",
        "MONEY",
        "shopping cart basket bag tag money currency payment wallet card credit receipt ticket gift rewards reward premium ribbon trophy diamond savings coin vault bank barcode qr briefcase",
    ),
    (
        "places",
        "地图与出行",
        "LOCATION",
        "location map building vehicle airplane airport road directions city backpack luggage scooter bicycle train car metro local real_estate travel navigation_location gas",
    ),
    (
        "nature",
        "自然与天气",
        "WEATHER_SUNNY",
        "weather leaf animal plant tree flower food drink beach fire water temperature earth_leaf sparkle stars moon sun umbrella tent mountain",
    ),
    (
        "education",
        "教育与阅读",
        "BOOK",
        "book notebook reading library learning class hat_graduation globe_person quiz puzzle brain calculator beaker microscope science molecule atom graduation",
    ),
    (
        "lifestyle",
        "生活与健康",
        "HEART",
        "heart emoji sport fitness pulse_square bandage patient doctor pill syringe hospital medical tooth sleep bed bed_patient couch chair tennis joystick games chess dice balloon celebration clothes hat crown glasses hat_graduation ribbon_medal",
    ),
    (
        "developer",
        "开发与工具",
        "CODE",
        "code braces branch bug wrench hammer tool toolbox terminal command prompt binary developer pipeline source control_button service slide_stack stack split merge connected_repair",
    ),
    ("other", "其他符号", "ICONS", ""),
)

# More specific families take precedence over the broad first word.
OVERRIDES = {
    "desktop_speaker": "media",
    "phone_speaker": "media",
    "tablet_speaker": "media",
    "dual_screen_speaker": "media",
    "options_speaker": "media",
    "heart_pulse": "lifestyle",
    "earth_leaf": "nature",
    "hat_graduation": "education",
    "organization_chart": "data",
    "cube_tree": "data",
    "cube_multiple": "data",
    "cube_sync": "data",
    "control_button": "developer",
    "food": "lifestyle",
    "drink": "lifestyle",
}

FAMILY_EXTENSIONS = {
    "interface": "bookmark star flag icons info open approvals_app autopilot badge bin bin_recycle catch_up check content_settings content_view dark_theme dock full_screen glance item_compare launcher_settings match_app_layout maximize new question re_order style_guide sub_grid status system tabs target tasks_app thumb tooltip uninstall_app web_asset fluent fluid drag error",
    "navigation": "arrows caret contract ios_arrow next previous step steps slash_forward",
    "files": "binder box drafts open_folder page_fit rename scratchpad slide news shortpick",
    "text": "auto_fit autocorrect autosum backspace clear_formatting convert_range decimal fixed_width omega symbols translate divider",
    "media": "closed_caption fps guitar hd hdr live microphone multiplier read_aloud stop subtitles walkie_talkie next_frame previous_frame",
    "images": "album blur brightness calligraphy_pen center f_stop frame hexagon inking_tool layer orientation ratio remix rhombus scale_fill scale_fit transparency teardrop wallpaper gif sticker space_3d point_scan",
    "communication": "broad_activity_feed compose dialpad feed rss",
    "people": "agents breakout_room cowork diversity group pair thinking work_iq",
    "devices": "component_2 double_swipe double_tap extended_dock flashlight gesture iot kiosk mobile_optimized projection_screen screen_search screenshot serial_port server swipe tap view_desktop",
    "network": "virtual_network preview_link",
    "data": "classification column counter equal flowchart gauge likert predictions row sine_wave vote",
    "time": "access_time timeline",
    "security": "gavel guardian inprivate_account sanitize",
    "commerce": "lottery medal scales store_microsoft vip",
    "places": "door drive_train elevator engine fast_acceleration highway my_location rocket street_sign top_speed",
    "nature": "clover drop dust mold planet",
    "education": "immersive_reader presenter teaching whiteboard",
    "lifestyle": "bench bow_tie bowl cookies dentist desk dishwasher dumbbell fireplace oven patch rating_mature run seat showerhead spatula_spoon stethoscope swimming_pool teddy tetris_app wheelchair_access xray washer",
    "developer": "broom javascript markdown production protocol_handler script",
}

SYNONYMS = (
    ("speaker volume sound", "音量 扬声器 音箱 喇叭 声音 音频"),
    ("mic microphone record", "麦克风 录音 音频"),
    ("headphones headset", "耳机 音频"),
    ("music midi piano", "音乐 音符 乐器 音频"),
    ("play replay", "播放 重播"),
    ("pause", "暂停"),
    ("skip rewind fast_forward", "快进 快退 跳转"),
    ("mute off", "静音 关闭 禁用"),
    ("video filmstrip movies", "视频 电影 影片"),
    ("camera", "相机 摄像 拍照"),
    ("image photo picture", "图片 图像 照片"),
    ("arrow", "箭头 导航"),
    ("chevron", "展开 收起 箭头"),
    ("left", "左 向左"),
    ("right", "右 向右"),
    ("up", "上 向上"),
    ("down", "下 向下"),
    ("download", "下载"),
    ("upload", "上传"),
    ("home", "首页 主页 房屋"),
    ("search", "搜索 查找 放大镜"),
    ("folder", "文件 文件夹 目录"),
    ("document", "文件 文档"),
    ("archive box", "归档 存档 箱子"),
    ("clipboard", "剪贴板 粘贴"),
    ("copy", "复制"),
    ("cut", "剪切"),
    ("paste", "粘贴"),
    ("save", "保存"),
    ("delete dismiss", "删除 清除 关闭"),
    ("print", "打印 打印机"),
    ("attach attachment", "附件 附加"),
    ("text textbox font", "文字 文本 字体 排版"),
    ("bold", "加粗 粗体"),
    ("italic", "斜体"),
    ("underline", "下划线"),
    ("strikethrough", "删除线"),
    ("align", "对齐"),
    ("edit pen pencil", "编辑 铅笔"),
    ("paint brush draw", "绘图 绘画 画笔"),
    ("color palette eyedropper", "颜色 调色 取色 吸管"),
    ("crop resize zoom", "裁剪 缩放 放大 缩小"),
    ("chat comment message", "消息 聊天 对话 评论"),
    ("mail", "邮件 信封 邮箱"),
    ("call phone", "电话 通话 手机"),
    ("alert notification", "提醒 通知 铃铛"),
    ("person people guest contact", "人物 用户 联系人 人像"),
    ("people team organization", "团队 群组 组织"),
    ("desktop laptop", "电脑 桌面 笔记本 显示器"),
    ("device tablet dual_screen", "设备 平板 屏幕 硬件"),
    ("keyboard mouse cursor", "键盘 鼠标 光标 输入"),
    ("battery power", "电池 电量 电源"),
    ("wifi cellular network", "网络 无线 信号 连接"),
    ("bluetooth", "蓝牙 连接"),
    ("cloud", "云 同步 网络"),
    ("link share", "链接 分享 共享"),
    ("table", "表格 单元格"),
    ("data chart database poll", "数据 图表 数据库 统计"),
    ("calendar", "日历 日期"),
    ("clock timer time hourglass", "时间 时钟 计时 定时"),
    ("shield", "安全 防护 盾牌"),
    ("lock key password passkey", "锁 密钥 钥匙 密码 隐私"),
    ("eye", "眼睛 可见 隐藏 隐私"),
    ("shopping cart basket", "购物 商店 购物车"),
    ("money currency payment wallet credit receipt", "金额 支付 钱包 货币 账单"),
    ("location map compass", "位置 定位 地图 指南针"),
    ("building", "建筑 楼宇"),
    ("vehicle airplane car bicycle", "交通 出行 汽车 飞机"),
    ("weather", "天气"),
    ("sunny sun", "晴天 太阳"),
    ("rain", "下雨 雨天"),
    ("snow", "下雪 雪天"),
    ("leaf plant tree flower", "叶子 植物 自然 环保"),
    ("food drink", "食物 饮料 餐饮"),
    ("book notebook library reading", "书籍 阅读 学习 教育"),
    ("heart pulse medical pill doctor", "健康 心形 医疗"),
    ("emoji", "表情 笑脸"),
    ("sport fitness", "运动 健身"),
    ("code braces terminal command", "代码 编程 开发 终端"),
    ("bug", "错误 调试 虫子"),
    ("wrench tool toolbox hammer", "工具 扳手 工具箱"),
    ("settings options", "设置 选项 齿轮"),
    ("checkmark checkbox", "勾选 复选框 选中 完成"),
    ("add", "添加 新增 加号"),
    ("subtract", "减号 减去"),
    ("star bookmark pin", "收藏 星标 书签 固定"),
    ("window panel layout tab app apps", "窗口 面板 布局 标签 应用"),
)


def has_prefix(name, prefix):
    return name == prefix or name.startswith(prefix + "_")


def classify(name):
    for prefix, category in OVERRIDES.items():
        if has_prefix(name, prefix):
            return category
    for category, _label, _representative, prefixes in CATEGORIES:
        families = (prefixes + " " + FAMILY_EXTENSIONS.get(category, "")).split()
        if any(has_prefix(name, prefix) for prefix in families):
            return category
    return "other"


def enrich_icons(icons, upstream):
    inventory = upstream["icons"]
    for icon in icons:
        source = inventory.get(PurePosixPath(icon["file"]).name)
        filename = (
            PurePosixPath(source["upstream_path"]).name
            if source
            else "fluentpy_leaf_24_regular.svg"
        )
        base = (
            filename.removeprefix("ic_fluent_")
            .removeprefix("fluentpy_")
            .removesuffix("_24_regular.svg")
        )
        words = base.split("_")
        phrases = {
            "_".join(words[start:end])
            for start in range(len(words))
            for end in range(start + 1, len(words) + 1)
        }
        icon["category"] = classify(base)
        icon["localized"] = bool(source and len(PurePosixPath(source["upstream_path"]).parts) > 4)
        icon["keywords"] = " ".join(
            terms for tokens, terms in SYNONYMS if any(token in phrases for token in tokens.split())
        )
    return [
        {"id": category, "label": label, "icon": representative}
        for category, label, representative, _prefixes in CATEGORIES
        if any(icon["category"] == category for icon in icons)
    ]
