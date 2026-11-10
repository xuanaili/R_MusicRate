# MusicRate\backend\tests\test_net_domain.py 局域网域名预处理工具单测（纯逻辑，零 DB/网络依赖）
# 测试对象：backend/utils/net_domain.py
# 覆盖：URL 前缀解析 / 是否本项目后端域名 / 地址拼接 / 文件名提取 / 表字段筛选 / ipconfig 解析 / 候选地址排序
import pytest

from backend.config import PORT as BACKEND_PORT
from backend.utils import net_domain


class TestExtractUrlPrefix:
    def test_normal_cover_url(self):
        assert net_domain.extract_url_prefix(
            'http://localhost:5000/covers/a.jpg') == 'http://localhost:5000'

    def test_lan_ip_with_port(self):
        assert net_domain.extract_url_prefix(
            'http://192.168.19.139:5000/tracks/a.mp3') == 'http://192.168.19.139:5000'

    def test_https_and_no_port(self):
        assert net_domain.extract_url_prefix('https://example.com/covers/a.jpg') == 'https://example.com'

    def test_invalid_returns_none(self):
        assert net_domain.extract_url_prefix('') is None
        assert net_domain.extract_url_prefix(None) is None
        assert net_domain.extract_url_prefix('/covers/a.jpg') is None
        assert net_domain.extract_url_prefix(123) is None


class TestIsBackendDomain:
    @pytest.mark.parametrize('prefix', [
        'http://localhost:5000',
        'http://127.0.0.1:5000',
        'http://0.0.0.0:5000',
        'http://192.168.19.139:5000',
        'http://10.198.75.60:5000',
        'http://localhost',  # 省略端口也算（拼地址时按后端端口理解）
    ])
    def test_backend_prefixes(self, prefix):
        assert net_domain.is_backend_domain(prefix) is True

    @pytest.mark.parametrize('prefix', [
        'http://localhost:8080',      # 前端端口，不是后端
        'http://192.168.19.139:8081',  # 前端端口
        'https://example.com',         # 外链域名不动
        'http://picsum.photos',
        '',
        None,
    ])
    def test_non_backend_prefixes(self, prefix):
        assert net_domain.is_backend_domain(prefix) is False


class TestMakeDomain:
    def test_default_port(self):
        assert net_domain.make_domain('192.168.19.139') == f'http://192.168.19.139:{BACKEND_PORT}'

    def test_custom_port(self):
        assert net_domain.make_domain('localhost', 8080) == 'http://localhost:8080'


class TestUrlFileName:
    def test_localhost_url(self):
        assert net_domain.url_file_name('http://localhost:5000/tracks/a.mp3') == 'a.mp3'

    def test_lan_ip_url_with_chinese_name(self):
        url = 'http://192.168.19.139:5000/tracks/30_56fcd609_冀西南林路行.mp3'
        assert net_domain.url_file_name(url) == '30_56fcd609_冀西南林路行.mp3'

    def test_strips_query_and_hash(self):
        assert net_domain.url_file_name('http://x/tracks/a.mp3?v=1#t=2') == 'a.mp3'

    def test_plain_file_name(self):
        assert net_domain.url_file_name('a.mp3') == 'a.mp3'

    def test_empty(self):
        assert net_domain.url_file_name('') == ''
        assert net_domain.url_file_name(None) == ''


class TestColumnsForTable:
    def test_exact_table(self):
        assert net_domain.columns_for_table('album_pool') == ['cover_img', 'mp3_url']

    def test_pattern_table(self):
        assert net_domain.columns_for_table('albums_381') == ['cover_img', 'mp3_url']

    def test_users_table(self):
        assert net_domain.columns_for_table('users') == ['avatar']

    def test_unknown_table(self):
        assert net_domain.columns_for_table('album_tags') == []

    def test_intersect_existing_columns(self):
        # 老用户表可能没有 mp3_url 列 → 只保留真实存在的列，避免拼出非法 SQL
        assert net_domain.columns_for_table('albums_9', {'id', 'cover_img'}) == ['cover_img']

    def test_intersect_is_case_insensitive(self):
        assert net_domain.columns_for_table('users', {'AVATAR'}) == ['AVATAR']

    def test_match_table_pattern(self):
        assert net_domain.match_table_pattern('albums_1')['table_pattern'] == 'albums_%'
        assert net_domain.match_table_pattern('album_comments') is None


IPCONFIG_SAMPLE = """
Windows IP 配置

以太网适配器 以太网:

   连接特定的 DNS 后缀 . . . . . . . :
   IPv4 地址 . . . . . . . . . . . . : 192.168.19.139
   子网掩码  . . . . . . . . . . . . : 255.255.255.0
   默认网关. . . . . . . . . . . . . : 192.168.19.1

无线局域网适配器 WLAN:

   IPv4 地址 . . . . . . . . . . . . : 192.168.10.8
   子网掩码  . . . . . . . . . . . . : 255.255.255.0

以太网适配器 SSTAP 1:

   IPv4 地址 . . . . . . . . . . . . : 10.198.75.60
   子网掩码  . . . . . . . . . . . . : 255.255.255.0

隧道适配器 isatap.{0000}:

   IPv4 地址 . . . . . . . . . . . . : 127.0.0.1
"""


class TestParseIpconfig:
    def test_parses_adapters(self):
        result = net_domain.parse_ipconfig(IPCONFIG_SAMPLE)
        assert ('以太网适配器 以太网', '192.168.19.139') in result
        assert ('无线局域网适配器 WLAN', '192.168.10.8') in result
        assert ('以太网适配器 SSTAP 1', '10.198.75.60') in result

    def test_skips_loopback(self):
        result = net_domain.parse_ipconfig(IPCONFIG_SAMPLE)
        assert all(ip != '127.0.0.1' for _, ip in result)

    def test_empty_text(self):
        assert net_domain.parse_ipconfig('') == []
        assert net_domain.parse_ipconfig(None) == []


class TestVirtualAdapter:
    @pytest.mark.parametrize('name', ['以太网适配器 SSTAP 1', 'VMware Network Adapter VMnet1',
                                      'vEthernet (WSL)', 'Tailscale'])
    def test_virtual(self, name):
        assert net_domain.is_virtual_adapter(name) is True

    @pytest.mark.parametrize('name', ['以太网适配器 以太网', '无线局域网适配器 WLAN'])
    def test_physical(self, name):
        assert net_domain.is_virtual_adapter(name) is False


class TestBuildCandidateHosts:
    def test_order_and_dedup(self):
        adapters = [
            ('以太网适配器 以太网', '192.168.19.139'),
            ('VMware Network Adapter VMnet1', '192.168.74.1'),
            ('以太网适配器 以太网', '192.168.19.139'),  # 重复
        ]
        result = net_domain.build_candidate_hosts('192.168.19.139', adapters)
        hosts = [host for host, _ in result]
        assert hosts[0] == 'localhost'                 # 本机永远第一
        assert hosts[1] == '192.168.19.139'            # 自动识别的排第二
        assert hosts.count('192.168.19.139') == 1       # 去重
        assert hosts[-1] == '192.168.74.1'             # 虚拟网卡排最后

    def test_physical_before_virtual(self):
        adapters = [
            ('VMware Network Adapter VMnet1', '192.168.74.1'),
            ('无线局域网适配器 WLAN', '192.168.10.8'),
        ]
        hosts = [host for host, _ in net_domain.build_candidate_hosts(None, adapters)]
        assert hosts.index('192.168.10.8') < hosts.index('192.168.74.1')

    def test_without_primary_ip(self):
        hosts = [host for host, _ in net_domain.build_candidate_hosts(None, [])]
        assert hosts == ['localhost']
