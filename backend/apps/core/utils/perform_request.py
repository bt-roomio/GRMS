def with_tenant(request):
    tenant_id = request.user.tenant_id
    data = request.data.copy()
    data["tenant"] = tenant_id
    return data
