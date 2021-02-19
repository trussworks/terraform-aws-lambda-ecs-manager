FROM amazon/aws-lambda-python:3

ARG MANAGER_VERSION="2.1.2"

# Install build dependencies
RUN pip3 install --no-cache-dir --disable-pip-version-check --progress-bar off 'poetry==1.1.4'

# Install ecs manager
WORKDIR /home/
COPY . .

RUN poetry build && pip3 install --no-cache-dir --disable-pip-version-check dist/functions-"$MANAGER_VERSION"-py3-none-any.whl

CMD ["functions.manager"]
