import json
import logging

logger = logging.getLogger("relay")
logging.basicConfig(level=logging.INFO, format="%(message)s")


def emit(event, **fields):
    # Do not send incident bodies, tokens or Mongo connection strings to logs.
    logger.info(json.dumps({"event": event, **fields}))
