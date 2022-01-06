from django.conf import settings
from django.contrib.auth import get_permission_codename
from django.forms.models import BaseInlineFormSet


def i18n_formset_factory(languages=[]):
    # Create an ad-hoc form set
    class I18nFormSet(BaseInlineFormSet):
        def __init__(self, *args, **kwargs):
            kwargs['initial'] = [{'i18n_language': l} for l in languages]
            super(I18nFormSet, self).__init__(*args, **kwargs)

    return I18nFormSet


class I18nInlineMixin(object):
    max_num = len(settings.LANGUAGES) - 1

    def get_existing_translation(self, obj=None):
        if not obj or not obj.pk:
            return []
        return obj.translations.get_available_languages()

    def get_untranslated_languages(self, obj=None):
        if not obj or not obj.pk:
            return [lang[0] for lang in settings.LANGUAGES
                    if lang[0] != settings.LANGUAGE_CODE]
        else:
            translated = obj.translations.get_available_languages()
            return [lang[0] for lang in settings.LANGUAGES
                    if lang[0] not in translated
                    and lang[0] != settings.LANGUAGE_CODE]

    def get_extra(self, request, obj=None, **kwargs):
        existing_translations = self.get_existing_translation(obj)
        return len(settings.LANGUAGES) - 1 - len(existing_translations)

    def get_formset(self, request, obj=None, **kwargs):
        untranslated = self.get_untranslated_languages(obj)
        # Override the argument passed to superclass' get_formset method so
        # that our ad-hoc form set is used instead.
        kwargs['formset'] = i18n_formset_factory(untranslated)
        kwargs['extra'] = self.get_extra(request, obj)
        return super(I18nInlineMixin, self).get_formset(request, obj, **kwargs)

    # For inline forms to show up, Django checks whether the user
    # has permissions for the related model. In the most basic case,
    # `I18nModel`s wouldn't have their own permissions - so below we
    # make sure to inherit the permissions of the source model.
    
    def get_source_meta(self):
        source_field = self.model._meta.get_field_by_name('i18n_source')[0]
        return source_field.rel.to._meta

    def has_add_permission(self, request):
        opts = self.get_source_meta()
        codename = get_permission_codename('add', opts)
        return request.user.has_perm("%s.%s" % (opts.app_label, codename))

    def has_change_permission(self, request, obj=None):
        opts = self.get_source_meta()
        codename = get_permission_codename('change', opts)
        return request.user.has_perm("%s.%s" % (opts.app_label, codename))

    def has_delete_permission(self, request, obj=None):
        opts = self.get_source_meta()
        codename = get_permission_codename('delete', opts)
        return request.user.has_perm("%s.%s" % (opts.app_label, codename))
