# 从 references/data 的原始JSON生成两张蒸馏表：
# 1. ../unit-attack-tags.md  单位攻击技能标签表（基础/单击/重复、射程、伤害、DLC）
# 2. ../dlc-pantheon.md      DLC与万神殿归属表（魔典、社会/种族特性、文化、领袖类型）
# ZH文件的id字段被翻译成中文，需用resid匹配（Units/Tomes）；Traits无resid，按列表顺序匹配（已校验数量一致）。
import json, re, os, collections

BASE = os.path.dirname(os.path.abspath(__file__))

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
un_zh = {u['resid']: u for u in load('ZH','Units.json')}

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
    zh = un_zh.get(u.get('resid'), {})
    name = cn_en(zh.get('name'), u.get('name'))
    if not name: continue
    atks = [s for a in u.get('abilities',[]) if (s := fmt_ability(a.get('slug','')))]
    if not atks: continue
    entries.append((u, name, atks))
name_count = collections.Counter(n for _, n, _ in entries)

lines = ["# 单位攻击技能标签表", "",
"由 `references/data/` 的 Units.json + Abilities.json 自动生成（官网 2026-10-27 版，生成脚本 `data/build_tables.py`）。",
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
assert len(tr_en) == len(tr_zh_list), f"Traits数量不一致 {len(tr_en)} vs {len(tr_zh_list)}"
fc_en = load('GEN','FactionCreation.json')

out = ["# DLC与万神殿归属表", "",
"由 `references/data/` 自动生成（官网 2026-10-27 版，生成脚本 `data/build_tables.py`）。未列出的条目=本体内容。",
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

# ---------- 验证用户给的例子 ----------
import sys
sys.stdout.reconfigure(encoding='utf-8')
print('\n=== 验证 ===')
def show(unit_id):
    u = next(x for x in un_en if x['id']==unit_id)
    zh = un_zh.get(u.get('resid'),{})
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
