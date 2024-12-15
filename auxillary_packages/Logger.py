import os
import asyncio
import threading
import psutil
from datetime import datetime
from collections import deque

'''Interface for logging errors asynchronously to an error log file'''
class Logger:

    _lock = threading.Lock()
    waitlist_length: int = 0

    def __init__(self, fpath: str, interval: int = 60, check_load: bool = False, max_mem_load: float = 0.8, max_cpu_load: float = 0.8, defer_time: int = 10, max_defer_count: int = 3):
        if max_defer_count < 0 or not isinstance(defer_time, int) or not isinstance(max_defer_count, int) or (max_defer_count * defer_time >= interval):
            raise ValueError("Invalid configurations for defer and regular interval")

        if not os.path.isfile(fpath):
            raise FileNotFoundError("Invalid filepath provided")

        self._event_queue = deque()
        self.fpath = fpath
        self.check_load = check_load
        self.max_cpu_load = max_cpu_load
        self.max_memory_load = max_mem_load
        self.interval = interval

        self.defer_time = defer_time
        self.defer_count = 0
        self.max_defers = max_defer_count

        self.loop = asyncio.new_event_loop()
        self.background_thread = None
        self.start_background_task()

    def start_background_task(self):
        if self.background_thread is None or not self.background_thread.is_alive():
            self.background_thread = threading.Thread(target=self._run_periodically)
            self.background_thread.daemon = True
            self.background_thread.start()

    def _run_periodically(self):
        while True:
            # Schedule the periodic task in the event loop
            self.loop.call_soon_threadsafe(self.loop.create_task, self.dumpEntries())
            asyncio.set_event_loop(self.loop)
            self.loop.run_forever()

    def stop_background_task(self):
        if self.background_thread and self.background_thread.is_alive():
            self.background_thread.join()
        self.loop.close()

    async def dumpEntries(self, entries: int = 10):
        print("called")  # Debug print to check if it's being called
        if not self.check_resources():
            self.defer_count += 1
            if self.defer_count >= self.max_defers:
                deferOverflow = Exception()
                deferOverflow.__setattr__("description", "Failed to dump entries on time, resource usage deemed vulnerable")
                deferOverflow.__setattr__("_additional_info", "The maximum deferral count for this process has been reached. The process has been aborted and rescheduled for the next available time slot.")
                self.addEntryToQueue(deferOverflow)
                self.defer_count = 0

            await self.defer()

        with self._lock:
            with open(self.fpath, "a") as logFile:
                pyFormattedEntry = (f"{self._event_queue.popleft()}\n" for _ in range(min(entries, Logger.waitlist_length)))
                logFile.writelines(pyFormattedEntry)
            Logger.waitlist_length -= min(entries, self.waitlist_length)

    def addEntryToQueue(self, error: Exception, func: str = "N/A", obj: str = "N/A"):
        entry: str = f"{datetime.now()} - {getattr(error, 'description', 'N/A')}. Additional: {getattr(error, '_additional_info', 'None Provided')}. Function: {func}, Class: {obj}\n"
        with self._lock:
            self._event_queue.append(entry)

    def check_resources(self):
        memory_load = psutil.virtual_memory().percent / 100
        cpu_load = psutil.cpu_percent(interval=0.1) / 100
        if cpu_load > self.max_cpu_load or memory_load > self.max_memory_load:
            return False
        return True

    async def defer(self):
        await asyncio.sleep(self.defer_time)
