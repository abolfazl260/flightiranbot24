import requests

# لیست پروکسی‌ها (IP و پورت)
proxy_list = [
    "50.174.7.159:80",
    "50.207.199.87:80",
    "32.223.6.94:80",
    "13.38.153.36:80",
    "13.36.104.85:80",
    "13.36.113.81:3128",
    "44.215.100.135:8118",
    "50.207.199.80:80",
    "50.207.199.83:80",
    "50.174.7.153:80",
    # بقیه پروکسی‌ها را اینجا اضافه کنید
]

# آدرس وب‌سایت مورد نظر
target_url = "https://call.tgju.org/ajax.json"

# هدرهای درخواست
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.tgju.org/",
}

# فایل برای ذخیره نتایج
output_file = "proxy_results.txt"

# تابع برای تست پروکسی
def test_proxy(proxy):
    try:
        proxies = {
            "http": f"http://{proxy}",
            "https": f"http://{proxy}",
        }
        response = requests.get(target_url, headers=headers, proxies=proxies, timeout=10)
        if response.status_code == 200:
            return True, None  # پروکسی سالم است
        else:
            return False, f"Status Code: {response.status_code}"  # پروکسی غیرسالم است
    except requests.exceptions.RequestException as e:
        return False, str(e)  # پروکسی غیرسالم است

# بررسی تمام پروکسی‌ها
results = []
for proxy in proxy_list:
    is_valid, error_message = test_proxy(proxy)
    if is_valid:
        result = f"✅ پروکسی {proxy} سالم است."
    else:
        result = f"❌ پروکسی {proxy} غیرسالم است. خطا: {error_message}"
    results.append(result)
    print(result)  # نمایش نتیجه در کنسول

# ذخیره نتایج در فایل
with open(output_file, "w", encoding="utf-8") as file:
    for result in results:
        file.write(result + "\n")

print(f"نتایج در فایل {output_file} ذخیره شد.")