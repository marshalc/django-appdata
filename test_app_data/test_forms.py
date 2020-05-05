from datetime import date

from django import forms
from django.forms.models import ModelChoiceField, modelform_factory

from app_data.fields import ListModelMultipleChoiceField
from app_data.forms import multiform_factory, MultiForm, multiformset_factory
from app_data.registry import app_registry
from app_data.containers import AppDataContainer, AppDataForm

import pytest

from .cases import AppDataTestCase
from .models import Article, Category


class TestMultiForm(AppDataTestCase):
    class MyMultiForm(MultiForm):
        pass

    class MyForm(AppDataForm):
        title = forms.CharField(max_length=100)
        publish_from = forms.DateField()
        publish_to = forms.DateField(required=False)
        related_article = ModelChoiceField(queryset=Article.objects.all(), required=False)

    class MyForm2(AppDataForm):
        foo = forms.CharField(max_length=100)

    def setUp(self):
        super(TestMultiForm, self).setUp()
        MyAppContainer = AppDataContainer.from_form(self.MyForm)
        app_registry.register('myapp', MyAppContainer)
        app_registry.register('myapp2', AppDataContainer.from_form(self.MyForm2))

    def test_multi_form_can_work_with_formsets(self):
        FormSet = multiformset_factory(Article, form_opts={'myapp': {}}, exclude=())
        data = {
            'fs-TOTAL_FORMS': '1',
            'fs-INITIAL_FORMS': '0',

            'fs-0-myapp-title': 'First',
            'fs-0-myapp-publish_from': '2010-11-12',
        }
        formset = FormSet(data, prefix='fs')

        assert formset.is_valid()
        formset.save()
        assert Article.objects.count() == 1
        art = Article.objects.all()[0]
        assert art.app_data == {
                'myapp': {
                    'publish_from': '2010-11-12',
                    'publish_to': None,
                    'related_article': None,
                    'title': u'First'
                },
            }

    def test_multi_form_saves_all_the_forms(self):
        MF = multiform_factory(Article, form_opts={'myapp': {}, 'myapp2': {}}, exclude=())
        data = {
            'myapp-title': 'First',
            'myapp-publish_from': '2010-11-12',
            'myapp2-foo': 'Second',
        }
        form = MF(data)
        assert form.is_valid()
        assert form.errors == {}
        art = form.save()
        assert art.app_data == {
                'myapp': {
                    'publish_from': '2010-11-12',
                    'publish_to': None,
                    'related_article': None,
                    'title': u'First'
                },
                'myapp2': {'foo': 'Second'}
            }

    def test_form_can_be_added_to_parent(self):
        MF = multiform_factory(Article, multiform=self.MyMultiForm, exclude=())
        self.MyMultiForm.add_form('myapp', {})
        data = {
            'myapp-title': 'First',
            'myapp-publish_from': '2010-11-12',
        }
        form = MF(data)
        assert form.is_valid()
        assert form.errors == {}
        art = form.save()
        assert art.app_data == {
                'myapp': {
                    'publish_from': '2010-11-12',
                    'publish_to': None,
                    'related_article': None,
                    'title': u'First'
                }
            }

    def test_form_can_be_added(self):
        MF = multiform_factory(Article, exclude=())
        MF.add_form('myapp', {})
        data = {
            'myapp-title': 'First',
            'myapp-publish_from': '2010-11-12',
        }
        form = MF(data)
        assert form.is_valid()
        assert form.errors == {}
        art = form.save()
        assert art.app_data == {
                'myapp': {
                    'publish_from': '2010-11-12',
                    'publish_to': None,
                    'related_article': None,
                    'title': u'First'
                }
            }

    def test_added_form_doesnt_appear_on_parent(self):
        ArticleModelForm = modelform_factory(Article, exclude=())
        class MF(MultiForm):
            ModelForm = ArticleModelForm
        MF.add_form('myapp', {})

        assert MultiForm.app_form_opts == {}

    def test_form_can_be_removed(self):
        MF = multiform_factory(Article, form_opts={'myapp': {}}, exclude=())
        MF.remove_form('myapp')
        data = {
            'myapp-title': 'First',
            'myapp-publish_from': '2010-11-12',
        }
        form = MF(data)
        assert form.is_valid()
        assert form.errors == {}
        art = form.save()
        assert art.app_data =={}


class TestAppDataForms(AppDataTestCase):
    class MyForm(AppDataForm):
        title = forms.CharField(max_length=100)
        publish_from = forms.DateField()
        publish_to = forms.DateField(required=False)
        related_article = ModelChoiceField(queryset=Article.objects.all(), required=False)

    class MyOtherForm(AppDataForm):
        categories = ListModelMultipleChoiceField(Category.objects.all(), required=False)

    def setUp(self):
        super(TestAppDataForms, self).setUp()
        MyAppContainer = AppDataContainer.from_form(self.MyForm)
        app_registry.register('myapp', MyAppContainer)
        self.data = {
            'title': 'First!',
            'publish_from': '2010-10-1'
        }
        MyOtherContainer = AppDataContainer.from_form(self.MyOtherForm)
        app_registry.register('myotherapp', MyOtherContainer)

    def test_empty_list_model_multiple_choice_field(self):
        article = Article()
        assert isinstance(article.app_data.myotherapp.categories, list)
        assert article.app_data.myotherapp.categories == []

    def test_list_model_multiple_choice_field(self):
        c1, c2 = Category.objects.create(), Category.objects.create()

        article = Article()
        data = {'categories': [str(c1.pk), str(c2.pk)]}
        form = article.app_data.myotherapp.get_form(data)
        assert form.is_valid()
        form.save()
        article.save()
        article = Article.objects.get(pk=article.pk)
        assert isinstance(article.app_data.myotherapp.categories, list)
        assert article.app_data.myotherapp.categories == [c1, c2]

    def test_instance_is_accessible_to_the_form(self):
        art = Article()
        form = art.app_data.myapp.get_form(self.data)

        assert art is form.instance

    def test_foreign_keys_can_be_used(self):
        rel = Article.objects.create()
        self.data['related_article'] = str(rel.pk)

        article = Article()
        form = article.app_data.myapp.get_form(self.data)
        assert form.is_valid()
        form.save()
        article.save()
        article = Article.objects.get(pk=article.pk)
        assert article.app_data.myapp.related_article == rel

    def test_current_app_data_will_be_used_as_initial(self):
        article = Article()
        article.app_data = {'myapp': {'title': 'Hello', 'publish_from': '2012-10-10'}}
        form = article.app_data.myapp.get_form()
        assert form.initial == {'title': 'Hello', 'publish_from': '2012-10-10'}

    def test_form_save_alters_data_on_model(self):
        article = Article()
        form = article.app_data.myapp.get_form(self.data)
        assert form.is_valid()
        form.save()
        article.save()
        article = Article.objects.get(pk=article.pk)
        assert article.app_data.myapp.publish_from == date(2010, 10, 1)

    def test_form_with_limitted_fields_only_updates_those(self):
        article = Article()
        form = article.app_data.myapp.get_form(self.data, fields=['title',])
        assert form.is_valid()
        form.save()

        article.save()
        article = Article.objects.get(pk=article.pk)
        assert article.app_data.myapp._data['title'] == 'First!'
        assert not 'publish_from' in article.app_data.myapp._data

