project_name = input("Enter the project name:")
description = input("Enter the project description: ")
installation_steps = input("Enter the installation steps [comma seperated steps]:")
usage = input("Enter the usage steps [comma seperated steps] :")


project_name = project_name.title()

install_list = installation_steps.split(",")
usage_list = usage.split(",")


install_formatted = ""
for step in install_list:
    install_formatted += f"- {step.strip()}\n"


usage_formatted = ""
for step in usage_list:
    usage_formatted += f"- {step.strip()}\n"



readme_content = f"""

{project_name}

## Description
{description}

## Installation

{install_formatted}

## Usage

{usage_formatted}

"""


with open("README.md","w") as f:
    f.write(readme_content)

print("Readme Generated Successfully")