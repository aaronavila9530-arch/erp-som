import re
import requests
response=requests.get("https://api-som-fastapi-production-e66d.up.railway.app/som",timeout=30)
response.raise_for_status()
html=response.text
method=re.search(r'<select id="itpPayMethod">(.*?)</select>',html,re.S)
assert method and "HAZEL" not in method.group(1).upper()
for name in ("ITP_BI_BANK_ACCOUNTS","ITP_BI_PAYMENT_METHODS"):
    block=re.search(r"const "+name+r"\s*=\s*\[(.*?)\n\s*\];",html,re.S)
    assert block and "HAZEL" not in block.group(1).upper()
assert 'method === "THIRD_PARTY_HAZEL"' in html, "Historical labels should remain readable"
print("PASS live SOM: Hazel absent from payment method and biweekly bank/method selectors; historical labels retained.")
