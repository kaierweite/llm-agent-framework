# llm-agent-defense - Design Spec

> Human-readable design narrative. Machine-readable execution contract: `spec_lock.md`.

## I. Project Information

| Item | Value |
| ---- | ----- |
| **Project Name** | llm-agent-defense |
| **Canvas Format** | PPT 16:9 (1280×720) |
| **Page Count** | 8 pages |
| **Design Style** | B) General Consulting — data-driven academic defense |
| **Target Audience** | 毕业答辩评审老师（计算机科学背景） |
| **Use Case** | 本科毕业设计答辩汇报，3 分钟演讲 |
| **Created Date** | 2026-05-20 |

---

## II. Canvas Specification

| Property | Value |
| -------- | ----- |
| **Format** | PPT 16:9 |
| **Dimensions** | 1280 × 720 px |
| **viewBox** | `0 0 1280 720` |
| **Margins** | left/right 60px, top/bottom 50px |
| **Content Area** | 1160 × 620 px |

---

## III. Visual Theme

### Theme Style

- **Style**: Consulting + Academic Defense — data-driven, clean, professional
- **Theme**: Light theme
- **Tone**: 专业克制、科技感、学术严谨

### Color Scheme

> IKB 克莱因蓝为主色调，搭配高级灰白底，深灰文字。强调数据用蓝色，正文用深灰，保持克制不花哨。

| Role | HEX | Purpose |
| ---- | --- | ------- |
| **Background** | `#FAFAF8` | 主页面背景 |
| **Secondary bg** | `#F0F0EE` | 卡片背景、区块背景 |
| **Primary** | `#002FA7` | 标题装饰、关键区块、图标 |
| **Accent** | `#002FA7` | 数据高亮、关键信息 |
| **Secondary accent** | `#5B7BFF` | 次要强调、过渡 |
| **Body text** | `#0A0A0A` | 正文主色 |
| **Secondary text** | `#525252` | 说明文字、注释 |
| **Tertiary text** | `#737373` | 辅助信息、页脚 |
| **Border/divider** | `#E0E0E0` | 卡片边框、分割线 |

---

## IV. Typography System

### Font Plan

**Typography direction**: modern CJK sans — clean, legible, academic

| Role | Chinese | English | Fallback tail |
| ---- | ------- | ------- | ------------- |
| **Title** | `"Microsoft YaHei"` | `Arial` | `sans-serif` |
| **Body** | `"Microsoft YaHei"` | `Arial` | `sans-serif` |
| **Emphasis** | `"Microsoft YaHei"` | `Arial` | `sans-serif` |
| **Code** | — | `Consolas, "Courier New"` | `monospace` |

**Per-role font stacks**:

- Title: `"Microsoft YaHei", Arial, sans-serif`
- Body: `"Microsoft YaHei", Arial, sans-serif`
- Emphasis: same as Body
- Code: `Consolas, "Courier New", monospace`

### Font Size Ramp

| Role | Size (px) | Weight |
|------|-----------|--------|
| **Cover Title** | 64 | 700 |
| **Section Title** | 36 | 700 |
| **KPI Number** | 56 | 700 |
| **Subtitle** | 24 | 400 |
| **Body** | 20 | 400 |
| **Card Title** | 22 | 600 |
| **Annotation** | 14 | 400 |
| **Meta/Kicker** | 12 | 600 |

---

## V. Layout Strategy

### Page Rhythm

| Page | Content | Rhythm | Layout Style |
|------|---------|--------|-------------|
| 01 | 封面 | anchor | Centered hero with title + subtitle |
| 02 | 项目背景与动机 | breathing | Split: left statement / right context |
| 03 | 核心痛点与工具调用 | dense | 2×2 cards: 3 pain points + 1 solution |
| 04 | 工具调用成果与上下文压缩 | anchor | KPI hero: big number 93.3% + detail |
| 05 | 长期记忆系统 | dense | Data comparison: 45K→8.5K + 3 memory types |
| 06 | 动态技能与企业功能 | dense | 4-column cards + tech stack bar |
| 07 | 成果回顾与展望 | breathing | Split: left manifesto / right 3 KPIs |
| 08 | 致谢 | anchor | Centered closing with thank you |

---

## VI. Icon Strategy

- **Library**: `chunk-filled` (geometric, clean, matches consulting tone)
- **Usage**: Minimal — icon per card header only, no decorative icons
- **Color**: `var(--primary)` for active, `var(--tertiary-text)` for muted

---

## VII. Visualization Strategy

- No complex charts needed
- Data presented as large KPI numbers with context labels
- Comparison data (45K→8.5K) shown as side-by-side blocks

---

## VIII. Image Resource Plan

| Page | Image Need | Source | Status |
|------|-----------|--------|--------|
| All pages | No images required | — | — |

> All pages are text + data driven. No AI image generation needed. Skip Step 5.

---

## IX. Content Outline

### Page 01 — Cover
- Title: LLM Agent Framework · 智能代理框架
- Subtitle: 毕业设计答辩汇报
- Meta: 2026 · 计算机科学与技术

### Page 02 — 项目背景与动机
- Left (blue block): "从'会聊天'到'能干活'"
- Right: Problem scenario + core proposition
- Key message: LLM被困在对话框里 — 如何让它具备行动能力？

### Page 03 — 核心痛点与工具调用
- 4 cards (2×2 grid):
  - 痛点01: 知识时效性受限
  - 痛点02: 无外部行动能力
  - 痛点03: 上下文窗口瓶颈
  - 方案: LLM Agent Framework (accent card)

### Page 04 — 工具调用引擎
- Left: ReAct 范式说明 + 工具数量
- Right: KPI block — 93.3% 准确率
- Sub: 30道测试 · 28道正确 · 最多5轮链式调用

### Page 05 — 上下文压缩与长期记忆
- Left: 压缩数据对比 (45K → 8.5K, 5.3:1)
- Right: 3类长期记忆 (偏好/事实/任务)

### Page 06 — 动态技能与企业功能
- 4-column cards: 动态技能 / JWT认证 / 部门管理 / 审计日志
- Bottom: tech stack bar

### Page 07 — 成果回顾与展望
- Left (blue block): key achievements + personal reflection
- Right: 3 KPIs (93.3% / 5.3:1 / 1.2%)

### Page 08 — 致谢
- Centered: "感谢聆听"
- Sub: 期待各位老师的指导与建议

---

## X. Speaker Notes

Speaker notes will be extracted from `speech.txt` — one note per page matching the PPT marker sections.

---

## XI. Technical Constraints

- No external web fonts — use system pre-installed fonts only
- All colors via SVG `fill` attributes, no CSS classes
- Page size exactly 1280×720, viewBox `0 0 1280 720`
- Export target: PPTX via `svg_to_pptx.py`
