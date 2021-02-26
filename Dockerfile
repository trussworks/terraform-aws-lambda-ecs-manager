FROM amazon/aws-lambda-python:3

ARG MANAGER_VERSION="2.1.2"

# Install build dependencies
RUN pip3 install --no-cache-dir --disable-pip-version-check --progress-bar off 'poetry==1.1.4'

# Install ecs manager
WORKDIR /home/terraform-aws-lambda-ecs-manager-"$MANAGER_VERSION"

COPY README.md ./
COPY mypy.ini ./
COPY poetry.lock ./
COPY pyproject.toml ./
COPY pytest.ini ./
COPY setup.cfg ./
COPY functions ./functions

RUN poetry build && pip3 install --no-cache-dir --disable-pip-version-check dist/functions-"$MANAGER_VERSION"-py3-none-any.whl

CMD ["functions.manager.lambda_handler"]
