# 魔典序列理念与阶层校验：按 design-rules.md 的规则逐本检查入场门槛。
# 规则：T2=已有2本；T3=已有4本+理念3；T4=已有6本+理念6；T5=已有8本+理念8；
# 双理念魔典按两系之和；入场判定不计入正在选择的魔典；全场限1本T5；
# 宇宙魔典：六系全>=2 或 至少三系>=6。
# 理念来源：文化/亚文化（FactionCreation图标数）、社会特性（Traits结构化字段）、
# 巨龙亚型（+1所选系）；普通领袖起源不提供理念（已用既有BD反推校验）。
#
# 用法（在 references/data 下运行，Windows 必须 -X utf8）：
#   python -X utf8 validate_tomes.py --culture 建筑师 --sub 星辰建筑师 \
#       --traits 强大祈唤师,命运幻象·物质 \
#       --tomes 祈唤,护法,道标,燃烧热情,强化,占测,毁灭,混沌引导,星汇
#   python -X utf8 validate_tomes.py --culture 原初 --sub 隧行蜘蛛 --dragon 混沌 \
#       --traits 个人崇拜,部落 --tomes ...
# 名称中英文均可；魔典名可省略"魔典"二字。
import json, os, re, sys, argparse, collections
from unit_pairs import pair_units

sys.stdout.reconfigure(encoding='utf-8')
BASE = os.path.dirname(os.path.abspath(__file__))

def load(lang, name):
    with open(os.path.join(BASE, lang, name), encoding='utf-8') as f:
        return json.load(f)

AFF_TOKEN = {'empirenature':'自然','empirematter':'物质','empireorder':'秩序','empirechaos':'混沌',
             'empireshadow':'暗影','empirearcana':'星辰','arcana':'星辰','empireastral':'星辰',
             'nature':'自然','matter':'物质','order':'秩序','chaos':'混沌','shadow':'暗影','astral':'星辰'}
ELEMENTS = ['自然','物质','秩序','混沌','暗影','星辰']

def icons_aff(s):
    return collections.Counter(AFF_TOKEN.get(k, k) for k in re.findall(r'<(empire\w+|arcana)></\1>', s or ''))

tomes_en = load('EN','Tomes.json'); tomes_zh = {t['resid']: t for t in load('ZH','Tomes.json')}
tr_en = load('EN','Traits.json'); tr_zh = load('ZH','Traits.json')
fc = load('GEN','FactionCreation.json')
un_en = load('EN','Units.json')
un_zh = {id(u): z for u, z in pair_units(un_en, load('ZH', 'Units.json'))}

def tome_aff(t):
    return collections.Counter(
        {AFF_TOKEN[m.group(2)]: int(m.group(1))
         for m in re.finditer(r'(\d+)\s*<(empire\w+|arcana)></\2>', t.get('affinities') or '')})

# ---- 名称索引 ----
def norm(s):
    return re.sub(r'[\s\-—_·]', '', (s or '').lower().replace('魔典', ''))

tome_idx = {}
for t in tomes_en:
    if (t.get('tier') or 0) == 0: continue
    z = tomes_zh.get(t['resid'], {})
    for n in {t.get('name'), z.get('name')}:
        if n: tome_idx[norm(n)] = t

CUL_ALIASES = {'神奥调谐':'秘术', '神奥':'秘术'}
ARCH_EL = {'星辰':'Astral','暗影':'Shadow','混沌':'Chaos','物质':'Materium','自然':'Nature','秩序':'Order'}

fc_culs = {e['name']: e for e in fc if e.get('type') == 'Culture'}
fc_subs = [e for e in fc if e.get('type') == 'SubCulture']
t0 = [t for t in tomes_en if (t.get('tier') or 0) == 0]

# 文化中文名：文化T0魔典名 > 亚文化T0魔典名前缀 > 单位文化字段
cul_zh = {}
for t in t0:
    tn, zn = t.get('name') or '', (tomes_zh.get(t['resid'], {}).get('name') or '')
    if ' - ' in tn and ' - ' in zn:
        cul_zh.setdefault(tn.split(' - ')[0], zn.split(' - ')[0])
    elif tn in fc_culs and zn:
        cul_zh.setdefault(tn, zn)
for u in un_en:
    if u.get('culture_name'):
        z = un_zh[id(u)]
        if z.get('culture_name'): cul_zh.setdefault(u['culture_name'], z['culture_name'])

def find_culture(name):
    n = CUL_ALIASES.get(name, name)
    for en, e in fc_culs.items():
        if n in (en, cul_zh.get(en)): return e
    return None

def find_sub(name, cul_name):
    n = CUL_ALIASES.get(name, name)
    m = re.fullmatch(r'(星辰|暗影|混沌|物质|自然|秩序)建筑师', n)
    if m: n = f'Architects of {ARCH_EL[m.group(1)]}'
    cands = [s for s in fc_subs if not cul_name or (s.get('requirement') or '') == cul_name]
    for s in cands:
        sname = s.get('name') or ''
        t = next((x for x in t0 if x.get('name') == sname or
                  (x.get('name') or '').startswith((s.get('requirement') or '') + ' - ') and
                  ((x.get('name') or '').endswith(sname.split(' - ')[-1]) or sname.endswith((x.get('name') or '').split(' - ')[-1]))), None)
        zt = tomes_zh.get(t['resid'], {}).get('name') if t else ''
        names = {sname, sname.split(' - ')[-1]}
        if zt: names |= {zt, zt.split(' - ')[-1]}
        if n in names: return s
    return None

def find_trait(name):
    # 自选系特性（如 命运幻象·物质）：基础名 + 系别后缀
    parts = re.split(r'[·:：]', name, maxsplit=1)
    base, suffix = parts[0].strip(), (parts[1].strip() if len(parts) > 1 else '')
    for e, z in zip(tr_en, tr_zh):
        if e.get('type') != 'society': continue
        if base in (e.get('name'), z.get('name')): return e, z, suffix
    near = [z.get('name') or e.get('name') for e, z in zip(tr_en, tr_zh)
            if e.get('type') == 'society' and (base in (e.get('name') or '') or base in (z.get('name') or ''))]
    raise ValueError(f'社会特性未找到：{name}' + (f'，相近：{near}' if near else ''))

def trait_aff(e):
    out = collections.Counter()
    for a in e.get('affinities') or []:
        for m in re.finditer(r'(\d+)\s*<(\w+)></\2>', a.get('name') or ''):
            if m.group(2) in AFF_TOKEN:
                out[AFF_TOKEN[m.group(2)]] += int(m.group(1))
    return out

TIER_REQ = {2: (2, 0), 3: (4, 3), 4: (6, 6), 5: (8, 8)}

def as_list(value):
    if value is None: return []
    if isinstance(value, str): return [x.strip() for x in value.split(',') if x.strip()]
    return list(value)

def format_pool(pool):
    return ' '.join(f'{e}{pool[e]}' for e in ELEMENTS if pool[e])

def validate_route(culture, tomes, sub='', traits=None, dragon='', ruler_aff=None):
    """校验一条路线并返回结构化结果，供 CLI 与批量分析脚本共用。"""
    pool = collections.Counter()
    src_lines = []
    cul = find_culture(culture)
    if not cul: raise ValueError(f'文化未找到：{culture}（可用：' + '、'.join(sorted(set(cul_zh.values()))) + '）')
    ca = icons_aff(cul.get('affinity')); pool += ca
    src_lines.append(f"文化 {cul_zh.get(cul['name'], cul['name'])}：{dict(ca) or '无'}")
    if sub:
        sub_entry = find_sub(sub, cul['name'])
        if not sub_entry: raise ValueError(f'亚文化未找到：{sub}')
        sa = icons_aff(sub_entry.get('affinity')); pool += sa
        src_lines.append(f"亚文化 {sub_entry.get('name')}：{dict(sa) or '无'}")
    for tn in as_list(traits):
        e, z, suffix = find_trait(tn)
        ta = trait_aff(e)
        tname = z.get('name') or e.get('name')
        if not ta:
            if suffix and suffix in ELEMENTS:
                ta[suffix] += 2
                tname += f'·{suffix}'
            else:
                raise ValueError(f'社会特性 {tname} 无固定理念，请以"特性名·系别"指定（如 命运幻象·物质）')
        pool += ta
        src_lines.append(f"社会特性 {tname}：{dict(ta)}")
    if dragon:
        pool[dragon] += 1
        src_lines.append(f'巨龙亚型：{dragon}1')
    ruler_parts = [f'{el}:{n}' for el, n in ruler_aff.items()] if isinstance(ruler_aff, dict) else as_list(ruler_aff)
    for part in ruler_parts:
        el, n = str(part).split(':')
        pool[el.strip()] += int(n)
        src_lines.append(f'领袖额外：{part}')

    seq = []
    for name in as_list(tomes):
        t = tome_idx.get(norm(name))
        if not t: raise ValueError(f'魔典未找到：{name}')
        seq.append(t)
    if not seq: raise ValueError('魔典序列不能为空')

    initial_pool = format_pool(pool)
    ok_all, n_t5 = True, 0
    steps = []
    for i, t in enumerate(seq):
        z = tomes_zh.get(t['resid'], {})
        zname = z.get('name') or t.get('name')
        tier = t.get('tier') or 0
        aff = tome_aff(t)
        errs = []
        need_books, need_aff = TIER_REQ.get(tier, (0, 0))
        if i < need_books:
            errs.append(f'已有{i}本<T{tier}要求{need_books}本（提示：移至第{need_books+1}位或之后即可满足阶层要求）')
        is_cosmic = '宇宙' in (zname or '') or 'cosmos' in (t.get('name') or '').lower()
        if is_cosmic:
            ge2 = sum(1 for e in ELEMENTS if pool[e] >= 2)
            ge6 = sum(1 for e in ELEMENTS if pool[e] >= 6)
            if not (ge2 >= 6 or ge6 >= 3):
                errs.append(f'宇宙入场需六系全>=2或三系>=6（当前>=2的有{ge2}系，>=6的有{ge6}系）')
        elif need_aff:
            have = sum(pool[e] for e in aff)
            if have < need_aff:
                errs.append(f'理念不足：{"/".join(aff)}合计{have}<T{tier}要求{need_aff}（提示：还差{need_aff-have}点，可由社会特性·系别、巨龙亚型或调整前置魔典补齐）')
        if tier == 5:
            n_t5 += 1
            if n_t5 > 1: errs.append('全场只能选1本T5')
        if errs: ok_all = False
        steps.append({'index': i + 1, 'name': zname, 'tier': tier,
                      'pool_before': format_pool(pool), 'errors': errs})
        pool += aff
    return {'sources': src_lines, 'initial_pool': initial_pool, 'steps': steps,
            'final_pool': format_pool(pool), 'ok': ok_all}

def format_report(result):
    lines = ['理念来源：' + '；'.join(result['sources']), f'开局理念池：{result["initial_pool"]}', '']
    for step in result['steps']:
        mark = 'FAIL' if step['errors'] else 'OK '
        line = f'{mark} 第{step["index"]}本 {step["name"]}(T{step["tier"]}) | 入场前理念池：{step["pool_before"]}'
        if step['errors']: line += ' | ' + '；'.join(step['errors'])
        lines.append(line)
    lines += ['', f'最终理念池：{result["final_pool"]}', '校验结果：' + ('全部通过' if result['ok'] else '存在不通过的魔典')]
    return '\n'.join(lines)

def main(argv=None):
    ap = argparse.ArgumentParser(description='魔典序列理念/阶层校验')
    ap.add_argument('--culture', required=True)
    ap.add_argument('--sub', default='')
    ap.add_argument('--traits', default='', help='两个社会特性，逗号分隔')
    ap.add_argument('--dragon', default='', help='巨龙领袖亚型理念（如 混沌），普通领袖留空')
    ap.add_argument('--ruler-aff', default='', help='额外的领袖理念，形如 星辰:1（一般不用）')
    ap.add_argument('--tomes', required=True, help='魔典序列，逗号分隔，可省略"魔典"')
    a = ap.parse_args(argv)
    try:
        result = validate_route(a.culture, a.tomes, a.sub, a.traits, a.dragon, a.ruler_aff)
    except ValueError as e:
        sys.exit(str(e))
    print(format_report(result))
    return 0 if result['ok'] else 1

if __name__ == '__main__':
    sys.exit(main())
