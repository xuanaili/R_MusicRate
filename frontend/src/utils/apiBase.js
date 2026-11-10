// MusicRate\frontend\src\utils\apiBase.js
// 后端地址解析（局域网/手机访问的关键）
//
// 背景：之前 axios 的 baseURL 写死成 http://localhost:5000，
// 手机通过 http://192.168.19.139:8080 打开页面时，localhost 指的是【手机自己】，
// 登录请求根本到不了电脑上的 Flask，于是前端只能提示“服务异常/连接服务器失败”。
//
// 现在的规则：后端地址 = 页面自身的主机名 + 5000 端口
//   - 电脑上 http://localhost:8080 打开   → http://localhost:5000
//   - 电脑上 http://127.0.0.1:8080 打开   → http://127.0.0.1:5000
//   - 手机上 http://192.168.19.139:8080   → http://192.168.19.139:5000
//
// 需要指向别的机器/端口时（前端和后端不在同一台电脑），浏览器控制台执行后刷新：
//   localStorage.setItem('backend_origin', 'http://10.0.0.5:5000')
//   localStorage.removeItem('backend_origin')   // 恢复默认
export const BACKEND_PORT = 5000

const OVERRIDE_KEY = 'backend_origin'

// 媒体文件（封面/缩略图/音频/头像）在后端的路径前缀，按主机动态拼接
const MEDIA_PREFIXES = ['/covers/', '/covers_thumb/', '/tracks/']

// 后端写进数据库的媒体地址前缀：localhost / 127.0.0.1 / 0.0.0.0 / 任意 IPv4（含换网络后的旧局域网 IP）
// 端口为后端端口（省略端口也认）——换网络后表里残留的旧 IP 地址会被自动纠到当前访问的主机
const LOCAL_ORIGIN_RE = new RegExp(
  '^https?://(?:localhost|127\\.0\\.0\\.1|0\\.0\\.0\\.0|(?:\\d{1,3}\\.){3}\\d{1,3})(?::' + BACKEND_PORT + ')?(?=/|$)',
  'i'
)

/**
 * 当前应该访问的后端根地址，形如 http://192.168.19.139:5000（不带结尾斜杠）
 */
export function apiOrigin() {
  try {
    const override = (localStorage.getItem(OVERRIDE_KEY) || '').trim().replace(/\/+$/, '')
    if (override) return override
  } catch (e) {
    // localStorage 被禁用时走默认推导
  }
  const protocol = window.location.protocol === 'https:' ? 'https:' : 'http:'
  const hostname = window.location.hostname || 'localhost'
  return `${protocol}//${hostname}:${BACKEND_PORT}`
}

/**
 * 把后端返回的写死地址改写成当前访问主机的地址。
 *   http://localhost:5000/covers/a.jpg  → http://<当前主机>:5000/covers/a.jpg
 *   /covers/a.jpg（相对路径）            → http://<当前主机>:5000/covers/a.jpg
 * 外链（https://picsum.photos/...）与 blob: 预览地址原样返回。
 */
export function resolveBackendUrl(url) {
  if (typeof url !== 'string' || !url) return url
  if (LOCAL_ORIGIN_RE.test(url)) {
    const rest = url.replace(/^https?:\/\/[^/]+/i, '')
    return apiOrigin() + (rest || '/')
  }
  if (url.startsWith('/') && MEDIA_PREFIXES.some(prefix => url.startsWith(prefix))) {
    return apiOrigin() + url
  }
  return url
}

/**
 * 递归改写响应体里的本机媒体地址（响应体是接口原始数据，就地改写）。
 * 覆盖 cover_img / avatar / mp3_url / audioSrc 等所有字段，避免逐个组件打补丁。
 */
export function normalizeBackendUrls(value, depth = 0) {
  if (value === null || value === undefined) return value
  if (typeof value === 'string') return resolveBackendUrl(value)
  if (depth >= 8) return value
  if (Array.isArray(value)) {
    for (let i = 0; i < value.length; i += 1) {
      value[i] = normalizeBackendUrls(value[i], depth + 1)
    }
    return value
  }
  if (typeof value === 'object') {
    // 跳过 Date / File / Blob 等非纯数据对象（它们没有可枚举的自有字段，遍历无副作用）
    Object.keys(value).forEach(key => {
      value[key] = normalizeBackendUrls(value[key], depth + 1)
    })
    return value
  }
  return value
}
