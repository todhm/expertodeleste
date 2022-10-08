import asyncio
import json
from typing import Dict, List, Literal, Set
import re

import aiohttp
from flask import current_app

from models.product_data import ProductData
from dataparser.htmlparser import HtmlParserDao
from dataparser.func import async_retries
from dataparser.strings import split_by_string_length


def check_any_korean(korean: str):
    hangul = re.compile('[가-힣]+')
    return hangul.search(korean) is not None


class TranslationDao(object): 

    def __init__(self, origin_language: str = 'ko', target_language: str = "es"):
        self.translation_map: Dict = {}
        self.translator_url: str = current_app.config['CLOUDRUN_API_URL']
        self.origin = origin_language
        self.target = target_language
        check_func_map = {
            'ko': check_any_korean
        }
        self.check_func = check_func_map[self.origin]

    def make_translation_list(self, product_data: ProductData, description_dao: HtmlParserDao) -> Set[str]:
        translation_list = set()
        translation_list.add(product_data.goodsName)
        translation_list = translation_list.union(set(description_dao.extract_html_words()))
        return translation_list


    async def update_translation_map(
        self,
        text_list: Set[str] = [],
        error_save_method: Literal['json', 'file'] = 'json'
    ) -> None:
        text_list = text_list - set(self.translation_map.keys())
        text_list = list(text_list)
        text_list = [x for x in text_list if self.check_func(x)]
        new_text_list = [x.replace(u'\xa0', ' ') for x in text_list]
        request_list = split_by_string_length(new_text_list, limit_size=1500)
        data_list = [self.async_papago_translation_call(
            text_list=request_data,
            error_save_method=error_save_method
        ) for request_data in request_list]
        result_list = []
        translation_results = await asyncio.gather(
            *data_list
        )
        for tr in translation_results:
            result_list.extend(tr)
        new_map = {key: val for (key, val) in zip(text_list, result_list)}
        self.translation_map.update(new_map)

    @async_retries(5)
    async def async_papago_translation_call(
        self,
        text_list: List[str] = [],
        error_save_method: Literal['json', 'file'] = 'json'
    ):
        async with aiohttp.ClientSession() as s:
            url = f"{self.translator_url}/translate_papago"
            text_list = [text.replace('\n', ' ') for text in text_list]
            async with s.post(
                url,
                json={
                    'original_list': text_list,
                    'language': self.origin,
                    'targetLanguage': self.target,
                    'errorFetchMethod': error_save_method,
                }
            ) as resp:
                result_string = await resp.read()
                if resp.status != 200:
                    if error_save_method == 'file':
                        with open("error.png", "wb") as f:
                            f.write(result_string)
                            raise ValueError("Check image")
                    raise ValueError(f"{text_list} {result_string}")
                data_json = json.loads(result_string)
                return data_json

    async def translate_product(self, product_data: ProductData):
        hpd = HtmlParserDao(product_data.description)
        translation_list = self.make_translation_list(product_data, hpd)
        await self.update_translation_map(
            translation_list,
        )
        product_data.goodsName = self.translation_map.get(product_data.goodsName, product_data.goodsName)
        product_data.description = hpd.translate_goods_detail(self.translation_map)
