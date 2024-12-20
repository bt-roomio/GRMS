def response(data, cmd_id, error_code=0, error_msg=None):
    return {
        "subscription_id": cmd_id,
        "error_code": error_code,
        "error_msg": error_msg,
        "data": data,
    }
