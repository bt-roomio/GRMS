from django.apps import apps


def dynamic_query(model_name, app_names=None, **filters):
    """
    Dynamically query a model across multiple apps using the specified filters.

    Args:
        model_name (str): Name of the model to query.
        app_names (list): List of app names to search for the model.
        **filters: Field names and values to filter on.

    Returns:
        QuerySet: Resulting queryset after applying filters, or None if model not found.
    """
    # If app_names is not specified, search all installed apps
    if app_names is None:
        app_names = [app.label for app in apps.get_app_configs()]

    # Attempt to find the model in the specified apps
    Model = None
    for app_name in app_names:
        try:
            Model = apps.get_model(app_name, model_name)
            if Model:
                break
        except LookupError:
            continue

    if not Model:
        raise ValueError(f"Model '{model_name}' not found in specified apps: {app_names}")

    # Build and execute the query on the found model
    queryset = Model.objects.filter(**filters)
    return queryset
