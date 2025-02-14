import time
import urllib3
import requests
from core.config import settings

urllib3.disable_warnings()


def update():
    requests.post(
        url=f"https://sporbita-developers.ru/reboot_tokens/",
        params={
            'client_secret': settings.secret
        },
        verify=False)


status = True
try:
    update()
    while status:
        time.sleep(3600)
        update()
except KeyboardInterrupt:
    print('Exiting....')
finally:
    print('End App...')
