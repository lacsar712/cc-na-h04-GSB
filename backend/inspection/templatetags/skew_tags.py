from django import template

from inspection.order_skew import explain_rank, skewed_rows

register = template.Library()


@register.filter
def skew_reverse(rows):
    if hasattr(rows, "order_by"):
        return skewed_rows(rows)
    return sorted(list(rows), key=lambda row: row.pk)


@register.inclusion_tag("rank_note.html")
def rank_note(rows):
    return {"items": explain_rank(list(rows))}
