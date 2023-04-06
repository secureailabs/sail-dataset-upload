# -------------------------------------------------------------------------------
# Engineering
# async_tasks.py
# -------------------------------------------------------------------------------
"""Run and manage async tasks with fastapi"""
# -------------------------------------------------------------------------------
# Copyright (C) 2022 Secure Ai Labs, Inc. All Rights Reserved.
# Private and Confidential. Internal Use Only.
#     This software contains proprietary information which shall not
#     be reproduced or transferred to other documents and shall not
#     be disclosed to others for any purpose without
#     prior written permission of Secure Ai Labs, Inc.
# -------------------------------------------------------------------------------
import asyncio
from typing import Any, Coroutine

coroutines = set()


def add_async_task(task_function: Coroutine[Any, Any, None]):
    """
    Add a task to the set of coroutines to be run

    :param task_function: the function to be run
    :type task_function: Coroutine[Any, Any, None]
    """
    task = asyncio.create_task(task_function)
    coroutines.add(task)
    task.add_done_callback(coroutines.discard)
