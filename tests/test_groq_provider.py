from __future__ import annotations
import unittest
import httpx
from src.core.constants import DEFAULT_RETRY_COUNT
from src.core.exceptions import ExternalAPIError
from src.research.providers.groq_provider import GroqProvider
class GroqRetryTests(unittest.IsolatedAsyncioTestCase):
 def provider(self,handler,key="super-secret-groq-key"):
  self.calls=0;self.clients=[]
  def wrapped(request):self.calls+=1;return handler(request)
  def factory(**kwargs):
   client=httpx.AsyncClient(transport=httpx.MockTransport(wrapped),**kwargs);self.clients.append(client);return client
  return GroqProvider(key,"openai/gpt-oss-120b",http_client_factory=factory,sleep=lambda _:self.no_sleep())
 async def no_sleep(self):return None
 def error(self,status,code="error"):
  return httpx.Response(status,json={"error":{"code":code}},request=httpx.Request("POST","https://api.groq.com/openai/v1/chat/completions"))
 async def assert_non_retryable(self,status,code="error"):
  p=self.provider(lambda _:self.error(status,code));
  with self.assertRaises(ExternalAPIError) as caught:await p.generate("Return JSON")
  self.assertEqual(self.calls,1);self.assertIsInstance(caught.exception.__cause__,httpx.HTTPStatusError);self.assertNotIn("super-secret",str(caught.exception));self.assertTrue(all(c.is_closed for c in self.clients))
 async def test_404_model_not_found_one_attempt(self):await self.assert_non_retryable(404,"model_not_found")
 async def test_401_and_403_one_attempt(self):
  for status in (401,403):
   with self.subTest(status=status):await self.assert_non_retryable(status)
 async def test_retryable_statuses_are_bounded(self):
  for status in (429,500,502,503):
   with self.subTest(status=status):
    p=self.provider(lambda _,s=status:self.error(s));
    with self.assertRaises(ExternalAPIError) as caught:await p.generate("Return JSON")
    self.assertEqual(self.calls,DEFAULT_RETRY_COUNT);self.assertIsInstance(caught.exception.__cause__,httpx.HTTPStatusError);self.assertTrue(all(c.is_closed for c in self.clients))
 async def test_timeout_is_bounded_secret_safe_and_chained(self):
  def timeout(request):raise httpx.ReadTimeout("super-secret-groq-key",request=request)
  p=self.provider(timeout)
  with self.assertRaises(ExternalAPIError) as caught:await p.generate("Return JSON")
  self.assertEqual(self.calls,DEFAULT_RETRY_COUNT);self.assertIsInstance(caught.exception.__cause__,httpx.ReadTimeout);self.assertNotIn("super-secret",str(caught.exception));self.assertTrue(all(c.is_closed for c in self.clients))
