import hashlib
import hmac
import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / 'backend' / 'platform_core' / 'services' / 'payments.py'


def load_module():
    spec = importlib.util.spec_from_file_location('payments_under_test', MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class FakeTransport:
    def __init__(self):
        self.calls=[]

    def post(self,url,**kwargs):
        self.calls.append((url,kwargs))
        return {'data':{'id':'provider-object'}}


class FakeStripeWebhook:
    calls=[]

    @classmethod
    def construct_event(cls,payload,signature,secret,tolerance=300):
        cls.calls.append((payload,signature,secret,tolerance))
        return {'id':'evt_verified','type':'checkout.session.completed'}


class FakeStripeSDK:
    Webhook=FakeStripeWebhook


class PaymentAdapterTests(unittest.TestCase):
    def test_stripe_uses_official_construct_event_with_raw_payload(self):
        payments=load_module();payload=b'{"id":"evt_verified"}'
        event=payments.StripeAdapter.parse_webhook(payload,'t=1,v1=signature','whsec_test',sdk=FakeStripeSDK)
        self.assertEqual(event['id'],'evt_verified')
        self.assertEqual(FakeStripeWebhook.calls[-1],(payload,'t=1,v1=signature','whsec_test',300))

    def test_paymongo_signature_is_mode_specific_and_time_bounded(self):
        payments=load_module();payload=b'{}';timestamp=1_700_000_000;secret='whsk_test';digest=hmac.new(secret.encode(),f'{timestamp}.'.encode()+payload,hashlib.sha256).hexdigest();header=f't={timestamp},te={digest},li=wrong'
        self.assertTrue(payments.PayMongoAdapter.verify_signature(payload,header,secret,mode='test',now=timestamp+60))
        self.assertFalse(payments.PayMongoAdapter.verify_signature(payload,header,secret,mode='live',now=timestamp+60))
        self.assertFalse(payments.PayMongoAdapter.verify_signature(payload,header,secret,mode='test',now=timestamp+301))

    def test_paymongo_uses_current_payment_links_contract(self):
        payments=load_module();transport=FakeTransport();payments.PayMongoAdapter('sk_test',transport=transport).create_link(50000,'Annual dues','internal-123',currency='PHP')
        url,request=transport.calls[-1]
        self.assertEqual(url,'https://api.paymongo.com/v1/payment_links')
        self.assertEqual(request['json'],{'amount':50000,'currency':'PHP','description':'Annual dues','remarks':'internal-123','metadata':{'internal_reference':'internal-123'}})

    def test_xendit_uses_v3_versioned_payment_request_and_idempotency(self):
        payments=load_module();transport=FakeTransport();payments.XenditAdapter('xnd_test',transport=transport).create_payment_request('internal-123',500.0,currency='PHP',country='PH')
        url,request=transport.calls[-1]
        self.assertEqual(url,'https://api.xendit.co/v3/payment_requests')
        self.assertEqual(request['headers']['api-version'],'2024-11-11')
        self.assertEqual(request['headers']['Idempotency-key'],'internal-123')
        self.assertEqual(request['json']['request_amount'],500.0)


if __name__ == '__main__':
    unittest.main()
