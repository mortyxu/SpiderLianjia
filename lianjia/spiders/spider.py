#scrapy爬虫框架
from scrapy import Spider,Request
import re
from lxml import etree
import json
from urllib.parse import quote
from lianjia.items import LianjiaItem

class Lianjia_spider(Spider):
    name = 'lianjia'
    # name, 它是每个项目唯一的名字，用来区分不同的Spider

    allowed_domains = ['nj.lianjia.com']
    # allowed_domains,它是允许爬取的域名，如果初始或后续的请求链接不是这个域名下的，则请求链接会被过滤掉。

    regions = {'gulou': '鼓楼',
               'jianye': '建邺',
               'qinhuai': '秦淮',
               'xuanwu': '玄武',
               'yuhuatai': '雨花台',
               'qixia': '栖霞',
               'jiangning': '江宁',
               'liuhe': '六合',
               'pukou': '浦口',
               'lishui': '溧水',
               'gaochun': '高淳'
               }
    # 南京11个区域

    def start_requests(self):
        # start_requests() 此方法用于生成初始请求，它必须返回一个可迭代对象。

        for region in list(self.regions.keys()):
            url = "https://nj.lianjia.com/xiaoqu/" + region + "/"
            yield Request(url=url, callback=self.parse, meta={'region': region})
            #以行政区为单位，目的是爬取每一个行政区的小区列表。 获取页码。



    def parse(self, response):
        ''' parse() 该方法负责解析返回的响应，提取数据或者进一步生成要处理的请求。
            parse 对行政区返回的response进行解析，我们目的是拿到这个大的行政区，包含多少个页面，其中的
            total_pages就是具体的页面数，接下来就是按照页码请求每一个页面。
        '''
        region = response.meta['region']
        selector = etree.HTML(response.text)
        sel = selector.xpath("//div[@class='page-box house-lst-page-box']/@page-data")[0]
        sel =json.loads(sel)
        total_pages = sel.get("totalPage")


        for i in range(int(total_pages)):
            url_page = "https://nj.lianjia.com/xiaoqu/{}/pg{}/".format(region, str(i + 1))
            yield Request(url=url_page, callback=self.parse_xiaoqu, meta={'region':region})


    def parse_xiaoqu(self, response):
    # parse_xiaoqu 上面返回了每一个页面的信息，这个时候我们就把当前页面的小区列表拿到，而后，在针对小区列表，每一个小区进行一次请求。
        selector = etree.HTML(response.text)
        xiaoqu_list = selector.xpath('ul[@class="listContent"]//li//div[@class="title"]/a/text()')
        for xq_name in xiaoqu_list:
            url = "https://nj.lianjia.com/chengjiao/rs" + quote(xq_name) + "/"
            yield Request(url=url, callback=self.parse_chengjiao, meta={'xq_name':xq_name, \
                                                                                 'region':response.meta['region']})


    def parse_chengjiao(self, response):
    '''
    parse_chengjiao 解析小区的页面数，上面说到了，我们请求了每一个小区数据，这个小区肯定不止包含一页的数据，
    那么我们这个方法就是将这个小区包含的页面数抽取出来，而后针对每一个页面进行请求
    '''
        xq_name = response.meta['xq_name']
        selector = etree.HTML(response.text)
        content = selector.xpath("//div[@class='page-box house-lst-page-box']")
        total_pages = 0
        if len(content):
            page_data = json.loads(content[0].xpath('./@page-data')[0])
            total_pages = page_data.get("totalPage")

        for i in range(int(total_pages)):
            url_page = "https://nj.lianjia.com/chengjiao/pg{}rs{}/".format(str(i+1), quote(xq_name))
            yield Request(url=url_page, callback=self.parse_content, meta={'region': response.meta['region']})


    def parse_content(self, response):
    '''
    parse_content 这个方法就是解析具体的页面了，可以看到，这个方法里面包含了非常多的条件判断，这是因为，我们之前定义的item字段里面的
    信息，并不是每一个小区都有的，就是说，我们要的信息他不是一个规规矩矩的信息，很多的房源没有提供相关的信息，比如地
    铁，周边学校等等的信息，我们这里就是如果有这个信息，我们就把它提取出来，如果没有的话，我们就给他自定义一个内容。
    最后将item提交给item pipeline进行后续的处理。
    '''
        selector = etree.HTML(response.text)
        cj_list = selector.xpath("//ul[@class='listContent']/li")



        for cj in cj_list:
            item = LianjiaItem()
            item['region'] = self.regions.get(response.meta['region'])
            href = cj.xpath('./a/@href')
            if not len(href):
                continue
            item['href'] = href[0]

            content = cj.xpath('.//div[@class="title"]/a/text()')
            if len(content):
                content = content[0].split()
                item['name'] = content[0]
                item['style'] = content[1]
                item['area'] = content[2]

            content = cj.xpath('.//div[@class="houseInfo"]/text()')
            if len(content):
                content = content[0].split('|')
                item['orientation'] = content[0]
                item['decoration'] = content[1]
                if len(content) == 3:
                    item['elevator'] = content[2]
                else:
                    item['elevator'] = '无'

            content = cj.xpath('.//div[@class="positionInfo"]/text()')
            if len(content):
                content = content[0].split()
                item['floor'] = content[0]
                if len(content) == 2:
                    item['build_year'] = content[1]
                else:
                    item['build_year'] = '无'

            content = cj.xpath('.//div[@class="dealDate"]/text()')
            if len(content):
                item['sign_time'] = content[0]

            content = cj.xpath('.//div[@class="totalPrice"]/span/text()')
            if len(content):
                item['total_price'] = content[0]

            content = cj.xpath('.//div[@class="unitPrice"]/span/text()')
            if len(content):
                item['unit_price'] = content[0]

            content = cj.xpath('.//span[@class="dealHouseTxt"]/span/text()')
            if len(content):
                for i in content:
                    if i.find("房屋满") != -1:
                        item['fangchan_class'] = i

                    elif i.find("号线") != -1:
                        item['subway'] = i

                    elif i.find("学") != -1:
                        item['school'] = i

            yield  item










