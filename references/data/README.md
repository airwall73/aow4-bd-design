# 原始数据检索指南（data/ 目录使用说明）

本目录是官网 9.4MB 原始 JSON，仅供检索、勿通读。以下规则来自实际踩坑，检索前必读。

## 内容在哪个文件

| 要找什么 | 文件 | 说明 |
|---|---|---|
| 单位面板、类型标签、文化归属 | `Units.json` | 类型标签在 `secondary_passives`（slug），文化在 `culture_name`/`sub_culture_name`（仅 EN 有英文原名） |
| 单位技能与被动（攻击、防御模式、Frenzy 等） | `Abilities.json` | 按 slug 或 name 查；`modifiers` 里有减益概率等结构化数据 |
| **魔典内容、单位附魔、种族转换、战斗/世界法术** | **`Spells.json`** | **附魔不在 Abilities.json！** 单位附魔、种族转换、法术全部按中文 `name` 在 ZH/Spells.json 查；Tomes.json 的 `skills[]` 列魔典内容条目 |
| 种族特性、社会特性 | `Traits.json` | **`description` 字段为空**，实际效果在 `effect_descriptions[].name` |
| 文化与理念 | `GEN/FactionCreation.json` | 仅英文，文化只有理念等极简字段 |

## 检索操作要点（Windows 环境）

1. **控制台直接 print 中文会乱码（GBK）**：一律用 `python -X utf8`，把结果**写入 UTF-8 临时文件再用 Read 读**，不要依赖 stdout。
2. **Windows 的 Python 没有 `/tmp`**：临时文件写到工作区临时目录（如 `.kimi_tmp/`），用完删除。
3. **ZH/Units.json 的 `id` 被翻译成中文**：跨语言匹配单位用 `resid`；Tomes 同理。
4. **slug → 名称映射**：单位类型标签等 slug（如 `0000039f000016f1`）在 EN/Abilities.json 里按 slug 查 `name`。
5. **剥 HTML 标签会丢数值**：不少数值嵌在标签内部（如 `+2点<defensefire></defensefire>火焰防护`，粗暴去标签后变成"+点火焰防护"）。涉及具体数值时**必须看原始文本**，不要只看剥标签后的结果；Tomes.json 内嵌的 skills 简介里数值尤其容易被剥光，以 Spells.json 全文为准。
6. 同名单位是不同文化变体（如多个 Archer），枚举时按 `id`+文化去重。

## 最小可用示例

```bash
cd references/data
python -X utf8 -c "
import json, io
sp = {a.get('name',''): a for a in json.load(open('ZH/Spells.json',encoding='utf-8'))}
out = io.open('D:/Kimi Workspace/.kimi_tmp/out.txt','w',encoding='utf-8')
out.write(sp['淬毒之箭']['description'])   # 保留原始标签，数值不丢
out.close()
"
```
