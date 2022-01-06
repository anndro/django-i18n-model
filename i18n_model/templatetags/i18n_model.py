from __future__ import unicode_literals

from django.template import Library
from django.conf import settings
from django.utils.translation import get_language, override
from django.core.urlresolvers import reverse, resolve

register = Library()


@register.assignment_tag
def translate(obj, language=None):
    language = language or get_language()

    if language == settings.LANGUAGE_CODE:
        # If the langauge is default return original object
        return obj

    try:
        return obj.translations.get_by_lang(language)
    except:
        return obj


@register.simple_tag(takes_context=True)
def translate_url(context, path=None, language=None):
    try:
        if path:
            url = resolve(path)
        else:
            url = context['request'].resolver_match
    except:
        return ''

    language = language or get_language()

    # We need to call override here because the override from the {% language %}
    # tag doesn't affect the reverse() call for some reason.
    with override(language):
        url_full_name = url.url_name
        if url.namespace:
            url_full_name = '%s:%s' % (url.namespace, url_full_name)
        return reverse(url_full_name, args=url.args, kwargs=url.kwargs)
