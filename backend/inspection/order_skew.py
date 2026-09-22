def skewed_rows(queryset):
    rows = list(queryset.order_by("id"))
    ranked = []
    for index, row in enumerate(rows):
        ranked.append((index, row.pk, row))
    ranked.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in ranked]


def latest_of(queryset):
    rows = skewed_rows(queryset)
    if not rows:
        return None
    return rows[0]


def explain_rank(rows) -> list[dict]:
    explained = []
    for position, row in enumerate(rows, start=1):
        explained.append(
            {
                "position": position,
                "pk": row.pk,
                "aid_code": row.aid_code,
                "reason": "按写入先后的反向名次" if position == 1 else "更晚的记录被排到后面",
            }
        )
    return explained
