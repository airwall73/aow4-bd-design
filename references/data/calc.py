# AoW4 BD 伤害与命中计算工具，按 references/design-rules.md 的规则编码：
# - 每种伤害属性分别向上取整；同类增伤先相加；防抗倍率 = 1.1^(-防/抗)，整套攻击统一由防或抗抵挡
# - 暴击 +50% 与其他增伤加算；分别算 D0/Dc 后按暴击率加权：E=(1-c)*D0+c*Dc
# - 减益命中：实际概率 = 基础概率 × 0.9^状态抗性（负抗性反向提高，封顶100%；必中效果不要用本工具）
#
# 用法：
#   python -X utf8 calc.py dmg --base "12物 6火" --flat "2火 1电" --pct 40,20 --crit 20 --dr 5 --hits 1
#   python -X utf8 calc.py hit 60 5
# analyze_build.py 通过 damage_result()/hit_result() 复用相同公式批量计算。
import argparse, decimal, math, re, sys

sys.stdout.reconfigure(encoding='utf-8')

TYPES = '物火霜电疫精'

def parse_channels(s):
    out = {}
    for n, t in re.findall(r'(\d+(?:\.\d+)?)\s*([%s])' % TYPES, s or ''):
        out[t] = out.get(t, 0) + float(n)
    return out

def unparsed_warning(label, s):
    leftover = re.sub(r'\d+(?:\.\d+)?\s*[%s]' % TYPES, '', s or '')
    if re.search(r'\d', leftover):
        return f'{label} 含未识别的通道写法（已忽略）："{leftover.strip()}"，合法用字为 {TYPES}'
    return None

def channel_damage(base, flat, pct_mult, dr):
    per = {}
    for t in TYPES:
        v = base.get(t, 0) + flat.get(t, 0)
        if v <= 0: continue
        per[t] = math.ceil(v * pct_mult * 1.1 ** (-dr) - 1e-9)
    return per

def fmt(per):
    return ' '.join(f'{v}{t}' for t, v in per.items()) + f'（合计{sum(per.values())}）'

def parse_pct(value):
    if value is None or value == '': return 0.0
    if isinstance(value, (list, tuple)):
        return sum(float(x) for x in value) / 100
    if isinstance(value, (int, float)):
        return float(value) / 100
    return sum(float(x) for x in re.split(r'[,，]', value) if x.strip()) / 100

def damage_result(base_text, flat_text='', pct=None, crit=0, dr=5, hits=1):
    base, flat = parse_channels(base_text), parse_channels(flat_text)
    if not base and not flat:
        raise ValueError('base/flat 未解析出伤害通道，格式示例 "12物 6火"')
    if hits < 1:
        raise ValueError('hits 必须为正整数')
    warnings = [w for w in [unparsed_warning('base', base_text), unparsed_warning('flat', flat_text)] if w]
    pct_mult = parse_pct(pct)
    d0 = channel_damage(base, flat, 1 + pct_mult, dr)
    t0 = sum(d0.values()) * hits
    result = {'warnings': warnings, 'pct_percent': pct_mult * 100, 'crit_percent': float(crit),
              'dr': float(dr), 'hits': int(hits), 'normal_channels': d0, 'normal_total': t0,
              'critical_channels': None, 'critical_total': None, 'expected': None}
    if crit:
        c = decimal.Decimal(str(crit)) / 100
        dc = channel_damage(base, flat, 1 + pct_mult + 0.5, dr)
        tc = sum(dc.values()) * hits
        expected = (1 - c) * t0 + c * tc
        result.update(critical_channels=dc, critical_total=tc,
                      expected=float(expected.quantize(decimal.Decimal('0.1'), rounding=decimal.ROUND_HALF_UP)))
    return result

def hit_result(prob, res):
    p = prob / 100 * 0.9 ** res
    return {'probability': float(prob), 'status_resistance': float(res),
            'hit_percent': min(p, 1.0) * 100, 'capped': p > 1}

def cmd_dmg(a):
    try:
        r = damage_result(a.base, a.flat, a.pct, a.crit, a.dr, a.hits)
    except ValueError as e:
        sys.exit(f'错误：{e}')
    for warning in r['warnings']:
        print(f'警告：{warning}', file=sys.stderr)
    print(f'普通命中 D0: {fmt(r["normal_channels"])}' +
          (f' ×{a.hits}段 = {r["normal_total"]}' if a.hits > 1 else ''))
    if r['expected'] is not None:
        c = a.crit / 100
        print(f'暴击命中 Dc: {fmt(r["critical_channels"])}' +
              (f' ×{a.hits}段 = {r["critical_total"]}' if a.hits > 1 else ''))
        print(f'期望 E = (1-{c:.2f})×{r["normal_total"]} + {c:.2f}×{r["critical_total"]} = {r["expected"]:.1f}')

def cmd_hit(a):
    r = hit_result(a.prob, a.res)
    print(f'命中率 = {a.prob}% × 0.9^{a.res} = {r["hit_percent"]:.1f}%' + ('（封顶100%）' if r['capped'] else ''))

def main(argv=None):
    ap = argparse.ArgumentParser(description='AoW4 BD 伤害/命中计算')
    sub = ap.add_subparsers(dest='cmd', required=True)
    d = sub.add_parser('dmg', help='单次攻击伤害（普通/暴击/期望）')
    d.add_argument('--base', default='', help='基础伤害通道，如 "12物 6火"')
    d.add_argument('--flat', default='', help='固定附加通道，如 "2火 1电"')
    d.add_argument('--pct', default='', help='百分比增伤列表，如 40,20')
    d.add_argument('--crit', type=float, default=0, help='暴击率%%')
    d.add_argument('--dr', type=float, default=5, help='抵挡该攻击的防/抗数值（默认5）')
    d.add_argument('--hits', type=int, default=1, help='攻击段数（默认1）')
    d.set_defaults(f=cmd_dmg)
    h = sub.add_parser('hit', help='减益命中率 = 基础概率 × 0.9^状态抗性')
    h.add_argument('prob', type=float, help='基础概率%%')
    h.add_argument('res', type=float, help='状态抗性（可为负）')
    h.set_defaults(f=cmd_hit)
    args = ap.parse_args(argv)
    args.f(args)

if __name__ == '__main__':
    main()
