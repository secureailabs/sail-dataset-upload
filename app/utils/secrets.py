# -------------------------------------------------------------------------------
# Engineering
# secrets.py
# -------------------------------------------------------------------------------
"""Get secrets"""
# -------------------------------------------------------------------------------
# Copyright (C) 2022 Secure Ai Labs, Inc. All Rights Reserved.
# Private and Confidential. Internal Use Only.
#     This software contains proprietary information which shall not
#     be reproduced or transferred to other documents and shall not
#     be disclosed to others for any purpose without
#     prior written permission of Secure Ai Labs, Inc.
# -------------------------------------------------------------------------------

import json

initialization_vector = None


def get_secret(secret_name: str) -> str:
    """Get the value of a secret

    :param secret_name: key for the value to be fetched
    :type secret_name: str
    :return: the value for the key if it exists or an exception
    :rtype: str
    """
    global initialization_vector
    if not initialization_vector:
        with open("InitializationVector.json") as file:
            initialization_vector = json.load(file)

    if secret_name not in initialization_vector:
        raise Exception(f"Secret {secret_name} not found")

    return initialization_vector.get(secret_name)
