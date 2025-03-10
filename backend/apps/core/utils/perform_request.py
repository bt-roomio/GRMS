def with_tenant(request, **kwargs):
    tenant_id = request.user.tenant_id
    data = request.data.copy()
    data["tenant"] = tenant_id
    for key, value in kwargs.items():
        data[key] = value
    return data
