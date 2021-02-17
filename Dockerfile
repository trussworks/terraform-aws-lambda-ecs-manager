FROM python:3-buster

ARG MANAGER_VERSION="2.1.1"

# Install build dependencies
RUN pip3 install --no-cache-dir --disable-pip-version-check --progress-bar off 'poetry==1.1.4'

# Install ecs manager
WORKDIR /home/
RUN curl --silent --show-error --location https://github.com/trussworks/terraform-aws-lambda-ecs-manager/archive/"$MANAGER_VERSION".zip > manager.zip \
 && unzip manager.zip

WORKDIR /home/terraform-aws-lambda-ecs-manager-"$MANAGER_VERSION"
RUN poetry build && pip3 install --no-cache-dir --disable-pip-version-check dist/functions-"$MANAGER_VERSION"-py3-none-any.whl

ENTRYPOINT ["python3", "-m", "functions.manager"]
