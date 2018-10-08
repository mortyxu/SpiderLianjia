# -*- coding: utf-8 -*-

# Define here the models for your spider middleware
#
# See documentation in:
# https://doc.scrapy.org/en/latest/topics/spider-middleware.html

'''
设置随机User-Agent
'''

import scrapy
import random
from scrapy.downloadermiddlewares.useragent import UserAgentMiddleware


class MyUserAgentMiddleware(UserAgentMiddleware):

    def __init__(self, agents):
        self.agents = agents

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            agents=crawler.settings.get('USER_AGENTS')
        )

    def process_request(self, request, spider):
        agent = random.choice(self.agents)
        request.headers['User-Agent'] = agent
