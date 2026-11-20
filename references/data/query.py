# 原始数据通用查询：按中文或英文名检索 Spells/Abilities/Units/Traits/Tomes。
# 直接输出原始字段（不剥 HTML 标签，数值不丢），替代手写 python -c 探查。
#
# 用法：
#   python -X utf8 query.py 淬毒之箭                    # 精确优先，否则子串搜索
#   python -X utf8 query.py 小妖精 祈唤师 --type units --summary
#   python -X utf8 query.py 淬毒之箭 流星灌注 --type spells --json
#   python -X utf8 query.py 小妖精 寒冰新星 --type units --type spells
#   python -X utf8 query.py --candidates --tag 战斗法师单位 --enchant 闪电聚焦
#   python -X utf8 query.py 小妖精 祈唤师 --candidates --enchant 流星灌注 --json
# 同一进程内的数据文件只读取一次；批量查询未找到的项会逐个报告，不中断其他查询。
import argparse, functools, json, os, re, sys
from unit_pairs import pair_units

sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.dirname(os.path.abspath(__file__))

DATASETS = {
    'spells':    ('Spells.json',    'resid'),
    'abilities': ('Abilities.json', 'slug'),
    'units':     ('Units.json',     'resid'),
    'tomes':     ('Tomes.json',     'resid'),
    'traits':    ('Traits.json',    'order'),
}

@functools.lru_cache(maxsize=None)
def load(lang, name):
    with open(os.path.join(BASE, lang, name), encoding='utf-8') as f:
        return json.load(f)

@functools.lru_cache(maxsize=None)
def pairs(name, key):
    en = load('EN', name)
    zh = load('ZH', name)
    if name == 'Units.json':
        return tuple(pair_units(en, zh))
    if key == 'order':
        return tuple(zip(en, zh))
    zmap = {z.get(key): z for z in zh}
    return tuple((e, zmap.get(e.get(key), {})) for e in en)

@functools.lru_cache(maxsize=None)
def ability_map(lang):
    return {x.get('slug'): x for x in load(lang, 'Abilities.json')}

DMG_MAP = {'damagefrost':'霜','damagefire':'火','damagelightning':'电','damageblight':'疫',
           'damagespirit':'精','damagephysical':'物'}

def strip_tags(s):
    return re.sub(r'</?[^>]+>', '', s or '').strip()

def fmt_damage(d):
    return re.sub(r'<(damage\w+)></\1>', lambda m: DMG_MAP.get(m.group(1).lower(), m.group(1)), d or '').strip()

def fmt_cost(c):
    resources = {'unitprod': '产', 'gold': '金', 'mana': '法力', 'influence': '帝权',
                 'imperium': '帝权', 'souls': '魂', 'warspoils': '战利品', 'favors': '恩惠', 'population': '人口'}
    return re.sub(r'<\s*(\w+)></\1>', lambda m: resources.get(m[1], m[1]), c or '').strip()

def unit_summary(u):
    ab = ability_map('ZH')
    tags = [strip_tags(ab.get(p.get('slug'), {}).get('name', p.get('slug'))) for p in u.get('secondary_passives', [])]
    parts = [f"{u.get('name')} | T{u.get('tier')} | {'/'.join(tags)}",
             f"{u.get('hp')}命/{u.get('armor')}防/{u.get('resistance')}抗/{u.get('status_resistance')}状抗",
             f"造价{fmt_cost(u.get('cost'))} 维护{fmt_cost(u.get('upkeep'))}"]
    source = '/'.join(x for x in (u.get('culture_name'), u.get('sub_culture_name')) if x)
    if source:
        parts.append(source)
    lines = [' | '.join(parts)]
    skills = []
    for s in u.get('abilities', []):
        abil = ab.get(s.get('slug'))
        if not abil: continue
        req = '·'.join(strip_tags(r.get('requisite')) for r in abil.get('requisites', []))
        ap = {'<repeatingaction></repeatingaction>': '重复', '<singleuseaction></singleuseaction>': '单击'}.get(abil.get('actionPoints', ''), '')
        if ap and ap in req: ap = ''
        bits = [b for b in [req, ap, f"射程{abil.get('range')}" if abil.get('range') else '',
                            fmt_damage(abil.get('damage'))] if b]
        mods = '；'.join(strip_tags(m.get('description')) for m in abil.get('modifiers', []))
        entry = f"{abil.get('name')}[{'·'.join(bits)}]" if bits else abil.get('name')
        if mods: entry += f"（{mods[:60]}）"
        skills.append(entry)
    if skills: lines.append('  技能: ' + '; '.join(skills))
    return '\n'.join(lines)

def search(query, kinds):
    q = query.casefold()
    exact, sub = [], []
    for kind in kinds:
        fname, key = DATASETS[kind]
        for e, z in pairs(fname, key):
            zn, en = (z.get('name') or ''), (e.get('name') or '')
            if not zn and not en: continue
            rec = (kind, zn, en, z if z else e)
            if zn.casefold() == q or en.casefold() == q: exact.append(rec)
            elif q in zn.casefold() or q in en.casefold(): sub.append(rec)
    return exact if exact else sub, bool(exact)

def selected_kinds(values):
    if not values or 'all' in values:
        return list(DATASETS)
    selected = set(values)
    return [kind for kind in DATASETS if kind in selected]

def effect_text(value):
    # 少数效果只用图标表示数值的单位（如“压缩”的 10 点物理伤害）。
    value = re.sub(r'</?hyperlink>', '', value or '').replace('<br></br>', ' ').replace('<bullet>', ' ')
    labels = {'damagephysical': '物理伤害', 'damagefire': '火焰伤害', 'damagefrost': '寒霜伤害',
              'damagelightning': '闪电伤害', 'damageblight': '疫病伤害', 'damagespirit': '精神伤害',
              'defense': '防御', 'resistance': '抗性', 'hp': '生命值', 'temphp': '临时生命值',
              'turn': '回合', 'crit': '暴击率', 'range': '射程', 'statuseffectresistance': '状态抗性'}

    def keep_numeric_unit(match):
        label = labels.get(match[1].lower(), match[1])
        return '' if value.startswith(label, match.end()) else label

    value = re.sub(r'(?<=\d)<(\w+)></\1>', keep_numeric_unit, value)
    return strip_tags(value)


def skill_evidence(ability):
    tags = [strip_tags(req) for req in ability['requisites']]
    if ability['repeating']:
        tags.append('重复')
    action = ability['action_points']
    if action and not ability['repeating']:
        tags.append(action.split('>')[0].lstrip('<'))
    if ability['range']:
        tags.append('射程' + str(ability['range']))
    if ability['damage']:
        tags.append(fmt_damage(ability['damage']))
    title = ability['name'] or ability['slug']
    if tags:
        title += '[' + '·'.join(tags) + ']'
    effects = [ability.get('description')] + [m.get('description') for m in ability['modifiers']]
    return ' '.join([title] + [effect_text(s) for s in effects if s])


def candidate_report(queries, tags, enchantments):
    # 常规查询轻量启动；选择候选模式时才加载与最终校验相同的原始数据及附魔规则。
    import analyze_build as build

    names = {q.casefold() for q in queries}
    wanted = {t.casefold() for t in tags}
    seen_names, seen_tags = set(), set()
    skills, rewards, medal_sets, spells, cards = {}, {}, {}, {}, []
    spell_ids = []
    for selector in enchantments:
        spell = build.find_spell(selector)
        if 'Unit Enchantment' not in strip_tags(spell.get('spellType')):
            raise ValueError(f'{selector} 并非单位附魔，请核对法术类型')
        if spell['resid'] not in spell_ids:
            spell_ids.append(spell['resid'])

    for unit in build.units_en:
        zh = build.units_zh[id(unit)]
        labels = {s.casefold() for s in (unit.get('name'), zh.get('name')) if s and s.strip()}
        if not labels:
            continue
        slugs = [p['slug'] for p in unit.get('secondary_passives', [])]
        unit_tags = {strip_tags(db.get(slug, {}).get('name')).casefold()
                     for db in (build.abilities_zh, build.abilities_en) for slug in slugs}
        if 'deprecated unit!' in unit_tags:
            continue
        seen_tags.update(unit_tags & wanted)
        if wanted and not unit_tags.intersection(wanted):
            continue
        if names and not labels.intersection(names):
            continue
        seen_names.update(labels & names)
        audit = build.audit_unit(unit['resid'], spell_ids, unit.get('sub_culture_name'))
        card = {k: audit[k] for k in ('name', 'name_en', 'resid', 'id', 'tier', 'source', 'stats', 'tags')}
        card.update(cost=fmt_cost(audit['cost']), upkeep=fmt_cost(audit['upkeep']),
                    dlc=(unit.get('DLC') or '').strip())
        card['passives'] = [a['name'] or a['slug'] for a in audit['primary_passives']]
        card['skills'] = []
        for ability in audit['abilities']:
            detail = skill_evidence(ability)
            card['skills'].append(skills.setdefault(detail, len(skills) + 1))

        # 相同的各级勋章在整批中只说明一次。保留资源图标，避免把 +1 防与 +1 抗混为一项。
        progression = []
        for key, medals in sorted(audit['medals'].items()):
            rank_rewards = []
            for medal in medals:
                detail = (medal['name'] or medal['slug'], medal['description'] or '')
                rank_rewards.append(rewards.setdefault(detail, len(rewards) + 1))
            progression.append((key.split('_')[-1], tuple(rank_rewards)))
        card['medals'] = medal_sets.setdefault(tuple(progression), len(medal_sets) + 1)
        matches = {}
        for enchant in audit['enchantments']:
            spell_id = str(enchant['resid'])
            spells.setdefault(spell_id, {k: enchant[k] for k in ('name', 'description', 'requisites')})
            matches[spell_id] = enchant['matched_requisites'] if enchant['eligible'] is not None else None
        card['enchantments'] = matches
        cards.append(card)
    return {'total': len(cards), 'units': cards, 'skills': {v: k for k, v in skills.items()},
            'medals': {v: dict(k) for k, v in medal_sets.items()},
            'rewards': {v: {'name': k[0], 'description': k[1]} for k, v in rewards.items()}, 'enchantments': spells,
            'unmatched_names': [q for q in queries if q.casefold() not in seen_names],
            'unmatched_tags': [t for t in tags if t.casefold() not in seen_tags]}


def print_candidates(report):
    print(f"候选 {report['total']} 个 | 面板：生命/防/抗/状态抗")
    for u in report['units']:
        panel = '/'.join(str(u['stats'][k]) for k in ('hp', 'armor', 'resistance', 'status_resistance'))
        fields = [f"{u['name']}（{u['id']}，{u['resid']}）T{u['tier']}", u['source'], '/'.join(u['tags']),
                  panel, f"造价 {u['cost'] or '—'} 维护 {u['upkeep'] or '—'}", u['dlc'] or '本体',
                  '被动 ' + '/'.join(u['passives']), '技能 ' + ','.join(map(str, u['skills'])), f"勋章组 {u['medals']}"]
        for spell_id, matches in u['enchantments'].items():
            result = '待核对' if matches is None else '/'.join(matches) or '不适用'
            fields.append(f"{report['enchantments'][spell_id]['name']} {result}")
        print(' | '.join(fields))
    for i, detail in report['skills'].items():
        print(f'技能 {i} {detail}')
    for i, levels in report['medals'].items():
        levels_text = [f"{rank}级 " + ','.join(map(str, rewards)) for rank, rewards in levels.items()]
        print(f"勋章组 {i} " + ' / '.join(levels_text))
    for i, reward in report['rewards'].items():
        print(f"勋章奖励 {i} {reward['name']} {strip_tags(reward['description'])}")
    for spell in report['enchantments'].values():
        print(f"{spell['name']} | {'/'.join(spell['requisites']) or '条件待核对'} | {spell['description']}")
    if report['unmatched_names'] or report['unmatched_tags']:
        print('未匹配：' + '、'.join(report['unmatched_names'] + report['unmatched_tags']))


def main(argv=None):
    ap = argparse.ArgumentParser(description='AoW4 原始数据批量查询')
    ap.add_argument('queries', nargs='*', help='中文或英文名称；候选模式使用精确匹配')
    ap.add_argument('--candidates', action='store_true', help='按单位名或标签一次枚举全部候选并比较攻击、勋章与附魔')
    ap.add_argument('--tag', action='append', default=[], help='候选单位的精确中英文类型标签；可重复，取并集')
    ap.add_argument('--enchant', action='append', default=[], help='候选比较中核对的单位附魔，可重复')
    ap.add_argument('--type', action='append', choices=list(DATASETS) + ['all'],
                    help='数据集；可重复使用以合并多个数据集，默认 all')
    ap.add_argument('--max', type=int, default=8, help='每个查询最多返回的结果数（默认8）')
    ap.add_argument('--chars', type=int, default=2500, help='文本模式每条原始结果的最大字符数')
    ap.add_argument('--summary', action='store_true', help='单位输出紧凑卡片，代替原始JSON')
    ap.add_argument('--json', action='store_true', help='输出批量结构化JSON；原始条目不按 --chars 截断')
    a = ap.parse_args(argv)
    if a.max < 1 or a.chars < 1:
        ap.error('--max 和 --chars 必须为正数')
    if a.candidates:
        if not (a.queries or a.tag):
            ap.error('--candidates 需要单位名称或 --tag')
        if a.type or a.summary:
            ap.error('--candidates 已指定查询单位，使用 --tag、--enchant 或 --json')
        try:
            report = candidate_report(a.queries, a.tag, a.enchant)
        except ValueError as exc:
            ap.error(str(exc))
        if a.json:
            print(json.dumps(report, ensure_ascii=False))
        else:
            print_candidates(report)
        return int(not report['total'] or bool(report['unmatched_names'] or report['unmatched_tags']))
    if a.tag or a.enchant or not a.queries:
        ap.error('请提供查询名称；按单位标签或拟用附魔比较时需使用 --candidates')
    kinds = selected_kinds(a.type)
    reports = []
    missing = 0
    for query in a.queries:
        hits, exact = search(query, kinds)
        if not hits:
            missing += 1
        results = []
        for kind, zn, en, entry in hits[:a.max]:
            item = {'type': kind, 'name_zh': zn, 'name_en': en}
            if a.summary and kind == 'units':
                item['summary'] = unit_summary(entry)
            else:
                item['data'] = entry
            results.append(item)
        reports.append({'query': query, 'exact': exact, 'total_matches': len(hits),
                        'returned': len(results), 'not_found': not hits, 'results': results})

    if a.json:
        print(json.dumps(reports, ensure_ascii=False, indent=2))
    else:
        for report in reports:
            if len(a.queries) > 1:
                print(f'##### 查询：{report["query"]} #####')
            if report['not_found']:
                print(f'未找到：{report["query"]}')
                continue
            if not report['exact'] and report['total_matches'] > report['returned']:
                print(f'（子串匹配 {report["total_matches"]} 条，只显示前 {report["returned"]} 条；用更精确的名称或 --max 调整）')
            for item in report['results']:
                print(f'===== [{item["type"]}] {item["name_zh"]} / {item["name_en"]} =====')
                if 'summary' in item:
                    print(item['summary'])
                else:
                    s = json.dumps(item['data'], ensure_ascii=False, indent=1)
                    print(s[:a.chars] + ('\n…（截断，用 --chars 加大）' if len(s) > a.chars else ''))
    return 1 if missing else 0

if __name__ == '__main__':
    sys.exit(main())
