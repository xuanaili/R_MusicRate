# -*- coding: utf-8 -*-
"""MusicRate 桌面图标生成器（纯 Python 标准库，无 PIL 依赖）。

生成 launcher/musicrate.ico（含 256/128/64/48/32/16 多尺寸）与
launcher/musicrate_preview.png（预览用）。
用法：
    ..\portable\python\python.exe make_icon.py
设计：紫色→蓝色对角渐变圆角底板 + 白色双八分音符（带阴影）。
"""
import os
import struct
import zlib

SIZE = 256


def lerp(a, b, t):
    return int(a + (b - a) * t)


def clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


def dist_point_segment(px, py, ax, ay, bx, by):
    """点到线段 (a-b) 的距离"""
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    seg2 = vx * vx + vy * vy
    t = 0.0 if seg2 == 0 else clamp((wx * vx + wy * vy) / seg2, 0.0, 1.0)
    dx, dy = px - (ax + vx * t), py - (ay + vy * t)
    return (dx * dx + dy * dy) ** 0.5


class Canvas:
    """RGBA 画布：先画不透明底色，再叠 alpha-over。"""

    def __init__(self, size):
        self.size = size
        self.px = [(0, 0, 0, 0)] * (size * size)

    def _blend(self, i, r, g, b, a):
        if a <= 0:
            return
        if i < 0 or i >= len(self.px):
            return
        if a >= 255:
            self.px[i] = (r, g, b, 255)
            return
        br, bg, bb, ba = self.px[i]
        af = a / 255.0
        bf = ba / 255.0
        out_a = af + bf * (1.0 - af)
        if out_a <= 0:
            return
        w_src = af
        w_dst = bf * (1.0 - af)
        out_r = (r * w_src + br * w_dst) / out_a
        out_g = (g * w_src + bg * w_dst) / out_a
        out_b = (b * w_src + bb * w_dst) / out_a
        self.px[i] = (int(out_r + 0.5), int(out_g + 0.5), int(out_b + 0.5),
                      int(min(255.0, out_a * 255.0 + 0.5)))

    def fill_rrect(self, x0, y0, x1, y1, radius, color, alpha):
        """填充圆角矩形"""
        r, g, b = color
        cx = [x0 + radius, x1 - radius]
        cy = [y0 + radius, y1 - radius]
        rr = radius * radius
        for yy in range(int(y0), int(y1)):
            for xx in range(int(x0), int(x1)):
                # 判断是否在圆角区外（四个角）
                if xx < cx[0] and yy < cy[0]:
                    if (xx - cx[0]) ** 2 + (yy - cy[0]) ** 2 > rr:
                        continue
                elif xx > cx[1] and yy < cy[0]:
                    if (xx - cx[1]) ** 2 + (yy - cy[0]) ** 2 > rr:
                        continue
                elif xx < cx[0] and yy > cy[1]:
                    if (xx - cx[0]) ** 2 + (yy - cy[1]) ** 2 > rr:
                        continue
                elif xx > cx[1] and yy > cy[1]:
                    if (xx - cx[1]) ** 2 + (yy - cy[1]) ** 2 > rr:
                        continue
                self._blend(yy * self.size + xx, r, g, b, alpha)

    def fill_ellipse(self, cx_, cy_, rx, ry, color, alpha):
        r, g, b = color
        inv_rx = 1.0 / (rx * rx)
        inv_ry = 1.0 / (ry * ry)
        for yy in range(int(cy_ - ry), int(cy_ + ry) + 1):
            for xx in range(int(cx_ - rx), int(cx_ + rx) + 1):
                dx, dy = xx - cx_, yy - cy_
                if dx * dx * inv_rx + dy * dy * inv_ry <= 1.0:
                    self._blend(yy * self.size + xx, r, g, b, alpha)

    def fill_segment(self, ax, ay, bx, by, thick, color, alpha):
        r, g, b = color
        h = thick / 2.0
        x0 = int(min(ax, bx) - h - 1)
        x1 = int(max(ax, bx) + h + 1)
        y0 = int(min(ay, by) - h - 1)
        y1 = int(max(ay, by) + h + 1)
        for yy in range(max(0, y0), min(self.size, y1)):
            for xx in range(max(0, x0), min(self.size, x1)):
                if dist_point_segment(xx + 0.5, yy + 0.5, ax, ay, bx, by) <= h:
                    self._blend(yy * self.size + xx, r, g, b, alpha)

    def to_rgb_rows(self):
        return [bytes(v for px in self.px[y * self.size:(y + 1) * self.size] for v in px)
                for y in range(self.size)]


def draw_note(c, s, scale):
    """画两个相连的八分音符，整体缩放 scale，返回其外接盒中心供上层定位。

    音符单元尺寸按画布比例设计：头在下方 0.56s 处，杆向上，横梁连接两杆顶。
    """
    head_rx, head_ry = 0.088 * s, 0.066 * s
    lx, rx_ = 0.265 * s, 0.735 * s
    head_y = 0.585 * s
    l_stem_top = (lx, 0.405 * s)
    r_stem_top = (rx_, 0.300 * s)
    # 横梁：连接两个杆顶的粗线段，两端稍外延
    beam_color = (255, 255, 255)
    c.fill_segment(l_stem_top[0] - 0.025 * s, l_stem_top[1],
                   r_stem_top[0] + 0.025 * s, r_stem_top[1],
                   0.055 * s, beam_color, 255)
    # 杆
    c.fill_segment(l_stem_top[0], l_stem_top[1], lx, head_y - head_ry + 0.02 * s,
                   0.045 * s, beam_color, 255)
    c.fill_segment(r_stem_top[0], r_stem_top[1], rx_, head_y - head_ry + 0.02 * s,
                   0.045 * s, beam_color, 255)
    # 符头（两个椭圆）
    c.fill_ellipse(lx, head_y, head_rx, head_ry, beam_color, 255)
    c.fill_ellipse(rx_, head_y, head_rx, head_ry, beam_color, 255)


def render(size):
    c = Canvas(size)
    s = float(size)
    pad = 0.015 * s

    # —— 底板：圆角方形，紫色→蓝色对角渐变 ——
    r_grad = (0x8E, 0x24, 0xAA)   # 紫  #8E24AA
    b_grad = (0x1E, 0x88, 0xE5)   # 蓝  #1E88E5
    radius = 0.20 * s
    x0, y0, x1, y1 = pad, pad, s - pad, s - pad
    for yy in range(int(y0), int(y1)):
        for xx in range(int(x0), int(x1)):
            # 圆角测试
            cx0, cx1 = x0 + radius, x1 - radius
            cy0, cy1 = y0 + radius, y1 - radius
            rr = radius * radius
            corner = False
            if xx < cx0 and yy < cy0:
                corner = (xx - cx0) ** 2 + (yy - cy0) ** 2 > rr
            elif xx > cx1 and yy < cy0:
                corner = (xx - cx1) ** 2 + (yy - cy0) ** 2 > rr
            elif xx < cx0 and yy > cy1:
                corner = (xx - cx0) ** 2 + (yy - cy1) ** 2 > rr
            elif xx > cx1 and yy > cy1:
                corner = (xx - cx1) ** 2 + (yy - cy1) ** 2 > rr
            if corner:
                continue
            t = (xx + yy) / (2.0 * (s - 1))
            t = clamp(t, 0.0, 1.0)
            col = (lerp(r_grad[0], b_grad[0], t),
                   lerp(r_grad[1], b_grad[1], t),
                   lerp(r_grad[2], b_grad[2], t))
            c._blend(yy * size + xx, col[0], col[1], col[2], 255)

    # —— 左上高光（柔和半透明白）——
    c.fill_ellipse(0.30 * s, 0.18 * s, 0.42 * s, 0.34 * s,
                   (255, 255, 255), 26)
    c.fill_ellipse(0.24 * s, 0.14 * s, 0.30 * s, 0.24 * s,
                   (255, 255, 255), 18)

    # —— 音符阴影（深紫半透明，稍偏右下，先画）——
    def draw_shadow(offx, offy):
        o = 0.018 * s
        c.fill_segment(-999, -999, -999, -999, 0, (0, 0, 0), 0)  # no-op 占位
        c.fill_segment(0.265 * s + offx - 0.025 * s, 0.405 * s + offy,
                       0.735 * s + offx + 0.025 * s, 0.300 * s + offy,
                       0.055 * s, (26, 35, 126), 110)
        c.fill_segment(0.265 * s + offx, 0.405 * s + offy,
                       0.265 * s + offx, 0.585 * s - 0.066 * s + 0.02 * s + offy,
                       0.045 * s, (26, 35, 126), 110)
        c.fill_segment(0.735 * s + offx, 0.300 * s + offy,
                       0.735 * s + offx, 0.585 * s - 0.066 * s + 0.02 * s + offy,
                       0.045 * s, (26, 35, 126), 110)
        c.fill_ellipse(0.265 * s + offx, 0.585 * s + offy,
                       0.088 * s, 0.066 * s, (26, 35, 126), 110)
        c.fill_ellipse(0.735 * s + offx, 0.585 * s + offy,
                       0.088 * s, 0.066 * s, (26, 35, 126), 110)

    draw_shadow(0.016 * s, 0.020 * s)

    # —— 白色音符 ——
    draw_note(c, s, 1.0)

    # —— 后处理：圆角矩形之外的像素全部清为透明（防止高光/阴影越界留白晕）——
    def in_rrect(x, y, rx0, ry0, rx1, ry1, rr_):
        if not (rx0 <= x <= rx1 and ry0 <= y <= ry1):
            return False
        cx0, cx1 = rx0 + rr_, rx1 - rr_
        cy0, cy1 = ry0 + rr_, ry1 - rr_
        if cx0 <= x <= cx1 or cy0 <= y <= cy1:
            return True
        dcx = cx0 if x < cx0 else cx1
        dcy = cy0 if y < cy0 else cy1
        return (x - dcx) ** 2 + (y - dcy) ** 2 <= rr_ * rr_

    for i in range(size * size):
        if not in_rrect(i % size + 0.5, i // size + 0.5, x0, y0, x1, y1, radius):
            c.px[i] = (0, 0, 0, 0)

    return c


def png_chunk(tag, data):
    return (struct.pack('>I', len(data)) + tag + data +
            struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff))


def encode_png(canvas):
    size = canvas.size
    ihdr = struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0)
    raw = b''.join(b'\x00' + row for row in canvas.to_rgb_rows())
    return (b'\x89PNG\r\n\x1a\n' + png_chunk(b'IHDR', ihdr) +
            png_chunk(b'IDAT', zlib.compress(raw, 9)) + png_chunk(b'IEND', b''))


def make_ico(pngs):
    """pngs: [(size, png_bytes), ...]；ICO 内使用 PNG 压缩条目（Vista+ 支持）"""
    header = struct.pack('<HHH', 0, 1, len(pngs))
    offset = 6 + 16 * len(pngs)
    entries = b''
    blob = b''
    for size, png in pngs:
        b = 0 if size >= 256 else size
        entries += struct.pack('<BBBBHHII', b, b, 0, 0, 1, 32, len(png), offset)
        blob += png
        offset += len(png)
    return header + entries + blob


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    sizes = [256, 128, 64, 48, 32, 16]
    pngs = []
    for sz in sizes:
        canvas = render(sz)
        pngs.append((sz, encode_png(canvas)))
    with open(os.path.join(here, 'musicrate.ico'), 'wb') as f:
        f.write(make_ico(pngs))
    with open(os.path.join(here, 'musicrate_preview.png'), 'wb') as f:
        f.write(pngs[0][1])
    print('已生成 musicrate.ico（尺寸：%s）与 musicrate_preview.png' % ', '.join(str(s) for s in sizes))


if __name__ == '__main__':
    main()