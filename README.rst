=================
django-i18n-model
=================

Adding translations to Django models is a topic that has been discussed from a
vast variety of angles, and yet still not very well defined. django-i18n-model
is yet another solution for adding i18n to your models.

It is very similar to django-hvad_ in that it uses the actual database and
metaclasses to do its job, but unlike django-hvad, it does not modify the source
model. Unlike django-modeltranslation_, and like django-hvad, django-i18n-models
does not add any new fields to the source model.

One interesting library for handling i18n in models is django is django-lingua_.
Unlike any of the database-backed solutions, it uses the gettext interface to
facilitate translation of model data. While we find lingua interesting in
principle, we believe translation of database data should be kept in the
database (and lingua didn't work very well for us anyway).

The main advantage of using django-i18n-model is the ability to:

1. Add custom fields to translations

2. Ability to use South migrations

3. Not necessary to modify your existing models

Keep in mind that this library is fairly young so it still lacks many of the
convenience features such as automatic translation of fields. Those features 
are still being designed and are planned for future releases.

Backwards incompatible changes
==============================

Starting with v0.0.8, unique field handling is changed. Unique fields will no
longer be unique across all translations, but just per language. Please file a
bug report with a description of a use case if you know of a case where this
behavior is not desirable.

Overview
========

django-i18n-model works by creating a completely separate model for translation.
It does so by obtaining information about the model fields from the source model
and creating a clone with additional fields called ``i18n_language`` and
``i18n_source``. It currently offers several ways of referencing the translation
source model and the set of fields to include in the translations.

Installation
============

Install using pip or easy_install::

    pip install django-i18n-model

    easy_install django-i18n-model

You can also download the tarball and unpack it into your project directory.

If you want to use the supplied template tags, you also need to add the
``i18N_model`` app to ``INSTALLED_APPS``.

Basic usage
===========

To create a new translation model, simply subclass the ``I18nModel`` class::

    from django.db import models
    from i18n_model.models import I18nModel


    class Source(models.Model):
        """ Your normal model """
        title = models.CharField(max_length=20)
        body = models.TextField()
        date = models.DateField()

    class SourceI18N(I18nModel):
        class Meta:
            translation_fields = ('title', 'body')

With the above setup, a new model is created that is named ``SourceI18N`` and it
will contain the ``title``, ``body``, ``i18n_language`` and ``i18n_source``
fields. The ``i18n_source`` is a foreign key to ``Source`` model.

*New in 0.0.7:* The ``i18n_language`` field was limited to languages defined by
``settings.LANGUAGES``. Since 0.0.7, the selection of languages no longer
includes the default language defined by ``settings.LANGUAGE_CODE``.

Other than adding the 'I18N' suffix to the translation model name, you can also
use the ``source_model`` Meta option to reference the source model. For
example::

    class SourceTranslation(I18nModel):
        class Meta:
            source_model = Source
            translation_fields = ('title', 'body')

The ``source_model`` attribute can point to the class object directly, or it can
use a string name of the class (ex: ``'Source'``) or, if the model is in a
different app, you can also use the ``'app.Model'`` format commonly used in
Django. The following are all equivalent::

    class SourceTranslation(I18nModel):
        class Meta:
            source_model = Source


    class SourceTranslation(I18nModel):
        class Meta:
            source_model = 'Source'


    class SourceTranslation(I18nModel):
        class Meta:
            source_model = 'appname.Source'

Admin integration
=================

From day one, i18n-model was designed to allow conventional admin integration
using inline admin form sets. Since the translation model is a proper model,
this wasn't a big issue. However, this package now includes a mixin to help
manage the form set count and max count when adding inline form sets for
translations.

Using the above example models, an admin module may look like this::

    from django import admin
    from i18n_model.admin import I18nInlineMixin
    from .models import Source, SourceI18N

    
    class SourceI18nInline(I18nInlineMixin, admin.StackedInline):
        model = Source


    class SourceAdmin(admin.ModelAdmin):
        inlines = [SourceI18nInline]


    admin.site.register(Source, SourceAdmin)

The admin inline mixin checks the source module's translations and creates
inline formsets for missing ones. When translations exist for all languages
listed under ``settings.LANGUAGES``, it will create no further inline forms.

This feature is not tested on Django >= 1.6 yet. Please let me know if it works
for you.

Creating translations
=====================

You can create translations as usual by simply creating a new instance of the
``*I18N`` model, or you can use the ``translate`` class method on the ``*I18N``
class. Here is an example of the latter using the above code::

    my_source = Source(title='Test', body='test', date=datetime.date.today())
    my_translation = SourceI18N.translate(
        my_source,
        'sr',
        title='Тест',
        body='тест'
    )

Getting translations
====================

The translations are obtained using the ``translate`` class method. You can
obtain translations for a specific language by calling the ``translate``
class method without any keyword arguments::

    translation = SourceI18N.translate(my_source, 'sr')
    translation.title  # >> 'Тест'
    translation.body  # >> тест'

It is also possible to obtain translations directly from the source model. The
foreign key on the translation model creates a ``translations`` property on the
source model. This property is an instance of ``I18nManager`` custom manager,
and it behaves like a normal Django manager for most part. To get all
translations for a given object::

    my_source.translations.all()

To get translations for a specific language, the manager has shortcut manager
methods that are named after locales::

    translation = my_source.translations.sr().get()

Getting translation languages
=============================

If you need to get a list of languages for which translations exist, you can do
so using the ``get_available_languages()`` method. For example::

    my_source.translations.get_available_languages() # >> ['sr', 'it']

This has very little value under normal circumstances, and it does result in a
database lookup, but it is used in the admin area for determining the initial
value of form sets.

Retrieving translations programmatically
========================================

Although the hard-coded locale methods are useful in templates, you may
sometimes need to retrieve translations with variable locale. In that case, you
may want to use the ``lang`` manager method instead. Here's an example::

    SourceI18N.objects.lang('de').all()

or::

    my_source.translations.lang('de').get()

Using the ``lang`` method without any language code will filter languages for
the currently active language::

    translation.activate('de')
    my_source.translations.lang().get()  # Gets translation for 'de' language

The ``current_language`` manager method is a deprecated alias for the last form.

Retrieving a single translation object
======================================

The custom manager object has a shortcut for retrieving a single translation
object, which may be very useful when used on related source objects. The method
is named ``get_by_lang()`` and is called with an optional language code. The
language code defaults to the currently active language. Here's an example::

    my_source.translations.get_by_lang()  # Retrieves 'de' translation
    my_source.translations.get_by_lang('es')  # Retrieves 'es' translation

The added benefit of using this shortcut is that it reuses the existing
queryset, so it works well with methods like ``prefetch_related``.

Template tags
=============

To use the template tags first load the ``i18n_model`` library::

    {% load i18n_model %}

``{% translate %}`` tag
-----------------------

Translate tag is an assignment tag. It takes the source object, and returns a
translation object that you can use in your template. For example::

    {% translate my_source as my_translation %}
    {{ my_translation.title }}
    {{ my_translation.body }}

By default, it uses the currently active language for looking up translation. It
will return the original source object if there is no matching translation.

Note that non-translated fields from the original model are not copied to the
translation. For non-translated fields, always use the original.

``{% translate_url [path] [language] %}`` tag
---------------------------------------------

If you are using i18n in your URLs, you may sometimes need to obtain a
translated URL. This tag gives you that ability. The tag accepts an optional
path parameter which defaults to the current path. You must wrap it in the
Djago's built-in ``{% language %}`` tag to get translations for different
languages or use the language parameter. Here is an example::

    {% language 'es' %}
    {% translate_url %} current URL in Spanish
    {% endlanguage %}

    {% translate_url language='es' %} Same as above

    {% language 'es' %}
    {% translate_url object.get_absolute_path %} Object's URL in Spanish
    {% endlanguage %}

    {% translate_url object.get_absolute_path 'es' %} Same as above

.. _django-hvad: http://django-hvad.readthedocs.org/en/latest/index.html
.. _django-modeltranslation: https://github.com/deschler/django-modeltranslation
.. _django-lingua: http://code.google.com/p/django-lingua/
