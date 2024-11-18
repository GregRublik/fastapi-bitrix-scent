import time
import urllib3
import requests
from config import secret

urllib3.disable_warnings()


def update():
    response = requests.post(url=f"https://sporbita-developers.ru/reboot_tokens/", params={'client_secret': secret},
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
