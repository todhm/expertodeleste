import traceback 

from flask import flash
from flask_admin.babel import gettext
from flask_admin.model.fields import InlineFormField
from flask_admin.contrib.mongoengine import (
    ModelView,
)
import lxml.html as LH
from lxml import etree
from flask_admin.contrib.mongoengine.helpers import format_error
from bs4 import BeautifulSoup
from wtforms.fields import StringField
from flask_admin.model.fields import InlineFieldList
from flask_ckeditor import CKEditorField
from mongoengine import get_db

from shopify_dao.product import ProductDao
from shopify_dao.shop_app import create_shopify_app
from .forms import DescriptionTemplateForm
from .fields import NewInlineFieldList
from dataparser.htmlparser import (
    create_inner_product_description,
    create_header_description_html,
    create_inner_product_description_v2,
    HtmlParserDao
)
from models.product_data import ProductData


class DescriptionTemplateView(ModelView):

    column_list = ('productId', "goodsUrl", 'goodsName')
    column_filters = ('productId', 'goodsName', 'brandName')

    def update_model(self, form, model):
        try:
            style_string = ""
            base_html = ""
            if model.featureList or form.longDescription.data:
                base_html = create_header_description_html(
                    form.longDescription.data,
                    model.featureList
                )
            feature_img_html = ""
            inner_html_string = ""
            for dataobj in form.templatePairList.data:
                if dataobj.get('image'):
                    soup = BeautifulSoup(dataobj['image'], 'html.parser')
                    imgtag = soup.find('img')
                    img = None
                    use_img = True
                    if imgtag:
                        img = imgtag['src']
                    if not img:
                        img = str(soup.find('svg'))
                        use_img = False
                    inner_html_string += create_inner_product_description(
                        dataobj.get('title'),
                        dataobj.get('text'),
                        img,
                        use_img
                    )
            with open('templates/product-template.css') as f:
                style_css = f.read()
                style_string = f"<style>{style_css}</style>"
            if inner_html_string:
                feature_img_html = f'''
                <section class="product__features-section">
                    <div class="feature-grid">
                    {inner_html_string}
                    </div>
                </section>
                '''
            if feature_img_html or base_html:
                model.description = style_string + base_html + feature_img_html
            if model.shopifyId:
                product_data = ProductData(**model.to_json)
                db = get_db()
                shop = create_shopify_app()
                product_dao = ProductDao(shop, db)
                product_dao.upsert_product(
                    product_data,
                    selected_keys=["descriptionHtml"],
                    update_mongo=False,
                    update_meta=False
                )
            model.brandData.brandId = str(model.brandData.brandId)
            if model.upcCode:
                model.upcCode = str(model.upcCode)
            for x in model.goodsMustInfo:
                for idx, y in enumerate(x.valueList):
                    x.valueList[idx] = str(y)
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
        goods_data = self.get_one(id)
        super().on_form_prefill(form, id)
        try:
            htmldao = HtmlParserDao(goods_data.description)
            feature_image_list = htmldao.xpath('//section[@class="product__features-section"]/div[@class="feature-grid"]/div[@class="feature-grid--item"]')
            form_data_list = []
            for elem in feature_image_list:                
                image_src = htmldao.return_image_html(elem)
                text = htmldao.return_matched_text(elem, './/p')
                title = htmldao.return_matched_text(elem, './/h4')
                form_data_list.append({
                    "image": image_src, 
                    "text": text,
                    "title": title
                })
            form.templatePairList.process(None, form_data_list)
            header_html_elem = htmldao.return_matched_html_elem('//div[@class="featured__product"]/div[@class="featured_product-description txtArea"]')
            if header_html_elem:
                description_string = htmldao.return_matched_html_elem_html_string('.//div[@class="module"]', header_html_elem)
                header_html_elem.xpath('.//div[@class="module"]')
                form.longDescription.process(None, description_string)
            if not header_html_elem and not form_data_list:
                form.longDescription.process(None, goods_data.description)
        except Exception:
            print(traceback.format_exc())
            form.longDescription.process(None, goods_data.description)

        
    column_default_sort = ('_id', True)
    form_columns = (
        "longDescription",
        "featureList",
        'templatePairList',
    )
    form_extra_fields = {
        'templatePairList': NewInlineFieldList(
            InlineFormField(DescriptionTemplateForm, default=None),
            label='템플릿리스트',
            description='템플릿리스트'
        ),
        "longDescription": CKEditorField()

    }

    create_template = 'descriptiontemplateedit.html'
    edit_template = 'descriptiontemplateedit.html'


class DescriptionNewTemplateView(DescriptionTemplateView):

    column_list = ('productId', "goodsUrl", 'goodsName')
    column_filters = ('productId', 'goodsName', 'brandName')

    # https://ko.bellroy.com/products/hide-and-seek-premium/leather_lo/darkwood#slide-0 style 
    def update_model(self, form, model):
        try:
            style_string = ""
            base_html = ""
            model.featureList = form.featureList.data
            if model.featureList or form.longDescription.data:
                base_html = create_header_description_html(
                    form.longDescription.data,
                    model.featureList
                )
            feature_img_html = ""
            inner_html_string = ""
            for idx, dataobj in enumerate(form.templatePairList.data):
                if dataobj.get('image'):
                    soup = BeautifulSoup(dataobj['image'], 'html.parser')
                    imgtag = soup.find('img')
                    img = None
                    if imgtag:
                        img = imgtag['src']
                    if not img:
                        img = str(soup.find('svg'))
                    inner_html_string += create_inner_product_description_v2(
                        dataobj.get('title'),
                        idx,
                        dataobj.get('text'),
                        img,
                    )
            inner_style_string = ""
            with open('templates/product-template.css') as f:
                inner_style_string += f.read()
            with open('templates/product-template-v2.css') as f:
                inner_style_string += f.read()
            style_string = f"<style>{inner_style_string}</style>"
            if inner_html_string:
                feature_img_html = f'''
                <div class="bagsFeaturesGrid">
                    <div class="bagsFeaturesGrid__gridWrapper">
                    {inner_html_string}
                    </div>
                </div>
                '''
            if feature_img_html or base_html:
                model.description = style_string + base_html + feature_img_html
            product_data = ProductData(**model.to_json)
            if product_data.shopifyId:
                db = get_db()
                shop = create_shopify_app()
                product_dao = ProductDao(shop, db)
                product_dao.upsert_product(
                    product_data,
                    selected_keys=["descriptionHtml"],
                    update_mongo=False,
                    update_meta=False
                )
            model.brandData.brandId = str(model.brandData.brandId)
            if model.upcCode:
                model.upcCode = str(model.upcCode)
            for x in model.goodsMustInfo:
                for idx, y in enumerate(x.valueList):
                    x.valueList[idx] = str(y)
            model.save()
        except Exception as ex:
            print(traceback.format_exc())
            if not self.handle_view_exception(ex):
                flash(gettext('Failed to create record. %(error)s',
                              error=format_error(ex)),
                      'error')
            return False
        else:
            self.after_model_change(form, model, True)
        
        return model

    def on_form_prefill(self, form, id):
        goods_data = self.get_one(id)
        super().on_form_prefill(form, id)
        try:
            root = LH.fromstring(goods_data.description)
            feature_image_list = root.xpath('//div[@class="bagsFeaturesGrid__feature"]')
            form_data_list = []
            for elem in feature_image_list:
                imgtag = elem.find('.//img')
                svgtag = elem.find('.//svg')
                texttag = elem.find('.//p')
                titletag = elem.find('.//h1')
                image_src = None
                if imgtag is not None:
                    image_src = imgtag.attrib.get('src')
                    image_src = f'<img src= "{image_src}"/>'
                if svgtag:
                    image_src = etree.tostring(svgtag, pretty_print=True).decode('utf-8')
                text = texttag.text_content()
                title = titletag.text_content()
                form_data_list.append({
                    "image": image_src, 
                    "text": text,
                    "title": title
                })
            if not form_data_list:
                for img in goods_data.mainImageList:
                    image_src = f'<img src= "{img}"/>'
                    form_data_list.append({
                    "image": image_src, 
                        "text": "",
                        "title": ''
                    })
            form.templatePairList.process(None, form_data_list)
            header_html_elem = root.xpath('//div[@class="featured__product"]/div[@class="featured_product-description txtArea"]')
            if header_html_elem:
                header_html_elem = header_html_elem[0]
                description_elem = header_html_elem.xpath('.//div[@class="module"]')
                if description_elem:
                    description_elem = description_elem[0]
                    form.longDescription.process(None, etree.tostring(description_elem, pretty_print=True).decode('utf-8'))
            if not header_html_elem and not form_data_list:
                form.longDescription.process(None, goods_data.description)
        except Exception:
            form.longDescription.process(None, goods_data.description)

