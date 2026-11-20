# 原始数据检索指南（data/ 目录使用说明）

本目录包含官网 EN、ZH 两套文字数据及 GEN 派系表，按需检索即可。

## 内容在哪个文件

| 要找什么 | 文件 | 说明 |
|---|---|---|
| 单位面板、类型标签、文化归属 | `Units.json` | 类型标签在 `secondary_passives`（slug），文化在 `culture_name`/`sub_culture_name`（仅 EN 有英文原名） |
| 单位技能与被动（攻击、防御模式、Frenzy 等） | `Abilities.json` | 按 slug 或 name 查；`modifiers` 里有减益概率等结构化数据 |
| **魔典内容、单位附魔、种族转换、战斗/世界法术** | **`Spells.json`** | **附魔不在 Abilities.json！** 单位附魔、种族转换、法术全部按中文 `name` 在 ZH/Spells.json 查；Tomes.json 的 `skills[]` 列魔典内容条目 |
| 种族特性、社会特性 | `Traits.json` | **`description` 字段为空**，实际效果在 `effect_descriptions[].name` |
| 文化与理念 | `GEN/FactionCreation.json` | 仅英文，文化只有理念等极简字段 |

## 检索操作要点（Windows 环境）

1. Windows 用 `python -X utf8` 运行脚本。终端能正确显示中文时，直接读取输出。若显示乱码或结果超出工具显示上限，再将本批次输出保存为 UTF-8 文本，按名称定位需要的条目。
2. 同一批查询尽量合并。普通名称检索的 `--json` 输出会列出总命中数与实际返回数，二者不等时应继续读取剩余结果。
3. **ZH/Units.json 的 `id` 被翻译成中文**。魔典可以用 `resid` 对齐。单位的多个亚文化变体可能共用 `resid` 和英文 `id`，用 `unit_pairs.py` 对齐每个变体。
4. **slug → 名称映射**：单位类型标签等 slug（如 `0000039f000016f1`）在 EN/Abilities.json 里按 slug 查 `name`。
5. **剥 HTML 标签会丢数值**：不少数值嵌在标签内部（如 `+2点<defensefire></defensefire>火焰防护`，粗暴去标签后变成"+点火焰防护"）。涉及具体数值时**必须看原始文本**，不要只看剥标签后的结果；Tomes.json 内嵌的 skills 简介里数值尤其容易被剥光，以 Spells.json 全文为准。
6. 枚举同名单位时保留不同的 `resid`、文化和亚文化组合。使用 `analyze_build.py` 时可传 `sub` 来指定共享 `resid` 的亚文化变体，例如 `{"unit":"恶徒","sub":"卡特尔"}`。

## 工具速查

所有脚本只依赖 Python 3 标准库，以下路径相对于 `references/data/`。

- `query.py 小妖精 祈唤师 --type units --summary`：一次查询多个单位，输出紧凑卡片。
- `query.py --candidates --tag 战斗法师单位 --enchant 闪电聚焦` 按单位的实际类型标签列全候选，汇总来源、维护、攻击、勋章和指定附魔的适用情况。可重复 `--tag` 取并集，重复 `--enchant` 比较多项附魔。若已有具体单位，用 `query.py 小妖精 祈唤师 --candidates --enchant 流星灌注` 一次查询；名称与标签同时给出时两者都须匹配。按需求核对生产或召唤途径、文化、DLC 和成型时点，从完整结果中筛选。
- `query.py 流星灌注 强化注能 --type spells --json`：批量输出原始结构化字段；`--type` 可重复以合并数据集。进程内 JSON 与技能索引有缓存。
- `analyze_build.py "<文档名>.build.json" --final` 在写正文前批量核对各路线。默认在终端显示结果，加 `--json` 可读取结构化报告。
- `calc.py dmg ...` / `calc.py hit ...`：单点伤害与命中补算。
- `validate_tomes.py ...`：单路线理念校验；多路线优先使用 `analyze_build.py`。
- `build_tome_summaries.py`：重新生成 `../tome-summaries.md`；官网数据更新后需与 `build_tables.py` 一起运行。

候选卡共用技能、勋章和附魔说明。同组编号只在本批次有效。来源列给出已匹配的一种途径，维护费取自单位表。涉及多种召唤途径、地形动物池或召唤版与募役版维护费差异时，集中补查相关法术原文。

## 一份伤害记录贯穿制作和修订

1. 新 BD 确定核心单位后，在 BD 的输出目录填写原本就要交付的 `<文档名>.build.json`。先填 `unit`、`enchantments` 和区分亚文化所需的 `sub`，暂时省略 `routes`，运行 `analyze_build.py "<文档名>.build.json"` 核对单位。修订已有 BD 时直接读取原记录，保留相关路线、计算口径和备注。
2. 在同一文件补入公共派系参数，并在 `routes` 中逐条写入完整的九本 `tomes`、第 5/7/9 本的 `damage` 以及适用的 `hit_checks`。每条路线可以覆盖顶层的 `unit/enchantments/culture/sub/traits/dragon/ruler_aff/tomes`。把伤害分项来源、法术生效前提等说明留在原有的 `_notes`。
3. 正文动笔前，对这份文件运行 `analyze_build.py "<文档名>.build.json" --final`。按报错修改对应路线或共用参数，再用同一文件批量复核。用通过校验的报告填写伤害表；仅修改文字时可直接对照已有结果，改动计算输入后须重新运行。

可直接用随包的伤害记录试跑三条路线与九个节点：

```text
python -X utf8 analyze_build.py "../../examples/重商海图小妖精.build.json" --final
```

`base/flat` 使用 `物火霜电疫精`；`pct` 是加算的百分比列表；`crit` 为暴击率；`dr` 是该次攻击统一使用的防或抗；`hits` 为段数。同名单位用 `名称#ID` 或 `resid` 消除歧义。附魔条件是 OR 关系，脚本会列出实际命中的标签/等阶；缺少适用条件时返回“需人工核对”，不得当作通过。

退出码：0=全部通过，1=存在校验失败但报告完整，2=输入或数据错误。脚本的单位核对与附魔判定只替代机械查证，路线价值、基础攻击限制、单击增强数值和战斗法术取舍仍按 `../design-rules.md` 人工复核。
