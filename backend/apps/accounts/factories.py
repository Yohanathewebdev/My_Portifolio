import factory
from django.utils import timezone

from .models import Account, AccountMembership, User


class UserFactory(factory.django.DjangoModelFactory[User]):
    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "Password123!")


class AccountFactory(factory.django.DjangoModelFactory[Account]):
    class Meta:
        model = Account

    name = factory.Sequence(lambda n: f"Account {n}")
    slug = factory.Sequence(lambda n: f"account-{n}")
    billing_email = factory.LazyAttribute(lambda obj: f"{obj.slug}@example.com")
    country_code = "US"

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        return model_class.all_objects.create(*args, **kwargs)


class MembershipFactory(factory.django.DjangoModelFactory[AccountMembership]):
    class Meta:
        model = AccountMembership

    account = factory.SubFactory(AccountFactory)
    user = factory.SubFactory(UserFactory)
    role = AccountMembership.ROLE_OWNER
    accepted_at = factory.LazyFunction(timezone.now)

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        return model_class.all_objects.create(*args, **kwargs)
