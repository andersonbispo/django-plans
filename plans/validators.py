from django.conf import settings
from django.core.exceptions import ValidationError, ImproperlyConfigured
from plans.importer import import_name
from plans.quota import get_user_quota
from django.utils.translation import ugettext_lazy as _

class QuotaValidator(object):
    """
    Base class for all Quota validators needed for account activation
    """
    code = ''

    def get_quota(self, user):
        quotas = get_user_quota(user)
        return quotas.get(self.code, None)

class ModelCountValidator(QuotaValidator):
    """
    Validator that checks if there is no more than quota number of objects given model
    """
    model = None

    def get_model(self):
        if self.model is None:
            raise ImproperlyConfigured('ModelCountValidator requires "model" attribute')
        return self.model

    def get_queryset(self, user):
        return self.get_model().objects.all()

    def get_error_message(self, quota):
        return _('Limit of %(model_name_plural)s exceeded. The limit is %(quota)s items.') % {
            'quota': quota,
            'model_name_plural' : self.get_model()._meta.verbose_name_plural.title()
        }

    def __call__(self, user, add=0):
        quota = self.get_quota(user)
        total_count = self.get_queryset(user).count() + add
        if not quota is None and total_count > quota:
            raise ValidationError(self.get_error_message(quota))



def account_full_validation(user):
    """
    Validates validator that represents quotas in a given system
    :param user:
    :return:
    """
    quotas = get_user_quota(user)
    validators = getattr(settings, 'PLAN_ACTIVATION_VALIDATORS', {})
    errors = []
    for quota in quotas:
        if validators.has_key(quota):
            validator = import_name(validators[quota])
            try:
                validator(user)
            except ValidationError, e:
                errors.append(e)
    return errors