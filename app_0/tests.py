# Create your tests here.

# countries_prototype = ['America', 'Canada', 'Brazil', 'China', 'Chile']
#
# # ======== 错误示范 ========
# countries = countries_prototype
# for country in countries:
#     if country.startswith('C'):
#         countries.remove(country)
# print(countries)
#
# # ======== 方法一 ========
# ctr = [c for c in countries if not c.startswith('C')]
# print(ctr)
#
# # ======== 方法二 ========
# countries_copy = countries_prototype
# for country in countries:
#     if country.startswith('C'):
#         countries_copy.remove(country)
# print(countries_copy)

import requests

resp = requests.get('http://www.ujxsw.org/shuku/')

print(resp.text)