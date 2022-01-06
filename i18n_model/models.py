import copy

from django.core.exceptions import ImproperlyConfigured
from django.conf import settings
from django.db import models
from django.db.models.base import ModelBase, Model
from django.db.models.loading import get_model
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import get_language


__all__ = ['I18nModel', 'I18nManager']


def get_class(classname, modulename):
    from_module = __import__(modulename, globals(), locals(), classname)
    return getattr(from_module, classname)


def create_language_method(language_code):
    """ Creates a manager method that filters given language code """
    def get_language(self):
        return self.filter(i18n_language=language_code)
    return get_language


class I18nManager(models.Manager):
    """ The custom manager that adds i18n-related queries

    This method will add a method named after each supported locale according to
    ``settings.LANGUAGES``. For example, for an app that has 'en' and 'de'
    locales, the manager will add the following methods::

        Foo.objects.en()
        Foo.objects.de()

    Locales such as 'pt-br' will have the dash replaced by underscore::

        Foo.objects.pt_br()

    This works across relationships as well. Therefore::

        source.translations.de().get()

    The above yields a single object that matches the 'de' language.

    """

    use_for_related_fields = True

    def lang(self, language_code=None):
        language_code = language_code or get_language()
        return self.filter(i18n_language=language_code)

    def current_language(self):
        return self.lang()

    def get_by_lang(self, language_code=None):
        language_code = language_code or get_language()
        return self.get(i18n_language=language_code)

    def get_available_languages(self):
        return [t.i18n_language for t in self.all()]

    def __new__(cls, *args, **kwargs):
        for language in settings.LANGUAGES:
            language_code = language[0]
            setattr(cls,
                    language_code.replace('-', '_'),
                    create_language_method(language_code))
        return models.Manager.__new__(cls)


class I18nBase(ModelBase):
    """ Base metaclass for the I18nModel
    """

    def __new__(mcs, name, bases, attrs):
        if not 'I18nModel' in [b.__name__ for b in bases]:
            # This is not a I18nModel subclass, so ignore it
            return ModelBase.__new__(mcs, name, bases, attrs)

        attr_meta = attrs.get('Meta', None)

        # First determine what the source model is (and throw if unknown)

        # The most straightforward method is to just look for ``source_model``
        # attribute in model's Meta options:
        source = getattr(attr_meta, 'source_model', None)

        # Remove the source_model attribute if any, pass on exception
        try:
            del attrs['Meta'].source_model
        except AttributeError:
            pass

        if source and type(source) in [str, unicode]:
            # The source is a string, so we need to find out what the developer
            # meant by that. Possibly a class or a model.

            if '.' in source:
                # There's a dot in the name, so this is a model name in
                # ``app.Model`` format, most likely.
                source = get_model(source.split('.')[0],
                                   source.split('.')[1])

            else:
                # Otherwise, let's assume that developer meant just class name.
                # Let's try to get it as a class.
                source = get_class(source,
                                   attrs['__module__'],)

        if source is None and name.endswith('I18N'):
            # There wasn't a ``source_model`` attribute among the Meta options,
            # but there's still hope. The model name ends with ``I18N``, so
            # we can assume that it follows the ``SourceNameI18N`` pattern, and
            # stripping ``I18N`` part would give us the ``SourceName``.
            base_name = name[:-4]
            source = get_class(
                base_name,
                attrs['__module__']
            )

        if not source:
            # There is still no source for some reason... oh well, time to throw
            raise ImproperlyConfigured('Please specify the source model')

        # Now we need to find out what fields from the source model should
        # be translated. And those should be copied to our model.

        # First look at the ``translation_fields`` Meta options
        fields = getattr(attr_meta, 'translation_fields', [])

        # Remove translation_fields attribute if any, pass on exception
        try:
            del attrs['Meta'].translation_fields
        except AttributeError:
            pass

        if not fields:
            # No fields were found, so let's grab all CharField, SlugField,
            # and TextField from the source model.
            fields = [f.name for f in source._meta.fields
                      if type(f) in [models.TextField,
                                     models.CharField,
                                     models.SlugField]]

        unique_fields = []

        # We have the field names we need to copy, so let's copy them over
        # into our new model.
        for field in source._meta.fields:
            if field.name in fields:
                attrs[field.name] = copy.deepcopy(field)

                if field._unique:
                    # We don't allow unique fields in translations.
                    attrs[field.name]._unique = False
                    unique_fields.append(field.name)

        # Add unique_together to Meta
        if hasattr(attr_meta, 'unique_together'):
            if type(attrs['Meta'].unique_together[0]) in (str, unicode):
                attrs['Meta'].unique_together = (
                    attrs['Meta'].unique_together,
                    ('i18n_source', 'i18n_language'))
            else:
                attrs['Meta'].unique_together += ('i18n_source',
                                                  'i18n_language')
        else:
            attrs['Meta'].unique_together = (('i18n_source', 'i18n_language'),)

        # Also include unique fields in unique_together if needed
        if unique_fields:
            for field in unique_fields:
                attrs['Meta'].unique_together += (('i18n_language', field),)

        # Let's also add a reference to the original model
        attrs['i18n_source'] = models.ForeignKey(source,
                                                 related_name='translations',
                                                 editable=False,
                                                 verbose_name=_('source'))

        return ModelBase.__new__(mcs, name, bases, attrs)


class I18nModel(Model):
    """ Translatable model

    To translate any of your Django models, you need to create a translation
    model that will contain the translations. We call the original model the
    'source' model.

    To create a new translatable model, subclass this base model, and do one of
    the following:

     - Name the model using the source model's name with 'I18N' suffix (for
       example, if the source model is called 'Foo', the translation model will
       be called 'FooI18N'
     - Name the model any way you want, and add the ``Meta`` class with
       ``source_model`` property which references the class directly, or as a
       string. The string can be either in the ``'app.Model'`` or ``'Class'``
       format.

    By default, all ``CharField``, ``SlugField`` and ``TextField`` fields will
    be included for translation. You can specify the fields you want translated
    by adding the ``Meta`` class with ``translation_fields`` property, which
    must be an iterable containing the names of the fields. For example::

        class FooI18N(I18nModel):
            # ....
            class Meta:
                translation_fields = ('title', 'body')

    The resulting translation model will have two additional fields:

     - ``i18n_source``: Translation source object
     - ``i18n_language``: The translation locale (language code)

    Note that the two extra fields have translatable names ('source' and
    'language', respectively).

    Translation models have a translate class method which is used to save or
    retrieve translations. For each source object, translations are created like
    this::

        source = Foo.objects.create(
            title='This is a nice post',
            body='Yes, indeed'
        )

        translation = FooI18N.translate(
            source=source,
            language='de',
            title='Das ist ein schoner Beitrag', # Umlaut left off intentionally
            body='Ja, in der Tat'
        )

    Later on, this translation can be retrieved using the same class method::

        translation = FooI18N.translate(source, 'de')
        translation.title  # => 'Das ist ein schoner Beitrag'
        translation.body  # => 'Ja, in der Tat'

    """

    __metaclass__ = I18nBase

    i18n_language = models.CharField(
        _('language'),
        max_length=10,
        choices=[l for l in settings.LANGUAGES
                 if l[0] != settings.LANGUAGE_CODE])

    @classmethod
    def translate(cls, source, language, **kwargs):
        if not kwargs:
            return cls.objects.get(i18n_source=source,
                                   i18n_language=language)

        try:
            translation = cls.objects.get(i18n_source=source,
                                          i18n_language=language)
            for key, value in kwargs.items():
                setattr(translation, key, value)
            translation.save()
            return translation
        except cls.DoesNotExist:
            return cls.objects.create(i18n_source=source,
                                      i18n_language=language,
                                      **kwargs)

    def __unicode__(self):
        return _('%s translation for %s') % (self.get_i18n_language_display(),
                                             self.i18n_source)

    objects = I18nManager()

    class Meta:
        abstract = True
