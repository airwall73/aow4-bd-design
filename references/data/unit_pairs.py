"""对齐双语单位。多个亚文化可以共享同一单位的 resid 和本地化前的 id。"""
from collections import defaultdict, deque


def pair_units(en, zh):
    """按 resid 分组，并保留官网导出中同组变体的次序。"""
    groups = defaultdict(deque)
    for unit in zh:
        groups[unit['resid']].append(unit)

    pairs = []
    sub_names = {}
    for unit in en:
        group = groups[unit['resid']]
        if not group:
            raise ValueError(f"缺少中文单位变体：{unit['resid']}")
        localized = group.popleft()
        sub = unit.get('sub_culture_name')
        zh_sub = localized.get('sub_culture_name')
        if (sub_names.setdefault(sub, zh_sub) != zh_sub
                or unit.get('abilities') != localized.get('abilities')):
            raise ValueError(f"中英文单位变体不一致：{unit['id']} / {sub}")
        pairs.append((unit, localized))
    if any(groups.values()):
        raise ValueError('有中文单位变体未与英文单位匹配')
    return pairs
