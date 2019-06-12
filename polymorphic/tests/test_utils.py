from django.test import TransactionTestCase

from polymorphic.models import PolymorphicTypeUndefined, PolymorphicModel
from polymorphic.tests.models import Model2A, Model2B, Model2C, Model2D, Enhance_Inherit, \
    Enhance_Base, UserProfile, Participant, Team
from polymorphic.utils import reset_polymorphic_ctype, sort_by_subclass, get_base_polymorphic_model


class UtilsTests(TransactionTestCase):

    def test_sort_by_subclass(self):
        self.assertEqual(
            sort_by_subclass(Model2D, Model2B, Model2D, Model2A, Model2C),
            [Model2A, Model2B, Model2C, Model2D, Model2D]
        )

    def test_reset_polymorphic_ctype(self):
        """
        Test the the polymorphic_ctype_id can be restored.
        """
        Model2A.objects.create(field1='A1')
        Model2D.objects.create(field1='A1', field2='B2', field3='C3', field4='D4')
        Model2B.objects.create(field1='A1', field2='B2')
        Model2B.objects.create(field1='A1', field2='B2')
        Model2A.objects.all().update(polymorphic_ctype_id=None)

        with self.assertRaises(PolymorphicTypeUndefined):
            list(Model2A.objects.all())

        reset_polymorphic_ctype(Model2D, Model2B, Model2D, Model2A, Model2C)

        self.assertQuerysetEqual(
            Model2A.objects.order_by("pk"),
            [
                Model2A,
                Model2D,
                Model2B,
                Model2B,
            ],
            transform=lambda o: o.__class__,
        )

    def test_get_base_polymorphic_model(self):
        """
        Test that finding the base polymorphic model works.
        """
        # Finds the base from every level (including lowest)
        self.assertIs(get_base_polymorphic_model(Model2D), Model2A)
        self.assertIs(get_base_polymorphic_model(Model2C), Model2A)
        self.assertIs(get_base_polymorphic_model(Model2B), Model2A)
        self.assertIs(get_base_polymorphic_model(Model2A), Model2A)

        # Properly handles multiple inheritance
        self.assertIs(get_base_polymorphic_model(Enhance_Inherit), Enhance_Base)

        # Ignores PolymorphicModel itself.
        self.assertIs(get_base_polymorphic_model(PolymorphicModel), None)

    def test_get_base_polymorphic_model_skip_abstract(self):
        """
        Skipping abstract models that can't be used for querying.
        """
        class A(PolymorphicModel):
            class Meta:
                abstract = True

        class B(A):
            pass

        class C(B):
            pass

        self.assertIs(get_base_polymorphic_model(A), None)
        self.assertIs(get_base_polymorphic_model(B), B)
        self.assertIs(get_base_polymorphic_model(C), B)

        self.assertIs(get_base_polymorphic_model(C, allow_abstract=True), A)

    def test_unknown_issue(self):

        user_a = UserProfile.objects.create(name='a')
        user_b = UserProfile.objects.create(name='b')
        user_c = UserProfile.objects.create(name='c')

        team1 = Team.objects.create(team_name='team1')
        team1.user_profiles.add(user_a, user_b, user_c)
        team1.save()

        team2 = Team.objects.create(team_name='team2')
        team2.user_profiles.add(user_c)
        team2.save()

        # without prefetch_related, the test passes
        my_teams = Team.objects.filter(user_profiles=user_c).prefetch_related(
            'user_profiles').distinct()

        print(my_teams[0].user_profiles.all())
        print(my_teams[1].user_profiles.all())
        self.assertEqual(len(my_teams[0].user_profiles.all()), 3)
        self.assertEqual(len(my_teams[1].user_profiles.all()), 1)

        print(my_teams[0].user_profiles.all())
        print(my_teams[1].user_profiles.all())
        self.assertEqual(len(my_teams[0].user_profiles.all()), 3)
        self.assertEqual(len(my_teams[1].user_profiles.all()), 1)

        # without this "for" loop, the test passes
        for _ in my_teams:
            pass

        print(my_teams[0].user_profiles.all())
        print(my_teams[1].user_profiles.all())
        # This time, test fails.
        # with sqlite:      4 != 3
        # with postgresql:  2 != 3
        self.assertEqual(len(my_teams[0].user_profiles.all()), 3)
        self.assertEqual(len(my_teams[1].user_profiles.all()), 1)