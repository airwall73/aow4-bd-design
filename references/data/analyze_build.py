"""批量执行核心单位二次核对、附魔适用性、魔典序列、伤害与减益命中校验。

输入为 UTF-8 JSON。顶层公共字段可被每条 route 覆盖；仅做单位二次核对时省略 routes：
{
  "unit": "小妖精",
  "enchantments": ["流星灌注", "强化注能"],
  "culture": "重商",
  "sub": "男爵领地",
  "traits": ["海洋之子", "命运幻象·秩序"],
  "dragon": "物质",
  "routes": [{
    "name": "无T5熔炉线",
    "tomes": ["祈唤", "部落", "混乱", "匠造", "变化", "预言", "庇护", "熔炉", "强化"],
    "damage": [{"node": 9, "base": "20火", "flat": "8火 4电 6电",
                "pct": [20, 10, 50], "crit": 55, "dr": 5, "hits": 1}],
    "hit_checks": [{"label": "瓦解抗性", "prob": 60, "res": 5}]
  }]
}

用法：
  python -X utf8 analyze_build.py "文档名.build.json"
  python -X utf8 analyze_build.py "文档名.build.json" --final
  加 --json 可在标准输出读取结构化报告。--final 用于写正文前校验完整路线。
存在校验失败时仍输出完整报告，并以状态码1退出。
"""
import argparse, json, os, re, sys

import calc
import validate_tomes as vt

sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.dirname(os.path.abspath(__file__))

units_en = vt.un_en
units_zh = vt.un_zh
spells_en = vt.load('EN', 'Spells.json')
spells_zh = {s['resid']: s for s in vt.load('ZH', 'Spells.json')}
abilities_en = {a['slug']: a for a in vt.load('EN', 'Abilities.json')}
abilities_zh = {a['slug']: a for a in vt.load('ZH', 'Abilities.json')}

tome_of_unit, tome_of_spell = {}, {}
for tome in vt.tomes_en:
    for skill in tome.get('skills', []):
        if skill.get('unit_slug'): tome_of_unit.setdefault(skill['unit_slug'], tome)
        if skill.get('spell_slug'): tome_of_spell.setdefault(skill['spell_slug'], tome)
summon_of_unit = {}
for spell in spells_en:
    for summoned in spell.get('summoned_units') or []:
        summon_of_unit.setdefault(summoned.get('slug'), spell)


def strip_tags(value):
    return re.sub(r'</?[^>]+>', '', value or '').strip()


def exact_one(entries, selector, label, translated, sub=''):
    selector = str(selector)
    if '#' in selector:
        name, uid = selector.rsplit('#', 1)
        matches = [e for e in entries if str(e.get('id')) == uid and
                   name in {e.get('name'), translated(e).get('name')}]
    else:
        matches = [e for e in entries if selector in {str(e.get('id', '')), str(e.get('resid', ''))}]
    if not matches:
        matches = [e for e in entries if selector in {e.get('name'), translated(e).get('name')}]
    if not matches:
        raise ValueError(f'{label}未找到：{selector}')
    if len(matches) > 1 and sub:
        scoped = [e for e in matches if sub in (e.get('sub_culture_name'), translated(e).get('sub_culture_name'))]
        if scoped:
            matches = scoped
    if len(matches) > 1:
        if any(e.get('sub_culture_name') for e in matches):
            variants = '、'.join(f"{e['resid']} / {translated(e).get('sub_culture_name') or e.get('sub_culture_name') or e['id']}" for e in matches)
            raise ValueError(f'{label}存在同名变体，可在 sub 指定亚文化，或使用唯一的 resid：{variants}')
        choices = '、'.join(f'{translated(e).get("name") or e.get("name")}#{e.get("id")}' for e in matches)
        raise ValueError(f'{label}存在同名条目，请用 名称#ID 或 resid 指定：{choices}')
    return matches[0]


def find_unit(selector, sub=''):
    return exact_one(units_en, selector, '单位', lambda u: units_zh[id(u)], sub)


def find_spell(selector):
    return exact_one(spells_en, selector, '法术/附魔', lambda s: spells_zh.get(s.get('resid'), {}))


def tome_name(tome):
    translated = vt.tomes_zh.get(tome['resid'], {})
    return f'{translated.get("name") or tome.get("name")}(T{tome.get("tier")})'


def unit_source(unit, zh):
    uid = unit['id']
    if unit.get('culture_name'):
        culture = zh.get('culture_name') or unit.get('culture_name')
        sub = zh.get('sub_culture_name') or unit.get('sub_culture_name') or ''
        return '文化:' + culture + (f'-{sub}' if sub else '')
    if uid in tome_of_unit: return '魔典:' + tome_name(tome_of_unit[uid])
    if uid in summon_of_unit:
        spell = summon_of_unit[uid]
        translated = spells_zh.get(spell.get('resid'), {})
        source = '召唤:' + (translated.get('name') or spell.get('name'))
        tome = tome_of_spell.get(spell.get('id'))
        return source + (f'（{tome_name(tome)}）' if tome else '')
    return '其他'


def ability_details(slug):
    en = abilities_en.get(slug, {})
    zh = abilities_zh.get(slug, en)
    requisites = [strip_tags(r.get('requisite', '')) for r in en.get('requisites', [])]
    return {
        'slug': slug,
        'name': zh.get('name') or en.get('name'),
        'name_en': en.get('name'),
        'requisites': [r.get('requisite', '') for r in zh.get('requisites', en.get('requisites', []))],
        'base_attack': 'Base' in requisites,
        'single_shot': 'Single Shot' in requisites,
        'repeating': 'repeatingaction' in (en.get('actionPoints') or ''),
        'action_points': zh.get('actionPoints') or en.get('actionPoints'),
        'range': zh.get('range') or en.get('range'),
        'damage': zh.get('damage') or en.get('damage'),
        'description': zh.get('description') or en.get('description'),
        'modifiers': zh.get('modifiers') or en.get('modifiers') or []
    }


def audit_unit(selector, enchantment_selectors, sub=''):
    unit = find_unit(selector, sub)
    zh = units_zh[id(unit)]
    tags = [abilities_zh.get(p.get('slug'), {}).get('name') or
            abilities_en.get(p.get('slug'), {}).get('name') or p.get('slug')
            for p in unit.get('secondary_passives', [])]
    normalized_tags = {strip_tags(tag).replace(' ', '') for tag in tags}
    aliases = {'地狱恶魔': '恶魔', '进化': '进化单位'}
    normalized_tags.update(aliases.get(tag) for tag in list(normalized_tags) if tag in aliases)
    enchantments = []
    for selector in enchantment_selectors:
        spell = find_spell(selector)
        z = spells_zh.get(spell.get('resid'), {})
        raw_reqs = z.get('enchantment_requisites') or spell.get('enchantment_requisites') or []
        reqs = [strip_tags(r.get('requisite')).replace(' ', '') for r in raw_reqs]
        matched = []
        for req in reqs:
            tier_match = re.fullmatch(r'(I|II|III|IV|V)阶', req)
            if tier_match:
                if {'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5}[tier_match.group(1)] == unit.get('tier'):
                    matched.append(req)
            elif req in normalized_tags or (req == '已进化的单位' and '进化' in normalized_tags):
                matched.append(req)
        eligible = bool(matched) if reqs else None
        enchantments.append({
            'name': z.get('name') or spell.get('name'),
            'name_en': spell.get('name'), 'id': spell.get('id'), 'resid': spell.get('resid'),
            'spell_type': z.get('spellType') or spell.get('spellType'),
            'description': z.get('description') or spell.get('description'),
            'requisites': reqs, 'matched_requisites': matched, 'eligible': eligible
        })
    medals = {}
    for key, rewards in unit.items():
        if not key.startswith('medal_rewards_'): continue
        medals[key] = [{'slug': reward.get('slug'),
                        **{k: v for k, v in ability_details(reward.get('slug')).items()
                           if k in {'name', 'name_en', 'description'}}} for reward in rewards]
    return {
        'name': zh.get('name') or unit.get('name'), 'name_en': unit.get('name'),
        'id': unit.get('id'), 'resid': unit.get('resid'), 'tier': unit.get('tier'),
        'source': unit_source(unit, zh), 'cost': zh.get('cost') or unit.get('cost'),
        'upkeep': zh.get('upkeep') or unit.get('upkeep'),
        'stats': {k: zh.get(k, unit.get(k)) for k in ['hp', 'armor', 'resistance', 'status_resistance']},
        'tags': tags,
        'primary_passives': [ability_details(p.get('slug')) for p in unit.get('primary_passives', [])],
        'abilities': [ability_details(a.get('slug')) for a in unit.get('abilities', [])],
        'medals': medals, 'enchantments': enchantments,
        'ok': all(e['eligible'] is True for e in enchantments)
    }


def merged_route(defaults, route):
    return {key: route.get(key, defaults.get(key)) for key in [
        'unit', 'enchantments', 'culture', 'sub', 'traits', 'dragon', 'ruler_aff', 'tomes']}


def final_route_errors(report):
    errors = []
    if 'tome_validation' in report:
        names = [step['name'] for step in report['tome_validation']['steps']]
        if len(names) != 9:
            errors.append(f'完整路线需要 9 本魔典，当前有 {len(names)} 本')
        if len(set(names)) != len(names):
            errors.append('魔典序列中有重复魔典')

    nodes = {str(damage['node']) for damage in report['damage']}
    missing = [node for node in ('5', '7', '9') if node not in nodes]
    if missing:
        errors.append(f'缺少第 {"/".join(missing)} 本魔典的伤害计算')
    for damage in report['damage']:
        label = damage['label'] or f"{damage['node']} 本"
        if not calc.parse_channels(damage['input'].get('base')):
            errors.append(f'{label} 缺少可识别的基础伤害')
        for warning in damage['result']['warnings']:
            errors.append(f'{label} 伤害计算：{warning}')
    return errors


def analyze(request, final=False):
    if not isinstance(request, dict):
        raise ValueError('输入必须是 JSON 对象')
    defaults = {key: request.get(key) for key in [
        'unit', 'enchantments', 'culture', 'sub', 'traits', 'dragon', 'ruler_aff', 'tomes']}
    routes = request.get('routes')
    if routes is None and defaults['unit'] and not final:
        audit = audit_unit(defaults['unit'], defaults.get('enchantments') or [], defaults.get('sub'))
        return {'unit_audits': [audit], 'routes': [], 'ok': audit['ok']}
    if not isinstance(routes, list) or not routes:
        if final:
            raise ValueError('写正文前需要在同一份 .build.json 的 routes 中补齐候选路线')
        raise ValueError('输入必须包含非空 routes 数组；仅做单位二次核对时可省略 routes')
    errors = []
    if final and not request.get('_notes'):
        errors.append('缺少顶层 _notes，请记录伤害分项来源')
    audit_cache, audits, reports = {}, [], []
    for index, route in enumerate(routes, 1):
        if not isinstance(route, dict):
            raise ValueError(f'routes 第 {index} 项必须是 JSON 对象')
        cfg = merged_route(defaults, route)
        report = {'name': route.get('name') or f'路线{index}', 'ok': True, 'errors': []}
        try:
            if final and not cfg['culture']:
                raise ValueError('缺少文化 culture')
            validation = vt.validate_route(cfg['culture'], cfg['tomes'], cfg.get('sub') or '',
                                           cfg.get('traits'), cfg.get('dragon') or '', cfg.get('ruler_aff'))
            report['tome_validation'] = validation
            report['ok'] = report['ok'] and validation['ok']
        except (ValueError, TypeError, KeyError) as exc:
            report['errors'].append(f'魔典校验：{exc}')
            report['ok'] = False
        try:
            if final and not cfg['unit']:
                raise ValueError('缺少核心兵种 unit')
            enchantments = cfg.get('enchantments') or []
            key = (cfg['unit'], cfg.get('sub'), tuple(enchantments))
            if key not in audit_cache:
                audit = audit_unit(cfg['unit'], enchantments, cfg.get('sub'))
                audit_cache[key] = len(audits)
                audits.append(audit)
            report['unit_audit_index'] = audit_cache[key]
            report['ok'] = report['ok'] and audits[audit_cache[key]]['ok']
        except (ValueError, TypeError, KeyError) as exc:
            report['errors'].append(f'单位/附魔核对：{exc}')
            report['ok'] = False
        damage_reports = []
        for damage in route.get('damage') or []:
            if not isinstance(damage, dict):
                report['errors'].append('damage 条目必须是包含伤害输入的对象')
                report['ok'] = False
                continue
            try:
                result = calc.damage_result(damage.get('base', ''), damage.get('flat', ''),
                                            damage.get('pct'), damage.get('crit', 0),
                                            damage.get('dr', 5), int(damage.get('hits', 1)))
                damage_reports.append({'node': damage.get('node'), 'label': damage.get('label'),
                                       'input': damage, 'result': result})
            except (ValueError, TypeError) as exc:
                report['errors'].append(f'伤害计算 {damage.get("node") or damage.get("label") or "?"}：{exc}')
                report['ok'] = False
        report['damage'] = damage_reports
        hit_reports = []
        for check in route.get('hit_checks') or []:
            if not isinstance(check, dict):
                report['errors'].append('hit_checks 条目必须是含 prob 与 res 的对象')
                report['ok'] = False
                continue
            try:
                hit_reports.append({'label': check.get('label'),
                                    'result': calc.hit_result(float(check['prob']), float(check['res']))})
            except (ValueError, TypeError, KeyError) as exc:
                report['errors'].append(f'命中计算 {check.get("label") or "?"}：{exc}')
                report['ok'] = False
        report['hit_checks'] = hit_reports
        if final:
            report['errors'].extend(final_route_errors(report))
            report['ok'] = report['ok'] and not report['errors']
        reports.append(report)
    result = {'unit_audits': audits, 'routes': reports,
              'ok': not errors and all(a['ok'] for a in audits) and all(r['ok'] for r in reports)}
    if errors:
        result['errors'] = errors
    return result


def format_report(report):
    lines = [f'ERROR {error}' for error in report.get('errors', [])]
    for audit in report['unit_audits']:
        stats = audit['stats']
        lines += [f'## 核心单位二次核对：{audit["name"]} / {audit["name_en"]}',
                  f'ID={audit["id"]} | T{audit["tier"]} | {audit["source"]}',
                  '标签：' + '/'.join(audit['tags']),
                  f'面板：{stats["hp"]}命/{stats["armor"]}防/{stats["resistance"]}抗/{stats["status_resistance"]}状抗',
                  f'造价：{audit["cost"]} | 维护：{audit["upkeep"]}']
        for passive in audit['primary_passives']:
            lines.append(f'被动：{passive["name"]} | {passive["description"] or ""}')
        for ability in audit['abilities']:
            flags = [name for name, enabled in [('基础', ability['base_attack']),
                     ('单击', ability['single_shot']), ('重复', ability['repeating'])] if enabled]
            lines.append(f'技能：{ability["name"]} | {"/".join(flags) or "非基础/独立"} | '
                         f'射程{ability["range"] or "—"} | {ability["damage"] or "—"} | {ability["description"] or ""}')
        for medal_level, medals in sorted(audit['medals'].items()):
            lines.append(f'{medal_level}：' + '；'.join(f'{m["name"]}={m["description"]}' for m in medals))
        for enchant in audit['enchantments']:
            verdict = 'OK' if enchant['eligible'] else ('需人工核对' if enchant['eligible'] is None else 'FAIL')
            lines.append(f'{verdict} 附魔：{enchant["name"]} | 适用={"/".join(enchant["requisites"]) or "缺失"} | '
                         f'命中={"/".join(enchant["matched_requisites"]) or "无"} | {enchant["description"]}')
        lines.append('')
    for route in report['routes']:
        lines.append(f'## 路线：{route["name"]} | {"OK" if route["ok"] else "FAIL"}')
        lines.extend(f'ERROR {error}' for error in route['errors'])
        if 'tome_validation' in route:
            lines.append(vt.format_report(route['tome_validation']))
        for damage in route['damage']:
            result = damage['result']
            label = damage['label'] or f'{damage["node"]}本'
            normal = f'{label}：普通={result["normal_total"]}'
            if result['expected'] is not None:
                normal += f' | 暴击={result["critical_total"]} | 期望={result["expected"]:.1f}'
            lines.append(normal)
            lines.extend(f'WARNING {warning}' for warning in result['warnings'])
        for check in route['hit_checks']:
            result = check['result']
            lines.append(f'{check["label"] or "减益"}：{result["probability"]}% 对状态抗{result["status_resistance"]} '
                         f'→ {result["hit_percent"]:.1f}%')
        lines.append('')
    lines.append('总校验结果：' + ('全部通过' if report['ok'] else '存在失败项，见上方 FAIL/ERROR'))
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description='AoW4 批量构建核对与伤害计算')
    parser.add_argument('input', help='UTF-8 JSON 请求文件')
    parser.add_argument('--json', action='store_true', help='输出结构化JSON而非紧凑文本')
    parser.add_argument('--final', action='store_true', help='写正文前检查完整九本路线和 5/7/9 伤害节点')
    parser.add_argument('--output', help='写入UTF-8文件；默认输出到stdout')
    args = parser.parse_args(argv)
    try:
        with open(args.input, encoding='utf-8') as f:
            request = json.load(f)
        if args.output and os.path.exists(args.output) and os.path.samefile(args.input, args.output):
            raise ValueError('报告输出与 .build.json 输入指向同一文件，请直接读取标准输出')
        report = analyze(request, final=args.final)
        text = json.dumps(report, ensure_ascii=False, indent=2) if args.json else format_report(report)
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(text + '\n')
            print(f'已写入 {args.output}')
        else:
            print(text)
        return 0 if report['ok'] else 1
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(f'错误：{exc}', file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(main())
