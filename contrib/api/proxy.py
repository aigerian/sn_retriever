__author__ = '4ikist'
import datetime
import time
import urllib2

import requests
#from lxml import html
import properties



log = properties.logger.getChild('proxy')

proxy_list_url = "http://www.ip-adress.com/proxy_list/?k=time&d=desc"
xroxy_list_url = "http://www.xroxy.com/proxylist.php?port=&type=All_http&ssl=ssl&country=&latency=1000&reliability=9000&sort=reliability&desc=true&pnum=%i#table"
ssl_list_url = 'http://www.sslproxies.org/'

ip_check_url = 'https://icanhazip.com/'
user_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:12.0) Gecko/20100101 Firefox/12.0'
timeout = 1


def local_load():
    proxies = []
    try:
        with open(properties.local_proxy_list, 'r') as f:
            for line in f.readlines():
                proxies.append(line.strip())
    except Exception as e:
        log.exception(e)
    log.info("loaded proxies: %s" % len(proxies))
    return proxies


def ssl_load(html=None):
    proxies = []
    s = requests.Session()
    try:
        result = s.get(url=ssl_list_url)
        if result.status_code == 200:
            doc = html.document_fromstring(result.content)
            res_host_elements = doc.xpath('//table[@id="proxylisttable"]//tr/td[1]')
            res_port_elements = doc.xpath('//table[@id="proxylisttable"]//tr/td[2]')
            for i in range(len(res_host_elements)):
                host = res_host_elements[i].text
                port = res_port_elements[i].text
                proxies.append("%s:%s" % (host, port))
    except Exception as e:
        log.exception(e)
    log.info("loaded proxies: %s" % len(proxies))
    return proxies


def simple_load(html=None):
    s = requests.Session()
    proxies = []
    try:
        result = s.get(url=proxy_list_url)
        if result.status_code == 200:
            doc = html.document_fromstring(result.content)
            res_url_element = doc.xpath('//tr[@class!="grey"]/td[1]')
            for el in res_url_element:
                proxy = el.text
                proxies.append(proxy)
    except Exception as e:
        log.exception(e)
    s.close()
    log.info("loaded proxies: %s" % len(proxies))
    return proxies


def xroxy_load(html=None):
    s = requests.Session()
    proxies = []
    for i in range(0, 10):
        try:
            url = xroxy_list_url % i
            result = s.get(url)
            if result.status_code == 200:
                doc = html.document_fromstring(result.content)
                res_host_list = doc.xpath('//tr[@class!="header"]/td[2]/a')
                res_port_list = doc.xpath('//tr[@class!="header"]/td[3]/a')
                for j in range(len(res_host_list)):
                    host = res_host_list[j].text.strip()
                    port = res_port_list[j].text.strip()
                    proxies.append("%s:%s" % (host, port))
        except Exception as e:
            log.exception(e)
    s.close()
    log.info("loaded proxies %s" % len(proxies))
    return proxies


loaders = [ssl_load,
           xroxy_load,
           simple_load,
           local_load
]


def get_real_pip():
    s = requests.Session()
    s.headers = {'User-agent': user_agent}
    res = s.get(ip_check_url)
    page = res.content.strip()
    return page



class ProxyHandler(object):
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(ProxyHandler, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self, lazy=True):
        self._content = set()
        self._current_el = None
        self._used = {}
        self._last_retrieve = None
        self._real_ip = None
        if not lazy:
            self._reload_proxies()

    def _reload_proxies(self):
        log.info("loading proxies")
        while True:
            if not self._last_retrieve or (self._last_retrieve - datetime.datetime.now()) > datetime.timedelta(
                    minutes=1):
                for el in loaders:
                    self._content.update(el())
                log.info('now i have %i proxies' % len(self._content))
                self._last_retrieve = datetime.datetime.now()
                break
            else:
                time.sleep(1 * 60)

    def check_proxy(self, pip):
        try:
            # Build opener
            s = requests.Session()
            s.proxies = {'https': "http://%s" % pip}
            s.headers = {'User-agent': user_agent}

            # Build, time, and execute request
            time_start = time.time()
            res = s.get(ip_check_url, timeout=timeout)
            time_end = time.time()
            detected_pip = res.content.strip()

            # Calculate request time
            time_diff = time_end - time_start

            # Check if proxy is detected
            if not self._real_ip:
                self._real_ip = get_real_pip()
            if detected_pip == self._real_ip:
                proxy_detected = True
            else:
                proxy_detected = False

        # Catch exceptions
        except urllib2.HTTPError as e:
            return (True, False, 999)
        except Exception as detail:
            return (True, False, 999)

            # Return False if no exceptions, proxy_detected=True if proxy detected
        return (False, proxy_detected, time_diff)

    def get_next(self):
        while True:
            if not len(self._content) > 0:
                self._reload_proxies()
            self._current_el = self._content.pop()
            error, detected, time = self.check_proxy(self._current_el)

            if error or detected:
                self._used[self._current_el] = {'touch_time': datetime.datetime.now(), 'status': 'bad'}

            if self._current_el in self._used:
                el_params = self._used[self._current_el]
                if (el_params['touch_time'] - datetime.datetime.now()) > datetime.timedelta(hours=2) \
                    and el_params['status'] == 'good':
                    self._used[self._current_el]['touch_time'] = datetime.datetime.now()
                    break
            else:
                self._used[self._current_el] = {'touch_time': datetime.datetime.now(), 'status': 'good'}
                break
        log.info("now i have proxy: %s" % self._current_el)
        return self._current_el
