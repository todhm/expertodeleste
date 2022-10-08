import subprocess
from typing import Optional, List, Dict

import minify_html
from bs4 import BeautifulSoup, Comment
from bs4.element import Script
from html import escape
import lxml.html as LH
from lxml.html import HtmlElement
from lxml import etree


def create_brand_collection_html(text: str, image: str) -> str:
    if image:
        return f'<div class="brand-description-row"><img class="brand-description-img lazyload" src="{image}"/><p class="brand-row-text">{text}</p></div>'
    else:
        return f'<div class="brand-description-row"><p class="brand-row-text">{text}</p></div>'


def make_inline_style(inline_html: str) -> str:
    temp_html = "datacollections/htmldata/temp.html"
    temp_css = "datacollections/htmldata/temp.css"
    new_temp_css = "datacollections/htmldata/newtemp.css"
    soup = BeautifulSoup(inline_html, "html.parser")
    atag_list = soup.findAll('a')
    for x in atag_list:
        x['href'] = "#!"
    style_list = soup.findAll('style')
    script_list = soup.findAll('script')
    for script in script_list:
        script.decompose()
    style_string = ""
    for style in style_list:
        for content in style.contents:
            style_string += content
        style.decompose()
    if style_string:
        with open(temp_css, 'w') as f:
            f.write(style_string)
        inline_html = str(soup)
        with open(temp_html, 'w') as f:
            f.write(inline_html)
        subprocess.call(["purgecss", "--css", temp_css, "--content", temp_html, '--output', new_temp_css])
        # subprocess.call(["purifycss", temp_css, temp_html, '--min', '--rejected', '--out', new_temp_css])
        print(["purifycss", temp_css, temp_html, '--min', '--rejected', '--out', new_temp_css])
        with open(new_temp_css) as f:
            new_css = f.read()
        inline_html = f"<style>{new_css}</style>{inline_html}"
    return escape(
        minify_html.minify(
            inline_html,
            minify_js=True,
            minify_css=True, 
            remove_processing_instructions=True,
            do_not_minify_doctype=False,
            keep_spaces_between_attributes=False,
            keep_comments=False
        )
    )


def create_inner_product_description(title: str, text: Optional[str] = None, image: Optional[str] = None, use_img: bool = True) -> str:
    if use_img:
        htmlstring = f'''
        <div class="feature-grid--item">
            <img class="lazyload" src="{image}" alt="Product Features">
            <div>
            <h4 class="product-description-title">{title}</h4>
            <p>{text}</p>
            </div>
        </div>
        '''
    else:
        htmlstring = f'''
        <div class="feature-grid--item">
            {image}
            <div>
            <h4 class="product-description-title">{title}</h4>
            <p>{text}</p>
            </div>
        </div>
        '''
    return htmlstring


def create_header_description_html(description: str, feature_list: List[str] = []) -> str:
    feature_list = [f'<li class="description-feature-list">{x}</li>' for x in feature_list]
    feature_string = ''.join(feature_list)
    htmlstring = f'''
        <div class="featured__product">
            <div class="featured_product-description txtArea">
                <div class="module">
                {description}
                </div>
                <ul class="description-feature-wrapper">
                {feature_string}
                </ul>
            </div>
        </div>
    '''
    return htmlstring


def create_inner_product_description_v2(title: str, idx: int, text: Optional[str] = None, image: Optional[str] = None) -> str:
    left_right_string = "left" if idx % 2 == 0 else "right"
    text_div_elem = f'''
    <div class="bagsFeaturesGrid__feature--text {left_right_string}">
        <h1>{title}</h1>
        <p>{text}</p>
    </div>
    '''
    image_div_elem = f'''
    <div class="bagsFeaturesGrid__feature--image">
        <img class="lazyload" src="{image}" sizes="(min-width:1457px) 575px, (min-width:811px) 40vw, 100vw" loading="lazy">      	
        <div class="bagsFeaturesGrid__feature--image--logo"></div>
    </div>
    '''
    total_html = (
        f'<div class="bagsFeaturesGrid__feature">{text_div_elem}{image_div_elem}</div>' 
        if left_right_string == 'left' else 
        f'<div class="bagsFeaturesGrid__feature">{image_div_elem}{text_div_elem}</div>'
    )
    return total_html


def check_string_text(textelem: str) -> bool:
    if isinstance(textelem, Comment) or isinstance(textelem, Script):
        return False
    if str(textelem) == '\u200b':
        return False
    if '<!--' in textelem and '!-->' in textelem:
        return False
    if not textelem.strip():
        return False
    return True


class HtmlParserDao(object):

    def __init__(self, description: str):
        self.root: HtmlElement = LH.fromstring(description)
        self.soup: BeautifulSoup = BeautifulSoup(description, 'html.parser')

    def return_matched_string_list(self, xpath: str, elem: Optional[HtmlElement] = None) -> List[str]:
        if elem:
            li_list = elem.xpath(xpath)
        else:
            li_list = self.root.xpath(xpath)
        if li_list:
            return [x.text_content() for x in li_list]
        return []

    def return_matched_text(self, elem: HtmlElement, xpath: str) -> str:
        titletag = elem.find(xpath)
        return titletag.text_content()

    def return_matched_html_elems(self, xpath: str) -> List[HtmlElement]:
        return self.root.xpath(xpath)

    def return_matched_html_elem(self, xpath: str) -> Optional[HtmlElement]:
        html_elems =  self.root.xpath(xpath)
        if html_elems:
            return html_elems[0]
        return None
    
    def return_matched_html_elem_html_string(self, xpath: str, elem: Optional[HtmlElement] = None) -> str:
        if elem:
            html_elems = elem.xpath(xpath)
        else:
            html_elems = self.root.xpath(xpath)
        if html_elems:
            return etree.tostring(html_elems[0], pretty_print=True).decode('utf-8')
        return ""
    
    def xpath(self, xpath: str) ->List[HtmlElement]:
        return self.root.xpath(xpath)

    def return_image_html(self, elem: HtmlElement) -> Optional[str]:
        imgtag = elem.find('.//img')
        svgtag = elem.find('.//svg')
        if imgtag is not None:
            image_src = imgtag.attrib.get('src')
            image_html = f'<img src= "{image_src}"/>'
        if svgtag:
            image_html = etree.tostring(svgtag, pretty_print=True).decode('utf-8')
        return image_html


    def extract_html_words(self) -> List[str]:
        textelems = self.soup.findAll(text=True)
        textelems = list(filter(check_string_text, textelems))
        return textelems

    def extract_html_image_list(self) -> List[str]:
        url_list = []
        img_list = self.soup.findAll('img')
        for img_tag in img_list:
            url_list.append(img_tag['src'])
        return url_list

    def change_image_description(self, image_translation_map: Dict) -> str:
        img_list = self.soup.findAll('img')
        for img_tag in img_list:
            img_tag['src'] = image_translation_map.get(
                img_tag.get('src'),
                img_tag.get('src')
            )
        return str(self.soup.prettify()).replace("\\", "")

    def translate_goods_detail(self, translation_map: Dict) -> str:
        textelems = self.extract_html_words()
        for text_elem in textelems:
            if str(text_elem).strip() and not isinstance(text_elem, Comment):
                if translation_map.get(str(text_elem)):
                    text_elem.replace_with(
                        translation_map[str(text_elem)]
                    )
        return str(self.soup.prettify()).replace("\\", "")