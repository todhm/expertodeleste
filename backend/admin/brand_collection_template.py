from flask import flash
from flask_admin.babel import gettext
from flask_admin.model.fields import InlineFormField
from flask_admin.contrib.mongoengine import (
    ModelView,
)
import lxml.html as LH
from flask_admin.contrib.mongoengine.helpers import format_error
from bs4 import BeautifulSoup

from .forms import BrandTemplateForm
from .fields import NewInlineFieldList
from dataparser.htmlparser import create_brand_collection_html


class BrandCollectionTemplateView(ModelView):

    column_list = ('brandName', 'brandLogo')
    
    def update_model(self, form, model):
        try:
            total_html = ""
            with open('templates/brandcollectionstyle.css') as f:
                style_css = f.read()
            total_html += f"<style>{style_css}</style>"
            for dataobj in form.templatePairList.data:
                if dataobj.get('image'):
                    soup = BeautifulSoup(dataobj['image'], 'html.parser')
                    imgtag = soup.find('img')
                    img = None
                    if imgtag:
                        img = imgtag['src']
                    text = dataobj.get('text')
                    total_html += create_brand_collection_html(text, img)
            model.brandDescription = total_html
            model.brandId = str(model.brandId)
            model.save()
        except Exception as ex:
            if not self.handle_view_exception(ex):
                flash(gettext('Failed to create record. %(error)s',
                              error=format_error(ex)),
                      'error')
            return False
        else:
            self.after_model_change(form, model, True)
        
        return model



    def on_form_prefill(self, form, id):
        brand_data = self.get_one(id)
        super().on_form_prefill(form, id)

        # option image list와 ocr이미지 순서 일치화
        brandDescription = brand_data.brandDescription
        try:
            root = LH.fromstring(brandDescription)
            elems = root.xpath('//div[@class="brand-description-row"]')
        except Exception:
            elems = []
        form_data_list = []
        if elems:
            for elem in elems:
                imgtag = elem.find('.//img')
                image_src = None
                if imgtag is not None:
                    image_src = imgtag.attrib.get('src')
                    image_src = f'<img src= "{image_src}"/>'
                image_text = elem.text_content()
                form_data_list.append({
                    "image": image_src, 
                    "text": image_text
                })
            form.templatePairList.process(None, form_data_list)
        else:
            form_data_list = [{
                "image": brand_data.brandDescription,
                "text": "",
            }]
            form.templatePairList.process(None, form_data_list)
        
    column_default_sort = ('_id', True)
    form_columns = (
        'templatePairList',
    )
    form_extra_fields = {
        'templatePairList': NewInlineFieldList(
            InlineFormField(BrandTemplateForm, default=None),
            label='템플릿리스트',
            description='템플릿리스트'
        ),
    }

    create_template = 'brandtemplateedit.html'
    edit_template = 'brandtemplateedit.html'
