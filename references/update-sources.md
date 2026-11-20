# 官网文字资料更新流程

用户直接要求刷新资料时可以执行。制作 BD 时按开场询问取得的更新选择执行。

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

1. 在临时副本中更新，保留完整可用的旧快照，直到新版核验成功。
2. 表生成器会从 `version.json` 读取版本。在**临时副本**内将 `official_updated`、`official_updated_iso` 和 `raw_data` 的版本说明设为本次官网 `Updated:` 日期。单独检查日期只刷新 `last_checked_iso` 和 `last_seen_official_iso`，分别表示本地成功检查日与最近查到的官网版本。
3. 下载 `references/data/` 中 EN、ZH 各九份 JSON 及 GEN 的 FactionCreation，确认可解析后比较内容和记录数。不要下载图标、图片、字体或音视频。ZH 文件的 id 字段可能被翻译。单位跨语言关联使用 `references/data/unit_pairs.py`，保留同一 resid 下各亚文化变体的一一对应。按位置匹配的表先核对数量和对应关系。
4. 下载后运行 `references/data/build_tables.py` 重新生成 `references/unit-attack-tags.md`、`references/dlc-pantheon.md`、`references/unit-index.md`、`references/cultures.md` 与 `references/enchant-details.md` 五张蒸馏表，并运行 `references/data/build_tome_summaries.py` 重新生成 `references/tome-summaries.md`，再对照新版更新以下精简资料，而不是无差别追加整份数据库：
   - 魔典阶层、理念与附魔适用范围
   - 核心单位、文化、英雄、社会与种族特性
   - 提振矩阵、功放透镜与普通英雄标志技能
   - 经济建筑和维护费
   - 新BD会实际使用的单位与技能
5. 保留用户确认的实战规则、描述 bug 修正和伤害公式。官网原文有冲突时记录差异和本次采用的规则，交付时一并说明。
6. 重新检查现有BD的魔典门槛、附魔适用、勋章、维护费和攻城限定；只报告受影响项，用户要求时再改BD。
7. 核对临时副本中各生成表的版本标记、内容与目标快照一致，确认查询及 BD 校验脚本可运行后，将数据、索引和版本文件作为完整快照一起替换。只有用户确认实战规则变更才改 `user_rules_updated_iso`。
8. 最后报告更新日期、修改了哪些资料、哪些BD可能受影响。

## 失败处理

- 下载或校验失败时保留旧快照和已安装版本号。制作 BD 时优先恢复更新，仍失败则披露实际使用的旧版日期并继续完成。用户明确要求只能使用最新版时，如实报告该限制对结果的影响。
- 无法确认新版字段含义时标记“待确认”，不要猜测。
- 更新来源只使用上述官网及其明确链接的数据文件，不依赖某台电脑的镜像路径。
