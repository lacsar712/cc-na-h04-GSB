from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import Client, TestCase

from inspection.models import Inspection
from inspection.rules import judge


def make_row(aid_code, measured=1400.0, required=1200.0, bearing=0.4):
    verdict, note = judge(measured, required, bearing)
    return Inspection.objects.create(
        aid_code=aid_code,
        measured_cd=measured,
        required_cd=required,
        bearing_error_deg=bearing,
        verdict=verdict,
        note=note,
        created_by="tester",
    )


class ListOrderingTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.force_login(User.objects.create_user(username="tester"))

    def test_new_rows_appear_at_front_of_master_list(self):
        older = make_row("LH-10")
        middle = make_row("LH-11")
        newer = make_row("LH-10", measured=1500.0)

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.context["rows"].values_list("pk", flat=True)),
            [newer.pk, middle.pk, older.pk],
        )

    def test_rendered_page_lists_new_row_before_old_row(self):
        older = make_row("LH-20")
        newer = make_row("LH-20", measured=1500.0)

        content = self.client.get("/").content.decode()
        self.assertLess(
            content.index(f"/inspections/{newer.pk}/"),
            content.index(f"/inspections/{older.pk}/"),
        )


class LatestPerAidTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.client.force_login(User.objects.create_user(username="tester"))

    def test_latest_endpoint_returns_last_written_row(self):
        old = make_row("LH-30", measured=1300.0)
        make_row("LH-31")
        new = make_row("LH-30", measured=1500.0)

        response = self.client.get("/latest/LH-30/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["pk"], new.pk)
        self.assertNotEqual(response.json()["pk"], old.pk)

    def test_latest_queryset_picks_last_written_row(self):
        old = make_row("LH-40")
        new = make_row("LH-40", bearing=0.9)
        self.assertEqual(
            Inspection.objects.filter(aid_code="LH-40").order_by("-id").first(),
            new,
        )
        self.assertGreater(new.pk, old.pk)


class DimSeedVerdictTests(TestCase):
    def test_dim_seed_row_is_judged_insufficient_light(self):
        call_command("seed_demo")
        dim = Inspection.objects.get(aid_code="LH-09")
        self.assertEqual(dim.verdict, "不合格")
        self.assertEqual(dim.note, "光强不足")

    def test_judge_marks_dim_reading_insufficient_light(self):
        verdict, note = judge(800.0, 1200.0, 0.2)
        self.assertEqual(verdict, "不合格")
        self.assertEqual(note, "光强不足")
