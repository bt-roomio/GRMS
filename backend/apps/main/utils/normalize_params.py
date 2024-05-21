from django.http.request import QueryDict


def normalize_params(query_dict):
    normalized_dict = {}

    for key in query_dict.keys():
        normalized_key = key.rstrip("[]")
        if normalized_key in normalized_dict:
            normalized_dict[normalized_key].extend(query_dict.getlist(key))
        else:
            normalized_dict[normalized_key] = query_dict.getlist(key)

    return normalized_dict
