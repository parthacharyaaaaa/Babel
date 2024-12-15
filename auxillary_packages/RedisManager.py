import functools
from typing import Literal
from redis import Redis
import redis.exceptions as RedisExceptions
from redis.typing import ResponseT

class Cache_Manager:
    def __init__(self, host : str, port : int, db : int, startup_mandate : bool = False, error_behavior : Literal["lax", "strict"] = "strict", **kwargs):
        try:
            self._interface = Redis(host, int(port), int(db), kwargs)
            if startup_mandate and not self._interface.ping():
                raise ConnectionError("Redis Connection could not be established")
            elif not (startup_mandate or self._interface.ping()):
                print("\n\n===================WARNING: CACHE_MANAGER INSTANTIATED WITHOUT ACTIVE REDIS SERVER===================\n\n")

        except RedisExceptions.RedisError:
            raise ConnectionError("Failed to access cache banks")
        
        self.err_behavior = error_behavior
    def safe(func):
        @functools.wraps(func)
        def decorated(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except RedisExceptions.ConnectionError as e:
                # Logs for connection-related errors
                print(f"[Redis Error - ConnectionError] Failed to connect to Redis server. Details: {str(e)}")
            except RedisExceptions.TimeoutError as e:
                # Logs for timeout errors
                print(f"[Redis Error - TimeoutError] Redis operation timed out. Details: {str(e)}")
            except RedisExceptions.RedisError as e:
                # Logs for general Redis errors
                print(f"[Redis Error - RedisError] An unexpected Redis error occurred. Details: {str(e)}")
            except Exception as e:
                # Fallback for unexpected issues
                print(f"[Redis Error - Unknown] An unknown error occurred. Details: {str(e)}")

            if args[0].err_behavior == "strict":
                e = RedisExceptions.RedisError()
                e.__setattr__("description", "Raising error, error_policy = strict")
                raise e

            return None 
        return decorated

    @safe
    def setex(self, name : str | int, exp : int, value : str | int) -> None:
        self._interface.execute_command("SETEX", name, exp, value)

    @safe
    def delete(self, *names) -> None:
        self._interface.execute_command("DELETE", names)

    @safe
    def get(self, name : str) -> ResponseT | None:
        result = self._interface.execute_command("GET", name)
        if result != None:
            return result.decode("utf-8") if isinstance(result, bytes) else result
        return None

    @safe
    def lpush(self, name : str, val : str) -> None:
        self._interface.lpush(name, val)

    @safe
    def rpop(self, name : str, count : int = 1):
        self._interface.rpop(name, int(count))

    @safe
    def lindex(self, name : str, index : int) -> ResponseT | None:
        return self._interface.execute_command("LINDEX", name, index)
    
    @safe
    def llen(self, name : str) -> int:
        return self._interface.execute_command("LLEN", name)