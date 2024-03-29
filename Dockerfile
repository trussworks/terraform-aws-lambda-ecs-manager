FROM amazon/aws-lambda-python:3

ARG MANAGER_VERSION="2.3.0"

# Install build dependencies
RUN pip3 install --no-cache-dir --disable-pip-version-check --progress-bar off 'poetry==1.1.4'

# Install ecs manager
WORKDIR /home/terraform-aws-lambda-ecs-manager-"$MANAGER_VERSION"

COPY README.md ./
COPY poetry.lock ./
COPY pyproject.toml ./
COPY functions ./functions

RUN poetry build && pip3 install --no-cache-dir --disable-pip-version-check dist/functions-"$MANAGER_VERSION"-py3-none-any.whl

CMD ["functions.manager.lambda_handler"]
