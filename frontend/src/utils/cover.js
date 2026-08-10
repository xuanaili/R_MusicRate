// MusicRate\frontend\src\utils\cover.js 封面缩略图工具
// 列表页小图用缩略图URL（几十KB），详情页大图用原图URL
// 仅对本地图床（/covers/）转换，外部URL（picsum等）原样返回

export function coverThumb(url) {
  if (!url || typeof url !== 'string') return url
  if (url.includes('/covers/')) {
    return url.replace('/covers/', '/covers_thumb/')
  }
  return url
}
