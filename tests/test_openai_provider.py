from __future__ import annotations
import unittest
import httpx
from src.core.constants import DEFAULT_RETRY_COUNT
from src.core.exceptions import ExternalAPIError
from src.research.providers.openai_provider import OpenAIProvider
class OpenAIRetryTests(unittest.IsolatedAsyncioTestCase):
 def provider(self,handler,key="super-secret-openai-key"):
  self.calls=0;self.clients=[]
  def wrapped(request):self.calls+=1;return handler(request)
  def factory(**kwargs):client=httpx.AsyncClient(transport=httpx.MockTransport(wrapped),**kwargs);self.clients.append(client);return client
  return OpenAIProvider(key,"gpt-4.1-mini",http_client_factory=factory,sleep=lambda _:self.no_sleep())
 async def no_sleep(self):return None
 def error(self,status):return httpx.Response(status,json={"error":{"type":"invalid_request_error"}})
 async def test_deterministic_4xx_are_not_retried(self):
  for status in (400,401,403,404,422):
   with self.subTest(status=status):
    p=self.provider(lambda _,s=status:self.error(s))
    with self.assertRaises(ExternalAPIError) as caught:await p.generate("Return JSON")
    self.assertEqual(self.calls,1);self.assertIsInstance(caught.exception.__cause__,httpx.HTTPStatusError);self.assertNotIn("super-secret",str(caught.exception));self.assertTrue(all(c.is_closed for c in self.clients))
 async def test_retryable_statuses_are_bounded(self):
  for status in (429,500,502,503,504):
   with self.subTest(status=status):
    p=self.provider(lambda _,s=status:self.error(s))
    with self.assertRaises(ExternalAPIError) as caught:await p.generate("Return JSON")
    self.assertEqual(self.calls,DEFAULT_RETRY_COUNT);self.assertIsInstance(caught.exception.__cause__,httpx.HTTPStatusError);self.assertTrue(all(c.is_closed for c in self.clients))
 async def test_timeout_bounded_chained_cleaned_and_secret_safe(self):
  def timeout(request):raise httpx.ReadTimeout("super-secret-openai-key",request=request)
  p=self.provider(timeout)
  with self.assertRaises(ExternalAPIError) as caught:await p.generate("Return JSON")
  self.assertEqual(self.calls,DEFAULT_RETRY_COUNT);self.assertIsInstance(caught.exception.__cause__,httpx.ReadTimeout);self.assertNotIn("super-secret",str(caught.exception));self.assertTrue(all(c.is_closed for c in self.clients))
 async def test_official_responses_output_is_normalized(self):
  p=self.provider(lambda _:httpx.Response(200,json={"id":"resp_1","output":[{"type":"message","content":[{"type":"output_text","text":"{\"answer\":\"Veloura Intimate\"}"}]}]}));text=await p.generate("Return JSON");self.assertIn("Veloura Intimate",text);self.assertEqual(self.calls,1);self.assertTrue(all(c.is_closed for c in self.clients))
