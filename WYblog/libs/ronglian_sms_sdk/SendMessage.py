import json
from ronglian_sms_sdk import SmsSDK

accId = '2c94887686c00d750186efc4bd470add'
accToken = '73c4db53ed5e40e4b912aeb2f861fa04'
appId = '2c94887686c00d750186efc4be6c0ae4'


def send_message(mobile, datas):
    sdk = SmsSDK(accId, accToken, appId)
    tid = '1'
    resp = sdk.sendMessage(tid, mobile, datas)
    result = json.loads(resp)
    if result["statusCode"] == "000000":
        return 0
    else:
        return -1


if __name__ == '__main__':
    mobile = '18569546920'
    datas = ['1234', '5']
    send_message(mobile, datas)
