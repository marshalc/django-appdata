from django.contrib.auth.models import User

import pytest

from .models import Article, Author
from .cases import AppDataTestCase


class TestAppDataAdmin(AppDataTestCase):

    def setUp(self):
        super(TestAppDataAdmin, self).setUp()
        self.url = '/admin/test_app_data/article/'
        User.objects.create_superuser('admin', 'admin@example.com', 'secret')
        self.client.login(username='admin', password='secret')

    def test_admin_can_create_article(self):
        response = self.client.post(self.url + 'add/', {
            'publish-publish_from': '2010-10-10',
            'rss-title': 'Hullo!',
            'rss-author': 'Me and Myself',

            'author_set-INITIAL_FORMS': '0',
            'author_set-TOTAL_FORMS': '0',
        })
        assert response.status_code == 302
        assert Article.objects.count() == 1
        art = Article.objects.all()[0]
        assert art.app_data == {
                u'publish': {
                    u'publish_from': u'2010-10-10 00:00:00',
                    u'published': False
                },
                u'rss': {
                    u'title': u'Hullo!',
                    u'author': u'Me and Myself'
                }
            }

    def test_admin_can_create_article_with_inlines(self):
        response = self.client.post(self.url + 'add/', {
            'publish-publish_from': '2010-10-10',
            'rss-title': 'Hullo!',
            'rss-author': 'Me and Myself',

            'author_set-INITIAL_FORMS': '0',
            'author_set-TOTAL_FORMS': '1',

            'author_set-0-personal-first_name': 'Johnny',
            'author_set-0-personal-last_name': 'Mnemonic',
        })
        assert response.status_code == 302
        assert Article.objects.count() == 1
        art = Article.objects.all()[0]
        assert Author.objects.count() == 1
        author = Author.objects.all()[0]
        assert author.publishable_id == art.id
        assert author.app_data == {
                u'personal': {
                    u'first_name': u'Johnny', u'last_name': u'Mnemonic'
                }
            }

    def test_admin_can_render_multiform(self):
        response = self.client.get(self.url + 'add/')
        assert response.status_code == 200
