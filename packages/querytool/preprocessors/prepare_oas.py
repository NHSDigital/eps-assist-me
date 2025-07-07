import requests
import subprocess

oas_url = "https://digital.nhs.uk/restapi/oas/324177"
oas_content = requests.get(oas_url)

with open("./querytool/eps_assist/preprocessors/.eps_oas.json", "w") as f:
    f.write(oas_content.text)

oas_version = oas_content.json()["info"]["version"]

with open("./querytool/eps_assist/docs/eps_oas.version", "w") as f:
    f.write(oas_version)

subprocess.check_output(
    ["widdershins",
     "--expandBody",
     "true",
     "querytool/eps_assist/preprocessors/.eps_oas.json",
     "querytool/eps_assist/docs/eps_output.md"])
