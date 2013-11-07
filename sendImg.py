# coding: UTF-8
import urllib2,cookielib,re
import json
import hashlib
from urllib import URLopener
import time

def goodboy(funcname): print "%s finished." % funcname

class WXSender:

    '''
        !!!注意：2013年10月29日更新后不再需要获取微信公众账号fakeid
        登录->获取微信公众账号 fakeid->获取好友 fakeid->向所有好友群发送微信或者向指定好友发送微信
        其中 fakeid 是在网页版微信中用到的参数，可以看作是用户的标识

        `登录过程中，主要是记录 cookie，在之后的通信中都要往 HTTP header 中添加 cookie，否则微信会作「登陆超时」处理，微信后台应该
            是用此 cookie 来作 session 的；另，在返回的 json 中有 token 参数，也需要记录，具体作用还不明，但发现一个现象：当下
            修改 token 为其他值不影响操作，但隔一天使用前一天的 token 则无效
        `获取的好友 fakeid 全在返回页面的 json 中
        `聊天，用 fiddler 抓包，所以手上三件东西就可以聊天了：cookie，fromfakeid 和 tofakeid
    '''

    wx_cookie = ''
    token = ''
    user_fakeid = ''    # 微信公众账号 fakeid
    friend_info = []        # 好友 fakeid

#     def __init__(self):
#         pass

    def login(self,account,pwd):
        # 获取 cookie
        cookies = cookielib.LWPCookieJar()
        cookie_support= urllib2.HTTPCookieProcessor(cookies)

        # bulid a new opener
        opener = urllib2.build_opener(cookie_support, urllib2.HTTPHandler)
        urllib2.install_opener(opener)

        pwd = hashlib.md5(pwd).hexdigest()
        req = urllib2.Request(url = 'https://mp.weixin.qq.com/cgi-bin/login?lang=zh_CN',
                              data = ('username=' + account +
                              '&pwd=' + pwd +
                              '&imgcode='
                              '&f=json'))

        req.add_header("x-requested-with", "XMLHttpRequest")
        req.add_header("referer", "https://mp.weixin.qq.com/cgi-bin/loginpage?t=wxm2-login&lang=zh_CN")
        respond = opener.open(req).read()

        respond_json = json.loads(respond)

        if respond_json['ErrCode'] < 0:
            raise Exception("Login error.")

        s = re.search(r'token=(\d+)', respond_json['ErrMsg'])

        if not s:
            raise Exception("Login error.")

        self.token = s.group(1)

        for cookie in cookies:
            self.wx_cookie += cookie.name + '=' + cookie.value + ';'
#         print 'wx_cookie ',self.wx_cookie
#         print 'token ',self.token

        goodboy(self.login.__name__)


    def get_friend_fakeid(self, num1, num2, grpid):
        if not (self.wx_cookie and self.token):
            raise Exception("Cookies,token or user_fakeid is missing.")

        # 获取 friend fakeid
        base_url = ('https://mp.weixin.qq.com/cgi-bin/contactmanage?t=t=user/index&lang=zh_CN&pagesize=40' +
                    '&type=0&groupid=' + grpid +
                    '&token=' + self.token +
                    '&pageidx=')    # pageidx = ?

        # 这里可以根据微信好友的数量调整，由 base_url 可知一页可以显示 pagesize = 40 人，看实际情况吧。
        for page_idx in xrange(num1,num2):

            url = base_url + str(page_idx)
            req = urllib2.Request(url)
            req.add_header('cookie',self.wx_cookie)
            data = urllib2.urlopen(req).read()
            p = re.compile(r'"id":([0-9]{4,20})')
            res = p.findall(data)

            if not res:
                break

            for id in res:
                self.friend_info.append({"id":id})

        goodboy(self.get_friend_fakeid.__name__)

    def group_sender(self,app_id, appmsgid):
        if not (self.wx_cookie and self.token and self.friend_info):
            raise Exception("Cookies,token or friend_info is missing.")

        '''
        fakeId nickName groupId remarkName
        '''
        url = 'https://mp.weixin.qq.com/cgi-bin/singlesend?t=ajax-response&lang=zh_CN'
        post_data = ('type=10&app_id=%s&appmsgid=%s&error=false&imgcode='
             '&token=%s'
             '&ajax=1&tofakeid=') % (app_id, appmsgid,self.token)   # 图文发送时的信息

        fromfakeid = self.user_fakeid

        for friend in self.friend_info:
            postdata = (post_data + friend["id"]).encode('utf-8')

            req = urllib2.Request(url,postdata)
            req.add_header('cookie',self.wx_cookie)

            # 添加 HTTP header 里的 referer 欺骗腾讯服务器。如果没有此 HTTP header，将得到登录超时的错误。
            req.add_header('referer', ('https://mp.weixin.qq.com/cgi-bin/singlesendpage?t=message/send'
                                   '&token=%s&tofakeid=%s'
                                   '&action=index&lang=zh_CN') % (self.token,friend["id"]))

            # {"ret":"0", "msg":"ok"}
            res = urllib2.urlopen(req).read()
            res_json = json.loads(res)

            if res_json["base_resp"]["ret"] != 0:
                # do something.
                print "A user passed"
                """
                print "finally got"
                i=0
                while(res_json["base_resp"]["ret"]!=0 and i<=2):   #当未发出时，最多等八分钟否则跳过此人
                    time.sleep(10)     #需要输验证码或对方屏蔽发送时，等2分钟再试
                    res = urllib2.urlopen(req).read()
                    res_json = json.loads(res)
                    i=i+1
                    """
            time.sleep(1)   #间隔2s发送防验证码

        goodboy(self.get_friend_fakeid.__name__)

    def run_test(self,account,pwd, num1, num2, grpid):
        # 登录，需要提供正确的账号密码
        self.login(account, pwd)

        # 获取微信好友的所有 fakeid，保存再 self.friend_info 中
        self.get_friend_fakeid(num1, num2, grpid)

        # 群发接口
        self.group_sender("10000072", "10000072")   #此处用于修改图文的app_id和appmsgid

from urllib2 import BaseHandler, build_opener
class HTTPHeaderPrint(BaseHandler):
    def __init__(self):
        pass

    def http_request(self, request):
        print request.headers
        return request

    def http_response(self, request, response):
        print response.info()
        return response

    https_request = http_request
    https_response = http_response

if __name__ == '__main__':
    wxs = WXSender()

    for i in xrange(0,25):   #此处的数字表示在好友列表的翻页数
        wxs.run_test("s_tao16@sina.com","9362716",i,i+1,"105")  #此处数字代表groupId
        time.sleep(10)
        wxs.friend_info=[]




