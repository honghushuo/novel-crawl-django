import requests

from lxml import etree

# url = 'https://www.zjuyc.com/files/13/'
#
# r = requests.get(url)
# page = etree.HTML(r.text)
# cp_list = page.xpath('//td[@class="L"]/a')
# for cp in cp_list:
#     chapter_name = cp.xpath('./@title')[0]
#     chapter_id = cp.xpath('./@href')[0].split('/')[-1].split('.')[0]
#     print(chapter_id, chapter_name)
#
# print(r.text)

# url = 'https://www.zjuyc.com/files/2/19.html'

# r = requests.get(url)
# page = etree.HTML(r.text)
# print(r.text)