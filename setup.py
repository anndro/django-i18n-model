from distutils.core import setup

setup(
    name='django-i18n-model',
    version='0.0.9',
    packages=['i18n_model', 'i18n_model.templatetags'],
    license='BSD',
    author='Branko Vukelic',
    author_email='branko@brankovukelic.com',
    description='Translations for Django models',
    url='https://bitbucket.org/Lacrymology/django-i18n-model',
    download_url='https://bitbucket.org/Lacrymology/django-i18n-model/downloads',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Framework :: Django',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
    ]
)
