import importlib.util

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import Client, TestCase

from inspection.models import Inspection
from inspection.rules import judge


class OrderingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="watch", password="watch123456")
        self.client.force_login(self.user)

    def test_new_rows_listed_first(self):
        # 交错写入两条灯号，后写入的记录必须出现在总表最前面，
        # 不能把更早的记录排到更晚的记录前面。
        first = Inspection.objects.create(
            aid_code="LH-01", measured_cd=1400, required_cd=1200,
            bearing_error_deg=0.4, verdict="合格", note="", created_by="watch",
        )
        Inspection.objects.create(
            aid_code="LH-09", measured_cd=900, required_cd=1200,
            bearing_error_deg=0.2, verdict="不合格", note="光强不足", created_by="watch",
        )
        latest = Inspection.objects.create(
            aid_code="LH-01", measured_cd=1500, required_cd=1200,
            bearing_error_deg=0.1, verdict="合格", note="", created_by="watch",
        )

        rows = list(Inspection.objects.newest_first())
        self.assertEqual([row.pk for row in rows], [latest.pk, first.pk + 1, first.pk])
        self.assertEqual(rows[0], latest)
        # 默认管理器顺序同样是新行在前，不依赖视图额外排序。
        self.assertEqual(list(Inspection.objects.all())[0], latest)

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        listed = list(response.context["rows"])
        self.assertEqual(listed[0].pk, latest.pk)
        self.assertLess(listed.index(latest), listed.index(first))

    def test_latest_for_aid_returns_newly_written_row(self):
        # 同灯号重复登记后，“最近一条”必须是后写的那条。
        old = Inspection.objects.create(
            aid_code="LH-01", measured_cd=1400, required_cd=1200,
            bearing_error_deg=0.4, verdict="合格", note="", created_by="watch",
        )
        other = Inspection.objects.create(
            aid_code="LH-09", measured_cd=900, required_cd=1200,
            bearing_error_deg=0.2, verdict="不合格", note="光强不足", created_by="watch",
        )
        new = Inspection.objects.create(
            aid_code="LH-01", measured_cd=1300, required_cd=1200,
            bearing_error_deg=0.3, verdict="合格", note="", created_by="watch",
        )

        self.assertEqual(Inspection.objects.latest_for("LH-01"), new)
        self.assertNotEqual(Inspection.objects.latest_for("LH-01"), old)
        self.assertEqual(Inspection.objects.latest_for("LH-09"), other)
        self.assertIsNone(Inspection.objects.latest_for("LH-404"))

        response = self.client.get(f"/latest/{new.aid_code}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["pk"], new.pk)

    def test_order_skew_bypass_removed(self):
        # 名为 OrderSkew 的旁路模块及其模板标签必须已废除，
        # 排序只能走模型/查询集这一条路。
        self.assertIsNone(importlib.util.find_spec("inspection.order_skew"))
        self.assertIsNone(importlib.util.find_spec("inspection.templatetags.skew_tags"))


class VerdictTests(TestCase):
    def test_dim_light_is_insufficient_intensity(self):
        verdict, note = judge(800, 1200, 0.2)
        self.assertEqual(verdict, "不合格")
        self.assertEqual(note, "光强不足")

    def test_dim_seed_row_keeps_insufficient_verdict(self):
        # 演示种子里偏暗的 LH-09，判词仍必须是“光强不足”。
        call_command("seed_demo")
        dim = Inspection.objects.latest_for("LH-09")
        self.assertIsNotNone(dim)
        self.assertEqual(dim.measured_cd, 800)
        self.assertEqual(dim.required_cd, 1200)
        self.assertEqual(dim.verdict, "不合格")
        self.assertEqual(dim.note, "光强不足")

    def test_dim_submission_via_view_keeps_insufficient_verdict(self):
        group = Group.objects.create(name="inspector")
        keeper = User.objects.create_user(username="keeper", password="light123456")
        keeper.groups.add(group)
        self.client.force_login(keeper)

        response = self.client.post(
            "/inspections/new/",
            {
                "aid_code": "LH-77",
                "measured_cd": "500",
                "required_cd": "1200",
                "bearing_error_deg": "0.1",
            },
        )
        self.assertEqual(response.status_code, 302)
        row = Inspection.objects.get(aid_code="LH-77")
        self.assertEqual(row.verdict, "不合格")
        self.assertEqual(row.note, "光强不足")
