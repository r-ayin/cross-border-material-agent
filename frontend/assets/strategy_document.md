# 一键出海：本次运行策略与验收记录

## English Abstract
A standard-library Python pipeline prepares three localized listings, six role-specific images and one product video. File existence, technical validity and publishable quality are separate states. Unknown checks remain unverified.

## 事实与本地化
商品源数据是事实边界。英、美式英语；韩、韩国韩语；葡、巴西葡语。保留真实SKU与来源，不虚构成分、尺寸、价格、洗护和物流承诺。没有实测数据时标记缺失，不把市场尺码习惯当作等码证明。

## 图像职责与产品保真
交付主图、卖点整体图、工艺特写、材质特写、生活场景、完整全景六个不同槽位。主图要求完整主体与白底；生活场景不套用主图的白底限制。来源URL始终是权威参照，生成图不能反过来证明原商品的结构。已知违规候选不作为合格交付；视觉检查不可用则明确待复核。

## 视频完成度
优先单次参考图驱动的完整视频，禁止把单个分镜冒充整片。目标时长不是实测时长；容器、视频轨道、实际尺寸和时长由本地解析核验。字幕旁挂文件不等于字幕已烧录，配乐指令不等于已生成或混音。分镜覆盖、动态形变、水印、音画质量仍需要真实生成与观看验收。

## 预算与调用纪律
先离线预检，再用已核实接口的小样测试，最后在授权后生成正式产物。默认禁网；配置密钥本身不会触发调用。请求共享截止时间、总次数和媒体次数上限。任务已受理后的轮询失败不会自动新建任务；避免未知状态重复计费。

## 本次可观察证据
以下仅记录实际收集到的状态；记录为空代表未知，不代表没有发生降级。

```json
{
  "source_product_id": "8822221153828",
  "source_platform": "123批发网",
  "source_url": "https://www.123.com/",
  "target_category": {},
  "attribute_mapping": {},
  "style": "premium-editorial",
  "reference_policy": "original source URLs are authoritative; no invented multi-view anchor",
  "observed_media_and_copy_models": [
    "qwen3.8-max"
  ],
  "copy_quality": {
    "en": {
      "status": "needs_review",
      "checks_status": "needs_review",
      "semantic_review": "pending",
      "reasons": [
        "facts:source_identifier_missing",
        "facts:raw_sku_integrity",
        "language:mixed_script",
        "facts:unverified_season",
        "facts:unverified_composition",
        "facts:unverified_logistics",
        "facts:dimension_pending_review",
        "facts:size_data_repair_required",
        "facts:unsupported_number:2026",
        "facts:unsupported_number:5.0",
        "facts:unsupported_number:1",
        "facts:unsupported_number:397",
        "facts:unverified_quoted_data",
        "facts:unsupported_number:7",
        "facts:unsupported_number:4",
        "facts:unsupported_number:98",
        "facts:unsupported_number:99",
        "facts:unsupported_number:100",
        "fallback:source_only_template",
        "insufficient_facts:bullet_points",
        "insufficient_facts:search_keywords",
        "review:semantic_facts_and_native_language_pending"
      ],
      "model": "qwen3.8-max",
      "attempts": 2,
      "fallback": true,
      "history": [
        {
          "attempt": 1,
          "model": "qwen3.8-max",
          "issues": [
            "facts:source_identifier_missing",
            "facts:raw_sku_integrity",
            "language:mixed_script",
            "facts:unverified_season",
            "facts:unverified_composition",
            "facts:unverified_logistics",
            "facts:dimension_pending_review",
            "facts:size_data_repair_required",
            "facts:unsupported_number:2026",
            "facts:unsupported_number:5.0",
            "facts:unsupported_number:1",
            "facts:unsupported_number:397"
          ]
        },
        {
          "attempt": 2,
          "model": "qwen3.8-max",
          "issues": [
            "facts:source_identifier_missing",
            "facts:raw_sku_integrity",
            "facts:unverified_quoted_data",
            "language:mixed_script",
            "facts:unverified_composition",
            "facts:unverified_season",
            "facts:dimension_pending_review",
            "facts:size_data_repair_required",
            "facts:unsupported_number:2026",
            "facts:unsupported_number:5.0",
            "facts:unsupported_number:1",
            "facts:unsupported_number:397",
            "facts:unsupported_number:7",
            "facts:unsupported_number:4",
            "facts:unsupported_number:98",
            "facts:unsupported_number:99",
            "facts:unsupported_number:100"
          ]
        }
      ],
      "language": "en",
      "validation_scope": "schema, section bodies, source identity/SKUs, conservative claim and language heuristics"
    },
    "ko": {
      "status": "needs_review",
      "checks_status": "needs_review",
      "semantic_review": "pending",
      "reasons": [
        "facts:source_identifier_missing",
        "facts:raw_sku_integrity",
        "language:mixed_script",
        "facts:unverified_season",
        "facts:unverified_composition",
        "facts:unverified_logistics",
        "facts:size_data_repair_required",
        "facts:unsupported_number:2026",
        "facts:unsupported_number:2633",
        "facts:unsupported_number:5.0",
        "facts:unverified_quoted_data",
        "facts:unverified_media_completion",
        "facts:unsupported_number:98",
        "facts:unsupported_number:99",
        "facts:unsupported_number:100",
        "fallback:source_only_template",
        "insufficient_facts:bullet_points",
        "insufficient_facts:search_keywords",
        "review:semantic_facts_and_native_language_pending"
      ],
      "model": "qwen3.8-max",
      "attempts": 2,
      "fallback": true,
      "history": [
        {
          "attempt": 1,
          "model": "qwen3.8-max",
          "issues": [
            "facts:source_identifier_missing",
            "facts:raw_sku_integrity",
            "language:mixed_script",
            "facts:unverified_season",
            "facts:unverified_composition",
            "facts:unverified_logistics",
            "facts:size_data_repair_required",
            "facts:unsupported_number:2026",
            "facts:unsupported_number:2633",
            "facts:unsupported_number:5.0"
          ]
        },
        {
          "attempt": 2,
          "model": "qwen3.8-max",
          "issues": [
            "facts:source_identifier_missing",
            "facts:raw_sku_integrity",
            "facts:unverified_quoted_data",
            "language:mixed_script",
            "facts:unverified_media_completion",
            "facts:unverified_season",
            "facts:unverified_composition",
            "facts:size_data_repair_required",
            "facts:unsupported_number:2026",
            "facts:unsupported_number:2633",
            "facts:unsupported_number:5.0",
            "facts:unsupported_number:98",
            "facts:unsupported_number:99",
            "facts:unsupported_number:100"
          ]
        }
      ],
      "language": "ko",
      "validation_scope": "schema, section bodies, source identity/SKUs, conservative claim and language heuristics"
    },
    "pt": {
      "status": "needs_review",
      "checks_status": "needs_review",
      "semantic_review": "pending",
      "reasons": [
        "facts:source_identifier_missing",
        "facts:raw_sku_integrity",
        "language:mixed_script",
        "facts:unverified_season",
        "facts:unverified_composition",
        "facts:unverified_logistics",
        "facts:dimension_pending_review",
        "facts:size_data_repair_required",
        "facts:unsupported_number:2026",
        "facts:unsupported_number:5.0",
        "facts:unsupported_number:1",
        "schema:invalid_json:JSONDecodeError",
        "fallback:source_only_template",
        "insufficient_facts:bullet_points",
        "insufficient_facts:search_keywords",
        "review:semantic_facts_and_native_language_pending"
      ],
      "model": "qwen3.8-max",
      "attempts": 2,
      "fallback": true,
      "history": [
        {
          "attempt": 1,
          "model": "qwen3.8-max",
          "issues": [
            "facts:source_identifier_missing",
            "facts:raw_sku_integrity",
            "language:mixed_script",
            "facts:unverified_season",
            "facts:unverified_composition",
            "facts:unverified_logistics",
            "facts:dimension_pending_review",
            "facts:size_data_repair_required",
            "facts:unsupported_number:2026",
            "facts:unsupported_number:5.0",
            "facts:unsupported_number:1"
          ]
        },
        {
          "attempt": 2,
          "model": "qwen3.8-max",
          "issues": [
            "schema:invalid_json:JSONDecodeError"
          ]
        }
      ],
      "language": "pt",
      "validation_scope": "schema, section bodies, source identity/SKUs, conservative claim and language heuristics"
    }
  },
  "image_quality": {},
  "video_delivery": {},
  "degradation_events": [],
  "elapsed_seconds": 0.0,
  "remaining_seconds": 1680.0,
  "request_accounting": {
    "network_authorized": false,
    "model_requests": 0,
    "media_requests": 0,
    "max_model_requests": 64,
    "max_media_requests": 24
  }
}
```

## 配置候选（不代表全部调用过）
```json
[
  {
    "role": "text primary",
    "model": "qwen3.8-max"
  },
  {
    "role": "category / text fallback",
    "model": "qwen3.7-max"
  },
  {
    "role": "visual review",
    "model": "qwen-vl-max"
  },
  {
    "role": "image candidates",
    "model": "qwen-image-3.0-pro / wan2.7-image-pro / wan2.7-image"
  },
  {
    "role": "video candidates",
    "model": "wan2.7-i2v / happyhorse-1.1-r2v / happyhorse-1.1-t2v"
  }
]
```

## 完成标准
11个必需文件通过技术检查只是结构完成。发布就绪还需要三语事实复核、六图职责与保真检查、视频完整性和无水印检查；详见 quality_report.json。本文件由代码根据运行记录组装，没有额外调用文本模型。
