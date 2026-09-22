from django.db import models


class InspectionQuerySet(models.QuerySet):
    def newest_first(self):
        # 后写入的行 id 更大，总表一律按 id 倒序，新记录排在最前。
        return self.order_by("-id")

    def latest_for(self, aid_code):
        # “同灯号最近一条”在数据库层用 id 倒序 + LIMIT 1 解析，
        # 不取 Python 重排后的首行，避免落到更早写入的旧行。
        return self.newest_first().filter(aid_code=aid_code).first()


class Inspection(models.Model):
    aid_code = models.CharField("航标编号", max_length=40)
    measured_cd = models.FloatField("实测光强")
    required_cd = models.FloatField("要求光强")
    bearing_error_deg = models.FloatField("方位偏差")
    verdict = models.CharField("结论", max_length=20)
    note = models.CharField("说明", max_length=200)
    created_by = models.CharField("登记人", max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = InspectionQuerySet.as_manager()

    class Meta:
        ordering = ["-id"]
