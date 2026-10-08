FROM public.ecr.aws/lambda/python:3.12
COPY requirements.lock ${LAMBDA_TASK_ROOT}/requirements.lock
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.lock
COPY backend/relay ${LAMBDA_TASK_ROOT}/relay
CMD ["relay.lambda_handlers.api"]
