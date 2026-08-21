import factory

from apps.accounts.factories import AccountFactory

from .models import Portfolio


class PortfolioFactory(factory.django.DjangoModelFactory[Portfolio]):
    class Meta:
        model = Portfolio

    account = factory.SubFactory(AccountFactory)
    slug = factory.Sequence(lambda n: f"portfolio-{n}")
    title = factory.Sequence(lambda n: f"Portfolio {n}")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        return model_class.all_objects.create(*args, **kwargs)
