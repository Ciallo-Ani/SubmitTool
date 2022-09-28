# coding=UTF-8

import os
import multiprocessing
import time
import json
import base64
import requests

from flask import Flask
from flask import abort

app = Flask(__name__)
public_address = "0.0.0.0"


@app.route('/')
def home():
    return "hello world"


@app.route('/qrcode_src/', methods=['GET'])
def request_qrcode_src():
    if os.path.isfile('qr.jpg'):
        with open('qr.jpg', "rb") as file:
            file.seek(0, 0)
            return file.read()
    abort(404)


@app.route('/qrcode/', methods=['GET'])
def request_qrcode():
    link = "<html>" \
       "<head><title>微信扫码登录</title></head>" \
       "<body>" \
       "<img src='http://112.74.41.91:5000/qrcode_src/'>" \
       "</body>" \
       "</html>"

    return link


class SubmitTool:
    def __init__(self, eid, access_token):
        self.extra_info, self.req_info = {}, []
        self.main_url = 'https://api-xcx-qunsou.weiyoubot.cn'
        self.access_token = access_token
        self.eid = eid

    # 获取用户已保存数据(extra_info)
    def get_user_info(self):
        get_user_info_url = self.main_url + '/xcx/enroll/v1/userinfo?access_token=' + self.access_token
        user_info = json.loads(requests.get(get_user_info_url).text)
        for i in user_info['data']['extra_info']:
            self.extra_info[i['name']] = i['value']

    # 获取需要提交的数据并制作提交的字典(req_info)
    def get_info(self):
        get_info_url = self.main_url + '/xcx/enroll/v2/detail?eid=' + self.eid + '&access_token=' + self.access_token \
                       + '&admin=0&from=detail&referer= '
        info = json.loads(requests.get(get_info_url).text)  # 获取提交的数据
        for i in info['data']['req_info']:
            if i['field_name'] in self.extra_info:
                self.req_info.append({"field_name": i['field_name'], "field_value": self.extra_info[i['field_name']],
                                      "field_key": i["field_key"]})
            else:
                print(i['field_name'] + '已提交为123456789，请后续自行更改内容')
                tmp = '123456789'
                # tmp = input('请输入' + i['field_name'] + '：')
                self.req_info.append({"field_name": i['field_name'], "field_value": tmp, "field_key": i["field_key"]})
        if self.req_info:
            return True
        else:
            return False

    # 提交数据(req_info)
    def post(self):
        post_url = self.main_url + '/xcx/enroll/v5/enroll'
        body = {"access_token": self.access_token, "eid": self.eid, "info": self.req_info,
                "on_behalf": 0, "items": [], "referer": "", "fee_type": ""}
        return_info = json.loads(requests.post(post_url, json=body).text)
        if not return_info['sta']:  # 提交成功返回的sta为0，不成功为-1
            print('提交成功')
            return True
        else:
            if return_info['msg'] == '提交次数超过限制':  # 超过限制为已提交，不需要再次运行
                print('提交次数超过限制')
                return True
            else:
                print('提交失败，返回信息：' + return_info['msg'])
                return False

    # 类主入口
    def main(self):
        self.get_user_info()
        while True:
            if self.get_info():  # 判断获取需要提交的数据是否为空(未开始的数据为空)
                if not self.post():  # 不为空就进行提交，若提交成功或超过限制则结束，否则再次获取需要提交的数据并进行提交
                    continue
                break
            else:
                print('报名未开始')


class GetToken:
    def __init__(self):
        self.qr_url = 'https://api-xcx-qunsou.weiyoubot.cn/xcx/enroll_web/v1/pc_code'
        self.login_url = 'https://api-xcx-qunsou.weiyoubot.cn/xcx/enroll_web/v1/pc_login?code='

    # 通过qr码方式登录
    def get_token_qr(self):
        result = json.loads(requests.get(self.qr_url).text)  # 获取qr码及对应code
        code = result['data']['code']
        img = result['data']['qrcode'][22:]
        with open('qr.jpg', 'wb') as f:
            f.write(base64.b64decode(img))  # 写入qr码以便打开图片
        print('使用微信扫码登录, 请将连接复制到浏览器: http://{}:5000/qrcode/'.format(public_address))
        time.sleep(10)
        # os.system('start qr.jpg')
        while True:  # 循环判断登录是否成功，未登录sta为-1，登录成功为0并返回access_token
            login_data = json.loads(requests.get(self.login_url + code).text)
            if not login_data['sta']:
                myToken = login_data['data']['access_token']
                print("token -> " + myToken)
                return myToken
            print('等待登录...')
            time.sleep(5)

    # 通过手机号及密码方式登录
    @staticmethod
    def get_token_phone(phone, password):
        url = 'https://api-xcx-qunsou.weiyoubot.cn/xcx/enroll/v1/login_by_phone'
        data = {"phone": phone, "password": password}
        return json.loads(requests.post(url, json=data).text)['data']['access_token']

    # 类主入口
    def main(self):
        # 登录
        # token = self.get_token_phone('phone', 'password')
        token = self.get_token_qr()
        #token = "9d5c1c24d8d241d69f114514b5b34bdd"
        # 获取个人历史记录
        get_history_url = 'https://api-xcx-qunsou.weiyoubot.cn/xcx/enroll/v1/user/history?access_token=' + token
        result = json.loads(requests.get(get_history_url).text)
        history_data = []
        for i in result['data']:
            if i['status'] < 2:  # status状态码：0(未开始) 1(进行中) 2(已截至)
                history_data.append({'name': i['title'], 'status': '进行中' if i['status'] else '未开始', 'eid': i['eid']})

        if not history_data:
            print('请将需要提交的报名添加到个人记录中再运行程序')
            exit()
        else:
            print('请选择需要提交的表单序号')

        for i in range(len(history_data)):
            print('序号：' + str(i + 1) + '\t\t' + '名称：' + history_data[i]['name'] + '\t\t' + '状态：' + history_data[i][
                'status'])

        user_input = input('请输入序号：')
        error = True
        while error:
            try:
                user_input = int(user_input)
                error = False
            except ValueError as e:
                user_input = input('请输入正确的序号：')
                error = True

        if user_input <= len(history_data):
            run = SubmitTool(history_data[user_input - 1]['eid'], token)  # 选择eid并进行提交
            run.main()
        else:
            print('请输入正确的序号')
            exit()


def doSubmit():
    main = GetToken()
    main.main()
    os.remove('qr.jpg')
    input('按回车退出...')


def doBackend():
    app.run(host='0.0.0.0', port=5000, debug=False)


def getPublicIPAddress(url):
    return requests.get(url).text


# 主入口
if __name__ == '__main__':
    p1 = multiprocessing.Process(target=doBackend)
    p1.start()

    public_address = getPublicIPAddress('https://api.ipify.org')

    time.sleep(0.2)

    print("")
    print("====================")
    print("====================")
    print("====================")
    print("")

    time.sleep(0.8)

    doSubmit()
    p1.terminate()