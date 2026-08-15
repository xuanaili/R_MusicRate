// frontend/src/utils/styleAuto.js 动画样式自动生成纯函数（v0.9 P0）
// 服务「打开专辑时按类型(tags) + BPM 自动生成初始动画样式与参数」：
//   ① tags 决定风格预设（选 ball 小球水滴 / meteor 流星 / close 关闭 + 基础参数档位）
//   ② BPM 相对 100 基准微调能量参数（速度 / 密度 / 生成频率）
//   ③ 输出 {style_type, rhy_config, meteor_config}，供 AlbumDetail 落库 + 下发 RhythmBall 初始化
// 纯函数零 Vue 依赖 → 可 node 直接跑（golden 硬编码进 backend/tests/test_style_auto.py，
// 镜像 scoreList / lrcTime 既有模式）。
// 关键设计：基础参数档位不从配置重复手写，而是由 config/index.js 的 tagBallConfigList
// （单一数据源）按 RhythmBall 公式【反推】出 a-e（见 deriveRhyConfig），
// config 仅保留「能量启发式选型不理想的风格」的显式覆盖（stylePresetOverrides）。
import config from '../config/index.js';

// BPM 缩放基准（相对 100bpm）
const REF_BPM = 100;

function clamp(v, min, max) {
  return Math.max(min, Math.min(max, v));
}

function roundClamp(v, min, max) {
  return Math.round(clamp(v, min, max));
}

// 提取标签的【中文】部分（无括号返回 ''）
function extractZh(tag) {
  const m = String(tag).match(/【([^】]+)】/);
  return m ? m[1] : '';
}

// 提取标签的 English 部分（【之前的全部；无括号返回整串）
function extractEn(tag) {
  const t = String(tag);
  const idx = t.indexOf('【');
  return (idx >= 0 ? t.slice(0, idx) : t).trim();
}

/**
 * 按标签查配置（English 英文 + 【中文】双向匹配，优先级从高到低）：
 *   ① 精确全名（如 'Rock【摇滚音乐】'）
 *   ② 【中文】部分相等（如 '摇滚音乐'）
 *   ③ English 部分大小写不敏感相等（如 'rock'）
 * 未命中 → config.ballConfig.default（兜底参数档位）
 * @param {string|null|undefined} tag 单个标签
 * @returns {object} {minSize, maxSize, minRate, maxRate, numWeight}
 */
export function resolveBallParams(tag) {
  if (tag == null) return config.ballConfig.default;
  const t = String(tag).trim();
  if (!t) return config.ballConfig.default;
  if (config.ballConfig[t]) return config.ballConfig[t];
  const zh = extractZh(t);
  const en = extractEn(t).toLowerCase();
  for (const option of config.albumTagOptions) {
    const oZh = extractZh(option);
    const oEn = extractEn(option).toLowerCase();
    if (zh && oZh === zh) return config.ballConfig[option];
    if (en && oEn === en) return config.ballConfig[option];
  }
  return config.ballConfig.default;
}

// 能量启发式：numWeight × (1000 / minRate)，即「每秒生成量」近似（minRate 越小越频繁）
function energyOf(ballParams) {
  const { minRate = 200, numWeight = 1 } = ballParams || {};
  return numWeight * (1000 / Math.max(1, minRate));
}

// 基础参数档位 → 小球参数 a-e（0-100，与 RhythmBall 公式互逆，见文件头注释）
function deriveRhyConfig(ballParams) {
  const { minSize = 40, maxSize = 80, minRate = 200, maxRate = 400, numWeight = 1 } = ballParams || {};
  return {
    a: roundClamp((minSize - 5) / 0.95, 0, 100),
    b: roundClamp((maxSize - 10) / 0.9, 0, 100),
    c: roundClamp((minRate - 100) / 29, 0, 100),
    d: roundClamp((maxRate - 100) / 49, 0, 100),
    e: roundClamp((numWeight - 1) / 0.09, 0, 100)
  };
}

// 基础参数档位 → 流星参数（angle/size/tailLength/speed，0-100 量级，随能量提升）
function deriveMeteorConfig(ballParams, energy) {
  const { minSize = 40, maxSize = 80 } = ballParams || {};
  const avgSize = (minSize + maxSize) / 2;
  return {
    angle: 45,
    size: roundClamp(avgSize * 0.25, 8, 22),
    tailLength: roundClamp(30 + energy * 1.2, 30, 70),
    speed: roundClamp(15 + energy * 1.5, 20, 70)
  };
}

// 选动画类型：能量启发式（极低能量 close / 高能量 meteor / 其余 ball），被覆盖表优先
function pickStyleType(energy) {
  if (energy < 2.5) return 'close';
  if (energy >= 30) return 'meteor';
  return 'ball';
}

// 查 stylePresetOverrides（匹配逻辑同 resolveBallParams），未命中返回 null
function resolveOverride(tag) {
  if (tag == null || !config.stylePresetOverrides) return null;
  const t = String(tag).trim();
  if (!t) return null;
  if (config.stylePresetOverrides[t]) return config.stylePresetOverrides[t];
  const zh = extractZh(t);
  const en = extractEn(t).toLowerCase();
  for (const option of Object.keys(config.stylePresetOverrides)) {
    const oZh = extractZh(option);
    const oEn = extractEn(option).toLowerCase();
    if (zh && oZh === zh) return config.stylePresetOverrides[option];
    if (en && oEn === en) return config.stylePresetOverrides[option];
  }
  return null;
}

/**
 * 按专辑标签集合生成风格预设（首个命中标签决定，不匹配则默认预设）。
 * 返回 {style_type, rhy_config, meteor_config, bpm_scale}（新对象，不污染配置）。
 * @param {Array<string>|string|null} tags 专辑 tags（`English【中文】` 数组）
 * @returns {object} 风格预设
 */
export function presetFromTags(tags) {
  const list = Array.isArray(tags) ? tags : (tags != null ? [tags] : []);
  for (const tag of list) {
    if (tag == null) continue;
    const ballParams = resolveBallParams(tag);
    const override = resolveOverride(tag);
    const energy = energyOf(ballParams);
    return {
      style_type: override && override.style_type ? override.style_type : pickStyleType(energy),
      rhy_config: deriveRhyConfig(ballParams),
      meteor_config: deriveMeteorConfig(ballParams, energy),
      bpm_scale: override && override.bpm_scale != null ? override.bpm_scale : config.defaultBpmScale
    };
  }
  // 无标签 → 默认预设（defaultBallConfig + 默认类型/系数）
  const ballParams = config.ballConfig.default;
  const energy = energyOf(ballParams);
  return {
    style_type: config.defaultStyleType,
    rhy_config: deriveRhyConfig(ballParams),
    meteor_config: deriveMeteorConfig(ballParams, energy),
    bpm_scale: config.defaultBpmScale
  };
}

/**
 * BPM 相对 100 基准微调能量参数（速度 / 密度 / 生成频率）。
 * factor = (avgBpm / 100) ^ bpm_scale：
 *   - 生成间隔 c/d 越高 BPM 越短 → 除以 factor（越快）
 *   - 密度 e / 尺寸 a,b / 流星 speed、tailLength、size → 乘 factor（越高越强）
 * 返回 {rhy_config, meteor_config}（新对象，不污染原 preset）；avgBpm 非法/缺失 → 原样克隆。
 * @param {object} preset presetFromTags 的返回值
 * @param {number|null|undefined} avgBpm 专辑平均 BPM
 * @returns {object} {rhy_config, meteor_config}
 */
export function applyBpmAdjustment(preset, avgBpm) {
  const src = preset || {};
  const rc = src.rhy_config || {};
  const mc = src.meteor_config || {};
  const bpm = Number(avgBpm);
  if (!isFinite(bpm) || bpm <= 0) {
    return { rhy_config: { ...rc }, meteor_config: { ...mc } };
  }
  const scale = src.bpm_scale != null ? src.bpm_scale : config.defaultBpmScale;
  const factor = Math.pow(bpm / REF_BPM, scale);
  return {
    rhy_config: {
      a: roundClamp((rc.a || 0) * factor, 0, 100),
      b: roundClamp((rc.b || 0) * factor, 0, 100),
      c: roundClamp((rc.c || 0) / factor, 0, 100),
      d: roundClamp((rc.d || 0) / factor, 0, 100),
      e: roundClamp((rc.e || 0) * factor, 0, 100)
    },
    meteor_config: {
      angle: mc.angle != null ? mc.angle : 45,
      size: roundClamp((mc.size || 0) * factor, 0, 100),
      tailLength: roundClamp((mc.tailLength || 0) * factor, 0, 100),
      speed: roundClamp((mc.speed || 0) * factor, 0, 100)
    }
  };
}

/**
 * 一键生成初始样式：tags 定风格预设 → BPM 就绪则微调能量参数。
 * 返回 {style_type, rhy_config, meteor_config}，可直接落库 + 下发 RhythmBall 初始化。
 * @param {Array<string>|string|null} tags 专辑 tags
 * @param {object|null} tempoDict album_tempo 的 tempo JSON（{avg_bpm, ...}），缺失/未就绪传 null
 * @returns {object} {style_type, rhy_config, meteor_config}
 */
export function buildAutoConfig(tags, tempoDict) {
  const preset = presetFromTags(tags);
  const avgBpm = tempoDict && tempoDict.avg_bpm != null ? tempoDict.avg_bpm : null;
  const adjusted = applyBpmAdjustment(preset, avgBpm);
  return {
    style_type: preset.style_type,
    rhy_config: adjusted.rhy_config,
    meteor_config: adjusted.meteor_config
  };
}
