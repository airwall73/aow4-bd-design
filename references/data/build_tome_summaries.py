# 从 references/data 的原始JSON生成 ../tome-summaries.md：全魔典内容蒸馏表。
# 每本魔典按技能一行式列出（附魔含适用范围），数值取自 Spells.json 原文
# （不用 Tomes.json 内嵌的 skills 简介——其中的数值会被剥离）。
# 用途：魔典初筛与机会成本比较；最终选定路线的魔典在写文档/算伤害前仍应回 Spells.json 核对全文。
# 用法（在 references/data 下运行，Windows 必须 -X utf8）：
#   python -X utf8 build_tome_summaries.py
import json, re, os
from collections import defaultdict

BASE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE, '..', 'version.json'), encoding='utf-8') as _vf:
    DATA_VERSION = json.load(_vf)['official_updated']

def load(lang, name):
    with open(os.path.join(BASE, lang, name), encoding='utf-8') as f:
        return json.load(f)

DMG_MAP = {'damagefrost':'霜','damagefire':'火','damagelightning':'电','damageblight':'疫',
           'damagespirit':'精','damagephysical':'物'}

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

AFF = {'empirenature':'自然','empirematter':'物质','empireorder':'秩序','empirechaos':'混沌',
       'empireshadow':'暗影','empirearcana':'星辰','empireastral':'星辰','arcana':'星辰'}

def clean_type(t):
    t = re.sub(r'<cast\w+></cast\w+>', '', t or '')
    t = re.sub(r'</?[^>]+>', '', t)
    return t or '其他'

def compact(desc, limit=240):
    s = desc or ''
    s = s.replace('<br></br>', '；')
    s = re.sub(r'</bullet>\s*<bullet>', '；', s)
    s = re.sub(r'</?bulletlist>|</?bullet>', '', s)
    s = re.sub(r'<(damage\w+)></\1>', lambda m: DMG_MAP.get(m.group(1).lower(), ''), s)
    s = re.sub(r'<(\w+)></\1>', '', s)
    s = re.sub(r'</?[^>]+>', '', s)
    s = re.sub(r'([物火霜电疫精])(?:物理|火焰|寒霜|闪电|疫病|精神)伤害', r'\1', s)
    s = re.sub(r'\s+', '', s)
    s = s.replace('。；', '。')
    s = re.sub(r'；{2,}', '；', s).strip('；')
    return s[:limit] + '…' if len(s) > limit else s

tomes = [t for t in load('ZH', 'Tomes.json') if t.get('name') and t.get('tier') is not None]
spells = defaultdict(list)
for spell in load('ZH', 'Spells.json'):
    spells[spell['id']].append(spell)

def matching_spell(skill):
    # 部分特殊召唤无 spell_slug；用类型排除同名的建筑与单位。
    slug = skill.get('spell_slug') or skill.get('name')
    candidates = spells.get(slug, [])
    if not skill.get('spell_slug') or len(candidates) > 1:
        candidates = [spell for spell in candidates
                      if clean_type(spell['spellType']) == clean_type(skill.get('type'))]
    if len(candidates) > 1:
        # 同名的亚文化法术逐字核对简介，忽略简介中常被省略的数值。
        def normalized(desc):
            return re.sub(r'[\s\d]', '', re.sub(r'<[^>]*>', '', desc))
        wanted = normalized(skill['description'])
        candidates = [spell for spell in candidates if normalized(spell['description']) == wanted]
        if len({(spell['description'], str(spell.get('enchantment_requisites')))
                for spell in candidates}) > 1:
            raise ValueError(f"同名法术无法区分：{slug}")
    return candidates[0] if candidates else None

def tome_aff(t):
    return ' '.join(f"{n}{AFF[tag]}" for n, tag in
                    re.findall(r'(\d+)\s*<(empire\w+|arcana)></\2>', t.get('affinities') or ''))

out = ['# 魔典内容蒸馏表\n',
       f'> 由 build_tome_summaries.py 从 references/data（{DATA_VERSION}）生成，覆盖全部魔典。',
       '> 用途：魔典初筛与机会成本比较，替代逐本 dump 原始 JSON。',
       '> 摘要可能截断，**最终选定路线的魔典在写文档与算伤害前必须回 Spells.json 核对原文**；',
       '> [其他] 类条目（建筑、英雄技能等）的描述取自 Tomes.json 内嵌简介，数值可能已被剥离，需要时查原文。\n']

for tier in sorted({t.get('tier') for t in tomes}):
    group = [t for t in tomes if t.get('tier') == tier]
    out.append(f'## T{tier}\n')
    for t in sorted(group, key=lambda x: x.get('name', '')):
        aff = tome_aff(t)
        head = f"### {t.get('name')}" + (f"（{aff}）" if aff else '')
        dlc = dlc_name(t.get('DLC'))
        if dlc != '本体':
            head += f"｜{dlc}"
        out.append(head)
        for sk in t.get('skills', []):
            nm = sk.get('name', '')
            s = matching_spell(sk)
            if s:
                line = f"- {nm} [{clean_type(s.get('spellType'))}]: {compact(s.get('description'))}"
                req = s.get('enchantment_requisites')
                if req:
                    app = '/'.join(re.sub(r'</?[^>]+>', '', r.get('requisite', '')).strip() for r in req)
                    line += f"｜适用: {app}"
                out.append(line)
            elif sk.get('unit_slug'):
                out.append(f"- {nm} [单位]: 见 unit-index.md / unit-attack-tags.md")
            else:
                summary = compact(sk.get('description'), 120)
                if nm == '星辰贸易站' and '帝国中每有一个星辰贸易站' in summary:
                    summary += '（额外收入的计数条件与 11 月 19 日补丁有分歧，见 units-and-economy.md）'
                out.append(f"- {nm} [{clean_type(sk.get('type'))}]: {summary}")
        out.append('')

dst = os.path.join(BASE, '..', 'tome-summaries.md')
with open(dst, 'w', encoding='utf-8') as f:
    f.write('\n'.join(out))
print(f'已生成 {dst}（{len(out)} 行）')
