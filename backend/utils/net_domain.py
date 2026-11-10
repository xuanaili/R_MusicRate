# -*- coding: utf-8 -*-
"""MusicRate 局域网后端地址（URL 前缀）预处理

背景
----
数据库里存的是封面 / 音频的**绝对地址**，形如
    http://localhost:5000/covers/xxx.jpg
    http://localhost:5000/tracks/xxx.mp3
写死 localhost 时，手机通过 http://192.168.x.x:8080 打开页面，
拿到的封面/音频地址指向手机自己 → 全部裂图 / 放不出声音。

本模块负责把「旧域名前缀」批量改写成「当前局域网域名」，保证表里的 URL 与当前网络一致：
    1) 识别本机 IP（UDP connect 技巧，不实际发包）并从 ipconfig 收集候选地址
    2) 扫描 album_pool / albums_% / users 的 URL 字段，识别出旧域名前缀
    3) 用 MySQL REPLACE() 原地改写（兼容 JSON 字符串、长文本里的内嵌地址）

纯逻辑部分（前缀解析 / ipconfig 解析 / 候选排序 / 字段筛选）零依赖，便于单测；
DB 部分只在真正执行时导入 pymysql，不影响 Flask 启动。
"""
import os
import re
import socket
import subprocess

from backend.config import MYSQL_CONFIG, PORT as BACKEND_PORT, LAN_HOST_FILE

# ========== 需要处理 URL 的表 / 字段 ==========
# 表名支持 % 通配：albums_% 自动匹配所有用户专属专辑表（albums_1、albums_2 …），新增用户无需改配置
# 字段会与表的真实列取交集（某些表没有 mp3_url 列也不会 SQL 报错）
DOMAIN_TABLE_CONFIG = [
    {'table_pattern': 'album_pool', 'columns': ['cover_img', 'mp3_url']},
    {'table_pattern': 'albums_%', 'columns': ['cover_img', 'mp3_url']},
    {'table_pattern': 'users', 'columns': ['avatar']},
]

# 非本项目后端域名的端口一律不碰（避免误改用户填的外链）
IPV4_RE = r'(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}'
PREFIX_RE = re.compile(rf'^(https?)://([^/\s?#]+)', re.I)
BACKEND_DOMAIN_RE = re.compile(
    rf'^https?://(localhost|127\.0\.0\.1|0\.0\.0\.0|{IPV4_RE})(?::(\d+))?$', re.I
)
# ipconfig 输出里的 IPv4 行
IPV4_IN_LINE_RE = re.compile(IPV4_RE)


# ================= 纯逻辑：URL 前缀 =================

def extract_url_prefix(url):
    """从 URL 中提取 scheme://host:port 前缀（不含路径）；非法/空返回 None"""
    if not url or not isinstance(url, str):
        return None
    matched = PREFIX_RE.match(url.strip())
    if not matched:
        return None
    return f"{matched.group(1)}://{matched.group(2)}"


def is_backend_domain(prefix):
    """是否为本项目的后端地址前缀：localhost / 0.0.0.0 / 任意 IPv4，且端口为后端端口（或省略）

    只认本机地址与 IPv4，域名（如 example.com）不动，避免误替换外链。
    """
    if not prefix:
        return False
    matched = BACKEND_DOMAIN_RE.match(prefix)
    if not matched:
        return False
    port = matched.group(2)
    return port is None or port == str(BACKEND_PORT)


def make_domain(host, port=BACKEND_PORT):
    """拼接 http://host:port 服务地址"""
    return f"http://{host}:{port}"


def url_file_name(url):
    """从 URL / 路径中取最后一段文件名（忽略 host 前缀、查询串）

    删除旧音频文件时用：以前是 url.replace(AUDIO_BASE_URL, '')，
    后端 HOST 变化（localhost → 局域网 IP）后就匹配不上了，改成按路径取文件名更稳。
    """
    if not url or not isinstance(url, str):
        return ''
    path = url.strip().split('?', 1)[0].split('#', 1)[0]
    return path.rstrip('/').split('/')[-1]


# ================= 纯逻辑：IP 识别 =================

def parse_ipconfig(text):
    """解析 ipconfig 文本 → [(适配器名, IPv4)]，跳过回环/掩码/空行"""
    result = []
    current_adapter = '未知适配器'
    for raw_line in (text or '').splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # 适配器头部：包含 "适配器"/"adapter" 且以冒号结尾
        if ('适配器' in line or 'adapter' in line.lower()) and line.rstrip().endswith(':'):
            current_adapter = line.rstrip(':')
            continue
        if 'IPv4' not in line and 'IP 地址' not in line:
            continue
        matched = IPV4_IN_LINE_RE.search(line)
        if not matched:
            continue
        ip = matched.group(0)
        if ip.startswith(('127.', '255.')):
            continue
        result.append((current_adapter, ip))
    return result


def get_ipconfig_text():
    """执行 ipconfig 并解码（Windows 中文系统为 GBK，先试 utf-8 再回退 gbk）"""
    try:
        completed = subprocess.run(['ipconfig'], capture_output=True, timeout=10)
        raw = completed.stdout or completed.stderr or b''
        for encoding in ('utf-8', 'gbk'):
            try:
                return raw.decode(encoding)
            except (UnicodeDecodeError, AttributeError):
                continue
        return raw.decode('utf-8', errors='replace')
    except (OSError, subprocess.SubprocessError):
        return ''


def get_primary_ip():
    """自动识别当前网络出口 IPv4（UDP connect 技巧，不实际发包），失败返回 None"""
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(2)
        sock.connect(('8.8.8.8', 80))
        ip = sock.getsockname()[0]
        return ip if IPV4_IN_LINE_RE.fullmatch(ip) and not ip.startswith('127.') else None
    except OSError:
        return None
    finally:
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass


def is_virtual_adapter(adapter_name):
    """判断是否虚拟网卡（VPN / 虚拟机 / WSL 等），选地址时应排在物理网卡后面"""
    name = (adapter_name or '').lower()
    keywords = ('vmware', 'virtualbox', 'hyper-v', 'vethernet', 'sstap', 'tap', 'tun',
                'tailscale', 'zerotier', 'wsl', 'loopback', 'vmnet', 'docker', 'vpn')
    return any(k in name for k in keywords)


def build_candidate_hosts(primary_ip, adapters):
    """构建候选 host 列表 → [(host, 说明)]，本机 localhost 永远第一

    排序：localhost → 自动识别的出口 IP → 物理网卡 IP → 虚拟网卡 IP（去重）
    """
    candidates = [('localhost', 'localhost（仅本机可用，手机访问不到）')]
    seen = {'localhost', '127.0.0.1', '0.0.0.0'}
    ordered = []
    if primary_ip and primary_ip not in seen:
        ordered.append((primary_ip, '当前网络出口（自动识别）'))
        seen.add(primary_ip)
    physical, virtual = [], []
    for adapter, ip in adapters:
        if ip in seen:
            continue
        seen.add(ip)
        (virtual if is_virtual_adapter(adapter) else physical).append((ip, adapter))
    candidates.extend(ordered)
    candidates.extend(physical)
    candidates.extend(virtual)
    return candidates


def get_candidate_hosts(primary_ip=None):
    """自动检测主 IP + ipconfig 解析，构建候选 host 列表"""
    if primary_ip is None:
        primary_ip = get_primary_ip()
    return build_candidate_hosts(primary_ip, parse_ipconfig(get_ipconfig_text()))


# ================= 纯逻辑：表 / 字段筛选 =================

def match_table_pattern(table_name):
    """表名是否属于需要处理的表，返回命中的配置项或 None"""
    for config in DOMAIN_TABLE_CONFIG:
        pattern = config['table_pattern']
        if pattern == table_name:
            return config
        if pattern.endswith('%') and table_name.startswith(pattern[:-1]):
            return config
    return None


def columns_for_table(table_name, existing_columns=None):
    """返回该表需要处理的字段列表

    existing_columns 传入真实列名集合时取交集：老库/新库列不一致也不会拼出非法 SQL。
    """
    config = match_table_pattern(table_name)
    if not config:
        return []
    if existing_columns is None:
        return list(config['columns'])
    lower_map = {c.lower(): c for c in existing_columns}
    return [lower_map[c.lower()] for c in config['columns'] if c.lower() in lower_map]


# ================= 数据库：扫描与改写 =================

def get_db_connection():
    """独立数据库连接（不依赖 Flask 上下文），失败返回 None"""
    try:
        import pymysql
        # pymysql 的 'db' 参数已废弃，转成 'database' 后连接（避免刷 DeprecationWarning）
        config = {k: v for k, v in MYSQL_CONFIG.items() if k != 'db'}
        config['database'] = MYSQL_CONFIG.get('db')
        return pymysql.connect(**config, connect_timeout=10, read_timeout=30)
    except Exception as e:  # noqa: BLE001 - 工具脚本需要把失败原因打给用户
        print(f"❌ 数据库连接失败：{e}")
        return None


def _fetch_all_columns(cursor):
    """一次性读取当前库所有表的列名 → {表名: [列名, ...]}

    注意：MYSQL_CONFIG 默认是 DictCursor，而 MySQL 8 的 information_schema 列名是大写
    （TABLE_NAME / COLUMN_NAME），故用 AS t / AS c 定义小写别名，保证取到的字典键稳定。
    """
    cursor.execute(
        'SELECT table_name AS t, column_name AS c FROM information_schema.columns '
        'WHERE table_schema = DATABASE()'
    )
    result = {}
    for row in cursor.fetchall():
        if isinstance(row, dict):
            table_name, column_name = row.get('t'), row.get('c')
        else:
            table_name, column_name = row[0], row[1]
        if table_name:
            result.setdefault(table_name, []).append(column_name)
    return result


def discover_domain_tables(cursor):
    """发现需要处理的表：album_pool + 所有 albums_% 用户表 + users"""
    cursor.execute('SHOW TABLES')
    rows = cursor.fetchall()
    tables = [(row[list(row.keys())[0]] if isinstance(row, dict) else row[0]) for row in rows]
    return [t for t in tables if match_table_pattern(t)]


def plan_targets(cursor):
    """返回 [(table, [column, ...]), ...]，只保留真正存在的字段"""
    columns_map = _fetch_all_columns(cursor)
    targets = []
    for table in discover_domain_tables(cursor):
        columns = columns_for_table(table, columns_map.get(table, []))
        if columns:
            targets.append((table, columns))
    return targets


def detect_old_domains(cursor, targets, new_domain=None):
    """扫描各 URL 字段，统计后端旧域名前缀出现次数 → [(prefix, count)]，按次数降序"""
    prefixes = {}
    for table, columns in targets:
        for column in columns:
            sql = (f"SELECT DISTINCT `{column}` AS v FROM `{table}` "
                   f"WHERE `{column}` LIKE 'http%%' AND `{column}` IS NOT NULL AND `{column}` != '' "
                   f"LIMIT 5000")
            try:
                cursor.execute(sql)
            except Exception as e:  # noqa: BLE001 - 单表失败不应中断整体扫描
                print(f"⚠️ 扫描 [{table}.{column}] 失败（跳过）：{e}")
                continue
            for row in cursor.fetchall():
                value = row['v'] if isinstance(row, dict) else row[0]
                prefix = extract_url_prefix(value)
                if prefix and is_backend_domain(prefix) and prefix != new_domain:
                    prefixes[prefix] = prefixes.get(prefix, 0) + 1
    return sorted(prefixes.items(), key=lambda item: -item[1])


def count_affected_rows(cursor, table, column, old_domain):
    """统计某字段里含旧域名的行数"""
    cursor.execute(
        f"SELECT COUNT(*) AS c FROM `{table}` "
        f"WHERE `{column}` LIKE %s AND `{column}` IS NOT NULL AND `{column}` != ''",
        (f"%{old_domain}%",)
    )
    row = cursor.fetchone()
    return row['c'] if isinstance(row, dict) else row[0]


def replace_domain_in_column(conn, cursor, table, column, old_domain, new_domain):
    """把某个字段里的旧域名替换为新域名（REPLACE 兼容 JSON / 长文本），返回影响行数"""
    try:
        affected = cursor.execute(
            f"UPDATE `{table}` SET `{column}` = REPLACE(`{column}`, %s, %s) "
            f"WHERE `{column}` LIKE %s AND `{column}` IS NOT NULL AND `{column}` != ''",
            (old_domain, new_domain, f"%{old_domain}%")
        )
        conn.commit()
        return affected
    except Exception as e:  # noqa: BLE001
        conn.rollback()
        print(f"❌ 更新 [{table}.{column}] 失败：{e}")
        return 0


def replace_all(conn, cursor, targets, old_domain, new_domain):
    """对所有目标字段执行域名替换，返回 {表名: 行数} 与总行数"""
    stats = {}
    total = 0
    for table, columns in targets:
        for column in columns:
            affected = replace_domain_in_column(conn, cursor, table, column, old_domain, new_domain)
            if affected:
                stats[f'{table}.{column}'] = affected
                total += affected
    return stats, total


def preview(conn, targets, old_domains, new_domain):
    """预览：每条旧域名在各表各字段的影响行数（不写入）"""
    lines = []
    cursor = conn.cursor()
    for old_domain, _ in old_domains:
        lines.append(f"  {old_domain} → {new_domain}")
        for table, columns in targets:
            for column in columns:
                count = count_affected_rows(cursor, table, column, old_domain)
                if count:
                    lines.append(f"    {table}.{column}：{count} 行")
    cursor.close()
    return lines


def save_preferred_host(host):
    """把选定地址写入 backend/data/lan_host.txt（config.py 启动时优先读取，不入库）"""
    try:
        os.makedirs(os.path.dirname(LAN_HOST_FILE), exist_ok=True)
        with open(LAN_HOST_FILE, 'w', encoding='utf-8') as f:
            f.write(f'{host}\n')
        return True
    except (IOError, OSError) as e:
        print(f"⚠️ 保存首选地址失败（不影响本次替换）：{e}")
        return False
