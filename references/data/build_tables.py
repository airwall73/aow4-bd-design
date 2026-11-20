# 从 references/data 的原始JSON生成五张蒸馏表：
# 1. ../unit-attack-tags.md  单位攻击技能标签表（基础/单击/重复、射程、伤害、DLC）
# 2. ../dlc-pantheon.md      DLC与万神殿归属表（魔典、社会/种族特性、文化、领袖类型）
# 3. ../unit-index.md        单位索引表（等阶、来源、类型标签、面板、造价与维护费、DLC）
# 4. ../cultures.md          文化与亚文化机制
# 5. ../enchant-details.md    附魔与种族转换效果
# 注意：../tome-summaries.md（全魔典内容蒸馏表）由 build_tome_summaries.py 单独生成，更新数据后两个脚本都要运行。
# ZH文件的id字段被翻译成中文，需用resid匹配（Units/Tomes）；Traits无resid，按列表顺序匹配（已校验数量一致）。
import json, re, os, collections
from unit_pairs import pair_units

BASE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE, '..', 'version.json'), encoding='utf-8') as _vf:
    DATA_VERSION = json.load(_vf)['official_updated']

def load(lang, name):
    with open(os.path.join(BASE, lang, name), encoding='utf-8') as f:
        return json.load(f)

def strip_tags(s):
    if not s: return ''
    return re.sub(r'</?[^>]+>', '', s).strip()

DMG_MAP = {'damagefrost':'霜','damagefire':'火','damagelightning':'电','damageblight':'疫',
           'damagespirit':'精','damagephysical':'物'}

def fmt_damage(d):
    if not d: return ''
    def rep(m): return DMG_MAP.get(m.group(1), m.group(1))
    return re.sub(r'<(damage\w+)></\1>', rep, d).strip()

DLC_NAMES = {
 'DRAGONLORDS':'Dragon Dawn 龙之黎明', 'EMPIRESANDASHES':'Empires & Ashes 帝国与灰烬',
 'PRIMALFURY':'Primal Fury 原初之怒', 'ELDRITCHREALMS':'Eldritch Realms 诡秘领域',
 'HERALDOFGLORY':'Herald of Glory 荣耀先驱', 'WAYSOFWAR':'Ways of War 战争之道',
 'GIANTKINGS':'Giant Kings 巨人国王', 'SECRETSOFTHEARCHMAGES':'Secrets of the Archmages 大法师之秘',
 'THRONESOFBLOOD':'Thrones of Blood 鲜血王座', 'COSMICWANDERER':'Cosmic Wanderer 宇宙漫游者',
 'RISEFROMRUIN':'Rise from Ruin 废墟崛起', 'SILVERSEAS':'The Silver Seas 白银之海',
 'WITCHOFTHEWAVES':'Witch of the Waves 浪女巫', 'ARCHONPROPHECY':'Archon Prophecy 执政官预言',
}
def dlc_name(code):
    code = (code or '').strip()
    return DLC_NAMES.get(code, code) if code else '本体'

def cn_en(zh_name, en_name):
    zh_name = strip_tags(zh_name); en_name = strip_tags(en_name)
    if not zh_name or zh_name == en_name: return en_name
    return f"{zh_name} {en_name}"

ab_en = {a['slug']: a for a in load('EN','Abilities.json')}
ab_zh = {a['slug']: a for a in load('ZH','Abilities.json')}
un_en = load('EN','Units.json')
un_zh = {id(u): z for u, z in pair_units(un_en, load('ZH', 'Units.json'))}

def req_set(a):
    return {strip_tags(r.get('requisite','')) for r in a.get('requisites',[])}

def is_attack(a):
    if (a.get('damage') or '').strip(): return True
    if 'Base' in req_set(a): return True
    if 'repeatingaction' in (a.get('actionPoints') or ''): return True
    return False

def fmt_ability(slug):
    a = ab_en.get(slug)
    if not a or not is_attack(a): return None
    zh = ab_zh.get(slug, {})
    tags = []
    r = req_set(a)
    if 'Base' in r: tags.append('基础')
    if 'Single Shot' in r: tags.append('单击')
    if 'repeatingaction' in (a.get('actionPoints') or ''): tags.append('重复')
    rng = (a.get('range') or '').strip()
    if rng and rng != '0': tags.append(f'射程{rng}')
    dmg = fmt_damage(a.get('damage',''))
    if dmg: tags.append(dmg)
    return f"{cn_en(zh.get('name'), a.get('name'))}[{'·'.join(tags)}]"

# 预统计单位名重复情况（同名的文化变体用id区分）
entries = []
for u in sorted(un_en, key=lambda x: (x.get('tier') or 0, x.get('name') or '')):
    zh = un_zh[id(u)]
    name = cn_en(zh.get('name'), u.get('name'))
    if not name: continue
    atks = [s for a in u.get('abilities',[]) if (s := fmt_ability(a.get('slug','')))]
    if not atks: continue
    entries.append((u, name, atks))
name_count = collections.Counter(n for _, n, _ in entries)

lines = ["# 单位攻击技能标签表", "",
f"由 `references/data/` 的 Units.json + Abilities.json 自动生成（官网 {DATA_VERSION} 版，生成脚本 `data/build_tables.py`）。",
"标签含义：**基础**=基础攻击；**单击**=单击攻击（Single Shot，享受单击攻击增强）；**重复**=repeating attack（多段攻击，无单击标签）。",
"只收录攻击类技能（有伤害或带基础/重复标记）；防御模式、纯被动不列出。同名单位为不同文化变体，以括号内id区分。", ""]
cur_tier = None
for u, name, atks in entries:
    t = u.get('tier') or 0
    if t != cur_tier:
        cur_tier = t; lines += ["", f"## T{t}"]
    suffix = f"（{u['id']}）" if name_count[name] > 1 else ""
    lines.append(f"- {name}{suffix} | {dlc_name(u.get('DLC'))} | " + '; '.join(atks))

with open(os.path.join(BASE,'..','unit-attack-tags.md'),'w',encoding='utf-8') as f:
    f.write('\n'.join(lines)+'\n')
print('unit-attack-tags.md lines:', len(lines))

# ---------- 表2：DLC与万神殿归属 ----------
tomes_en = load('EN','Tomes.json'); tomes_zh = {t['resid']:t for t in load('ZH','Tomes.json')}
tr_en = load('EN','Traits.json');  tr_zh_list = load('ZH','Traits.json')
if [t.get("icon") for t in tr_en] != [t.get("icon") for t in tr_zh_list]:
    raise ValueError("Traits 英中条目的数量或图标顺序不一致，请核对原始数据。")
fc_en = load('GEN','FactionCreation.json')

out = ["# DLC与万神殿归属表", "",
f"由 `references/data/` 自动生成（官网 {DATA_VERSION} 版，生成脚本 `data/build_tables.py`）。未列出的条目=本体内容。",
"万神殿列为**推断**：数据无显式万神殿字段，用 `front_end:false`（不在派系创建默认列表显示）推断；已核对个人崇拜、魔法成瘾、治安骑士、地下社会、残忍贩奴者等用户确认的万神殿特性，全部符合。FactionCreation无中文版，文化/领袖名以英文为准。", "",
"## DLC代码对照", ""]
seen = set()
for src in (tomes_en, tr_en, fc_en):
    for e in src:
        c = (e.get('DLC') or '').strip()
        if c and c not in seen: seen.add(c)
for c in sorted(seen): out.append(f"- `{c}` = {DLC_NAMES.get(c,c)}")

out += ["", "## DLC魔典（未列出=本体；T0为文化/契约研究，不占魔典序列）", ""]
for t in sorted(tomes_en, key=lambda x:(x.get('tier') or 0, x.get('name') or '')):
    c = (t.get('DLC') or '').strip()
    if c:
        zh = tomes_zh.get(t.get('resid'),{})
        out.append(f"- T{t.get('tier')} {cn_en(zh.get('name'), t.get('name'))} — {dlc_name(c)}")

for ttype, label in (('society','社会特性'), ('form','种族特性')):
    out += ["", f"## {label}（DLC或万神殿；未列出=本体且非万神殿）", ""]
    # 顺序匹配：ZH的id被翻译，只能靠原始列表顺序对应
    pairs = list(zip(tr_en, tr_zh_list))
    for e, z in sorted(pairs, key=lambda p: p[0].get('name') or ''):
        if e.get('type') != ttype: continue
        c = (e.get('DLC') or '').strip()
        pan = not e.get('front_end', True)
        if c or pan:
            marks = []
            if c: marks.append(dlc_name(c))
            if pan: marks.append('万神殿?')
            out.append(f"- {cn_en(z.get('name'), e.get('name'))} — {'; '.join(marks)}")

# 用户确认的人工修正：FactionCreation中Architect文化的DLC字段缺失，
# 但其T0魔典和全部分亚文化均属Archon Prophecy，用户确认建筑师文化来自该DLC。
OVERRIDE_DLC = {('Culture', 'Architect'): 'ARCHONPROPHECY'}

out += ["", "## 文化 / 亚文化 / 职业 / 领袖类型 / 领袖亚型（FactionCreation，仅DLC条目）", ""]
for ttype in ('Culture','SubCulture','Class','Ruler Origin','SubType'):
    rows = []
    for e in fc_en:
        if e.get('type') != ttype: continue
        c = (e.get('DLC') or '').strip() or OVERRIDE_DLC.get((ttype, e.get('name')), '')
        if c: rows.append((e, c))
    if not rows: continue
    out.append(f"### {ttype}")
    for e, c in sorted(rows, key=lambda p: p[0].get('name') or ''):
        mark = '（人工确认，数据缺DLC字段）' if (ttype, e.get('name')) in OVERRIDE_DLC and not (e.get('DLC') or '').strip() else ''
        out.append(f"- {strip_tags(e.get('name'))} — {dlc_name(c)}{mark}")
    out.append("")

with open(os.path.join(BASE,'..','dlc-pantheon.md'),'w',encoding='utf-8') as f:
    f.write('\n'.join(out)+'\n')
print('dlc-pantheon.md lines:', len(out))

# ---------- 表3：单位索引表 ----------
sp_en = load('EN','Spells.json'); sp_zh = {s['resid']: s for s in load('ZH','Spells.json')}

tome_of_unit, tome_of_spell = {}, {}
for t in tomes_en:
    for s in t.get('skills', []):
        if s.get('unit_slug'): tome_of_unit.setdefault(s['unit_slug'], t)
        if s.get('spell_slug'): tome_of_spell.setdefault(s['spell_slug'], t)
summon_of_unit = {}
for s in sp_en:
    for su in s.get('summoned_units') or []:
        summon_of_unit.setdefault(su.get('slug'), s)

# 纯移动/伪装/杂项被动不列入标签列（EN名）；飞行/漂浮保留并放在标签末尾
NOISE_TAGS = {'Land Movement','Forest Walk','Cave Walk','Lava Walk','Desolate Walk','Arctic Walk',
 'Swamp Walk','Sand Walk','Grassland Walk','Road Walk','Mountain Walk','Water Movement',
 'Forest Camouflage','Swamp Camouflage','Water Camouflage','Underground Camouflage','Sand Camouflage',
 'Mountain Camouflage','Universal Camouflage','Primal Concealment','Spirit Finder','Amphibious',
 'Cannot be Displaced','Settler Unit','Civilian','Large Target','Tiny'}
MOBILITY = {'Flying','Floating'}

RES_MAP = {'gold':'金','mana':'法力','influence':'帝权','souls':'魂','warspoils':'战利',
           'favors':'恩惠','population':'人口','unitprod':'产'}
def fmt_res(s):
    if not s: return ''
    return '+'.join(f'{n}{RES_MAP.get(k,k)}' for n, k in re.findall(r'(\d+)\s*<(\w+)></\2>', s))

def tome_ref(t):
    return f"{(tomes_zh.get(t['resid'],{}).get('name') or t.get('name') or '').strip()}(T{t.get('tier')})"

def source_of(u, zh):
    uid = u['id']
    if u.get('culture_name'):
        zc = zh.get('culture_name') or u.get('culture_name')
        zs = zh.get('sub_culture_name') or u.get('sub_culture_name') or ''
        return '文化:' + zc + (f'-{zs}' if zs else '')
    if uid in tome_of_unit:
        return '魔典:' + tome_ref(tome_of_unit[uid])
    if uid in summon_of_unit:
        sp = summon_of_unit[uid]
        t = tome_of_spell.get(sp.get('id'))
        suffix = f"（{tome_ref(t)}）" if t else ''
        return '召唤:' + cn_en(sp_zh.get(sp['resid'],{}).get('name'), sp.get('name')) + suffix
    return '其他'

idx_entries, n_deprecated = [], 0
for u in sorted(un_en, key=lambda x: (x.get('tier') or 0, x.get('name') or '')):
    zh = un_zh[id(u)]
    name = cn_en(zh.get('name'), u.get('name'))
    if not name: continue
    tags, deprecated = [], False
    for p in u.get('secondary_passives', []):
        a = ab_en.get(p['slug'])
        if not a: continue
        en = a.get('name')
        if en == 'DEPRECATED UNIT!': deprecated = True; break
        if en in NOISE_TAGS: continue
        zhn = (ab_zh.get(p['slug'], {}).get('name') or en).strip()
        if en in MOBILITY: tags.append('*' + zhn)  # 飞行/漂浮加星号便于识别
        else: tags.append(zhn)
    if deprecated:
        n_deprecated += 1; continue
    idx_entries.append((u, zh, name, tags))
name_count3 = collections.Counter(n for _, _, n, _ in idx_entries)

lines3 = ["# 单位索引表", "",
f"由 `references/data/` 自动生成（官网 {DATA_VERSION} 版，生成脚本 `data/build_tables.py`）。",
"用途：候选兵种的系统枚举与核心单位的二次核对，按类型标签 Grep 本表，不必每次扫描原始 Units.json。", "",
"列含义：名称 | 来源 | 标签 | 面板 | 造价/维护 | DLC。",
"- 标签来自 Units.json `secondary_passives`（附魔资格判定只认这些标签）；纯移动/伪装类已剔除；飞行/漂浮带 `*` 前缀。",
"- 来源：文化兵=文化（-亚文化）；魔典兵=所属魔典；召唤物=召唤法术（所属魔典）；其余=其他（野怪、塔楼、事件兵等）。",
"- 维护费中 influence 字段按帝权处理（与募役版一致）；**召唤版的法力维护不在 Units.json，需另查召唤法术与既有备注**（召唤/募役维护费可能不同）。",
"- 面板=生命/防/抗/状态抗；单项防护抗性明细仍需回原始数据。",
"- **数据无“种族单位”字段**，种族判断沿用既有规则（文化兵与部分魔典兵为种族单位；动物/构装体/亡灵/元素/魔法起源召唤物等通常非种族）。",
"- 同名单位为不同文化变体，以括号内 id 区分；已剔除 DEPRECATED 单位。文化/亚文化名为数据原文，译名以 FactionCreator 页面为准。",
"- 原始数据更新后必须重跑 `data/build_tables.py` 再生本表，否则以原始 Units.json 为准。", ""]
cur_tier = None
for u, zh, name, tags in idx_entries:
    t = u.get('tier') or 0
    if t != cur_tier:
        cur_tier = t; lines3 += ["", f"## T{t}"]
    suffix = f"（{u['id']}）" if name_count3[name] > 1 else ""
    stats = f"{u.get('hp','?')}命/{u.get('armor','?')}防/{u.get('resistance','?')}抗/{u.get('status_resistance','?')}状抗"
    econ = ' '.join(x for x in [f"造价{fmt_res(u.get('cost'))}" if fmt_res(u.get('cost')) else '',
                                f"维护{fmt_res(u.get('upkeep'))}" if fmt_res(u.get('upkeep')) else ''] if x)
    lines3.append(f"- {name}{suffix} | {source_of(u, zh)} | {'/'.join(tags) or '—'} | {stats} | {econ or '—'} | {dlc_name(u.get('DLC'))}")

with open(os.path.join(BASE,'..','unit-index.md'),'w',encoding='utf-8') as f:
    f.write('\n'.join(lines3)+'\n')
print('unit-index.md lines:', len(lines3), ' deprecated skipped:', n_deprecated)

# ---------- 共用：描述文本清洗（非贪婪去标签，保留数值） ----------
def clean_desc(s):
    if not s: return ''
    s = re.sub(r'<bulletlist>\s*<bullet>', '\n  · ', s)
    s = re.sub(r'<bullet>', '\n  · ', s)
    s = s.replace('</bulletlist>', '')
    s = re.sub(r'<br\s*/?>', '\n', s)
    s = re.sub(r'</?hyperlink>', '', s)
    s = re.sub(r'<[^>]*>', '', s)  # 非贪婪：只去标签本身，标签间数值保留
    return re.sub(r'\n{3,}', '\n\n', s).strip()

AFF_TOKEN = {'empirenature':'自然','empirematter':'物质','empireorder':'秩序','empirechaos':'混沌',
             'empireshadow':'暗影','empirearcana':'星辰','arcana':'星辰','empireastral':'星辰'}
def aff_icons(s):
    return [AFF_TOKEN.get(k, k) for k in re.findall(r'<(empire\w+|arcana)></\1>', s or '')]
def aff_culture(s):
    # 已用用户确认的BD5反推校验：理念=图标数（封建/秘术/原初等单图标文化=1点，
    # 至高/勤勉=2点，蛮族两系各1，建筑师0点）
    return dict(collections.Counter(aff_icons(s)))
def aff_sub(s):
    return dict(collections.Counter(aff_icons(s)))
def aff_fmt(d):
    return ' '.join(f'{k}{v}' for k, v in d.items()) or '无'

# ---------- 表4：文化机制表 ----------
fc_zh_sub_from_units = {}  # (EN culture, EN sub) -> (ZH culture, ZH sub)
for u in un_en:
    if not u.get('culture_name'): continue
    z = un_zh[id(u)]
    if z.get('culture_name'):
        fc_zh_sub_from_units[(u.get('culture_name'), u.get('sub_culture_name') or '')] = \
            (z.get('culture_name'), z.get('sub_culture_name') or '')

t0_tomes = [t for t in tomes_en if (t.get('tier') or 0) == 0]
def zh_of_tome(t):
    return (tomes_zh.get(t['resid'], {}).get('name') or t.get('name') or '').strip()

def match_sub_tome(sub):
    req = sub.get('requirement') or ''
    sname = sub.get('name') or ''
    short = sname.split(' - ')[-1]
    for t in t0_tomes:
        tn = t.get('name') or ''
        if tn == sname: return t
        if req and tn.startswith(req + ' - ') and (tn.endswith(short) or short in tn): return t
        if req and tn.startswith(req + ' - ') and tn.split(' - ')[-1] in sname: return t
    return None

def fmt_tome_skills(t):
    """魔典 skills 逐条：法术用 ZH/Spells.json 完整描述，单位给名称，其余给简介。"""
    zt = tomes_zh.get(t['resid'], {})
    zskills = zt.get('skills', [])
    rows = []
    for i, s in enumerate(t.get('skills', [])):
        zname = (zskills[i].get('name') if i < len(zskills) else '') or s.get('name') or ''
        if s.get('unit_slug'):
            uu = next((x for x in un_en if x['id'] == s['unit_slug']), None)
            uname = cn_en(un_zh[id(uu)].get('name'), uu.get('name')) if uu else s['unit_slug']
            rows.append(f"  - 单位：{uname}（见 unit-index.md）")
        elif s.get('spell_slug'):
            # 法术 id 可能重名（如7个亚文化各有一个 ancestral_harmony），
            # 用魔典自带的技能简介与法术描述匹配来定位正确变体
            cands = [x for x in sp_en if x.get('id') == s['spell_slug']]
            sp = cands[0] if cands else None
            if len(cands) > 1:
                def _norm(t):
                    return re.sub(r'[\d\s]', '', re.sub(r'<[^>]*>', '', t or ''))
                want = _norm(s.get('description'))
                hit = next((x for x in cands if _norm(x.get('description')) == want), None)
                if hit: sp = hit
            if sp:
                zsp = sp_zh.get(sp['resid'], {})
                rows.append(f"  - {zsp.get('name') or sp.get('name')}：{clean_desc(zsp.get('description') or sp.get('description'))}")
            else:
                rows.append(f"  - {zname}：{clean_desc(s.get('description'))}")
        else:
            rows.append(f"  - {zname}：{clean_desc(s.get('description'))}（简介，数值以原始数据为准）")
    return rows

fc_cultures = [e for e in fc_en if e.get('type') == 'Culture']
fc_subs = [e for e in fc_en if e.get('type') == 'SubCulture']
lines4 = ["# 文化机制表", "",
f"由 `references/data/` 自动生成（官网 {DATA_VERSION} 版，生成脚本 `data/build_tables.py`）。",
"用途：设计“某文化BD”时查文化/亚文化机制，不必回原始 JSON 探查。", "",
"约定与注意：",
"- 理念按图标数计（每个图标1点）：多数文化1点，至高/勤勉2点，蛮族两系各1点，建筑师0点；亚文化多数1点，建筑师亚文化2点。领袖起源除巨龙亚型（+1所选系）外均不提供理念（已用既有BD反推校验）。",
"- 法术条目描述取自 ZH/Spells.json 全文（标签已清洗、数值保留）；标“简介”的条目来自 Tomes.json 内嵌简介，数值可能被标签吞掉，以原始数据为准。",
"- 文化/亚文化中文名为数据原文（T0魔典名与单位文化字段），译名仍以 FactionCreator 页面为准。",
"- 只有部分文化有独立 T0 文化魔典（蛮族/至高/勤勉/建筑师），其余文化的通用机制见 `factions-and-heroes.md` 的人工笔记。", ""]
for c in sorted(fc_cultures, key=lambda x: x.get('name') or ''):
    cname = c.get('name')
    subs = [s for s in fc_subs if (s.get('requirement') or '') == cname]
    cul_tome = next((t for t in t0_tomes if t.get('name') == cname), None)
    if cul_tome: zh_cul = zh_of_tome(cul_tome)
    else:
        zh_cul = next((v[0] for k, v in fc_zh_sub_from_units.items() if k[0] == cname), '') or cname
        st = next((match_sub_tome(s) for s in subs if match_sub_tome(s)), None)
        if st and ' - ' in zh_of_tome(st): zh_cul = zh_of_tome(st).split(' - ')[0]
    head = f"## {zh_cul} {cname}（{aff_fmt(aff_culture(c.get('affinity')))}"
    if (c.get('DLC') or '').strip(): head += f" | {dlc_name(c.get('DLC'))}"
    head += "）"
    lines4 += ["", head]
    if c.get('incompatible'):
        lines4.append("- 互斥/锁定：" + '、'.join(x.get('name','') for x in c['incompatible']))
    cunits = [u for u in un_en if u.get('culture_name') == cname
              and not any(ab_en.get(p['slug'], {}).get('name') == 'DEPRECATED UNIT!'
                          for p in u.get('secondary_passives', []))]
    if cunits:
        seen_unames = []
        for u in sorted(cunits, key=lambda x: (x.get('tier') or 0, x.get('name') or '')):
            uname = f"{cn_en(un_zh[id(u)].get('name'), u['name'])}(T{u.get('tier')})"
            if uname not in seen_unames: seen_unames.append(uname)
        lines4.append("- 文化兵（同名含各亚文化变体）：" + '、'.join(seen_unames))
    if cul_tome:
        lines4.append("- 文化机制：")
        lines4 += fmt_tome_skills(cul_tome)
    for s in sorted(subs, key=lambda x: x.get('name') or ''):
        sname = s.get('name')
        t = match_sub_tome(s)
        if t:
            zt = zh_of_tome(t)
            zh_sub = zt.split(' - ')[-1] if ' - ' in zt else zt
        else:
            zh_sub = fc_zh_sub_from_units.get((cname, sname), ('', sname))[1] or sname.split(' - ')[-1]
        lines4.append(f"### {zh_sub}（{sname}；{aff_fmt(aff_sub(s.get('affinity')))}）")
        if t: lines4 += fmt_tome_skills(t)
        else: lines4.append("  - （无独立T0魔典；机制见文化条目与原始数据）")

with open(os.path.join(BASE,'..','cultures.md'),'w',encoding='utf-8') as f:
    f.write('\n'.join(lines4)+'\n')
print('cultures.md lines:', len(lines4))

# ---------- 表5：附魔与种族转换效果表 ----------
def spell_source(sid):
    t = tome_of_spell.get(sid)
    return tome_ref(t) if t else '非魔典来源'

lines5 = ["# 附魔与种族转换效果表", "",
f"由 `references/data/` 自动生成（官网 {DATA_VERSION} 版，生成脚本 `data/build_tables.py`）。",
"用途：核对附魔的实际效果与数值，不必回 Spells.json；适用范围速查仍看 `enchant-map.txt`。",
"描述已清洗标签并保留数值；个别词条若与游戏内显示不符，以原始 ZH/Spells.json 为准（可用 `query.py <名称>` 查看原文）。“非魔典来源”的获取途径见 enchant-map.txt 头部说明。", ""]
enchant_kinds = {'Unit Enchantment':'单位附魔', 'Minor Race Transformation':'次级种族转换',
                 'Major Race Transformation':'高等种族转换'}
ech_entries = []
for s in sp_en:
    kind = next((v for k, v in enchant_kinds.items() if k in (s.get('spellType') or '')), None)
    if not kind: continue
    z = sp_zh.get(s['resid'], {})
    src = spell_source(s.get('id'))
    req_src = z.get('enchantment_requisites') or s.get('enchantment_requisites') or []
    reqs = '、'.join(clean_desc(r.get('requisite','')) for r in req_src) or '—'
    ech_entries.append((kind, src, s, z, reqs))
tier_of_src = lambda src: int(re.search(r'\(T(\d)\)', src).group(1)) if re.search(r'\(T(\d)\)', src) else 99
ech_entries.sort(key=lambda e: (e[0] != '单位附魔', tier_of_src(e[1]), e[1], e[2].get('name') or ''))
for kind, src, s, z, reqs in ech_entries:
    name = cn_en(z.get('name'), s.get('name'))
    cost = fmt_res(s.get('casting_cost')) or '—'
    up = fmt_res(s.get('upkeep'))
    lines5 += ["", f"## {name} — {src}",
               f"{kind} | 施法{cost}" + (f" | 维护{up}" if up else '') + f" | 适用：{reqs}",
               clean_desc(z.get('description') or s.get('description'))]
with open(os.path.join(BASE,'..','enchant-details.md'),'w',encoding='utf-8') as f:
    f.write('\n'.join(lines5)+'\n')
print('enchant-details.md lines:', len(lines5), ' entries:', len(ech_entries))

# ---------- 验证用户给的例子 ----------
import sys
sys.stdout.reconfigure(encoding='utf-8')
print('\n=== 验证 ===')
def show(unit_id):
    u = next(x for x in un_en if x['id']==unit_id)
    zh = un_zh[id(u)]
    print(cn_en(zh.get('name'), u['name']))
    for a in u.get('abilities',[]):
        s = fmt_ability(a.get('slug',''))
        if s: print('   ', s)
show('evoker')
show('hoarfrost_manta')
# 护印者 Sigil Warden?
cands = [u['id'] for u in un_en if 'sigil' in u['id'].lower() or 'warden' in u['id'].lower()]
print('sigil/warden candidates:', cands)
# Traits顺序匹配抽查
i = next(i for i,e in enumerate(tr_en) if e.get('id')=='cult_of_personality')
print('CoP ZH name:', tr_zh_list[i].get('name'))
