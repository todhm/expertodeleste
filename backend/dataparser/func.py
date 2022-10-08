import logging
import asyncio


logger = logging.getLogger(__name__)

def async_retries(times: int, sleep_time: float = 1.5):
    def func_wrapper(f):
        async def wrapper(*args, **kwargs):
            error_message = ""
            last_error = None
            for current_time in range(kwargs.get('retry_times', times)):
                logger.debug(f'times: {current_time + 1}')
                # noinspection PyBroadException
                try:
                    return await f(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    error_message += str(e)
                    await asyncio.sleep(sleep_time)
                    pass
            raise last_error
        return wrapper
    return func_wrapper