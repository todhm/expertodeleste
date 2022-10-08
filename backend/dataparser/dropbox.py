import re

import requests
import aiohttp
from bs4 import BeautifulSoup


def parse_img_url_from_dropbox(url: str) -> str:
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    pattern = re.compile(r'function streamPreviewImg.*\((\"https.*)\)', re.MULTILINE | re.DOTALL)
    img_script = soup.find('script', text=pattern)
    result = re.search(pattern,img_script.text)
    for img in result.group(1).split(','):
        if '800w' in img:
            img = re.search(r'(.*size=\d+x\d+)', img).group(1).strip()
            return img
    raise ValueError(f"Error while parse dropbox url {url}")


async def async_parse_img_url_from_dropbox(url: str) -> str:
    async with aiohttp.ClientSession() as s:
        async with s.get(url) as resp:
            response_text = await resp.text()    
    soup = BeautifulSoup(response_text, "html.parser")
    pattern = re.compile(r'function streamPreviewImg.*\((\"https.*)\)', re.MULTILINE | re.DOTALL)
    img_script = soup.find('script', text=pattern)
    result = re.search(pattern,img_script.text)
    for img in result.group(1).split(','):
        if '800w' in img:
            img = re.search(r'(.*size=\d+x\d+)', img).group(1).strip()
            return img
    raise ValueError(f"Error while parse dropbox url {url}")