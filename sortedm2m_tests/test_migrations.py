# -*- coding: utf-8 -*-
import os
import sys
import shutil

# Python 2 support.
if sys.version_info < (3,):
    from StringIO import StringIO
else:
    from io import StringIO

import django
# Django 1.5 support.
if django.VERSION >= (1, 6):
    from django.db.utils import OperationalError, ProgrammingError
from django.core.management import call_command
from django.test import TestCase
from django.utils import six
from django.utils.unittest import skipIf

from sortedm2m_tests.migrations_tests.models import Gallery, Photo


str_ = six.text_type


@skipIf(django.VERSION < (1, 7), 'New migrations framework only available in Django >= 1.7')
class TestMigrateCommand(TestCase):
    def setUp(self):
        sys.stdout = StringIO()
        self.orig_stdout = sys.stdout

    def tearDown(self):
        sys.stdout = self.orig_stdout

    def test_migrate(self):
        call_command('migrate', interactive=False)


@skipIf(django.VERSION < (1, 7), 'New migrations framework only available in Django >= 1.7')
class TestMigrations(TestCase):
    def setUp(self):
        sys.stdout = StringIO()
        self.orig_stdout = sys.stdout

        self.migrations_path = os.path.join(os.path.dirname(__file__),
                                            'migrations_tests',
                                            'django17_migrations')

        # Roll back all migrations to be sure what we test against.
        call_command('migrate', 'migrations_tests', 'zero')
        call_command('migrate', 'migrations_tests', '0001')

    def tearDown(self):
        sys.stdout = self.orig_stdout

        # Remove created migrations.
        if os.path.exists(self.migrations_path):
            for filename in os.listdir(self.migrations_path):
                if filename not in ('__init__.py',
                                    '0001_initial.py',
                                    '0002_data_migration.txt'):
                    filepath = os.path.join(self.migrations_path, filename)
                    if os.path.isdir(filepath):
                        shutil.rmtree(filepath)
                    else:
                        os.remove(filepath)

    def test_data_migration(self):
        '''Test the AlterSortedManyToManyField operation'''

        p1 = Photo.objects.create(name='A')
        p1.save()
        p2 = Photo.objects.create(name='C')
        p2.save()
        p3 = Photo.objects.create(name='B')
        p3.save()
        p4 = Photo.objects.create(name='D')
        p4.save()
        p5 = Photo.objects.create(name='E')
        p5.save()

        gallery = Gallery.objects.create(name='Gallery')
        gallery.photos3 = [p3, p1, p2]
        gallery.save()

        self.assertEqual(gallery.photos3.count(), 3)

        # Simulate updating the model
        models_path = os.path.join(os.path.dirname(__file__), 'migrations_tests')
        shutil.copy(os.path.join(models_path, 'models.py'),
                    os.path.join(models_path, 'models.py.bak'))

        shutil.copy(os.path.join(models_path, 'models2.txt'),
                    os.path.join(models_path, 'models.py'))

        shutil.copy(os.path.join(self.migrations_path, '0002_data_migration.txt'),
                    os.path.join(self.migrations_path, '0002_data_migration.py'))
        call_command('makemigrations', 'migrations_tests')

        #shutil.move(os.path.join(models_path, 'models.py.bak'),
        #            os.path.join(models_path, 'models.py'))
        call_command('migrate')

        # TODO: test data order after migration
        gallery.photos3.add(p4)
        gallery.photos3.add(p5)

        shutil.move(os.path.join(models_path, 'models.py.bak'),
                    os.path.join(models_path, 'models.py'))

    def test_defined_migration(self):
        photo = Photo.objects.create(name='Photo')
        gallery = Gallery.objects.create(name='Gallery')
        # photos field is already migrated.
        self.assertEqual(gallery.photos.count(), 0)
        # photos2 field is not yet migrated.
        self.assertRaises((OperationalError, ProgrammingError), gallery.photos2.count)

    def test_make_migration(self):
        call_command('makemigrations', 'migrations_tests')
        call_command('migrate')

        gallery = Gallery.objects.create(name='Gallery')
        self.assertEqual(gallery.photos.count(), 0)
        self.assertEqual(gallery.photos2.count(), 0)

    def test_stable_sorting_after_migration(self):
        call_command('makemigrations', 'migrations_tests')
        call_command('migrate')

        p1 = Photo.objects.create(name='A')
        p2 = Photo.objects.create(name='C')
        p3 = Photo.objects.create(name='B')

        gallery = Gallery.objects.create(name='Gallery')
        gallery.photos = [p1, p2, p3]
        gallery.photos2 = [p3, p1, p2]

        gallery = Gallery.objects.get(name='Gallery')

        self.assertEqual(list(gallery.photos.values_list('name', flat=True)), ['A', 'C', 'B'])
        self.assertEqual(list(gallery.photos2.values_list('name', flat=True)), ['B', 'A', 'C'])

        gallery.photos = [p3, p2]
        self.assertEqual(list(gallery.photos.values_list('name', flat=True)), ['B', 'C'])

        gallery = Gallery.objects.get(name='Gallery')
        self.assertEqual(list(gallery.photos.values_list('name', flat=True)), ['B', 'C'])
