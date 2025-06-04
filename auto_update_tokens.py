import time
import urllib3
import requests
from core.config import settings

urllib3.disable_warnings()


def update():
    requests.post(
        url=f"{settings.hosting_url}reboot_tokens/",
        params={
            'client_secret': settings.client_secret
        },
        verify=False)


status = True
try:
    update()
    while status:
        time.sleep(3500)
        update()
except KeyboardInterrupt:
    print('Exiting....')
finally:
    print('End App...')
