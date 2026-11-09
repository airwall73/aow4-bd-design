# 官网文字资料更新流程

仅在官网日期晚于 `version.json` 且用户明确同意更新时执行。

## 来源

- 首页：`https://minionsart.github.io/aow4db/`（通过 JavaScript 动态加载页眉，首页源码可能没有日期）
- 日期：`https://minionsart.github.io/aow4db/HTML/header.html`（读取原始 HTML 中 `.current-version` 的 `Updated:`；正文提取可能漏掉该字段）
- 数据根目录：`https://minionsart.github.io/aow4db/Data/`

常用文字文件：

- `EN/Tomes.json`：魔典、技能、初始建筑
- `EN/Units.json`：单位、技能引用、维护费
- `EN/Abilities.json`：单位技能与被动正文
- `EN/Spells.json`：法术、附魔适用范围
- `EN/Traits.json`：社会与种族特性
- `EN/HeroSkills.json`：英雄职业与领袖技能
- `EN/StructureUpgrades.json`：城邦建筑与行省强化
- `EN/ItemForgeUpgrades.json`：装备灌注
- `EN/SiegeProjects.json`：攻城项目，避免把攻城限定效果当常规收益
- `GEN/FactionCreation.json`：文化、亚文化、领袖类型与理念

需要中文时可读取对应的 `ZH/` 文件，但译名仍与 FactionCreator 当前页面交叉核对。

## 更新步骤

1. 备份 `references/` 与 `examples/` 中的现有内容。
2. 读取官网 `Updated:` 日期并保存为 `official_updated` 和 `official_updated_iso`。
3. 只下载更新所需的文字JSON，不下载 `Icons/`、图片、字体或音视频。原始JSON存放在 `references/data/`（EN+ZH双语，FactionCreation仅有GEN/EN版；ZH文件的id字段被翻译成中文，Units/Tomes用resid匹配，Traits按列表顺序匹配）。
4. 下载后运行 `references/data/build_tables.py` 重新生成 `references/unit-attack-tags.md` 与 `references/dlc-pantheon.md` 两张蒸馏表，再对照新版更新以下精简资料，而不是无差别追加整份数据库：
   - 魔典阶层、理念与附魔适用范围
   - 核心单位、文化、英雄、社会与种族特性
   - 提振矩阵、功放透镜与普通英雄标志技能
   - 经济建筑和维护费
   - 新BD会实际使用的单位与技能
5. 保留用户确认的实战规则、描述bug修正和伤害公式。官网原文与这些规则冲突时，把差异列出并询问用户，不自动覆盖。
6. 重新检查现有BD的魔典门槛、附魔适用、勋章、维护费和攻城限定；只报告受影响项，用户要求时再改BD。
7. 更新 `user_rules_updated_iso` 为实际规则确认日期，更新 `official_updated*` 为官网日期。
8. 最后报告更新日期、修改了哪些资料、哪些BD可能受影响。

## 失败处理

- 下载失败时保留旧文件，不写入半份更新。
- 无法确认新版字段含义时标记“待确认”，不要猜测。
- 更新来源只使用上述官网及其明确链接的数据文件，不依赖某台电脑的镜像路径。
